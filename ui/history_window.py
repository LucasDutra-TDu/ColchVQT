from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

# Lógica
from logic.facturas_db_handler import obtener_historial, buscar_por_fecha
from logic.financiero import format_currency
from logic.credits_service import obtener_id_credito_por_factura
from ui.widgets import MonthYearSelector

# Diálogos
from ui.credits_window import CreditDetailDialog
from ui.widgets import  SuccessDialog
from logic.pdf_service import generar_comprobante_venta

class DetalleFacturaDialog(QDialog):
    # ... (El código de DetalleFacturaDialog que te pasé antes se mantiene IGUAL) ...
    # ... (Si no lo tienes a mano, avísame, pero asumo que ya está pegado de la respuesta anterior) ...
    # Asegúrate de incluir la clase DetalleFacturaDialog aquí o importarla si la moviste.
    def __init__(self, factura, parent=None):
        super().__init__(parent)
        self.factura = factura
        self.setWindowTitle(f"Detalle Factura #{factura['id']}")
        self.resize(450, 550)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        lbl_fecha = QLabel(f"{factura['fecha']}")
        lbl_metodo = QLabel(f"<b>{factura['metodo_pago']}</b>")
        form.addRow("Fecha:", lbl_fecha)
        form.addRow("Método:", lbl_metodo)
        layout.addLayout(form)
        layout.addWidget(QLabel("<hr>"))

        items = factura.get("items", [])
        total_base_acumulado = 0
        total_final_acumulado = 0

        for item in items:
            nombre = f"{item.get('modelo', '')} {item.get('descripcion', '')}"
            cant = int(item.get("cantidad", 1))
            p_unit_final = float(item.get("precio_unitario", 0))
            p_unit_base = float(item.get("precio_lista_base", p_unit_final))
            
            total_base_acumulado += p_unit_base * cant
            total_final_acumulado += p_unit_final * cant

            detalles_txt = f"{cant} x {format_currency(p_unit_final)}"
            if p_unit_base < p_unit_final:
                detalles_txt += f" <small style='color:gray'>(Base: {format_currency(p_unit_base)})</small>"
            
            form_item = QFormLayout()
            form_item.addRow(QLabel(f"• {nombre}"), QLabel(detalles_txt))
            layout.addLayout(form_item)

        layout.addWidget(QLabel("<hr>"))
        footer_layout = QFormLayout()
        diferencia = total_final_acumulado - total_base_acumulado
        if diferencia > 1: 
            lbl_base = QLabel(format_currency(total_base_acumulado))
            lbl_base.setStyleSheet("color: #555;")
            footer_layout.addRow("Subtotal Base (Efectivo):", lbl_base)
            
            lbl_gastos = QLabel(format_currency(diferencia))
            lbl_gastos.setStyleSheet("color: #c0392b; font-weight: bold;")
            
            etiqueta_gasto = "Interés / Recargo:"
            if "Tarjeta" in factura['metodo_pago'] or "Debito" in factura['metodo_pago']:
                etiqueta_gasto = "Gastos Bancarios / Tarjeta:"
            elif "Crédito" in factura['metodo_pago']:
                etiqueta_gasto = "Interés Financiación:"
            footer_layout.addRow(etiqueta_gasto, lbl_gastos)
            footer_layout.addRow(QLabel("----------------"), QLabel("----------------"))

        lbl_total = QLabel(format_currency(factura['total']))
        lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
        footer_layout.addRow("TOTAL COBRADO:", lbl_total)
        layout.addLayout(footer_layout)
        botones = QDialogButtonBox(QDialogButtonBox.Ok)
        botones.accepted.connect(self.accept)
        layout.addWidget(botones)
        
        botones_layout = QHBoxLayout()
        
        # Botón Imprimir
        btn_print = QPushButton("🖨️ Imprimir Comprobante")
        btn_print.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 8px;")
        btn_print.clicked.connect(self.imprimir_comprobante)
        botones_layout.addWidget(btn_print)
        
        botones_layout.addStretch()
        
        # Botón Cerrar (Standard)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        botones_layout.addWidget(btn_cerrar)
        
        layout.addLayout(botones_layout)

    def imprimir_comprobante(self):
        try:
            path = generar_comprobante_venta(self.factura)
            
            # Usamos tu nuevo diálogo de éxito que tiene botones de abrir/copiar
            dlg = SuccessDialog(
                "Comprobante Generado",
                f"Se ha creado el PDF del comprobante #{self.factura['id']}",
                ruta_archivo=path,
                parent=self
            )
            dlg.exec()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{e}")

class HistoryWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historial de Ventas")
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Filtros
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar por Mes:"))
        self.selector_fecha = MonthYearSelector()
        self.selector_fecha.dateChanged.connect(self.cargar_datos) 
        filter_layout.addWidget(self.selector_fecha)
        filter_layout.addStretch()
        
        btn_refresh = QPushButton("Recargar Todo")
        btn_refresh.clicked.connect(self.cargar_todos)
        filter_layout.addWidget(btn_refresh)
        layout.addLayout(filter_layout)

        # Tabla
        self.table = QTableView()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        self.model = QStandardItemModel()
        # --- CAMBIO: Quitamos 'Ganancia' ---
        self.model.setHorizontalHeaderLabels(["ID", "Fecha", "Método", "Total", "Items Resumen"])
        self.table.setModel(self.model)
        
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 50)
        
        # Conectar Doble Click
        self.table.doubleClicked.connect(self.abrir_detalle)
        
        layout.addWidget(self.table)
        self.datos_actuales = [] # Para guardar referencia de objetos completos
        self.cargar_datos()

    def _llenar_tabla(self, facturas):
        self.datos_actuales = facturas # Guardamos la lista cruda para usarla en el detalle
        self.model.removeRows(0, self.model.rowCount())
        
        for f in facturas:
            item_id = QStandardItem(str(f['id']))
            item_fecha = QStandardItem(f['fecha'])
            item_metodo = QStandardItem(f['metodo_pago'])
            item_total = QStandardItem(format_currency(f['total']))
            
            # Resumen de items
            items_str = ", ".join([f"{i.get('cantidad',1)}x {i.get('modelo','')}" for i in f.get('items', [])])
            item_resumen = QStandardItem(items_str)
            
            self.model.appendRow([item_id, item_fecha, item_metodo, item_total, item_resumen])

    def cargar_datos(self):
        mes, anio = self.selector_fecha.get_date()
        fecha_filtro = f"{anio}-{mes:02d}"
        facturas = buscar_por_fecha(fecha_filtro)
        self._llenar_tabla(facturas)

    def cargar_todos(self):
        facturas = obtener_historial()
        self._llenar_tabla(facturas)

    def abrir_detalle(self, index):
        row = index.row()
        factura = self.datos_actuales[row] # Obtenemos el objeto completo
        metodo = factura['metodo_pago']
        
        # --- CAMBIO: Lógica de Derivación ---
        # Verificamos si es "Crédito de la Casa" usando la misma lógica robusta que en financiero
        es_credito = "Casa" in metodo or ("Crédito" in metodo and "Tarjeta" not in metodo)
        
        if es_credito:
            # Buscamos el ID real del crédito en la otra tabla
            credito_id = obtener_id_credito_por_factura(factura['id'])
            if credito_id:
                dlg = CreditDetailDialog(credito_id, self)
                dlg.exec()
            else:
                QMessageBox.warning(self, "Error", "No se encontró el expediente de crédito asociado.")
        else:
            # Es venta normal (Contado o Tarjeta)
            dlg = DetalleFacturaDialog(factura, self)
            dlg.exec()