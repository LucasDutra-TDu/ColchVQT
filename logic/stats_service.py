import sqlite3
from pathlib import Path
from logic.financiero import calcular_comisiones
from logic.credits_service import _get_connection as get_conn_credits
from logic.facturas_db_handler import _get_connection as get_conn_invoices

def obtener_reporte_mensual(mes: int, anio: int) -> dict:
    """
    Genera el reporte unificado de ventas y comisiones.
    Combina:
    1. Ventas Efectivo/Tarjeta (Facturas directas de ese mes).
    2. Cuotas de Créditos (Que vencen en ese mes, aunque la venta fuera antes).
    """
    mes_str = f"{anio}-{mes:02d}" # Ej: "2023-10"
    
    reporte = {
        "ventas": [], # Lista plana para la tabla
        "totales": {
            "empresa": 0.0,
            "gerente": 0.0,
            "vendedor": 0.0,
            "total_bruto": 0.0
        }
    }
    
    with get_conn_invoices() as con:
        # A) Ventas DIRECTAS (Efectivo/Tarjeta)
        # Filtramos por fecha y EXCLUIMOS 'Crédito de la Casa' (se procesan vía cuotas)
        sql_directas = """
            SELECT * FROM facturas 
            WHERE strftime('%Y-%m', fecha) = ? 
            AND metodo_pago != 'Crédito de la Casa'
        """
        facturas = con.execute(sql_directas, (mes_str,)).fetchall()
        
        # Procesar Directas
        for f in facturas:
            f_dict = dict(f)
            # Parsear items para tener precio base
            import json
            try:
                items = json.loads(f_dict['items_json'])
            except:
                items = []
                
            # Calcular comisiones item por item (para mayor precisión)
            # Ojo: El requerimiento define comisiones sobre el TOTAL de la venta
            # pero necesitamos la base 'EFECTIVO/TRANSF' para Tarjetas.
            
            total_venta = f_dict['total']
            metodo = f_dict['metodo_pago']
            
            # Para el cálculo de comisión, necesitamos saber la "Base Efectivo Total" de esta factura
            base_efectivo_total = 0
            for item in items:
                # Usamos el campo nuevo que creamos en el Paso 1
                base_efectivo_total += float(item.get('precio_lista_base', item.get('precio_unitario', 0))) * int(item.get('cantidad', 1))
            
            # Aplicamos regla [A] o [B]
            comis = calcular_comisiones(metodo, base_efectivo_total, total_venta)
            
            # Sumar al reporte global
            reporte["totales"]["empresa"] += comis["empresa"]
            reporte["totales"]["gerente"] += comis["gerente"]
            reporte["totales"]["vendedor"] += comis["vendedor"]
            reporte["totales"]["total_bruto"] += total_venta
            
            # Agregar a lista visual
            reporte["ventas"].append({
                "fecha": f_dict['fecha'][:10],
                "tipo": "VENTA " + metodo,
                "detalle": f"Factura #{f_dict['id']}",
                "monto": total_venta,
                "comis_ven": comis["vendedor"]
            })

    # B) Cuotas de CRÉDITOS (Método [C])
    # "Un crédito de 3 cuotas aportará una cuota a la estadística de cada uno de los 3 meses"
    with get_conn_credits() as con:
        sql_cuotas = """
            SELECT c.*, cr.factura_id, cl.nombre 
            FROM cuotas c
            JOIN creditos cr ON c.credito_id = cr.id
            JOIN clientes cl ON cr.cliente_id = cl.id
            WHERE strftime('%Y-%m', c.fecha_vencimiento) = ?
        """
        cuotas = con.execute(sql_cuotas, (mes_str,)).fetchall()
        
        for c in cuotas:
            monto_cuota = c['monto']
            
            # Regla [C]: Gerente 10%, Vendedor 8% sobre el precio final (monto cuota incluye interés)
            # calcular_comisiones ya tiene esta lógica si le pasamos "Crédito..."
            comis = calcular_comisiones("Crédito", 0, monto_cuota) # Base 0 porque usa el final
            
            reporte["totales"]["empresa"] += comis["empresa"]
            reporte["totales"]["gerente"] += comis["gerente"]
            reporte["totales"]["vendedor"] += comis["vendedor"]
            reporte["totales"]["total_bruto"] += monto_cuota
            
            reporte["ventas"].append({
                "fecha": c['fecha_vencimiento'],
                "tipo": "CUOTA CRÉDITO",
                "detalle": f"Cuota {c['numero_cuota']} - {c['nombre']}",
                "monto": monto_cuota,
                "comis_ven": comis["vendedor"]
            })
            
    return reporte