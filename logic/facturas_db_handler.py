import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configuración de Rutas
# TODO: Idealmente mover esto a logic/constants.py para tener todas las rutas juntas
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ventas.db"

def _get_connection() -> sqlite3.Connection:
    """Crea conexión con la DB, asegurando que el directorio exista."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    """Inicializa la tabla de facturas si no existe."""
    schema = """
    CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,      -- ISO 8601
        metodo_pago TEXT NOT NULL,
        total REAL NOT NULL,
        ganancia REAL DEFAULT 0,
        items_json TEXT NOT NULL  -- Detalle serializado
    )
    """
    with _get_connection() as con:
        con.execute(schema)
        # Migraciones futuras irían aquí (alter table...)

def registrar_venta(items_carrito: List[Dict[str, Any]], metodo_pago: str, total_venta: float) -> int:
    """
    Registra una venta en la base de datos.
    
    Args:
        items_carrito: Lista de items PROCESADOS (debe incluir 'precio_venta' unitario y 'costo_base').
        metodo_pago: String descriptivo (ej: 'Efectivo').
        total_venta: El monto final cobrado al cliente.
    
    Returns:
        int: El ID de la factura generada.
    """
    fecha_iso = datetime.datetime.now().replace(microsecond=0).isoformat()
    
    # 1. Preparar datos para persistencia (Snapshot)
    # Convertimos la data compleja del carrito en un registro simple para historia
    items_to_store = []
    ganancia_total = 0.0

    for item in items_carrito:
        cantidad = int(item.get("cantidad", 1))
        
        # Precio al que se vendió (puede tener recargos de tarjeta/crédito)
        precio_unitario = float(item.get("precio_venta_final", 0)) 
        
        # Costo interno
        costo_unitario = float(item.get("COSTO", 0)) 
        
        # --- NUEVO: Precio Base para cálculo de comisiones ---
        # Intentamos obtener "EFECTIVO/TRANSF", si no existe (ej: producto manual), usamos el unitario.
        precio_base_ref = float(item.get("EFECTIVO/TRANSF", 0))
        if precio_base_ref == 0:
             precio_base_ref = float(item.get("PRECIO", precio_unitario))
        # -----------------------------------------------------

        ganancia_item = (precio_unitario - costo_unitario) * cantidad
        ganancia_total += ganancia_item

        items_to_store.append({
            "codigo": item.get("CÓDIGO", "S/C"),
            "modelo": item.get("MODELO", "Desconocido"),
            "descripcion": item.get("CARACTERISTICAS", ""),
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "costo_historico": costo_unitario,
            "precio_lista_base": precio_base_ref
        })

    items_json = json.dumps(items_to_store, ensure_ascii=False)

    # 2. Guardar en SQLite
    with _get_connection() as con:
        cursor = con.execute(
            """
            INSERT INTO facturas (fecha, metodo_pago, total, ganancia, items_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fecha_iso, metodo_pago, total_venta, ganancia_total, items_json)
        )
        con.commit()
        return cursor.lastrowid

def _parse_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Convierte una fila SQL en un diccionario y parsea el JSON de items."""
    d = dict(row)
    if "items_json" in d and d["items_json"]:
        try:
            d["items"] = json.loads(d["items_json"])
        except json.JSONDecodeError:
            d["items"] = []
    else:
        d["items"] = []
    return d

def obtener_historial() -> List[Dict]:
    """Recupera todas las ventas ordenadas por fecha reciente."""
    with _get_connection() as con:
        rows = con.execute("SELECT * FROM facturas ORDER BY id DESC").fetchall()
    
    return [_parse_row(row) for row in rows]

# Agrega también esta función que usaremos en el buscador por fecha
def buscar_por_fecha(fecha_str: str) -> List[Dict]:
    """Busca facturas que coincidan con la fecha (YYYY-MM-DD)."""
    with _get_connection() as con:
        rows = con.execute(
            "SELECT * FROM facturas WHERE fecha LIKE ? ORDER BY id DESC", 
            (f"{fecha_str}%",)
        ).fetchall()
    return [_parse_row(row) for row in rows]

# Inicialización automática al importar (Singleton style para DB local)
init_db()