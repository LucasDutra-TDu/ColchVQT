from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QPushButton, QLabel, QHeaderView, QMessageBox, QDialog, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PySide6.QtCore import Qt, QDate

from logic.credits_service import obtener_creditos_activos, obtener_detalle_credito, pagar_cuota
from logic.financiero import format_currency
from datetime import datetime

class CreditDetailDialog(QDialog):
    def __init__(self, credito_id, parent=None):
        super().__init__(parent)
        self.credito_id = credito_id
        self.setWindowTitle("Detalle de Crédito y Cuotas")
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Cargar datos
        data = obtener_detalle_credito(credito_id)
        credito = data['credito']
        cuotas = data['cuotas']
        
        # Info Cabecera
        info_str = (f"<b>Cliente ID:</b> {credito['cliente_id']}<br>"
                    f"<b>Monto Financiado:</b> {format_currency(credito['monto_financiado'])}<br>"
                    f"<b>Plan:</b> {credito['cantidad_cuotas']} Cuotas")
        lbl_info = QLabel(info_str)
        lbl_info.setTextFormat(Qt.RichText)
        layout.addWidget(lbl_info)
        
        layout.addWidget(QLabel("<b>Cuotas (Doble click para cobrar):</b>"))

        # Lista de Cuotas
        self.list_widget = QListWidget()
        self.hoy = datetime.now().strftime("%Y-%m-%d")
        
        for c in cuotas:
            item_text = f"Cuota {c['numero_cuota']} - Vence: {c['fecha_vencimiento']} - {format_currency(c['monto'])}"
            item = QListWidgetItem(item_text)
            
            # Lógica Visual de Estado
            if c['estado'] == 'PAGADO':
                item.setText(f"✅ {item_text} (Pagado: {c.get('fecha_pago', '-')})")
                item.setForeground(QColor("green"))
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled) # Deshabilitar si ya pagó
            else:
                # Pendiente
                if c['fecha_vencimiento'] < self.hoy:
                    item.setText(f"⚠️ {item_text} [VENCIDA]")
                    item.setForeground(QColor("red"))
                    item.setFont(QFont("Arial", weight=QFont.Bold))
                else:
                    item.setText(f"⏳ {item_text}")
                    item.setForeground(QColor("black"))
            
            # Guardamos ID en el item para usarlo al clickear
            item.setData(Qt.UserRole, c['id']) 
            self.list_widget.addItem(item)
            
        self.list_widget.itemDoubleClicked.connect(self.pagar_cuota_seleccionada)
        layout.addWidget(self.list_widget)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

    def pagar_cuota_seleccionada(self, item):
        cuota_id = item.data(Qt.UserRole)
        
        # Obtenemos el estado actual leyendo el texto del item (truco visual rápido)
        # O idealmente consultando la DB, pero el texto es confiable aquí.
        texto_item = item.text()
        es_pago = "✅" in texto_item
        
        from logic.credits_service import pagar_cuota, anular_pago # Import local
        
        if es_pago:
            # --- LÓGICA DE REVERSIÓN (SEGURIDAD EXTRA) ---
            advertencia = QMessageBox.warning(
                self, "Seguridad - Anular Pago",
                "⚠️ ESTÁ A PUNTO DE ANULAR UN PAGO YA REGISTRADO.\n\n"
                "¿Está seguro que desea volver esta cuota a estado PENDIENTE?\n"
                "Esto afectará el estado de cuenta del cliente.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No # Por defecto NO para evitar accidentes
            )
            
            if advertencia == QMessageBox.Yes:
                anular_pago(cuota_id)
                # Actualizamos visualmente el item a estado pendiente
                # (Lo limpiamos quitando el check y restaurando color)
                texto_limpio = texto_item.replace("✅ ", "").split(" (Pagado")[0]
                item.setText(f"⏳ {texto_limpio}") # Icono reloj
                item.setForeground(QColor("black"))
                item.setFlags(item.flags() | Qt.ItemIsEnabled) # Reactivar
                QMessageBox.information(self, "Anulado", "El pago ha sido revertido exitosamente.")
        
        else:
            # --- LÓGICA DE COBRO NORMAL ---
            confirm = QMessageBox.question(
                self, "Confirmar Cobro", 
                "¿Confirmar recepción del dinero y marcar cuota como PAGADA?", 
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                pagar_cuota(cuota_id)
                
                # Actualizar visualmente a Pagado
                # Quitamos iconos viejos de espera o alerta
                texto_limpio = texto_item.replace("⏳ ", "").replace("⚠️ ", "").replace(" [VENCIDA]", "")
                hoy = datetime.now().strftime("%Y-%m-%d")
                item.setText(f"✅ {texto_limpio} (Pagado: {hoy})")
                item.setForeground(QColor("green"))
                # Opcional: No deshabilitar si queremos permitir anular inmediatamente
                # item.setFlags(item.flags() & ~Qt.ItemIsEnabled) 
                
                QMessageBox.information(self, "Éxito", "Pago registrado.")

class CreditsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Créditos Activos")
        self.resize(1000, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        layout.addWidget(QLabel("<h2>Listado de Créditos Activos</h2>"))
        btn_refresh = QPushButton("🔄 Actualizar Lista")
        btn_refresh.clicked.connect(self.cargar_datos)
        layout.addWidget(btn_refresh)
        
        # Tabla
        self.table = QTableView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Cliente", "DNI", "Próx. Vencimiento", "Monto Cuota", "Estado", "ID Oculto"])
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setColumnHidden(5, True) # Ocultamos ID
        
        self.table.doubleClicked.connect(self.abrir_detalle)
        layout.addWidget(self.table)
        
        self.cargar_datos()

    def cargar_datos(self):
        self.model.removeRows(0, self.model.rowCount())
        creditos = obtener_creditos_activos() # Trae JOIN con clientes
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        
        for cr in creditos:
            # Necesitamos saber la próxima cuota pendiente para mostrarla en la lista
            detalle = obtener_detalle_credito(cr['id'])
            cuotas_pendientes = [c for c in detalle['cuotas'] if c['estado'] == 'PENDIENTE']
            
            if not cuotas_pendientes:
                continue # No debería pasar si la query filtra FINALIZADO, pero por seguridad
                
            prox_cuota = cuotas_pendientes[0] # La primera pendiente
            
            # Items Visuales
            i_cliente = QStandardItem(cr['nombre'])
            i_dni = QStandardItem(cr['dni'])
            i_venc = QStandardItem(prox_cuota['fecha_vencimiento'])
            i_monto = QStandardItem(format_currency(prox_cuota['monto']))
            i_estado = QStandardItem("Al Día")
            i_id = QStandardItem(str(cr['id']))
            
            # Lógica de Color (Rojo si vencida)
            if prox_cuota['fecha_vencimiento'] < hoy_str:
                rojo = QColor(255, 200, 200) # Fondo rojizo suave
                texto_rojo = QColor("red")
                
                i_venc.setForeground(texto_rojo)
                i_monto.setForeground(texto_rojo)
                i_estado.setText("MORA")
                i_estado.setForeground(texto_rojo)
                
                # Pintar fila (opcional)
                for item in [i_cliente, i_dni, i_venc, i_monto, i_estado]:
                    item.setBackground(rojo)
            
            self.model.appendRow([i_cliente, i_dni, i_venc, i_monto, i_estado, i_id])

    def abrir_detalle(self, index):
        row = index.row()
        # ID está en columna 5
        id_str = self.model.item(row, 5).text()
        dlg = CreditDetailDialog(int(id_str), self)
        dlg.exec()
        self.cargar_datos() # Recargar al volver por si pagó