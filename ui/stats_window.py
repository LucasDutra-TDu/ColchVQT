from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QMessageBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QDate
from logic.financiero import format_currency
from logic.stats_service import obtener_reporte_mensual
from ui.widgets import MonthYearSelector

# Imports de detalle
from ui.history_window import DetalleFacturaDialog 
from ui.credits_window import CreditDetailDialog   
from logic.facturas_db_handler import obtener_historial, buscar_por_fecha
from logic.credits_service import obtener_id_credito_por_factura

class StatsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estadísticas y Comisiones")
        self.resize(1100, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 1. Selector
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Seleccionar Período:"))
        self.selector_fecha = MonthYearSelector()
        top_layout.addWidget(self.selector_fecha)
        
        btn_calc = QPushButton("Generar Reporte")
        btn_calc.clicked.connect(self.generar_reporte)
        top_layout.addWidget(btn_calc)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 2. Tarjetas
        cards_layout = QHBoxLayout()
        self.card_empresa = self._create_card("Ganancia Empresa", "#2c3e50")
        self.card_gerente = self._create_card("Comisión Gerente", "#27ae60")
        self.card_vendedor = self._create_card("Comisión Vendedor", "#e67e22")
        cards_layout.addWidget(self.card_empresa)
        cards_layout.addWidget(self.card_gerente)
        cards_layout.addWidget(self.card_vendedor)
        layout.addLayout(cards_layout)
        
        # 3. Tabla
        layout.addWidget(QLabel("<b>Detalle de Movimientos del Mes (Doble click para ver detalle):</b>"))
        self.table = QTableView()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.model = QStandardItemModel()
        
        # Definición de Columnas
        # 0:Fecha, 1:Tipo, 2:Detalle, 3:G.Empresa, 4:C.Gerente, 5:C.Vendedor, 6:ID, 7:TIPO
        headers = [
            "Fecha", "Tipo", "Detalle", 
            "Ganancia Empresa", "Com. Gerente", "Com. Vendedor", 
            "ID", "TIPO_ORIGEN" 
        ]
        self.model.setHorizontalHeaderLabels(headers)
        self.table.setModel(self.model)
        
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        # --- CORRECCIÓN: Ocultar las columnas 6 y 7 ---
        self.table.setColumnHidden(6, True) # ID
        self.table.setColumnHidden(7, True) # TIPO
        # ----------------------------------------------
        
        self.table.doubleClicked.connect(self.abrir_detalle)
        layout.addWidget(self.table)
        
        self.generar_reporte()

    def _create_card(self, title, color):
        from PySide6.QtWidgets import QFrame
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {color}; border-radius: 10px; color: white;")
        l = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        lbl_val = QLabel("$0")
        lbl_val.setObjectName("value")
        lbl_val.setStyleSheet("font-size: 24px; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignCenter)
        l.addWidget(lbl_title, alignment=Qt.AlignCenter)
        l.addWidget(lbl_val)
        return frame

    def _update_card(self, card_widget, valor):
        lbl = card_widget.findChild(QLabel, "value")
        lbl.setText(format_currency(valor))

    def generar_reporte(self):
        mes, anio = self.selector_fecha.get_date()
        data = obtener_reporte_mensual(mes, anio)
        
        totales = data["totales"]
        self._update_card(self.card_empresa, totales["empresa"])
        self._update_card(self.card_gerente, totales["gerente"])
        self._update_card(self.card_vendedor, totales["vendedor"])
        
        self.model.removeRows(0, self.model.rowCount())
        for row in data["ventas"]:
            self.model.appendRow([
                QStandardItem(row["fecha"]),
                QStandardItem(row["tipo"]),
                QStandardItem(row["detalle"]),
                
                QStandardItem(format_currency(row.get("ganancia_empresa", 0))),
                QStandardItem(format_currency(row.get("comis_gerente", 0))),
                QStandardItem(format_currency(row.get("comis_vendedor", 0))),
                
                QStandardItem(str(row["id_origen"])),
                QStandardItem(str(row["tipo_origen"]))
            ])

    def abrir_detalle(self, index):
        """Abre el diálogo correspondiente."""
        row = index.row()
        
        # --- CORRECCIÓN CRÍTICA AQUÍ ---
        # Antes buscábamos en 5, ahora el ID está en 6 y el TIPO en 7
        try:
            id_origen = int(self.model.item(row, 6).text()) # <--- Índice 6
            tipo_origen = self.model.item(row, 7).text()    # <--- Índice 7
        except ValueError:
            return # Seguridad por si clickean cabecera o algo raro
        # -------------------------------
        
        if tipo_origen == "FACTURA":
            # Obtener objeto factura completo (Buscamos en historial general)
            # Esto es ineficiente pero simple. Idealmente 'obtener_por_id'
            historial = obtener_historial()
            factura = next((f for f in historial if f['id'] == id_origen), None)
            
            if factura:
                dlg = DetalleFacturaDialog(factura, self)
                dlg.exec()
            else:
                QMessageBox.warning(self, "Error", "No se encontró la factura.")
                
        elif tipo_origen == "CREDITO":
            dlg = CreditDetailDialog(id_origen, self)
            dlg.exec()