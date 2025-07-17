#logic\catalogo_utils.py

from PySide6.QtWidgets import QApplication
import pandas as pd

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
            f"Línea: {row.get('PROVEEDOR', '-')}",
            f"Producto: {row.get('CARACTERISTICAS', '-')}",
            f"Color: {row.get('MODELO', '-')}"
        ]

    # Precios comunes
    for key in ['EFECTIVO', 'TRANSF/DEBIT/CREDIT', '3 CUOTAS', '6 CUOTAS']:
        if key in row and pd.notnull(row[key]):
            if key.startswith("3") or key.startswith("6"):
                cuotas = int(key[0])
                partes.append(f"{key}: ${row[key]} ({cuotas}x ${int(row[key]) // cuotas})")
            else:
                partes.append(f"{key}: ${row[key]}")

    return "\n".join(partes)


def copiar_al_portapapeles(texto: str):
    QApplication.clipboard().setText(texto)
