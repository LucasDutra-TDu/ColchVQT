# logic/catalogo_service.py

import pandas as pd
from typing import List, Dict, Optional
from logic.stock_service import inyectar_stock_a_df

# --- Lógica de Acceso a Datos (Data Access) ---

def obtener_df_por_hoja(sheets: Dict[str, pd.DataFrame], hoja_nombre: str) -> pd.DataFrame:
    """
    Obtiene y normaliza una hoja del diccionario de DataFrames.
    AHORA CON STOCK INYECTADO.
    """
    df = sheets.get(hoja_nombre, pd.DataFrame()).copy()
    if df.empty:
        return pd.DataFrame()
        
    df.columns = df.columns.str.strip().str.upper()
    df.dropna(how='all', inplace=True)
    
    # Inyectamos el stock antes de devolvérselo a la interfaz
    df = inyectar_stock_a_df(df)
    
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
    """
    if not termino:
        return pd.DataFrame()

    dfs_a_concatenar = []
    
    for nombre_hoja in ['GENERAL', 'OTROS']:
        # NOTA: obtener_df_por_hoja ya nos devuelve el DF con la columna STOCK_ACTUAL inyectada.
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

    mask = df_completo['MODELO'].astype(str).str.contains(termino, case=False, na=False)
    return df_completo[mask]

def formatear_producto_para_clipboard(row: dict) -> str:
    """
    Genera un texto ordenado del producto para pegar en WhatsApp/Redes.
    Detecta automáticamente si es Colchón o Mueble/Otro.
    """
    partes = []
    
    # 1. Detección de Tipo
    es_colchon = "MEDIDA (LARG-ANCH-ESP)" in row or "SOPORTA (PORPLAZA)" in row

    if es_colchon:
        # --- FORMATO COLCHONES (Sin cambios) ---
        marca = row.get('PROVEEDOR', '-')
        modelo = row.get('MODELO', '-')
        medida = row.get('MEDIDA (LARG-ANCH-ESP)', '-')
        
        partes.append(f"🛏️ *{marca} - {modelo}*")
        partes.append(f"📏 Medida: {medida}")
        
        if row.get('MATERIAL') and str(row.get('MATERIAL')) != '-': 
            partes.append(f"🧶 Material: {row.get('MATERIAL')}")
        
        if row.get('SOPORTA (PORPLAZA)') and str(row.get('SOPORTA (PORPLAZA)')) != '-':
            partes.append(f"🏋️ Soporta: {row.get('SOPORTA (PORPLAZA)')}")

    else:
        # --- FORMATO MUEBLES / OTROS (CORREGIDO) ---
        # El usuario pidió: Primero Modelo, luego Características.
        
        modelo = row.get('MODELO', '')
        caracteristicas = row.get('CARACTERISTICAS', row.get('DESCRIPCION', ''))
        
        # 1. Modelo
        if modelo and str(modelo) not in ['-', '', 'None']:
            partes.append(f"🏷️ Modelo: {modelo}")
            
        # 2. Características (Con el subtítulo solicitado)
        if caracteristicas and str(caracteristicas) not in ['-', '', 'None']:
            partes.append(f"📦 Caracteristicas: {caracteristicas}")

    partes.append("") # Espacio separador

    # 2. Precios y Financiación
    cols_precios = [
        ('EFECTIVO/TRANSF', '💵 Efectivo/Transf'),
        ('DEBIT/CREDIT', '💳 Lista/Tarjeta')
    ]

    for key_col, etiqueta in cols_precios:
        val = row.get(key_col)
        # Filtramos valores vacíos, nulos o guiones
        if val and str(val).strip() not in ['', '-', 'None', '$0', '$ 0']:
            partes.append(f"{etiqueta}: {val}")

    return "\n".join(partes)