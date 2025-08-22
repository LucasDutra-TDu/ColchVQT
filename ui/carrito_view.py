from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from logic import carrito
from logic.constants import METODOS_PAGO, ESTILOS


carrito_window_instance = None

def abrir_carrito():
    from ui.carrito_view import CarritoWindow  # import perezoso para evitar ciclos
    global carrito_window_instance
    if carrito_window_instance is None or not carrito_window_instance.isVisible():
        carrito_window_instance = CarritoWindow()
        carrito_window_instance.show()
    else:
        carrito_window_instance.actualizar_tabla()  # <- refresca datos
        carrito_window_instance.raise_()
        carrito_window_instance.activateWindow()


def agregar_producto_y_abrir(producto_dict, cantidad: int = 1):
    """Helper que usa la lógica central para agregar producto y abrir carrito."""
    carrito.agregar_y_abrir(producto_dict, abrir_carrito, cantidad)


class CarritoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Carrito de Compras")
        self.resize(750, 500)

        # Layout principal
        layout = QVBoxLayout(self)

        # Selector de método de pago
        metodo_layout = QHBoxLayout()
        metodo_label = QLabel("Método de pago:")
        metodo_label.setStyleSheet(ESTILOS.get("label", ""))
        self.metodo_combo = QComboBox()
        self.metodo_combo.addItems(METODOS_PAGO)
        self.metodo_combo.setCurrentText(carrito.obtener_metodo_pago())
        self.metodo_combo.currentTextChanged.connect(self.cambiar_metodo_pago)
        metodo_layout.addWidget(metodo_label)
        metodo_layout.addWidget(self.metodo_combo)
        layout.addLayout(metodo_layout)

        # Tabla de productos
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Código", "Modelo", "Precio unitario", "Cantidad", "Subtotal", "Acciones"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Total + botón finalizar
        bottom_layout = QHBoxLayout()
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet(ESTILOS.get("total_label", ""))
        bottom_layout.addWidget(self.total_label)

        self.finalizar_btn = QPushButton("Finalizar compra")
        self.finalizar_btn.setStyleSheet(ESTILOS.get("boton", ""))
        self.finalizar_btn.clicked.connect(self.finalizar_compra)
        bottom_layout.addWidget(self.finalizar_btn, alignment=Qt.AlignRight)
        layout.addLayout(bottom_layout)

        self.actualizar_tabla()

    def actualizar_tabla(self):
        items = carrito.obtener_items()
        metodo = carrito.obtener_metodo_pago()
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            codigo = QTableWidgetItem(str(item["CÓDIGO"]))
            codigo.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            modelo = QTableWidgetItem(str(item["MODELO"]))
            modelo.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            precio_val = item.get(metodo, 0)
            precio = QTableWidgetItem(f"${precio_val:.2f}")
            precio.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            spin = QSpinBox()
            spin.setMinimum(0)
            spin.setValue(item["cantidad"])
            spin.valueChanged.connect(
                lambda val, codigo=item["CÓDIGO"]: self.cambiar_cantidad(codigo, val)
            )

            subtotal_val = precio_val * item["cantidad"]
            subtotal = QTableWidgetItem(f"${subtotal_val:.2f}")
            subtotal.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            btn_eliminar = QPushButton()
            btn_eliminar.setIcon(QIcon.fromTheme("edit-delete"))  # ícono de tacho de basura
            btn_eliminar.setToolTip("Eliminar producto")
            btn_eliminar.setStyleSheet(ESTILOS.get("boton_eliminar", ""))
            btn_eliminar.clicked.connect(
                lambda _, codigo=item["CÓDIGO"]: self.eliminar_producto(codigo)
            )

            self.table.setItem(row, 0, codigo)
            self.table.setItem(row, 1, modelo)
            self.table.setItem(row, 2, precio)
            self.table.setCellWidget(row, 3, spin)
            self.table.setItem(row, 4, subtotal)
            self.table.setCellWidget(row, 5, btn_eliminar)

        self.actualizar_total()

    def actualizar_total(self):
        total = carrito.obtener_total()
        self.total_label.setText(f"Total: ${total:.2f}")

    def cambiar_cantidad(self, codigo, cantidad):
        carrito.actualizar_cantidad(codigo, cantidad)
        self.actualizar_tabla()

    def cambiar_metodo_pago(self, metodo):
        carrito.set_metodo_pago(metodo)
        self.actualizar_tabla()

    def eliminar_producto(self, codigo):
        carrito.eliminar_producto(codigo)
        self.actualizar_tabla()

    def finalizar_compra(self):
        items = carrito.obtener_items()
        if not items:
            QMessageBox.information(self, "Carrito vacío", "No hay productos en el carrito.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar compra",
            "¿Desea confirmar la compra?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            resultado = carrito.finalizar_compra()
            if resultado is None:
                QMessageBox.warning(self, "Error", "No se pudo finalizar la compra.")
                return

            resumen = "\n".join(
                f"{i['CÓDIGO']} - {i['MODELO']} x{i['cantidad']}" for i in resultado["items"]
            )
            QMessageBox.information(
                self,
                "Compra confirmada",
                f"Fecha: {resultado['fecha']}\n\n"
                f"Productos:\n{resumen}\n\n"
                f"TOTAL: ${resultado['total']:.2f}\n\nFactura guardada en DB."
            )

            self.actualizar_tabla()

