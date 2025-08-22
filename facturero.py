from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QPushButton, QLineEdit, QLabel, QDialog, QDialogButtonBox,
    QFormLayout, QDateEdit, QMessageBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QDate
import sys

# Importar lógica de persistencia
from logic import facturas


def formato_moneda(valor: int) -> str:
    return "$" + format(valor, ",").replace(",", ".")


class DetalleFacturaDialog(QDialog):
    def __init__(self, factura, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalle Factura #{factura['id']}")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        ganancia_total = 0

        for item in factura.get("items", []):
            descripcion = item.get("descripcion", "")
            cantidad = int(item.get("cantidad", 1))
            precio = int(float(item.get("precio", 0)))
            costo = int(float(item.get("costo", 0)))

            ganancia_item = (precio - costo) * cantidad
            ganancia_total += ganancia_item

            detalles = [
                f"Cantidad: {cantidad}",
                f"Precio: {formato_moneda(precio)}",
                f"Costo: {formato_moneda(costo)}",
                f"Ganancia: {formato_moneda(ganancia_item)}"
            ]

            form.addRow(QLabel(descripcion), QLabel(" | ".join(detalles)))

        # Mostrar ganancia total de la factura
        form.addRow(QLabel("Ganancia Total:"), QLabel(formato_moneda(int(ganancia_total))))

        layout.addLayout(form)

        botones = QDialogButtonBox(QDialogButtonBox.Ok)
        botones.accepted.connect(self.accept)
        layout.addWidget(botones)


class FacturasViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visualizador de Facturas")
        self.resize(900, 600)

        # Widget central
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Barra de búsqueda
        search_layout = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.search_btn = QPushButton("Buscar por Fecha")
        self.search_btn.clicked.connect(self.buscar_por_fecha)

        self.reload_btn = QPushButton("Recargar Todas")
        self.reload_btn.clicked.connect(self.cargar_facturas)

        search_layout.addWidget(QLabel("Fecha:"))
        search_layout.addWidget(self.date_edit)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.reload_btn)

        layout.addLayout(search_layout)

        # Tabla de facturas
        self.table = QTableView()
        self.model = QStandardItemModel(0, 5)
        self.model.setHorizontalHeaderLabels(["ID", "Fecha", "Método de Pago", "Total", "Ganancia"])
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self.abrir_detalle)

        layout.addWidget(self.table)

        # Cargar facturas iniciales
        self.cargar_facturas()

    def cargar_facturas(self):
        self.model.removeRows(0, self.model.rowCount())
        data = facturas.listar_facturas()
        for f in data:
            self._agregar_fila(f)

    def buscar_por_fecha(self):
        fecha = self.date_edit.date().toString("yyyy-MM-dd")
        try:
            data = facturas.buscar_por_fecha(fecha)
            self.model.removeRows(0, self.model.rowCount())
            for f in data:
                self._agregar_fila(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo buscar facturas: {e}")

    def _agregar_fila(self, f):
        row = [
            QStandardItem(str(f["id"])),
            QStandardItem(f["fecha"]),
            QStandardItem(f["metodo_pago"]),
            QStandardItem(formato_moneda(int(float(f["total"])))),
            QStandardItem(formato_moneda(int(float(f.get("ganancia", 0)))))
        ]
        self.model.appendRow(row)

    def abrir_detalle(self, index):
        row = index.row()
        factura_id = int(self.model.item(row, 0).text())
        factura = facturas.obtener_factura(factura_id)
        dlg = DetalleFacturaDialog(factura, self)
        dlg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FacturasViewer()
    viewer.show()
    sys.exit(app.exec())
