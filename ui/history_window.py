from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QPushButton, QLabel, QDialog, QDialogButtonBox,
    QFormLayout, QDateEdit, QMessageBox, QHeaderView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QDate

# Imports de Lógica
from logic import facturas_db_handler
from logic.financiero import format_currency

class DetalleFacturaDialog(QDialog):
    def __init__(self, factura, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalle Factura #{factura['id']}")
        self.resize(400, 500)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # --- Cabecera ---
        layout.addWidget(QLabel(f"<b>Fecha:</b> {factura['fecha']}"))
        layout.addWidget(QLabel(f"<b>Método:</b> {factura['metodo_pago']}"))
        layout.addWidget(QLabel("<hr>"))

        # --- Items ---
        items = factura.get("items", [])
        for item in items:
            # Recuperamos datos guardados en el snapshot
            nombre = f"{item.get('modelo', '')} {item.get('descripcion', '')}"
            cant = item.get("cantidad", 1)
            p_unit = item.get("precio_unitario", 0)
            
            detalles = f"{cant} x {format_currency(p_unit)}"
            form.addRow(QLabel(nombre), QLabel(detalles))

        layout.addLayout(form)
        layout.addWidget(QLabel("<hr>"))

        # --- Totales ---
        lbl_total = QLabel(f"TOTAL: {format_currency(factura['total'])}")
        lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
        layout.addWidget(lbl_total, alignment=Qt.AlignRight)

        # Ganancia (Solo visible para admin/gerente en teoría)
        ganancia = factura.get("ganancia", 0)
        layout.addWidget(QLabel(f"Margen: {format_currency(ganancia)}"), alignment=Qt.AlignRight)

        botones = QDialogButtonBox(QDialogButtonBox.Ok)
        botones.accepted.connect(self.accept)
        layout.addWidget(botones)

class HistoryWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial de Ventas")
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Barra Superior ---
        search_layout = QHBoxLayout()
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        
        btn_buscar = QPushButton("Buscar por Fecha")
        btn_buscar.clicked.connect(self.buscar_por_fecha)

        btn_reload = QPushButton("Ver Todas")
        btn_reload.clicked.connect(self.cargar_facturas)

        search_layout.addWidget(QLabel("Filtrar Fecha:"))
        search_layout.addWidget(self.date_edit)
        search_layout.addWidget(btn_buscar)
        search_layout.addWidget(btn_reload)
        search_layout.addStretch()
        
        layout.addLayout(search_layout)

        # --- Tabla ---
        self.table = QTableView()
        self.table.setEditTriggers(QTableView.NoEditTriggers) # Solo lectura
        self.table.setSelectionBehavior(QTableView.SelectRows)
        
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["ID", "Fecha", "Método Pago", "Total", "Ganancia"])
        self.table.setModel(self.model)
        
        # Estética de tabla
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch) # Fecha estirada
        
        self.table.doubleClicked.connect(self.abrir_detalle)
        layout.addWidget(self.table)

        self.cargar_facturas()

    def cargar_facturas(self):
        try:
            data = facturas_db_handler.obtener_historial()
            self._llenar_tabla(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando base de datos:\n{e}")

    def buscar_por_fecha(self):
        fecha_str = self.date_edit.date().toString("yyyy-MM-dd")
        data = facturas_db_handler.buscar_por_fecha(fecha_str)
        self._llenar_tabla(data)

    def _llenar_tabla(self, data):
        self.model.removeRows(0, self.model.rowCount())
        for f in data:
            item_id = QStandardItem(str(f["id"]))
            item_fecha = QStandardItem(str(f["fecha"]))
            item_metodo = QStandardItem(str(f["metodo_pago"]))
            
            # Formateo de moneda
            item_total = QStandardItem(format_currency(f["total"]))
            item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            item_ganancia = QStandardItem(format_currency(f.get("ganancia", 0)))
            item_ganancia.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.model.appendRow([item_id, item_fecha, item_metodo, item_total, item_ganancia])

    def abrir_detalle(self, index):
        row = index.row()
        id_str = self.model.item(row, 0).text()
        # Buscamos en la DB de nuevo para tener el objeto completo con items
        # (O podríamos guardar el objeto en la fila, pero consultar es más seguro)
        # Nota: obtener_historial devuelve lista, aquí hacemos una query rápida si existiera 'obtener_una'
        # Por simplicidad, recargamos el historial filtrado o usamos un helper.
        # Vamos a iterar lo que ya tenemos en memoria del servicio sería lo ideal, 
        # pero para ser robustos, añadimos 'obtener_factura_por_id' al servicio.
        
        # Como no añadimos 'obtener_factura_por_id' explícitamente en el paso anterior,
        # usaremos un truco visual o asumimos que la data está.
        # Implementemos un filtrado rápido en el servicio o recuperemos.
        # AGREGADO AD-HOC:
        todas = facturas_db_handler.obtener_historial()
        factura = next((f for f in todas if str(f["id"]) == id_str), None)
        
        if factura:
            dlg = DetalleFacturaDialog(factura, self)
            dlg.exec()