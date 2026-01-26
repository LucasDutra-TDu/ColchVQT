import sqlite3
import json
from logic.financiero import calcular_comisiones
from logic.credits_service import _get_connection as get_conn_credits
from logic.facturas_db_handler import _get_connection as get_conn_invoices

def obtener_reporte_mensual(mes: int, anio: int) -> dict:
    mes_str = f"{anio}-{mes:02d}"
    
    reporte = {
        "ventas": [],
        "totales": {
            "empresa": 0.0,
            "gerente": 0.0,
            "vendedor": 0.0,
            "total_bruto": 0.0
        }
    }
    
    # 1. OBTENER LISTA NEGRA DE IDs (Facturas que son Créditos)
    ids_excluir = []
    with get_conn_credits() as con:
        rows = con.execute("SELECT factura_id FROM creditos").fetchall()
        ids_excluir = [row['factura_id'] for row in rows]

    # A) Ventas DIRECTAS (Efectivo/Tarjeta)
    with get_conn_invoices() as con:
        if ids_excluir:
            placeholders = ','.join(['?'] * len(ids_excluir))
            sql_condicion_excluir = f"AND id NOT IN ({placeholders})"
            params = [mes_str] + ids_excluir
        else:
            sql_condicion_excluir = ""
            params = [mes_str]
            
        sql_directas = f"""
            SELECT * FROM facturas 
            WHERE strftime('%Y-%m', fecha) = ? 
            {sql_condicion_excluir}
        """
        facturas = con.execute(sql_directas, params).fetchall()
        
        for f in facturas:
            f_dict = dict(f)
            try:
                items = json.loads(f_dict['items_json'])
            except:
                items = []
            
            total_venta = f_dict['total']
            
            # --- CÁLCULO DE BASES Y COSTOS ---
            base_efectivo_total = 0.0
            costo_total_venta = 0.0 # Nuevo acumulador
            
            for item in items:
                cant = int(item.get('cantidad', 1))
                
                # 1. Base
                p_base = item.get('precio_lista_base')
                if p_base is None or float(p_base) == 0:
                    p_base = item.get('EFECTIVO/TRANSF')
                if p_base is None or float(p_base) == 0:
                    p_base = item.get('precio_unitario', 0)
                
                # 2. Costo (Nuevo)
                p_costo = float(item.get('costo_historico', item.get('COSTO', 0)))
                
                base_efectivo_total += float(p_base) * cant
                costo_total_venta += p_costo * cant
            
            # --- CÁLCULO DE COMISIONES Y GANANCIA NETA ---
            comis = calcular_comisiones(f_dict['metodo_pago'], base_efectivo_total, total_venta)
            
            # REFINAMIENTO: Restamos el costo a la ganancia de la empresa
            comis["empresa"] = comis["empresa"] - costo_total_venta
            
            _sumar_totales(reporte, comis, total_venta)
            
            reporte["ventas"].append({
                "fecha": f_dict['fecha'][:10],
                "tipo": f"VENTA {f_dict['metodo_pago']}",
                "detalle": f"Factura #{f_dict['id']}",
                
                "ganancia_empresa": comis["empresa"],
                "comis_gerente": comis["gerente"],
                "comis_vendedor": comis["vendedor"],
                
                "monto": total_venta,
                "id_origen": f_dict['id'],
                "tipo_origen": "FACTURA"
            })

    # B) Cuotas de CRÉDITOS
    with get_conn_credits() as con:
        # Actualizamos la consulta para traer también los items de la factura original (para sacar el costo)
        # y la cantidad total de cuotas (para prorratear el costo)
        sql_cuotas = """
            SELECT c.*, cr.monto_financiado, cr.monto_base, cr.cantidad_cuotas,
                   cl.nombre, cr.id as credito_real_id,
                   f.items_json 
            FROM cuotas c
            JOIN creditos cr ON c.credito_id = cr.id
            JOIN clientes cl ON cr.cliente_id = cl.id
            JOIN facturas f ON cr.factura_id = f.id
            WHERE strftime('%Y-%m', c.fecha_vencimiento) = ?
        """
        cuotas = con.execute(sql_cuotas, (mes_str,)).fetchall()
        
        for c in cuotas:
            monto_cuota = c['monto']
            total_financiado = c['monto_financiado']
            total_base = c['monto_base']
            
            if total_base == 0: total_base = total_financiado
            
            # 1. Prorrateo Financiero (Para comisiones)
            ratio_base = total_base / total_financiado
            parte_capital = monto_cuota * ratio_base
            parte_interes = monto_cuota - parte_capital
            
            # 2. Prorrateo de Costos (Para ganancia empresa)
            # Calculamos el costo total original del crédito
            try:
                items_origen = json.loads(c['items_json'])
            except:
                items_origen = []
            
            costo_total_credito = 0.0
            for item in items_origen:
                p_costo = float(item.get('costo_historico', item.get('COSTO', 0)))
                cant = int(item.get('cantidad', 1))
                costo_total_credito += p_costo * cant
            
            # Dividimos el costo total por la cantidad de cuotas
            # Así, cada cuota paga su "pedacito" de costo
            cant_cuotas_total = c['cantidad_cuotas'] if c['cantidad_cuotas'] > 0 else 1
            costo_prorrateado_cuota = costo_total_credito / cant_cuotas_total

            # 3. Comisiones
            comis_gerente = (parte_capital * 0.04) + (parte_interes * 0.10)
            comis_vendedor = (parte_capital * 0.03) + (parte_interes * 0.08)
            comis_empresa_bruta = monto_cuota - (comis_gerente + comis_vendedor)
            
            # 4. Refinamiento: Restamos el costo prorrateado
            comis_empresa_neta = comis_empresa_bruta - costo_prorrateado_cuota
            
            comis = {
                "empresa": comis_empresa_neta,
                "gerente": comis_gerente,
                "vendedor": comis_vendedor
            }
            
            _sumar_totales(reporte, comis, monto_cuota)
            
            reporte["ventas"].append({
                "fecha": c['fecha_vencimiento'],
                "tipo": "CUOTA CRÉDITO",
                "detalle": f"Cuota {c['numero_cuota']} - {c['nombre']}",
                
                "ganancia_empresa": comis["empresa"],
                "comis_gerente": comis["gerente"],
                "comis_vendedor": comis["vendedor"],

                "monto": monto_cuota,
                "id_origen": c['credito_real_id'],
                "tipo_origen": "CREDITO"
            })
            
    return reporte

def _sumar_totales(reporte, comis, bruto):
    reporte["totales"]["empresa"] += comis["empresa"]
    reporte["totales"]["gerente"] += comis["gerente"]
    reporte["totales"]["vendedor"] += comis["vendedor"]
    reporte["totales"]["total_bruto"] += bruto