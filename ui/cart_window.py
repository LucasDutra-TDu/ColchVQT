from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QComboBox, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# Imports de Lógica y Constantes
from logic.constants import METODOS_PAGO, ESTILOS
from logic.cart_service import CartService
from logic.facturas_db_handler import registrar_venta
from logic.financiero import format_currency, calcular_precio_final

class CartWindow(QWidget):
    def __init__(self, cart_service: CartService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cart_service = cart_service
        
        # Configuración de Ventana
        self.setWindowTitle("Carrito de Compras")
        self.resize(800, 600)
        
        # UI Setup
        self._init_ui()
        
        # Carga inicial de datos
        self.actualizar_tabla()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- 1. Header: Método de Pago ---
        metodo_layout = QHBoxLayout()
        metodo_label = QLabel("Método de pago:")
        metodo_label.setStyleSheet(ESTILOS.get("label", ""))
        
        self.metodo_combo = QComboBox()
        self.metodo_combo.addItems(METODOS_PAGO)
        self.metodo_combo.setCurrentText(self.cart_service.get_metodo_pago())
        self.metodo_combo.currentTextChanged.connect(self._handle_cambio_metodo)
        
        metodo_layout.addWidget(metodo_label)
        metodo_layout.addWidget(self.metodo_combo)
        metodo_layout.addStretch() # Empujar a la izquierda
        layout.addLayout(metodo_layout)

        # --- 2. Tabla de Productos ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Código", "Modelo", "Precio Unit.", "Cantidad", "Subtotal", "Acciones"
        ])
        
        # Ajuste de columnas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Modelo elástico
        layout.addWidget(self.table)

        # --- 3. Footer: Totales y Acciones ---
        bottom_layout = QHBoxLayout()
        
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet(ESTILOS.get("total_label", "font-size: 18px; font-weight: bold;"))
        bottom_layout.addWidget(self.total_label)

        self.btn_finalizar = QPushButton("Finalizar Compra")
        self.btn_finalizar.setStyleSheet(ESTILOS.get("boton", "background-color: #4CAF50; color: white; padding: 10px;"))
        self.btn_finalizar.clicked.connect(self._handle_finalizar_compra)
        bottom_layout.addWidget(self.btn_finalizar, alignment=Qt.AlignRight)
        
        layout.addLayout(bottom_layout)

    def actualizar_tabla(self):
        items = self.cart_service.obtener_items()
        metodo_actual = self.cart_service.get_metodo_pago()
        
        self.table.setRowCount(len(items))
        self.table.setSortingEnabled(False)

        for row, item in enumerate(items):
            # Datos Base (Aseguramos String)
            codigo = str(item.get("CÓDIGO", ""))
            modelo = str(item.get("MODELO", "Desconocido"))
            cantidad = int(item.get("cantidad", 1))
            
            # --- CORRECCIÓN BUG PRECIO $0 ---
            # 1. Intentamos obtener precio directo (ej: si existe columna "Tarjeta")
            precio_unitario = float(item.get(metodo_actual, 0))
            
            # 2. Si es 0 (ej: Crédito Casa), calculamos desde el Base
            if precio_unitario == 0:
                precio_base = float(item.get("EFECTIVO/TRANSF", 0))
                # Asumimos 1 cuota para mostrar el precio unitario base del método
                precio_unitario = calcular_precio_final(precio_base, metodo_actual, cuotas=1)

            subtotal = precio_unitario * cantidad
            # --------------------------------

            # Widgets
            self.table.setItem(row, 0, QTableWidgetItem(codigo))
            self.table.setItem(row, 1, QTableWidgetItem(modelo))
            self.table.setItem(row, 2, QTableWidgetItem(format_currency(precio_unitario)))
            
            # SpinBox Cantidad
            spin = QSpinBox()
            spin.setRange(1, 999)
            spin.setValue(cantidad)
            # Desconectamos señales previas por seguridad (aunque al recrear es nuevo)
            spin.valueChanged.connect(lambda val, c=codigo: self._handle_cambio_cantidad(c, val))
            self.table.setCellWidget(row, 3, spin)
            
            # Subtotal
            self.table.setItem(row, 4, QTableWidgetItem(format_currency(subtotal)))
            
            # Botón Eliminar
            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setStyleSheet("color: red; font-weight: bold;")
            btn_eliminar.setFixedWidth(40)
            btn_eliminar.clicked.connect(lambda _, c=codigo: self._handle_eliminar(c))
            
            # Contenedor centrado para el botón
            widget_btn = QWidget()
            layout_btn = QHBoxLayout(widget_btn)
            layout_btn.setContentsMargins(0,0,0,0)
            layout_btn.setAlignment(Qt.AlignCenter)
            layout_btn.addWidget(btn_eliminar)
            self.table.setCellWidget(row, 5, widget_btn)

        self._actualizar_total_visual()

    def _actualizar_total_visual(self):
        total = self.cart_service.obtener_total()
        self.total_label.setText(f"Total: {format_currency(total)}")

    # --- Manejadores de Eventos (Controller Logic) ---

    def _handle_cambio_metodo(self, metodo: str):
        self.cart_service.set_metodo_pago(metodo)
        self.actualizar_tabla()

    def _handle_cambio_cantidad(self, codigo: str, cantidad: int):
        self.cart_service.actualizar_cantidad(codigo, cantidad)
        # Solo actualizamos totales para no redibujar toda la tabla y perder foco
        # Pero si cambiamos lógica compleja, mejor redibujar todo:
        self.actualizar_tabla()

    def _handle_eliminar(self, codigo: str):
        self.cart_service.eliminar_producto(codigo)
        self.actualizar_tabla()

    def _handle_finalizar_compra(self):
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