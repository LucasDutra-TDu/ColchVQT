import pandas as pd
from typing import List, Dict, Optional

# --- Lógica de Acceso a Datos (Data Access) ---

def obtener_df_por_hoja(sheets: Dict[str, pd.DataFrame], hoja_nombre: str) -> pd.DataFrame:
    """
    Obtiene y normaliza una hoja del diccionario de DataFrames.
    """
    df = sheets.get(hoja_nombre, pd.DataFrame()).copy()
    if df.empty:
        return pd.DataFrame()
        
    # Normalización estándar: Trim y Mayúsculas
    df.columns = df.columns.str.strip().str.upper()
    
    # Limpieza de datos basura
    df.dropna(how='all', inplace=True)
    return df

def filtrar_por_proveedor(df: pd.DataFrame, proveedor: str) -> pd.DataFrame:
    """Retorna un subconjunto de datos filtrado por proveedor."""
    if 'PROVEEDOR' not in df.columns:
        return pd.DataFrame()
    return df[df['PROVEEDOR'] == proveedor].copy()

def obtener_proveedores_unicos(df: pd.DataFrame) -> List[str]:
    """Retorna lista ordenada de proveedores únicos."""
    if 'PROVEEDOR' not in df.columns:
        return []
    return sorted(df['PROVEEDOR'].dropna().unique().tolist())

# --- Lógica de Búsqueda (Search Service) ---

def buscar_producto_por_modelo(sheets: Dict[str, pd.DataFrame], termino: str) -> pd.DataFrame:
    """
    Busca productos cuyo MODELO coincida parcialmente con el término dado.
    Busca en las hojas 'GENERAL' y 'OTROS'.
    """
    if not termino:
        return pd.DataFrame()

    # Estrategia: Obtener -> Limpiar -> Concatenar -> Filtrar
    dfs_a_concatenar = []
    
    for nombre_hoja in ['GENERAL', 'OTROS']:
        df_temp = obtener_df_por_hoja(sheets, nombre_hoja)
        if not df_temp.empty:
            dfs_a_concatenar.append(df_temp)

    if not dfs_a_concatenar:
        return pd.DataFrame()

    try:
        df_completo = pd.concat(dfs_a_concatenar, ignore_index=True)
    except Exception as e:
        print(f"[ERROR] Fallo al concatenar hojas para búsqueda: {e}")
        return pd.DataFrame()

    if 'MODELO' not in df_completo.columns:
        return pd.DataFrame()

    # Búsqueda Case-Insensitive
    mask = df_completo['MODELO'].astype(str).str.contains(termino, case=False, na=False)
    return df_completo[mask]

# --- NOTA DE MIGRACIÓN ---
# Las funciones de copiado (copiar_info_colchones, etc.) han sido ELIMINADAS.
# La lógica de formateo de texto ahora vive en 'logic/financiero.py' o
# se maneja directamente en la UI.
# La acción de copiar al portapapeles ahora es exclusiva