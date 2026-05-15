# ui/main_window.py
from typing import Dict, Any
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar, QStatusBar, QPushButton, QWidget, QHBoxLayout, QInputDialog, QLineEdit, QMessageBox, QDialog
from PySide6.QtGui import QAction, QIcon

from ui.catalogo_view import CatalogoView
from ui.cart_window import CartWindow
from ui.history_window import HistoryWindow
from logic.cart_service import CartService
from ui.credits_window import CreditsWindow
from ui.stats_window import StatsWindow    
from ui.widgets import StockManagerDialog 

class MainWindow(QMainWindow):
    def __init__(self, data_context: Dict[str, Any], cart_service: CartService):
        super().__init__()
        self.data_context = data_context
        self.cart_service = cart_service # Guardamos referencia
        
        # Referencias a ventanas secundarias (para no abrirlas mil veces)
        self.w_carrito = None
        self.w_historial = None
        self.w_creditos = None
        self.w_stats = None

        # --- CONEXIÓN DE SEÑAL AUTOMÁTICA ---
        # Cada vez que el servicio diga "cambié", ejecutamos _on_cart_update
        self.cart_service.cart_updated.connect(self._on_cart_update)

        self.setWindowTitle("Sistema de Gestión - ColchVQT")
        self.resize(1200, 800)

        # --- Toolbar Superior --- 
        toolbar = QToolBar("Barra Principal")
        self.addToolBar(toolbar)

        # Acción: Ver Carrito
        action_cart = QAction("🛒 Ver Carrito", self)
        action_cart.triggered.connect(self.abrir_carrito)
        toolbar.addAction(action_cart)

        # Acción: Créditos Activos
        action_cred = QAction("💸 Créditos Activos", self)
        action_cred.triggered.connect(self.abrir_creditos)
        toolbar.addAction(action_cred)

        # Acción: Estadísticas
        action_stats = QAction("📊 Estadísticas", self)
        action_stats.triggered.connect(self.abrir_stats)
        toolbar.addAction(action_stats)

        # Acción: Ver Historial
        action_hist = QAction("📜 Historial Ventas", self)
        action_hist.triggered.connect(self.abrir_historial)
        toolbar.addAction(action_hist)

        # Acción: Plataforma de Stock
        action_stock = QAction("📦 Inventario / Stock", self)
        action_stock.triggered.connect(self.abrir_gestor_stock)
        toolbar.addAction(action_stock)

        # --- Stack Central (Catálogo) ---
        self.stack = QStackedWidget()
        self.catalogo_view = CatalogoView(data_context,cart_service) # Le pasamos data
        
        # ¡IMPORTANTE! Conectamos el botón de agregar al carrito del catálogo
        # Esto requiere que modifiquemos 'catalogo_view' ligeramente o usemos señales.
        # Por simplicidad ahora: El usuario agrega desde la tabla y nosotros inyectamos
        # el cart_service en la vista de catálogo si fuera necesario, 
        # O MEJOR: Pasamos el 'cart_service' a 'CatalogoView' también.
        
        self.stack.addWidget(self.catalogo_view)
        self.setCentralWidget(self.stack)

    def _on_cart_update(self):
        """
        Reacciona a cambios en el carrito.
        1. Si la ventana no existe, la crea.
        2. Si está oculta y se agregó algo, la muestra.
        3. Siempre actualiza la tabla.
        """
        # 1. Asegurar que la ventana existe
        if self.w_carrito is None:
            self.w_carrito = CartWindow(self.cart_service)

        # 2. Lógica de visualización "Pop-up"
        # Si hay items y la ventana está cerrada, la abrimos automáticamente
        if self.cart_service.get_count() > 0 and not self.w_carrito.isVisible():
            self.w_carrito.show()
            self.w_carrito.raise_()
            self.w_carrito.activateWindow()

        # 3. Refresco de datos en tiempo real
        if self.w_carrito.isVisible():
            self.w_carrito.actualizar_tabla()

    def abrir_carrito(self):
        if self.w_carrito is None:
            self.w_carrito = CartWindow(self.cart_service)
        
        self.w_carrito.actualizar_tabla() # Refrescar datos
        self.w_carrito.show()
        self.w_carrito.raise_()
        self.w_carrito.activateWindow()

    def abrir_historial(self):
        # El historial se recarga solo al iniciarse
        self.w_historial = HistoryWindow(self)
        self.w_historial.show()

    def abrir_creditos(self):
        self.w_creditos = CreditsWindow(self)
        self.w_creditos.show()

    def abrir_stats(self):
        """
        Solicita contraseña de gerente antes de mostrar la información sensible.
        """
        # --- BLOQUE DE SEGURIDAD ---
        password, ok = QInputDialog.getText(
            self, 
            "Acceso Restringido", 
            "🔒 Área Gerencial\nIngrese la contraseña:", 
            QLineEdit.Password
        )
        
        if not ok: return
        
        # --- DEFINIR CONTRASEÑA AQUÍ ---
        CLAVE_GERENTE = "Galpon950"
        
        if password != CLAVE_GERENTE:
            QMessageBox.warning(self, "Acceso Denegado", "La contraseña ingresada es incorrecta.")
            return
        # ---------------------------

        # Si la contraseña es correcta, procedemos a abrir la ventana normalmente
        from ui.stats_window import StatsWindow # Import local para evitar ciclos si es necesario
        
        if not hasattr(self, 'stats_window') or self.stats_window is None:
            self.stats_window = StatsWindow(self)
        
        self.stats_window.show()
        self.stats_window.activateWindow() # Traer al frente

    def abrir_gestor_stock(self):
        try:
            from ui.widgets import StockManagerDialog
            from logic.constants import MENU_CONFIG
            
            dialog = StockManagerDialog(self, self.data_context, MENU_CONFIG)
            
            # El programa se queda "esperando" aquí mientras el Gestor de Stock esté abierto
            dialog.exec()
            
            # 🆕 CORRECCIÓN: Al cerrarse el Gestor (con la X o tecla Esc), 
            # forzamos el refresco de las tablas sin preguntar si fue "Accepted".
            for vista_cacheada in self.catalogo_view.active_views.values():
                if hasattr(vista_cacheada, 'refrescar'):
                    vista_cacheada.refrescar()
                
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"No se pudo abrir el gestor de stock:\n{e}")
