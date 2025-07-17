#main.py

import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from logic.data_loader import descargar_archivo, cargar_hojas
from logic.constants import LOCAL_FILENAME, messages

def main():
    print(f"[INFO] {messages['logs']['inicio_aplicacion']}")
    app = QApplication(sys.argv)

    ok, usando_local = descargar_archivo()

    if not ok:
        QMessageBox.critical(None, "Error", messages["errors"]["fallo_descarga"])
        print("[ERROR] " + messages["errors"]["fallo_descarga"])
        sys.exit(1)

    if usando_local:
        QMessageBox.warning(None, "Aviso", messages["logs"]["usando_local"])
        print("[WARNING] " + messages["logs"]["usando_local"])

    sheets = cargar_hojas()
    window = MainWindow(sheets)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
