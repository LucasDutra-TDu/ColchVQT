# ui/catalogo_view.py

from typing import Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QStackedLayout

# Imports de Lógica y Configuración
from logic.constants import MENU_CONFIG, ESTILOS
from logic.catalogo_service import buscar_producto_por_modelo
from logic.cart_service import CartService

# Imports de UI Builders
# NOTA: Asumimos que refactorizaremos 'views.py' pronto.
from .views import build_menu_view, build_categoria_view, build_busqueda_view

class CatalogoView(QWidget):
    def __init__(self, data_context: Dict[str, Any], cart_service: CartService):
        super().__init__()
        self.data_context = data_context
        self.cart_service = cart_service
        
        self.stack = QStackedLayout()
        self.active_views: Dict[str, QWidget] = {} 
        self.setLayout(self.stack)
        self._init_main_menu()

    def _init_main_menu(self):
        """Inicializa la vista raíz (Menú Principal)."""
        menu_view = build_menu_view(
            opciones=MENU_CONFIG,
            on_click=self._handle_menu_navigation,
            estilo_boton=ESTILOS.get('boton_menu', '')
        )
        self._add_view("menu", menu_view)

    def _handle_menu_navigation(self, key: str):
        """Callback centralizado para la navegación desde el menú principal."""
        config = MENU_CONFIG.get(key)
        if not config:
            return

        if config.get("tipo") == "busqueda":
            self._navigate_to_search()
        else:
            self._navigate_to_submenu(key, config)

    def _navigate_to_submenu(self, key: str, config: dict):
        """Navega (o crea) un submenú de categorías."""
        if key not in self.active_views:
            submenu_widget = self._build_submenu_widget(key, config)
            self._add_view(key, submenu_widget)
        
        self.show_view(key)

    def _build_submenu_widget(self, key: str, config: dict) -> QWidget:
        """Construye dinámicamente el widget de submenú."""
        # TODO: Idealmente, esto debería moverse a 'views.py' como 'build_submenu_view'
        # para mantener consistencia, pero por ahora lo encapsulamos aquí.
        tipo_producto = config.get("tipo_producto", "colchones")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Botones de Hojas (Categorías específicas)
        for hoja_nombre in config.get("hojas", []):
            btn = QPushButton(hoja_nombre)
            btn.setStyleSheet(ESTILOS.get('boton_menu', ''))
            # Usamos un closure seguro para capturar el valor de hoja_nombre
            btn.clicked.connect(self._create_category_callback(hoja_nombre, tipo_producto))
            layout.addWidget(btn)

        # Botón Volver
        btn_volver = QPushButton("Volver")
        btn_volver.setStyleSheet(ESTILOS.get('boton_volver', ''))
        btn_volver.clicked.connect(lambda: self.show_view("menu"))
        layout.addWidget(btn_volver)

        return widget

    def _create_category_callback(self, hoja: str, tipo: str):
        """Factory de callbacks para evitar problemas con lambdas en loops."""
        return lambda: self._navigate_to_sheet(hoja, tipo)

    def _navigate_to_sheet(self, sheet_key: str, product_type: str):
        if sheet_key not in self.active_views:
            view = build_categoria_view(
                parent_window=self,
                key=sheet_key,
                sheets=self.data_context,
                volver_callback=lambda: self.show_view("menu"),
                tipo_producto=product_type,
                cart_service=self.cart_service  # <--- PASARLO AQUÍ
            )
            self._add_view(sheet_key, view)
        self.show_view(sheet_key)

    def _navigate_to_search(self):
        if "busqueda" not in self.active_views:
            view = build_busqueda_view(
                parent_window=self,
                on_buscar=lambda codigo: buscar_producto_por_modelo(self.data_context, codigo),
                volver_callback=lambda: self.show_view("menu"),
                cart_service=self.cart_service # <--- PASARLO AQUÍ TAMBIÉN
            )
            self._add_view("busqueda", view)
        self.show_view("busqueda")

    def _add_view(self, name: str, widget: QWidget):
        self.active_views[name] = widget
        self.stack.addWidget(widget)

    def show_view(self, name: str):
        if name in self.active_views:
            self.stack.setCurrentWidget(self.active_views[name])
        else:
            print(f"[ERROR] Vista no encontrada: {name}")