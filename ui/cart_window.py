from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QComboBox, QMessageBox, 
    QHeaderView, QDialog, QLineEdit, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import os # Para abrir el PDF automáticamente

# Imports Lógica
from logic.constants import METODOS_PAGO, ESTILOS, TASA_INTERES_MENSUAL
from logic.cart_service import CartService
from logic.facturas_db_handler import registrar_venta
from logic.financiero import format_currency, calcular_plan_credito
from logic.credits_service import registrar_venta_a_credito
from logic.pdf_service import generar_documentacion_credito
from logic.stock_service import procesar_descuento_por_venta
from logic.log_service import log_error
from logic.pricing_service import encontrar_precio_base, obtener_precio_unitario

# --- Diálogo para pedir Datos del Cliente ---
class ClienteFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datos del Cliente - Crédito")
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.inp_nombre = QLineEdit()
        self.inp_dni = QLineEdit()
        self.inp_direccion = QLineEdit()
        self.inp_telefono = QLineEdit()
        
        form.addRow("Nombre Completo:", self.inp_nombre)
        form.addRow("DNI:", self.inp_dni)
        form.addRow("Domicilio:", self.inp_direccion)
        form.addRow("Teléfono:", self.inp_telefono)
        
        layout.addLayout(form)
        
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.validar)
        self.btn_box.rejected.connect(self.reject)
        layout.addWidget(self.btn_box)
        
        self.datos = {}

    def validar(self):
        if not self.inp_nombre.text() or not self.inp_dni.text():
            QMessageBox.warning(self, "Datos Faltantes", "Nombre y DNI son obligatorios.")
            return
        
        self.datos = {
            "nombre": self.inp_nombre.text(),
            "dni": self.inp_dni.text(),
            "direccion": self.inp_direccion.text(),
            "telefono": self.inp_telefono.text()
        }
        self.accept()

