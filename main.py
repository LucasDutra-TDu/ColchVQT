import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from logic.data_loader import descargar_archivo, cargar_hojas
from logic.constants import messages
from logic.cart_service import CartService

def show_critical_error(title: str, message: str):
    """Helper para mostrar errores críticos antes de que exista la ventana principal."""
    app_instance = QApplication.instance()
    if not app_instance:
        app_instance = QApplication(sys.argv)
    QMessageBox.critical(None, title, message)
    print(f"[CRITICAL] {message}")

def main():
    print(f"[INFO] {messages['logs']['inicio_aplicacion']}")
    
    # Instanciamos QApplication primero para poder usar QMessageBox si algo falla
    app = QApplication(sys.argv)

    try:
        # 1. Fase de Sincronización (Red)
        # TODO: Mover esto a un QThread + Splash Screen para no congelar la UI
        ok_descarga, usando_local = descargar_archivo()

        if not ok_descarga:
            error_msg = messages["errors"].get("fallo_descarga", "Error desconocido en descarga.")
            QMessageBox.critical(None, "Error de Inicialización", error_msg)
            print(f"[ERROR] {error_msg}")
            sys.exit(1)

        if usando_local:
            warn_msg = messages["logs"].get("usando_local", "Usando archivo local.")
            # Sugerencia: Considerar quitar este popup bloqueante en el futuro y usar una barra de estado.
            QMessageBox.warning(None, "Aviso de Conexión", warn_msg)
            print(f"[WARNING] {warn_msg}")

        # 2. Fase de Carga de Datos (I/O)
        sheets = cargar_hojas()
        cart_service = CartService()

        # 3. Inyección y Lanzamiento
        window = MainWindow(sheets,cart_service)
        window.show()
        
        sys.exit(app.exec())

    except Exception as e:
        # Captura cualquier error no controlado durante el arranque
        error_trace = traceback.format_exc()
        print(f"[FATAL ERROR] {e}\n{error_trace}")
        QMessageBox.critical(None, "Error Fatal", f"Ocurrió un error inesperado:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()