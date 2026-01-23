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
from logic.credits_service import registrar_plan_credito
from logic.pdf_service import generar_contrato_pdf, generar_desglose_pdf

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
            cant = int(item.get("cantidad", 1))
            
            # --- LÓGICA DE PRECIO UNITARIO UNIFICADA ---
            # 1. Obtenemos el Precio Base (Efectivo)
            p_base = float(item.get("EFECTIVO/TRANSF", 0))
            if p_base == 0: 
                p_base = float(item.get("PRECIO", 0))

            # 2. Calculamos el Precio Unitario según el método
            precio_unitario = 0
            
            if metodo_actual == "Crédito de la Casa":
                # Usamos la misma función financiera que usamos para el contrato
                plan_item = calcular_plan_credito(p_base, cuotas)
                # El precio unitario a mostrar es el valor financiado dividido cantidad
                # O mejor: El precio final financiado unitario
                precio_unitario = plan_item['precio_final'] # Esto ya incluye interés y redondeo
            
            elif "Tarjeta" in metodo_actual:
                 # Intentamos buscar columna específica de tarjeta
                 precio_unitario = float(item.get("DEBIT/CREDIT", 0))
                 # Si no tiene columna tarjeta, quizás quieras aplicar un recargo fijo o usar base
                 if precio_unitario == 0:
                     precio_unitario = p_base # O aplicar recargo aquí si tu negocio lo requiere

            else:
                # Efectivo
                precio_unitario = p_base

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
        # 1. Obtenemos el total BASE (Efectivo) del carrito
        # Truco: forzamos obtener el total como si fuera efectivo para tener la base limpia
        items = self.cart_service.obtener_items()
        total_base = sum(float(i.get("EFECTIVO/TRANSF", 0)) * i.get("cantidad", 1) for i in items)
        
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
        
        elif "Tarjeta" in metodo:
             # Si tu lógica de tarjeta es precio de lista simple:
             total_tarjeta = sum(float(i.get("DEBIT/CREDIT", 0)) * i.get("cantidad", 1) for i in items)
             texto_total = f"Total Lista: {format_currency(total_tarjeta)}"
             self.plan_credito_actual = None
             
        else:
            texto_total = f"Total Contado: {format_currency(total_base)}"
            self.plan_credito_actual = None

        self.lbl_total.setText(texto_total)

    def _handle_finalizar(self):
        if self.cart_service.get_count() == 0: return

        metodo = self.combo_metodo.currentText()
        cliente_data = {}
        
        # 1. Si es Crédito, pedir datos
        if metodo == "Crédito de la Casa":
            dlg = ClienteFormDialog(self)
            if dlg.exec() == QDialog.Accepted:
                cliente_data = dlg.datos
            else:
                return # Cancelado por usuario

        # 2. Confirmación
        confirm = QMessageBox.question(self, "Confirmar", "¿Finalizar venta?", QMessageBox.Yes|QMessageBox.No)
        if confirm != QMessageBox.Yes: return

        try:
            # 3. Guardar Venta (Factura General)
            # Preparamos items. Si es crédito, el precio unitario final es el financiado prorrateado
            items_checkout = self.cart_service.preparar_checkout()
            
            if metodo == "Crédito de la Casa" and self.plan_credito_actual:
                total_venta = self.plan_credito_actual['precio_final']
                # Ajustar precios unitarios en los items para que coincidan con el total financiado
                # (Simplificación: guardamos el item con su precio base, pero la factura con el total financiado)
            else:
                # Recalcular total real basado en items_checkout
                total_venta = sum(i['precio_venta_final'] * i['cantidad'] for i in items_checkout)

            factura_id = registrar_venta(items_checkout, metodo, total_venta)

            # 4. Si es Crédito: Generar Contratos y Registrar Deuda
            if metodo == "Crédito de la Casa":
                # A. Registrar en DB Créditos
                registrar_plan_credito(factura_id, cliente_data, self.plan_credito_actual)
                
                # B. Generar PDFs
                path_contrato = generar_contrato_pdf(cliente_data, items_checkout, self.plan_credito_actual)
                path_desglose = generar_desglose_pdf(cliente_data, self.plan_credito_actual)
                
                QMessageBox.information(self, "Éxito", 
                    f"Venta Crédito Registrada.\n\nDocumentos generados en:\n{path_contrato}\n{path_desglose}")
                
                # Intentar abrir carpeta
                os.startfile(os.path.dirname(path_contrato))
            
            else:
                QMessageBox.information(self, "Éxito", "Venta registrada correctamente.")

            self.cart_service.limpiar_carrito()
            self.close()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Fallo al procesar: {e}")
        """Orquesta la transacción final."""
        if self.cart_service.get_count() == 0:
            QMessageBox.warning(self, "Carrito Vacío", "No hay productos para facturar.")
            return

        # 1. Confirmación
        total = self.cart_service.obtener_total()
        resp = QMessageBox.question(
            self, "Confirmar Compra", 
            f"¿Desea finalizar la venta por un total de {format_currency(total)}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if resp != QMessageBox.Yes:
            return

        try:
            # 2. Preparación de Datos (Usando el nuevo método del servicio)
            items_checkout = self.cart_service.preparar_checkout()
            metodo = self.cart_service.get_metodo_pago()
            
            # 3. Persistencia (Invoice Service)
            factura_id = registrar_venta(items_checkout, metodo, total)
            
            # 4. Limpieza y Feedback
            self.cart_service.limpiar_carrito()
            self.actualizar_tabla()
            
            QMessageBox.information(
                self, "Venta Exitosa", 
                f"La venta ha sido registrada correctamente.\nID Factura: #{factura_id}"
            )
            # Opcional: Cerrar ventana
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error de Transacción", f"No se pudo registrar la venta:\n{e}")