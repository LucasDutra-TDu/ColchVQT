# logic\catalogo_utils_v2.py

from PySide6.QtWidgets import QApplication
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