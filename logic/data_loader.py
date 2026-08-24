# logic\data_loader.py

import os
import sys
import time
import requests
import pandas as pd
from logic.constants import LOCAL_FILENAME, messages

# Reintentos para el os.replace() final (ver _reemplazar_con_reintentos).
REEMPLAZO_MAX_INTENTOS = 5
REEMPLAZO_ESPERA_SEGUNDOS = 0.4

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1gBXFjr48AqRrzTAl-47fY5aq05NcpDZZpR9nEYsQI4U/export?format=xlsx"

def get_base_dir():
    """
    Obtiene la carpeta base donde guardar el archivo descargado.
    En .exe: carpeta del ejecutable
    En desarrollo: carpeta del main.py
    """
    if getattr(sys, 'frozen', False):
        # Ejecutando como .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Ejecutando como script
        base_dir = os.path.dirname(os.path.abspath(__file__))  # logic/
        base_dir = os.path.abspath(os.path.join(base_dir, ".."))  # subir a nivel de main.py
    return base_dir

def get_data_dir():
    """
    Retorna la carpeta data/ donde se guarda el archivo descargado
    """
    data_dir = os.path.join(get_base_dir(), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def get_local_file_path():
    """
    Ruta completa al archivo .xlsx local persistente
    """
    return os.path.join(get_data_dir(), LOCAL_FILENAME)

def _es_excel_valido(path) -> bool:
    """
    Verifica que el archivo sea un Excel legible y tenga al menos una hoja
    con columnas reales, antes de arriesgarnos a pisar con él la única
    copia local de respaldo. Protege contra el caso de que Google devuelva
    una respuesta 200 con contenido inválido (ej: una página de error, o
    una descarga cortada a la mitad).

    Usa 'with' para cerrar el archivo explícitamente: pd.ExcelFile() abre
    un handle sobre 'path' que en Windows queda tomado hasta que se cierra
    (a diferencia de Linux, donde el reference-counting de CPython lo
    libera enseguida). Sin el 'with', el handle podía seguir abierto justo
    cuando el llamador intenta hacer os.replace() sobre este mismo archivo
    unos milisegundos después -- causando el "[WinError 32] El proceso no
    tiene acceso al archivo..." que se creyó primero un problema de OneDrive
    (hallazgo 24/08/2026, revisado el mismo día al reproducirse igual en
    una carpeta local sin ningún sync de por medio).
    """
    try:
        with pd.ExcelFile(path) as excel_file:
            if not excel_file.sheet_names:
                return False
            for hoja in excel_file.sheet_names:
                df = excel_file.parse(hoja, nrows=1)
                if len(df.columns) > 0:
                    return True
            return False
    except Exception:
        return False

def _reemplazar_con_reintentos(origen, destino):
    """
    os.replace(origen, destino) con reintentos ante bloqueos transitorios
    del archivo destino (ej: un antivirus escaneándolo, un backup en la
    nube tocándolo, u otro handle tardando en liberarse).

    Hallazgo 24/08/2026: esto falló en la práctica con "[WinError 32] El
    proceso no tiene acceso al archivo porque está siendo utilizado por
    otro proceso". Se sospechó primero de OneDrive (el proyecto vivía en
    una carpeta sincronizada), pero se reprodujo igual el mismo día en una
    carpeta 100% local sin ningún sync de por medio -- la causa real era
    que _es_excel_valido() dejaba abierto el handle de pd.ExcelFile() sobre
    este mismo archivo (ver el 'with' agregado ahí). Con eso corregido,
    estos reintentos ya no deberían hacer falta en el caso normal; se
    dejan como red de contención ante bloqueos externos genuinos (ej.
    antivirus, backup en la nube si el proyecto volviera a vivir en una
    carpeta sincronizada). Si sigue bloqueado después de todos los
    intentos, se re-lanza la excepción original y el llamador cae al
    comportamiento normal de fallback (usar el archivo local existente).
    """
    ultimo_error = None
    for intento in range(1, REEMPLAZO_MAX_INTENTOS + 1):
        try:
            os.replace(origen, destino)
            return
        except (PermissionError, OSError) as e:
            ultimo_error = e
            if intento < REEMPLAZO_MAX_INTENTOS:
                time.sleep(REEMPLAZO_ESPERA_SEGUNDOS)
    raise ultimo_error


def descargar_archivo():
    """
    Intenta descargar el archivo desde Google Sheets y guardarlo en data/.
    Si falla, o si lo descargado no resulta ser un Excel válido, usa la
    última versión local persistente SIN pisarla.
    """
    local_file = get_local_file_path()
    archivo_temporal = local_file + ".tmp"

    try:
        print(f"[INFO] {messages['logs']['descargando']}")
        r = requests.get(GOOGLE_SHEET_URL, timeout=100)
        r.raise_for_status()

        with open(archivo_temporal, 'wb') as f:
            f.write(r.content)

        if not _es_excel_valido(archivo_temporal):
            raise ValueError("El archivo descargado no es un Excel válido o no tiene datos.")

        # Recién acá, con el archivo ya validado, pisamos la copia
        # persistente. os.replace es atómico dentro del mismo filesystem;
        # se reintenta ante bloqueos transitorios (ver _reemplazar_con_reintentos).
        _reemplazar_con_reintentos(archivo_temporal, local_file)

        print(f"[INFO] {messages['logs']['descarga_exitosa']}")
        return local_file, False  # archivo descargado exitosamente
    except Exception as e:
        print(f"[WARNING] {messages['errors']['fallo_descarga']} {e}")
        if os.path.exists(archivo_temporal):
            try:
                os.remove(archivo_temporal)
            except OSError:
                pass
        if os.path.exists(local_file):
            print(f"[INFO] {messages['logs']['usando_local']}")
            return local_file, True  # se usa archivo local (intacto)
        else:
            print(f"[ERROR] {messages['errors']['fallo_total']}")
            return None, False  # no hay archivo local disponible

def cargar_hojas(path=None):
    """
    Carga las hojas del archivo Excel especificado o usa el archivo local persistente.
    """
    if path is None:
        path = get_local_file_path()
    return pd.read_excel(path, sheet_name=None)
