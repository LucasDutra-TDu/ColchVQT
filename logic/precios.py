import pandas as pd
import math

def redondear_a_50_superior(valor: float) -> int:
    """
    Redondea el valor al múltiplo de 50 superior más cercano.
    """
    return int(math.ceil(valor / 50.0) * 50)

def calcular_precios_desde_fila(row: pd.Series) -> dict:
    """
    Dado un producto con costo base y campos de porcentaje por fila,
    devuelve los precios finales como enteros redondeados al múltiplo de 50 superior.
    Requiere que 'COSTO', 'PORC_EFECTIVO', 'PORC_TRANSF', 'PORC_3CUOTAS', 'PORC_6CUOTAS' existan en la fila.
    Si algún campo porcentaje es nulo, se asume como 0.
    """
    required_fields = ['COSTO', 'PORC_EFECTIVO', 'PORC_TRANSF', 'PORC_3CUOTAS', 'PORC_6CUOTAS']

    for field in required_fields:
        if field not in row:
            raise ValueError(f"Falta el campo requerido: '{field}' en la fila.")

    try:
        costo = float(row['COSTO'])
    except (ValueError, TypeError):
        raise ValueError("El campo 'COSTO' debe ser un valor numérico.")

    porc_efectivo = row['PORC_EFECTIVO'] if pd.notnull(row['PORC_EFECTIVO']) else 0
    porc_transf = row['PORC_TRANSF'] if pd.notnull(row['PORC_TRANSF']) else 0
    porc_3cuotas = row['PORC_3CUOTAS'] if pd.notnull(row['PORC_3CUOTAS']) else 0
    porc_6cuotas = row['PORC_6CUOTAS'] if pd.notnull(row['PORC_6CUOTAS']) else 0

    return {
        'EFECTIVO': redondear_a_50_superior(costo * (1 + porc_efectivo)),
        'TRANSF/DEBIT/CREDIT': redondear_a_50_superior(costo * (1 + porc_transf)),
        '3 CUOTAS': redondear_a_50_superior(costo * (1 + porc_3cuotas)),
        '6 CUOTAS': redondear_a_50_superior(costo * (1 + porc_6cuotas)),
    }
