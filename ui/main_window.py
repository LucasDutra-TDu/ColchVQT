from PySide6.QtWidgets import QMainWindow, QStackedWidget
from ui.catalogo_v2 import CatalogoWidgetV2
from logic.constants import messages


class MainWindow(QMainWindow):
    def __init__(self, sheets):
        super().__init__()

        # Configuración inicial de la ventana
        self.setWindowTitle(messages["ui"]["app_title"])
        self.resize(1100, 800)

        # Inicializar widgets
        self.catalogo_widget = CatalogoWidgetV2(sheets)

        # Diccionario de vistas disponibles
        self.vistas = {
            "catalogo": self.catalogo_widget
            # Podés agregar más vistas aquí en el futuro
        }

        # Stacked widget para manejar navegación entre vistas
        self.stack = QStackedWidget(self)
        for widget in self.vistas.values():
            self.stack.addWidget(widget)

        self.setCentralWidget(self.stack)

        # Mostrar la vista inicial
        self.navegar_a("catalogo")

    def navegar_a(self, nombre_widget: str):
        """
        Cambia la vista actual al widget indicado por su nombre.
        """
        if nombre_widget in self.vistas:
            self.stack.setCurrentWidget(self.vistas[nombre_widget])
        else:
            print(f"[WARNING] Vista desconocida: '{nombre_widget}'")
