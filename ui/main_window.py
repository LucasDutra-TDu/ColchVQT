# ui/main_window.py
from typing import Dict, Any
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar, QStatusBar, QPushButton, QWidget, QHBoxLayout
from PySide6.QtGui import QAction, QIcon

from ui.catalogo_view import CatalogoView
from ui.cart_window import CartWindow
from ui.history_window import HistoryWindow
from logic.cart_service import CartService

class MainWindow(QMainWindow):
    def __init__(self, data_context: Dict[str, Any], cart_service: CartService):
        super().__init__()
        self.data_context = data_context
        self.cart_service = cart_service # Guardamos referencia
        
        # Referencias a ventanas secundarias (para no abrirlas mil veces)
        self.w_carrito = None
        self.w_historial = None

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

        # Acción: Ver Historial
        action_hist = QAction("📜 Historial Ventas", self)
        action_hist.triggered.connect(self.abrir_historial)
        toolbar.addAction(action_hist)

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