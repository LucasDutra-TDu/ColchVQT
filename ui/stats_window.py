from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QPushButton, QLabel, QHeaderView, QDateEdit, QFrame
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QDate
from logic.financiero import format_currency
from logic.stats_service import obtener_reporte_mensual

class StatsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estadísticas y Comisiones")
        self.resize(1000, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 1. Selector de Mes
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Seleccionar Período:"))
        
        self.date_selector = QDateEdit()
        self.date_selector.setDisplayFormat("MMMM yyyy")
        self.date_selector.setDate(QDate.currentDate())
        # Truco para que parezca un selector de mes (aunque el día siga ahí)
        self.date_selector.setCalendarPopup(True) 
        top_layout.addWidget(self.date_selector)
        
        btn_calc = QPushButton("Generar Reporte")
        btn_calc.clicked.connect(self.generar_reporte)
        top_layout.addWidget(btn_calc)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 2. Tarjetas de Totales (Resumen)
        cards_layout = QHBoxLayout()
        self.card_empresa = self._create_card("Ganancia Empresa", "#2c3e50")
        self.card_gerente = self._create_card("Comisión Gerente", "#27ae60")
        self.card_vendedor = self._create_card("Comisión Vendedor", "#e67e22")
        
        cards_layout.addWidget(self.card_empresa)
        cards_layout.addWidget(self.card_gerente)
        cards_layout.addWidget(self.card_vendedor)
        layout.addLayout(cards_layout)
        
        # 3. Tabla Detalle
        layout.addWidget(QLabel("<b>Detalle de Movimientos del Mes:</b>"))
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Fecha", "Tipo", "Detalle", "Monto Bruto", "Comisión Vend."])
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Cargar inicial
        self.generar_reporte()

    def _create_card(self, title, color):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {color}; border-radius: 10px; color: white;")
        l = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        lbl_val = QLabel("$0")
        lbl_val.setObjectName("value") # Para buscarlo después
        lbl_val.setStyleSheet("font-size: 24px; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignCenter)
        l.addWidget(lbl_title, alignment=Qt.AlignCenter)
        l.addWidget(lbl_val)
        return frame

    def _update_card(self, card_widget, valor):
        lbl = card_widget.findChild(QLabel, "value")
        lbl.setText(format_currency(valor))

    def generar_reporte(self):
        qdate = self.date_selector.date()
        mes = qdate.month()
        anio = qdate.year()
        
        data = obtener_reporte_mensual(mes, anio)
        
        # Actualizar Tarjetas
        totales = data["totales"]
        self._update_card(self.card_empresa, totales["empresa"])
        self._update_card(self.card_gerente, totales["gerente"])
        self._update_card(self.card_vendedor, totales["vendedor"])
        
        # Actualizar Tabla
        self.model.removeRows(0, self.model.rowCount())
        for row in data["ventas"]:
            self.model.appendRow([
                QStandardItem(row["fecha"]),
                QStandardItem(row["tipo"]),
                QStandardItem(row["detalle"]),
                QStandardItem(format_currency(row["monto"])),
                QStandardItem(format_currency(row["comis_ven"]))
            ])