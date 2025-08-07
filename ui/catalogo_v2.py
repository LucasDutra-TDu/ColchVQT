# logic\catalogo_v2.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QStackedLayout
from PySide6.QtGui import QKeySequence, QShortcut
from logic.constants import MENU_CONFIG, ESTILOS, CAMPOS_CATALOGO
from .views import build_menu_view, build_categoria_view, build_busqueda_view
from logic.catalogo_utils_v2 import buscar_por_codigo

class CatalogoWidgetV2(QWidget):
    def __init__(self, sheets):
        super().__init__()
        self.sheets = sheets
        self.stack = QStackedLayout()
        self.vistas = {}

        self._init_menu()
        self.setLayout(self.stack)

    def _init_menu(self):
        menu_view = build_menu_view(
            opciones=MENU_CONFIG,
            on_click=self._handle_menu_click,
            estilo_boton=ESTILOS['boton_menu']
        )
        self.vistas['menu'] = menu_view
        self.stack.addWidget(menu_view)

        # Atajos del menú principal (1–0)
        visible_keys = [k for k in MENU_CONFIG.keys() if MENU_CONFIG[k].get("tipo") in ("categoria", "busqueda")]
        for i, key in enumerate(visible_keys[:10]):
            key_seq = QKeySequence(str((i + 1) % 10))
            QShortcut(key_seq, menu_view).activated.connect(self._make_menu_shortcut_handler(key))

        # Escape vuelve al menú desde cualquier vista
        QShortcut(QKeySequence("Esc"), self).activated.connect(lambda: self.mostrar_vista("menu"))

    def _make_menu_shortcut_handler(self, key):
        return lambda: self._handle_menu_click(key)

    def _handle_menu_click(self, key):
        if MENU_CONFIG[key]["tipo"] == "busqueda":
            self._abrir_busqueda()
        else:
            self._abrir_submenu(key)

    def _abrir_submenu(self, categoria_key):
        config = MENU_CONFIG[categoria_key]
        tipo_producto = config.get("tipo_producto", "colchones")

        submenu = QWidget()
        layout = QVBoxLayout(submenu)

        hojas = config.get("hojas", [])
        for i, hoja in enumerate(hojas):
            boton = QPushButton(hoja)
            boton.setStyleSheet(ESTILOS['boton_menu'])
            boton.clicked.connect(lambda _, h=hoja: self._abrir_hoja(h, tipo_producto))
            layout.addWidget(boton)

            if i < 10:
                key_seq = QKeySequence(str((i + 1) % 10))
                QShortcut(key_seq, submenu).activated.connect(self._make_hoja_shortcut_handler(hoja, tipo_producto))

        boton_volver = QPushButton("Volver")
        boton_volver.setStyleSheet(ESTILOS['boton_volver'])
        boton_volver.clicked.connect(lambda: self.mostrar_vista("menu"))
        layout.addWidget(boton_volver)

        self.vistas[categoria_key] = submenu
        self.stack.addWidget(submenu)
        self.mostrar_vista(categoria_key)

    def _make_hoja_shortcut_handler(self, hoja, tipo_producto):
        return lambda: self._abrir_hoja(hoja, tipo_producto)

    def _abrir_hoja(self, hoja_key, tipo_producto):
        if hoja_key not in self.vistas:
            vista = build_categoria_view(
                key=hoja_key,
                sheets=self.sheets,
                volver_callback=lambda: self.mostrar_vista("menu"),
                tipo_producto=tipo_producto
            )
            self.vistas[hoja_key] = vista
            self.stack.addWidget(vista)
        self.mostrar_vista(hoja_key)

    def _abrir_busqueda(self):
        if "busqueda" not in self.vistas:
            vista = build_busqueda_view(
                on_buscar=lambda codigo: buscar_por_codigo(self.sheets, codigo),
                volver_callback=lambda: self.mostrar_vista("menu")
            )
            self.vistas["busqueda"] = vista
            self.stack.addWidget(vista)
        self.mostrar_vista("busqueda")

    def mostrar_vista(self, nombre):
        if nombre in self.vistas:
            self.stack.setCurrentWidget(self.vistas[nombre])
        elif isinstance(nombre, QWidget):
            self.stack.addWidget(nombre)
            self.stack.setCurrentWidget(nombre)
