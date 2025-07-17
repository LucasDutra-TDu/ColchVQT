#logic\catalogo_utils.py

from PySide6.QtWidgets import QApplication
import pandas as pd

def formatear_info_para_copiar(row: pd.Series, tipo: str) -> str:
    partes = []

    if tipo == "colchones":
        partes += [
            f"Marca: '{row['PROVEEDOR']}'",
            f"Modelo: '{row['MODELO']}'",
            f"Medida: '{row['MEDIDA (LARG-ANCH-ESP)']}'"
        ]
        if pd.notnull(row.get('MATERIAL')):
            partes.append(f"Material: '{row['MATERIAL']}'")
        if pd.notnull(row.get('SOPORTA (PorPlaza)')):
            partes.append(f"PesoSoportado: '{row['SOPORTA (PorPlaza)']}'")
    elif tipo == "otros":
        partes += [
            f"Línea: {row['PROVEEDOR']}",
            f"Producto: {row['CARACTERISTICAS']}",
            f"Color: {row['MODELO']}"
        ]

    # Precios comunes
    partes += [
        f"Efectivo: ${row['EFECTIVO']}",
        f"Transf/Déb/Créd: ${row['TRANSF/DEBIT/CREDIT']}",
        f"3 Cuotas: ${row['3 CUOTAS']} (3x ${int(row['3 CUOTAS']) // 3})",
        f"6 Cuotas: ${row['6 CUOTAS']} (6x ${int(row['6 CUOTAS']) // 6})"
    ]
    return "\n".join(partes)


def copiar_al_portapapeles(texto: str):
    QApplication.clipboard().setText(texto)
