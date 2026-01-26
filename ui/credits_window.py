from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QPushButton, QLabel, QHeaderView, QMessageBox, QDialog, QListWidget, QListWidgetItem, QGroupBox, QFormLayout
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PySide6.QtCore import Qt, QDate

from logic.credits_service import obtener_creditos_activos, obtener_detalle_credito, pagar_cuota, anular_pago
from logic.financiero import format_currency
from datetime import datetime


class CreditDetailDialog(QDialog):
    def __init__(self, credito_id, parent=None):
        super().__init__(parent)
        self.credito_id = credito_id
        self.setWindowTitle(f"Detalle de Crédito #{credito_id}")
        self.resize(500, 700)
        self._procesando = False # Blindaje para evitar doble ejecución
        
        layout = QVBoxLayout(self)
        
        # Cargar datos
        data = obtener_detalle_credito(credito_id)
        credito = data['credito']
        cuotas = data['cuotas']
        items = data['items']
        
        # --- SECCIÓN 1: DATOS DEL CLIENTE ---
        layout.addWidget(QLabel("<b>👤 DATOS DEL CLIENTE</b>"))
        
        info_cliente = (
            f"<b>Nombre:</b> {credito['nombre']}<br>"
            f"<b>DNI:</b> {credito['dni']}<br>"
            f"<b>Teléfono:</b> {credito.get('telefono', 'No registrado')}<br>"
            f"<b>Dirección:</b> {credito.get('direccion', '-')}"
        )
        lbl_cliente = QLabel(info_cliente)
        lbl_cliente.setTextFormat(Qt.RichText)
        layout.addWidget(lbl_cliente)
        
        layout.addWidget(QLabel("<hr>"))
        
        # --- SECCIÓN 2: PRODUCTOS FINANCIADOS ---
        layout.addWidget(QLabel("<b>📦 PRODUCTOS COMPRADOS</b>"))
        
        txt_productos = ""
        for item in items:
            modelo = item.get('MODELO', item.get('modelo', 'Producto'))
            cant = item.get('cantidad', 1)
            
            # --- CORRECCIÓN DE PRECIO ---
            # Priorizamos 'precio_unitario' (nombre en DB Facturas)
            # Fallback a 'precio_venta_final' (nombre en Carrito)
            precio = float(item.get('precio_unitario', item.get('precio_venta_final', 0)))
            
            txt_productos += f"• {cant} x {modelo} ({format_currency(precio)})\n"
            
        lbl_productos = QLabel(txt_productos)
        lbl_productos.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 4px;")
        layout.addWidget(lbl_productos)
        
        layout.addWidget(QLabel("<hr>"))
        
        # --- SECCIÓN 3: RESUMEN FINANCIERO ---
        layout.addWidget(QLabel("<b>💰 PLAN DE PAGOS</b>"))
        info_financiera = (
            f"<b>Monto Total Financiado:</b> {format_currency(credito['monto_financiado'])}<br>"
            f"<b>Plan:</b> {credito['cantidad_cuotas']} Cuotas"
        )
        lbl_fin = QLabel(info_financiera)
        lbl_fin.setTextFormat(Qt.RichText)
        layout.addWidget(lbl_fin)
        
        layout.addWidget(QLabel("<b>Estado de Cuotas (Doble click para cobrar/anular):</b>"))

        # Lista de Cuotas
        self.list_widget = QListWidget()
        self.hoy = datetime.now().strftime("%Y-%m-%d")
        
        for c in cuotas:
            item_text = f"Cuota {c['numero_cuota']} - Vence: {c['fecha_vencimiento']} - {format_currency(c['monto'])}"
            item = QListWidgetItem(item_text)
            
            # Lógica Visual
            if c['estado'] == 'PAGADO':
                item.setText(f"✅ {item_text} (Pagado: {c.get('fecha_pago', '-')})")
                item.setForeground(QColor("green"))
            else:
                if c['fecha_vencimiento'] < self.hoy:
                    item.setText(f"⚠️ {item_text} [VENCIDA]")
                    item.setForeground(QColor("red"))
                    item.setFont(QFont("Arial", weight=QFont.Bold))
                else:
                    item.setText(f"⏳ {item_text}")
                    item.setForeground(QColor("black"))
            
            item.setData(Qt.UserRole, c['id']) 
            self.list_widget.addItem(item)
            
        self.list_widget.itemDoubleClicked.connect(self.pagar_cuota_seleccionada)
        layout.addWidget(self.list_widget)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

    def pagar_cuota_seleccionada(self, item):

        # Blindaje: Si ya estamos mostrando un diálogo, ignorar clicks extra
        if self._procesando: return
        self._procesando = True
        
        try:
            cuota_id = item.data(Qt.UserRole)
            texto_item = item.text()
            es_pago = "✅" in texto_item
            
            if es_pago:
                # --- FLUJO DE ANULACIÓN ---
                advertencia = QMessageBox.warning(
                    self, "Anular Pago",
                    "⚠️ ¿Desea ANULAR este pago y volver la cuota a estado PENDIENTE?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if advertencia == QMessageBox.Yes:
                    anular_pago(cuota_id)
                    
                    # Actualizar visualmente
                    texto_limpio = texto_item.replace("✅ ", "").split(" (Pagado")[0]
                    item.setText(f"⏳ {texto_limpio}")
                    item.setForeground(QColor("black"))
                    
                    QMessageBox.information(self, "Anulado", "El pago ha sido revertido correctamente.")
                
                # Si dice NO, simplemente sale (gracias al return implícito al final)

            else:
                # --- FLUJO DE COBRO ---
                confirm = QMessageBox.question(
                    self, "Confirmar Cobro", 
                    "¿Confirmar recepción del dinero y marcar cuota como PAGADA?", 
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if confirm == QMessageBox.Yes:
                    pagar_cuota(cuota_id)
                    
                    # Actualizar visualmente
                    texto_limpio = texto_item.replace("⏳ ", "").replace("⚠️ ", "").replace(" [VENCIDA]", "")
                    hoy = datetime.now().strftime("%Y-%m-%d")
                    item.setText(f"✅ {texto_limpio} (Pagado: {hoy})")
                    item.setForeground(QColor("green"))
                    
                    QMessageBox.information(self, "Éxito", "Pago registrado correctamente.")
                
                # Si dice NO, no hace nada

        finally:
            # Liberamos el bloqueo siempre, pase lo que pase
            self._procesando = False

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