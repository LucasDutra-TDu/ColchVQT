import pandas as pd
from typing import Dict
from logic.stock_db_handler import obtener_stock_todos, registrar_movimiento_stock

def inyectar_stock_a_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recibe un DataFrame del catálogo (Sheets) y le inyecta una nueva 
    columna 'STOCK_ACTUAL' consultando la base de datos local (SQLite).
    """
    if df.empty:
        return df

    # 1. Hacemos una copia profunda para no alterar el caché del Sheets
    df_con_stock = df.copy()

    # 2. Obtenemos el diccionario completo de stock desde SQLite
    # Formato: {'1000': 5, '2005': 0, 'S/C': 10}
    dict_stock_actual = obtener_stock_todos()

    # 3. Limpiamos la columna de códigos del DF para garantizar el match
    # Aseguramos que CÓDIGO (o CODIGO, o MODELO como fallback) exista.
    if 'CÓDIGO' in df_con_stock.columns:
        col_codigo = 'CÓDIGO'
    elif 'CODIGO' in df_con_stock.columns:
        col_codigo = 'CODIGO'
    elif 'MODELO' in df_con_stock.columns:
        col_codigo = 'MODELO'
    else:
        # Si no hay identificador, devolvemos sin stock
        df_con_stock['STOCK_ACTUAL'] = 'N/A'
        return df_con_stock

    # Convertimos la columna a string puro (limpiando '.0' si pandas lo hizo float)
    def clean_codigo(val):
        if pd.isna(val) or str(val).strip() in ['', '-']: return "S/C"
        try:
            if isinstance(val, (float, int)): return str(int(float(val))).strip()
            return str(val).strip()
        except:
            return str(val).strip()

    # Creamos una columna temporal para mapear de forma segura
    df_con_stock['_temp_codigo_limpio'] = df_con_stock[col_codigo].apply(clean_codigo)

    # 4. Mapeo Rápido (Pandas Map)
    # Si el código no existe en dict_stock_actual, fillna le asigna 0 por defecto.
    df_con_stock['STOCK_ACTUAL'] = df_con_stock['_temp_codigo_limpio'].map(dict_stock_actual).fillna(0).astype(int)

    # Limpiamos la columna temporal
    df_con_stock.drop(columns=['_temp_codigo_limpio'], inplace=True)

    return df_con_stock

def procesar_descuento_por_venta(items_vendidos: list, id_factura: int):
    """
    Recibe la lista de ítems de una venta y descuenta el stock.
    - items_vendidos: Lista de diccionarios (el mismo JSON que va a facturas)
    - id_factura: Para dejar registro en el historial.
    """
    for item in items_vendidos:
        # Obtenemos el código y cantidad (garantizando fallback)
        codigo = str(item.get("codigo", item.get("CÓDIGO", "S/C"))).strip()
        cantidad_vendida = int(item.get("cantidad", 1))
        modelo_nombre = item.get("modelo", item.get("MODELO", "Producto Desconocido"))

        # Si el código es 'S/C' (Sin Código), no restamos nada para evitar 
        # que todos los items genéricos compartan la misma bolsa de stock.
        if codigo == "S/C":
            continue

        # Al registrar una venta, la alteración es NEGATIVA
        detalle = f"Venta - Factura #{id_factura} ({modelo_nombre})"
        registrar_movimiento_stock(codigo, -cantidad_vendida, "VENTA", detalle)