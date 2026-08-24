# logic/pricing_service.py
"""
Detección de precio por producto/método de pago -- fuente única de verdad.

Por qué existe: esta regla de negocio ("qué columna del catálogo usar como
precio base, y qué precio unitario corresponde según el método de pago
elegido") estaba reimplementada de 3 formas ligeramente distintas:
  - logic/cart_service.py (la más completa: búsqueda "inteligente" de la
    columna de precio base probando varios nombres posibles)
  - ui/cart_window.py::actualizar_tabla / _recalcular_totales (solo
    columnas exactas, sin fallback ante nombres alternativos)
  - ui/views.py::_handle_calculo_cuotas (solo columnas exactas)

Hallazgo de la auditoría (Fase 3): esa divergencia no era solo cosmética.
_recalcular_totales() en cart_window.py es lo que fija el total que
efectivamente se registra en una venta a "Crédito de la Casa" -- si el
precio base de un producto vivía en una columna con nombre distinto a
"EFECTIVO/TRANSF", esa venta se registraba con base $0 (cuotas y total
financiado en $0), mientras que la MISMA venta en efectivo del mismo
producto se calculaba bien (porque cart_service.py sí tenía el fallback).

Esta versión es la lógica "robusta" (la que ya tenía cart_service.py),
movida a logic/ para que cart_service.py, cart_window.py y views.py la
compartan y no puedan volver a divergir.
"""
from typing import Dict, Any


def encontrar_precio_base(item: Dict[str, Any]) -> float:
    """
    Intenta encontrar el precio de LISTA/EFECTIVO de un producto, buscando
    en varias columnas posibles del catálogo (Google Sheets no siempre usa
    exactamente el mismo nombre de columna en todas las hojas/versiones).
    """
    # 1. Intento Exacto (nombre estándar)
    val = float(item.get("EFECTIVO/TRANSF", 0))
    if val > 0:
        return val

    # 2. Intento Alternativo (nombres comunes)
    nombres_comunes = ["EFECTIVO", "CONTADO", "PRECIO", "PRECIO LISTA", "BASE"]
    for key in item.keys():
        key_upper = key.upper().strip()
        if any(x in key_upper for x in nombres_comunes):
            try:
                val = float(item[key])
                if val > 0:
                    return val
            except (TypeError, ValueError):
                continue

    # 3. Fallback final: si no hay nada, devolvemos 0 (para alertar después)
    return 0.0


def obtener_precio_unitario(item: Dict[str, Any], precio_base: float, metodo_pago: str) -> float:
    """
    Determina el precio unitario de un producto según el método de pago.

    Para "Crédito de la Casa" devuelve el precio BASE (sin interés): el
    recargo financiero se calcula aparte con calcular_plan_credito() y se
    guarda en el plan de cuotas, no en el precio unitario del item.
    """
    metodo = metodo_pago or ""

    if "6 Cuotas" in metodo:
        col_seis = next((k for k in item.keys() if "6 CUOTAS" in k.upper()), None)
        if col_seis:
            return float(item.get(col_seis, precio_base))
        return precio_base

    elif "Tarjeta" in metodo or "Debito" in metodo:
        col_tarjeta = next(
            (k for k in item.keys() if "DEBIT" in k.upper() or "CREDIT" in k.upper() or "TARJETA" in k.upper()),
            None,
        )
        if col_tarjeta:
            return float(item.get(col_tarjeta, precio_base))
        return precio_base

    elif "Crédito" in metodo:
        return precio_base

    return precio_base
