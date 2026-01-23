# logic/financiero.py
import math
from logic.constants import TASA_INTERES_MENSUAL

def calcular_precio_final(precio_base: float, metodo_pago: str, cuotas: int = 1) -> float:
    """
    Calcula el precio final de un item o total según el método.
    """
    if metodo_pago == "Crédito de la Casa":
        # Lógica: Base + (8% * cant_cuotas)
        # Nota: Validamos que cuotas sea al menos 1
        n_cuotas = max(1, cuotas)
        tasa_total = TASA_INTERES_MENSUAL * n_cuotas
        return precio_base * (1 + tasa_total)
    
    # Para Tarjeta o Efectivo, el precio ya viene definido en el Excel,
    # así que retornamos el precio base tal cual (se asume que se pasa el correcto).
    return precio_base

def calcular_plan_cuotas_detallado(precio_base: float, num_cuotas: int) -> dict:
    """
    Genera el desglose completo para el Gestor de Créditos.
    """
    # 1. Cálculo del total financiado
    tasa_total = TASA_INTERES_MENSUAL * num_cuotas
    precio_total_financiado = precio_base * (1 + tasa_total)
    
    # 2. Cálculo de la cuota pura
    valor_cuota_raw = precio_total_financiado / num_cuotas
    
    # 3. Redondeo a 100 (Regla de Negocio)
    valor_cuota = math.ceil(valor_cuota_raw / 100) * 100
    
    # 4. Recálculo del precio final real tras el redondeo
    precio_final_real = valor_cuota * num_cuotas

    return {
        "precio_base": precio_base,
        "num_cuotas": num_cuotas,
        "tasa_aplicada": tasa_total,
        "valor_cuota": valor_cuota,
        "precio_final": precio_final_real
    }

def calcular_plan_cuotas(precio_base: float, num_cuotas: int) -> dict:
    """
    Calcula el precio final financiado y el valor de la cuota.
    Aplica redondeo a la centena superior (Business Rule).
    """
    tasa_interes_total = TASA_INTERES_MENSUAL * num_cuotas
    precio_total_financiado = precio_base * (1 + tasa_interes_total)
    
    valor_cuota_raw = precio_total_financiado / num_cuotas
    
    # Regla de Negocio: Redondeo a 100 hacia arriba (Ceiling)
    valor_cuota = math.ceil(valor_cuota_raw / 100) * 100
    precio_final = valor_cuota * num_cuotas

    return {
        "num_cuotas": num_cuotas,
        "precio_base": precio_base,
        "precio_final": precio_final,
        "valor_cuota": valor_cuota,
        "tasa_aplicada": tasa_interes_total
    }

def format_currency(valor: float) -> str:
    """Formatea moneda estilo Argentina ($1.000)"""
    return f"${valor:,.0f}".replace(",", ".")

def generar_texto_clipboard(data_fila: dict, plan_info: dict, mapeo_campos: list) -> str:
    """Genera el texto plano para copiar al portapapeles."""
    lineas = []
    etiquetas_usadas = set()

    # 1. Datos del Producto
    for col_excel, etiqueta in mapeo_campos:
        if etiqueta in etiquetas_usadas: continue
        
        val = data_fila.get(col_excel)
        if val and str(val).strip() != "":
            lineas.append(f"{etiqueta}: '{val}'")
            etiquetas_usadas.add(etiqueta)

    # 2. Datos Financieros
    lineas.append(f"PLAN CRÉDITO DE LA CASA ({plan_info['num_cuotas']} PAGOS): {format_currency(plan_info['precio_final'])}")
    lineas.append(f"VALOR DE CUOTA: {format_currency(plan_info['valor_cuota'])}")
    
    return "\n".join(lineas)