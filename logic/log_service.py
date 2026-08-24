# logic/log_service.py
"""
Logging mínimo a archivo para rutas críticas de la aplicación.

Por qué existe: la app se compila con PyInstaller en modo --windowed
(sin consola), así que cualquier print() en producción no lo ve nadie.
Este módulo escribe además a un archivo (data/app.log) para que quede
rastro de errores silenciosos (ej: fallos al descontar stock, fallos
de backup, etc.) que hoy solo se veían con print().

No reemplaza excepciones ni cambia el flujo de control de quien lo llama:
solo dejamos constancia. Si el logging en sí falla (disco lleno, permisos),
nunca debe tirar abajo la app.
"""

import sys
import datetime
from pathlib import Path

# --- BRÚJULA UNIVERSAL (mismo patrón que el resto del proyecto) ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_path()
LOG_PATH = BASE_DIR / "data" / "app.log"

# Tamaño máximo antes de rotar el log a un .bak (evita crecimiento indefinido)
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB


def _rotar_si_corresponde():
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > MAX_LOG_BYTES:
            backup_path = LOG_PATH.with_suffix(".log.bak")
            LOG_PATH.replace(backup_path)
    except Exception:
        pass  # Rotar el log nunca debe romper la app


def _escribir(nivel: str, mensaje: str):
    # Siempre imprimimos a stdout también (equivalente al comportamiento
    # anterior basado en print(), útil si se corre desde una consola en dev).
    print(f"[{nivel}] {mensaje}")
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _rotar_si_corresponde()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{nivel}] {mensaje}\n")
    except Exception:
        # El logging es una red de contención, no una fuente de nuevos crashes.
        pass


def log_info(mensaje: str):
    _escribir("INFO", mensaje)


def log_warning(mensaje: str):
    _escribir("WARNING", mensaje)


def log_error(mensaje: str):
    _escribir("ERROR", mensaje)
