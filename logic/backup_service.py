# logic/backup_service.py
"""
Backup automático de los datos críticos de negocio.

Por qué existe: ventas.db, inventario.db y proveedores.json son la ÚNICA
copia del historial de ventas, stock y cuentas con proveedores. No están
versionados en git (correctamente, son datos, no código) pero tampoco había
ningún otro respaldo: un disco roto significaba perder todo.

Este módulo copia esos archivos a data/backups/<timestamp>/ al iniciar la
app, y conserva solo los últimos N snapshots para no crecer sin límite.

Reglas de diseño:
- Nunca debe impedir que la app arranque: cualquier error se loggea y se
  ignora (ver logic/log_service.py).
- Las bases SQLite se copian con el "Online Backup API" de sqlite3
  (Connection.backup), que produce una copia consistente aunque hubiera
  una transacción en curso, en vez de una copia de archivo "cruda".
"""

import shutil
import sqlite3
import sys
import datetime
from pathlib import Path

from logic.log_service import log_error, log_warning

# --- BRÚJULA UNIVERSAL (mismo patrón que el resto del proyecto) ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_path()
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"

# Bases de datos SQLite a respaldar con el backup API (copia consistente)
ARCHIVOS_SQLITE = ["ventas.db", "inventario.db"]

# Archivos planos a respaldar con una copia simple
ARCHIVOS_PLANOS = ["proveedores.json"]

# Cuántos snapshots conservar como máximo (se descartan los más viejos)
MAX_BACKUPS_A_CONSERVAR = 30


def _respaldar_sqlite(origen: Path, destino: Path) -> bool:
    """Copia consistente de una base SQLite usando el backup API nativo."""
    con_origen = None
    con_destino = None
    try:
        con_origen = sqlite3.connect(str(origen))
        con_destino = sqlite3.connect(str(destino))
        con_origen.backup(con_destino)
        return True
    finally:
        if con_destino is not None:
            con_destino.close()
        if con_origen is not None:
            con_origen.close()


def _limpiar_backups_antiguos():
    """Conserva solo los últimos MAX_BACKUPS_A_CONSERVAR snapshots."""
    if not BACKUP_DIR.exists():
        return
    carpetas = sorted(
        (d for d in BACKUP_DIR.iterdir() if d.is_dir()),
        key=lambda d: d.name,
        reverse=True,
    )
    for vieja in carpetas[MAX_BACKUPS_A_CONSERVAR:]:
        shutil.rmtree(vieja, ignore_errors=True)


def hacer_backup_datos() -> bool:
    """
    Crea un snapshot con timestamp de las bases de datos y archivos críticos.
    Se llama una vez al iniciar la app (ver main.py). Devuelve True si el
    backup se completó (aunque sea parcialmente, ej: algún archivo no
    existía todavía), False solo si falló algo inesperado.
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        carpeta_backup = BACKUP_DIR / timestamp

        algo_respaldado = False

        for nombre in ARCHIVOS_SQLITE:
            origen = DATA_DIR / nombre
            if origen.exists() and origen.stat().st_size > 0:
                carpeta_backup.mkdir(parents=True, exist_ok=True)
                try:
                    _respaldar_sqlite(origen, carpeta_backup / nombre)
                    algo_respaldado = True
                except Exception as e:
                    log_error(f"Backup: fallo al respaldar '{nombre}': {e}")

        for nombre in ARCHIVOS_PLANOS:
            origen = DATA_DIR / nombre
            if origen.exists():
                carpeta_backup.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(origen, carpeta_backup / nombre)
                    algo_respaldado = True
                except Exception as e:
                    log_error(f"Backup: fallo al respaldar '{nombre}': {e}")

        if not algo_respaldado:
            log_warning("Backup: no se encontró ningún archivo de datos para respaldar (¿primer arranque?).")

        _limpiar_backups_antiguos()
        return True

    except Exception as e:
        log_error(f"Backup: fallo inesperado creando el snapshot de datos: {e}")
        return False
