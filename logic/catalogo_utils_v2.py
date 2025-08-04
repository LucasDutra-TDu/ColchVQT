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

    if "MEDIDA (LARG-ANCH-ESP)" in row or "SOPORTA (PorPlaza)" in row:
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
        if 'SOPORTA (PorPlaza)' in row and pd.notnull(row['SOPORTA (PorPlaza)']):
            partes.append(f"PesoSoportado: '{row['SOPORTA (PorPlaza)']}'")

    elif tipo == "otros":
        partes += [
            f"Caracteristicas: {row.get('CARACTERISTICAS', '-')}",
            f"Modelo: {row.get('MODELO', '-')}"
        ]

    for key in ['EFECTIVO/TRANSF', 'DEBIT/CREDIT', '3 CUOTAS', '6 CUOTAS']:
        if key in row and pd.notnull(row[key]):
            partes.append(f"{key}: {row[key]}")

    return "\n".join(partes)

def buscar_por_codigo(sheets: dict, codigo: str) -> pd.DataFrame:
    """
    Busca el código de producto (coincidencia parcial, insensible a mayúsculas) en las hojas 'GENERAL' y 'OTROS'.
    Retorna un DataFrame limpio con columnas según su categoría, agregando una columna de origen.
    """
    if not isinstance(codigo, str):
        codigo = str(codigo)

    resultados = []

    for hoja, categoria in [('GENERAL', 'colchones'), ('OTROS', 'otros')]:
        df = sheets.get(hoja, pd.DataFrame()).copy()
        if df.empty:
            continue

        df.columns = df.columns.str.strip().str.upper()

        col_codigo = next((col for col in df.columns if col in ['CÓDIGO', 'CODIGO']), None)
        if not col_codigo:
            continue

        filtrado = df[df[col_codigo].astype(str).str.contains(codigo, case=False, na=False)]
        if filtrado.empty:
            continue

        columnas_deseadas = [col for col in CAMPOS_CATALOGO[categoria] if col in filtrado.columns]
        vista = filtrado[columnas_deseadas].copy()
        vista.insert(0, "ORIGEN", hoja)  # Añade columna de origen
        resultados.append(vista)

    if resultados:
        return pd.concat(resultados, ignore_index=True)
    return pd.DataFrame()
