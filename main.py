import sys
import os
import faulthandler
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from logic.data_loader import descargar_archivo, cargar_hojas
from logic.constants import messages
from logic.cart_service import CartService
from logic.log_service import log_info, log_warning, log_error
from logic.backup_service import hacer_backup_datos

# Comando PyInstaller
# pyinstaller --onedir --windowed --icon="elgalpon.ico" --name="Colchoneria Gestion x.x" main.py
# & "C:\Users\lucas\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m PyInstaller --onedir --windowed --icon="elgalpon.ico" --name="Colchoneria Gestion x.x" main.py

# --- RED DE SEGURIDAD: crashes nativos (Fase 3.1 de la auditoría) ---
# faulthandler intercepta crashes nativos (access violation / segfault en
# Qt, freetype, drivers gráficos, etc.) que un try/except de Python NO
# puede atrapar -- son exactamente el tipo de falla que causó que la app
# se cerrara sin dejar ningún traceback ni entrada en data/app.log (ver
# hallazgo del 24/08/2026: access violation dentro de un QMessageBox.warning
# llamado antes de que existiera la ventana principal). Se deja habilitado
# de forma permanente: si vuelve a pasar algo similar, data/crash_diag.log
# va a tener el detalle en vez de un cierre silencioso.
try:
    _base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    _crash_log_path = os.path.join(_base_dir, "data", "crash_diag.log")
    os.makedirs(os.path.dirname(_crash_log_path), exist_ok=True)
    _crash_log_file = open(_crash_log_path, "a", encoding="utf-8")
    faulthandler.enable(file=_crash_log_file, all_threads=True)
except Exception:
    pass
# --- FIN RED DE SEGURIDAD ---


def show_critical_error(title: str, message: str):
    """Helper para mostrar errores críticos antes de que exista la ventana principal."""
    app_instance = QApplication.instance()
    if not app_instance:
        app_instance = QApplication(sys.argv)
    QMessageBox.critical(None, title, message)
    print(f"[CRITICAL] {message}")

def main():
    log_info(messages['logs']['inicio_aplicacion'])

    # Instanciamos QApplication primero para poder usar QMessageBox si algo falla
    app = QApplication(sys.argv)

    try:
        # 0. Fase de Backup (Red de Contención)
        # Respaldamos ventas.db, inventario.db y proveedores.json ANTES de
        # cualquier otra operación. Nunca debe bloquear el arranque: un
        # fallo acá se loggea (data/app.log) y la app sigue igual.
        if hacer_backup_datos():
            log_info("Backup de datos de seguridad creado correctamente.")
        else:
            log_warning("No se pudo crear el backup de datos al iniciar (ver data/app.log).")

        # 1. Fase de Sincronización (Red)
        # TODO: Mover esto a un QThread + Splash Screen para no congelar la UI
        ok_descarga, usando_local = descargar_archivo()

        if not ok_descarga:
            error_msg = messages["errors"].get("fallo_descarga", "Error desconocido en descarga.")
            QMessageBox.critical(None, "Error de Inicialización", error_msg)
            log_error(error_msg)
            sys.exit(1)

        if usando_local:
            # Hallazgo 24/08/2026: acá había un QMessageBox.warning() BLOQUEANTE
            # mostrado antes de que existiera la ventana principal. La primera
            # vez que este camino se ejecutó de verdad en la máquina de Lucas
            # (la descarga siempre había funcionado hasta entonces), ese popup
            # produjo un "access violation" nativo -- un crash que un
            # try/except de Python no puede atrapar, y por eso la app se
            # cerraba sin ningún error ni traceback. Se saca el popup de acá
            # (antes de que exista ninguna ventana) y el aviso se muestra
            # como mensaje NO bloqueante en la barra de estado de MainWindow,
            # una vez que la ventana ya está construida y mostrada. El log
            # sigue quedando en data/app.log de todas formas.
            warn_msg = messages["logs"].get("usando_local", "Usando archivo local.")
            log_warning(warn_msg)

        # 2. Fase de Carga de Datos (I/O)
        # Si el .xlsx local está dañado o en un formato inválido, pd.read_excel
        # lanza una excepción. La capturamos acá puntualmente (en vez de dejar
        # que caiga en el catch genérico de más abajo) para mostrar un mensaje
        # claro y específico, y cerrar prolijamente -- sin intentar ninguna
        # recuperación automática (la descarga ya valida el .xlsx antes de
        # guardarlo, ver logic/data_loader.py::_es_excel_valido, así que este
        # caso debería ser muy raro en la práctica).
        try:
            sheets = cargar_hojas()
        except Exception as e:
            error_trace = traceback.format_exc()
            log_error(f"No se pudo leer el catálogo local (archivo dañado o formato inválido): {e}\n{error_trace}")
            QMessageBox.critical(
                None,
                "Catálogo dañado",
                "No se pudo abrir el archivo del catálogo de productos.\n\n"
                "El archivo local puede estar dañado o en un formato inválido.\n"
                "Contactá a soporte técnico para restaurar una copia de respaldo\n"
                "desde data/backups/ o volver a descargar el catálogo."
            )
            sys.exit(1)

        cart_service = CartService()

        # 3. Inyección y Lanzamiento
        window = MainWindow(sheets, cart_service, aviso_archivo_local=usando_local)
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        # Captura cualquier error no controlado durante el arranque
        error_trace = traceback.format_exc()
        log_error(f"[FATAL ERROR] {e}\n{error_trace}")
        QMessageBox.critical(None, "Error Fatal", f"Ocurrió un error inesperado:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()