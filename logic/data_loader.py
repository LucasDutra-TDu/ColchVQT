# logic\data_loader.py

import os
import sys
import requests
import pandas as pd
from logic.constants import LOCAL_FILENAME, messages

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
    """
    try:
        excel_file = pd.ExcelFile(path)
        if not excel_file.sheet_names:
            return False
        for hoja in excel_file.sheet_names:
            df = excel_file.parse(hoja, nrows=1)
            if len(df.columns) > 0:
                return True
        return False
    except Exception:
        return False

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
        # persistente. os.replace es atómico dentro del mismo filesystem.
        os.replace(archivo_temporal, local_file)

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
