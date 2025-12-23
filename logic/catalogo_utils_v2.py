# logic\catalogo_utils_v2.py

from PySide6.QtWidgets import QApplication
from logic.constants import CAMPOS_CATALOGO
import pandas as pd

def obtener_df_por_hoja(sheets: dict, hoja: str) -> pd.DataFrame:
    """
    Limpia y normaliza el DataFrame correspondiente a una hoja de Excel.
    - Normaliza nombres de columnas.
    - Elimina filas completamente vacías.
    """
    df = sheets.get(hoja, pd.DataFrame()).copy()
    if df.empty:
        return pd.DataFrame() # Devuelve DF vacío
        
    df.columns = df.columns.str.strip().str.upper()
    df = df.dropna(how='all')
    return df

def filtrar_por_proveedor(df: pd.DataFrame, proveedor: str) -> pd.DataFrame:
    """
    Filtra el DataFrame por el valor exacto de la columna 'PROVEEDOR'.
    """
    return df[df['PROVEEDOR'] == proveedor].copy()

def obtener_proveedores(df: pd.DataFrame) -> list[str]:
    """
    Retorna una lista ordenada de proveedores únicos y no nulos del DataFrame.
    """
    return sorted(df['PROVEEDOR'].dropna().unique().tolist())

def copiar_al_portapapeles(texto: str):
    QApplication.clipboard().setText(texto)

def copiar_info_colchones(row: pd.Series):
    texto = formatear_info_para_copiar(row, tipo="colchones")
    copiar_al_portapapeles(texto)

def copiar_info_otros(row: pd.Series):
    texto = formatear_info_para_copiar(row, tipo="otros")
    copiar_al_portapapeles(texto)

def copiar_info_busqueda(row):
    """
    Detecta el tipo de producto basado en los campos presentes,
    y utiliza la función formatear_info_para_copiar para formatear.
    """
    tipo = "otros"

    if "MEDIDA (LARG-ANCH-ESP)" in row or "SOPORTA (PORPLAZA)" in row:
        tipo = "colchones"

    texto = formatear_info_para_copiar(row, tipo=tipo)
    QApplication.clipboard().setText(texto)

def formatear_info_para_copiar(row: pd.Series, tipo: str) -> str:
    partes = []
    
    if tipo == "colchones":
        partes += [
            f"Marca: '{row.get('PROVEEDOR', '-')}'",
            f"Modelo: '{row.get('MODELO', '-')}'",
            f"Medida: '{row.get('MEDIDA (LARG-ANCH-ESP)', '-')}'"
        ]
        if 'MATERIAL' in row and pd.notnull(row['MATERIAL']):
            partes.append(f"Material: '{row['MATERIAL']}'")
        if 'SOPORTA (PORPLAZA)' in row and pd.notnull(row['SOPORTA (PORPLAZA)']):
            partes.append(f"PesoSoportado: '{row['SOPORTA (PORPLAZA)']}'")

    elif tipo == "otros":
        partes += [
            f"Caracteristicas: {row.get('CARACTERISTICAS', '-')}",
            f"Modelo: {row.get('MODELO', '-')}"
        ]

    for key in ['EFECTIVO/TRANSF', 'DEBIT/CREDIT']:
        if key in row and pd.notnull(row[key]):
            partes.append(f"{key}: {row[key]}")

    return "\n".join(partes)

def buscar_por_nombre(sheets: dict, termino_busqueda: str) -> pd.DataFrame:
    """
    Busca un término en la columna 'MODELO' de las hojas 'GENERAL' y 'OTROS'.
    """
    
    if not sheets:
        print("El diccionario de hojas está vacío.")
        return pd.DataFrame()

    # --- ¡CAMBIO CLAVE AQUÍ! ---
    # 1. Obtenemos y LIMPIAMOS/NORMALIZAMOS las hojas ANTES de usarlas.
    df_general = obtener_df_por_hoja(sheets, 'GENERAL')
    df_otros = obtener_df_por_hoja(sheets, 'OTROS')
    
    # 2. Concatenar las hojas (ya limpias)
    hojas_para_concatenar = []
    if not df_general.empty:
        hojas_para_concatenar.append(df_general)
    if not df_otros.empty:
        hojas_para_concatenar.append(df_otros)

    if not hojas_para_concatenar:
        print("No se encontraron datos en 'GENERAL' u 'OTROS' tras la limpieza.")
        return pd.DataFrame()

    try:
        # Ahora 'df_completo' tendrá columnas normalizadas
        df_completo = pd.concat(hojas_para_concatenar, ignore_index=True)
    except Exception as e:
        print(f"Error al concatenar 'GENERAL' y 'OTROS': {e}")
        return pd.DataFrame()
        
    # 3. El resto de la lógica ya es correcta...
    if 'MODELO' not in df_completo.columns:
        print("Error: La columna 'MODELO' no se encontró en 'GENERAL' u 'OTROS'.")
        return pd.DataFrame()

    # (Asegurarse de que MODELO sea string, etc.)
    df_completo['MODELO'] = df_completo['MODELO'].astype(str)
    
    df_filtrado = df_completo[
        df_completo['MODELO'].str.contains(
            termino_busqueda, case=False, na=False
        )
    ]
    
    return df_filtrado