# --- Ventana del Carrito ---
class CartWindow(QWidget):
    def __init__(self, cart_service: CartService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cart_service = cart_service
        self.plan_credito_actual = None # Cache del cálculo
        
        self.setWindowTitle("Carrito de Compras")
        self.resize(900, 600)
        self._init_ui()
        self.actualizar_tabla()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Header: Método y Cuotas
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # Selector Método
        top_layout.addWidget(QLabel("Método de Pago:"))
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(METODOS_PAGO)
        self.combo_metodo.setCurrentText(self.cart_service.get_metodo_pago())
        self.combo_metodo.currentTextChanged.connect(self._handle_cambio_metodo)
        top_layout.addWidget(self.combo_metodo)

        # Selector Cuotas (Oculto por defecto)
        self.container_cuotas = QWidget()
        l_cuotas = QHBoxLayout(self.container_cuotas)
        l_cuotas.setContentsMargins(0,0,0,0)
        l_cuotas.addWidget(QLabel("Cuotas (3-12):"))
        self.spin_cuotas = QSpinBox()
        self.spin_cuotas.setRange(3, 12)
        self.spin_cuotas.setValue(3)
        self.spin_cuotas.valueChanged.connect(self.actualizar_tabla)
        l_cuotas.addWidget(self.spin_cuotas)
        
        # Etiqueta de Interés
        self.lbl_interes_info = QLabel("")
        self.lbl_interes_info.setStyleSheet("color: #d35400; font-weight: bold; margin-left: 10px;")
        l_cuotas.addWidget(self.lbl_interes_info)
        
        top_layout.addWidget(self.container_cuotas)
        top_layout.addStretch()
        
        layout.addWidget(top_panel)

        # 2. Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Código", "Modelo", "Precio Base", "Cantidad", "Subtotal", "Borrar"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 3. Footer
        foot_layout = QHBoxLayout()
        self.lbl_total = QLabel("Total: $0")
        self.lbl_total.setStyleSheet(ESTILOS.get("total_label", "font-size: 18px; font-weight: bold;"))
        
        btn_finalizar = QPushButton("Confirmar Compra")
        btn_finalizar.setStyleSheet(ESTILOS.get("boton", "background-color: green; color: white; padding: 10px;"))
        btn_finalizar.clicked.connect(self._handle_finalizar)

        foot_layout.addWidget(self.lbl_total)
        foot_layout.addStretch()
        foot_layout.addWidget(btn_finalizar)
        layout.addLayout(foot_layout)

        # Estado inicial UI
        self._actualizar_visibilidad_cuotas()

    def _actualizar_visibilidad_cuotas(self):
        es_credito = self.combo_metodo.currentText() == "Crédito de la Casa"
        self.container_cuotas.setVisible(es_credito)
        self._recalcular_totales()

    def _handle_cambio_metodo(self, metodo):
        self.cart_service.set_metodo_pago(metodo)
        self._actualizar_visibilidad_cuotas()
        self.actualizar_tabla()

    def actualizar_tabla(self):
        items = self.cart_service.obtener_items()
        metodo_actual = self.cart_service.get_metodo_pago()
        
        # Obtenemos cuotas actuales (si aplica)
        cuotas = 1
        if metodo_actual == "Crédito de la Casa":
            cuotas = self.spin_cuotas.value()

        self.table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            codigo = str(item.get("CÓDIGO", ""))
            modelo = str(item.get("MODELO", ""))
            medida = item.get("MEDIDA (LARG-ANCH-ESP)", item.get("MEDIDA", ""))
            if medida and str(medida).lower() not in ["", "nan", "-"]:
                modelo += f" (Medida: {medida})"
            cant = int(item.get("cantidad", 1))
            
            # --- LÓGICA DE PRECIO UNITARIO UNIFICADA ---
            # Detección robusta compartida con cart_service.py y views.py
            # (ver logic/pricing_service.py -- Fase 3 de la auditoría).
            p_base = encontrar_precio_base(item)

            if metodo_actual == "Crédito de la Casa":
                # Usamos la misma función financiera que usamos para el contrato
                plan_item = calcular_plan_credito(p_base, cuotas)
                # El precio unitario a mostrar es el valor financiado (ya incluye interés y redondeo)
                precio_unitario = plan_item['precio_final']
            else:
                precio_unitario = obtener_precio_unitario(item, p_base, metodo_actual)
            # -------------------------------------------

            self.table.setItem(row, 0, QTableWidgetItem(codigo))
            self.table.setItem(row, 1, QTableWidgetItem(modelo))
            
            # Mostramos el Precio Unitario (Financiado si corresponde)
            self.table.setItem(row, 2, QTableWidgetItem(format_currency(precio_unitario)))
            
            spin = QSpinBox()
            spin.setRange(1, 999)
            spin.setValue(cant)
            # Usamos closure para evitar problemas de referencia
            spin.valueChanged.connect(lambda v, c=codigo: self.cart_service.actualizar_cantidad(c, v))
            self.table.setCellWidget(row, 3, spin)
            
            # Subtotal
            subtotal = precio_unitario * cant
            self.table.setItem(row, 4, QTableWidgetItem(format_currency(subtotal)))
            
            btn_del = QPushButton("X")
            btn_del.setStyleSheet("color: red; font-weight: bold;")
            btn_del.clicked.connect(lambda _, c=codigo: self.cart_service.eliminar_producto(c))
            self.table.setCellWidget(row, 5, btn_del)

        # Finalmente recalculamos el total general (etiqueta inferior)
        self._recalcular_totales()

    def _recalcular_totales(self):
        """Calcula el total aplicando recargos si es Crédito."""
        # 1. Obtenemos el total BASE (Efectivo) del carrito.
        # Detección robusta compartida con cart_service.py y views.py (ver
        # logic/pricing_service.py -- Fase 3 de la auditoría). ESTE es el
        # punto que antes generaba ventas a Crédito de la Casa registradas
        # con base $0 si el producto no tenía la columna exacta
        # EFECTIVO/TRANSF (hallazgo de la auditoría): total_base alimenta
        # directamente self.plan_credito_actual, que es lo que se guarda
        # como total de la venta en _handle_finalizar.
        items = self.cart_service.obtener_items()
        total_base = sum(encontrar_precio_base(i) * i.get("cantidad", 1) for i in items)

        metodo = self.combo_metodo.currentText()
        texto_total = ""

        if metodo == "Crédito de la Casa":
            cuotas = self.spin_cuotas.value()
            # Usamos logic/financiero.py
            self.plan_credito_actual = calcular_plan_credito(total_base, cuotas)

            total_final = self.plan_credito_actual['precio_final']
            v_cuota = self.plan_credito_actual['valor_cuota']

            # Actualizar label informativo
            interes_pct = int(TASA_INTERES_MENSUAL * cuotas * 100)
            self.lbl_interes_info.setText(f"+{interes_pct}% Interés")

            texto_total = f"Total Financiado: {format_currency(total_final)} ({cuotas} x {format_currency(v_cuota)})"

        elif "6 Cuotas" in metodo or "Tarjeta" in metodo:
             # Mismo detector que usa cada fila de la tabla (ver actualizar_tabla).
             total_metodo = sum(
                 obtener_precio_unitario(i, encontrar_precio_base(i), metodo) * i.get("cantidad", 1)
                 for i in items
             )
             etiqueta = "Total 6 Cuotas Fijas" if "6 Cuotas" in metodo else "Total Lista (Tarjeta)"
             texto_total = f"{etiqueta}: {format_currency(total_metodo)}"
             self.plan_credito_actual = None

        else:
            texto_total = f"Total Contado: {format_currency(total_base)}"
            self.plan_credito_actual = None

        self.lbl_total.setText(texto_total)

    def _handle_finalizar(self):
        # 1. Validación inicial
        if self.cart_service.get_count() == 0:
            QMessageBox.warning(self, "Carrito Vacío", "No hay productos para facturar.")
            return

        # Evitar doble click accidental
        sender = self.sender()
        if sender: sender.setEnabled(False)

        try:
            metodo = self.combo_metodo.currentText()
            cliente_data = {}
            
            # --- Recolección de Datos ---
            if metodo == "Crédito de la Casa":
                dlg = ClienteFormDialog(self)
                if dlg.exec() == QDialog.Accepted:
                    cliente_data = dlg.datos
                else:
                    # Si cancela el dialog, reactivamos botón
                    if sender: sender.setEnabled(True) 
                    return 

            # --- Construcción del Resumen ---
            items_checkout = self.cart_service.preparar_checkout()
            
            detalle_msg = f"<b>Método:</b> {metodo}<br><hr>"
            total_calc = 0
            
            if metodo == "Crédito de la Casa" and self.plan_credito_actual:
                 plan = self.plan_credito_actual
                 for item in items_checkout:
                     mod = item['MODELO']
                     med = item.get("MEDIDA (LARG-ANCH-ESP)", item.get("MEDIDA", ""))
                     if med and str(med).lower() not in ["", "nan", "-"]:
                         mod += f" (Medida: {med})"
                     detalle_msg += f"• {item['cantidad']} x {mod}<br>"
                 detalle_msg += f"<hr><b>Plan:</b> {plan['num_cuotas']} cuotas de {format_currency(plan['valor_cuota'])}<br>"
                 detalle_msg += f"<b style='font-size:14px'>Total Financiado: {format_currency(plan['precio_final'])}</b>"
                 total_venta = plan['precio_final']
            
            else:
                for item in items_checkout:
                    p_unit = item['precio_venta_final']
                    subtot = p_unit * item['cantidad']
                    total_calc += subtot
                    mod = item['MODELO']
                    med = item.get("MEDIDA (LARG-ANCH-ESP)", item.get("MEDIDA", ""))
                    if med and str(med).lower() not in ["", "nan", "-"]:
                         mod += f" (Medida: {med})"
                    detalle_msg += f"• {item['cantidad']} x {mod} ({format_currency(subtot)})<br>"
                
                detalle_msg += f"<hr><b style='font-size:14px'>Total a Pagar: {format_currency(total_calc)}</b>"
                total_venta = total_calc

            # --- Confirmación ---
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirmar Venta")
            msg_box.setText("<h3>¿Confirmar la operación?</h3>")
            msg_box.setInformativeText(detalle_msg)
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            if msg_box.exec() != QMessageBox.Yes:
                # Si dice que NO, reactivamos botón
                if sender: sender.setEnabled(True)
                return

            # --- Procesamiento ---
            if metodo == "Crédito de la Casa":
                # Factura + plan de crédito en UNA SOLA transacción atómica:
                # si falla el plan de cuotas, la factura tampoco queda
                # registrada. Antes podía quedar una factura de "Crédito de
                # la Casa" confirmada sin cliente ni cronograma asociado si
                # el segundo paso fallaba después de que el primero ya
                # hubiera hecho commit.
                factura_id, _credito_id = registrar_venta_a_credito(
                    items_checkout, metodo, total_venta, cliente_data, self.plan_credito_actual
                )
            else:
                factura_id = registrar_venta(items_checkout, metodo, total_venta)

            # ¡NUEVA LÓGICA DE STOCK! Descontamos lo vendido.
            # Se hace DESPUÉS de que la venta (y el crédito, si aplica) ya
            # están confirmados. Envolvemos en un try-except para que un
            # fallo en stock no arruine la venta ya registrada, pero
            # avisamos explícitamente para que se pueda reconciliar a mano.
            stock_ok = True
            try:
                procesar_descuento_por_venta(items_checkout, factura_id)
            except Exception as e:
                stock_ok = False
                # Antes esto se perdía en un print() invisible en el .exe
                # --windowed: ahora queda registrado en data/app.log Y se
                # avisa explícitamente más abajo.
                log_error(f"Fallo al descontar stock tras venta (Factura #{factura_id}): {e}")

            if metodo == "Crédito de la Casa":
                path_contrato = generar_documentacion_credito(cliente_data, items_checkout, self.plan_credito_actual)

                QMessageBox.information(self, "Éxito",
                    f"Venta Crédito Registrada.\n\nDocumentos generados en:\n{path_contrato}")
                try:
                    os.startfile(os.path.dirname(path_contrato))
                except:
                    pass
            else:
                QMessageBox.information(self, "Éxito", "Venta registrada correctamente.")

            if not stock_ok:
                QMessageBox.warning(
                    self, "Atención: stock no descontado",
                    f"La venta (Factura #{factura_id}) se registró correctamente,\n"
                    "pero no se pudo descontar el stock automáticamente.\n\n"
                    "Revisá y ajustá el stock de estos productos a mano desde\n"
                    "'📦 Inventario / Stock'. El detalle del error quedó guardado\n"
                    "en el log de la aplicación."
                )

            # Limpieza FINAL
            self.cart_service.limpiar_carrito()
            
            # --- CORRECCIÓN AQUÍ: Reactivar botón antes de cerrar ---
            if sender: sender.setEnabled(True) 
            # --------------------------------------------------------
            
            self.close()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error Crítico", f"Fallo al procesar: {e}")
            # En caso de error, siempre reactivar
            if sender: sender.setEnabled(True)