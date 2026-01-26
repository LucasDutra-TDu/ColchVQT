import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


import sys
import os
from pathlib import Path

# --- INICIO DE LA BRÚJULA UNIVERSAL ---
def get_base_path():
    """
    Devuelve la ruta raíz del proyecto, detectando si estamos
    en modo desarrollo (Python) o en modo producción (.exe).
    """
    if getattr(sys, 'frozen', False):
        # CASO 1: Estamos corriendo como EJECUTABLE (.exe)
        # En este caso, queremos la carpeta donde está el .exe
        return Path(sys.executable).parent
    else:
        # CASO 2: Estamos corriendo en DESARROLLO (.py)
        # Path(__file__) es este archivo (invoice_service.py)
        # .parent es la carpeta 'logic'
        # .parent.parent es la carpeta raíz del proyecto 'ColchVQT'
        return Path(__file__).resolve().parent.parent

# --- USANDO LA BRÚJULA ---
BASE_DIR = get_base_path()

# Ahora definimos las rutas relativas a esa "Base Segura"
DB_PATH = BASE_DIR / "data" / "ventas.db"
OUTPUT_DIR = BASE_DIR / "output_docs"
# --------------------------------------

def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        metodo_pago TEXT NOT NULL,
        total REAL NOT NULL,
        ganancia REAL DEFAULT 0,
        items_json TEXT NOT NULL
    )
    """
    with _get_connection() as con:
        con.execute(schema)

def registrar_venta(items_carrito: List[Dict[str, Any]], metodo_pago: str, total_venta: float) -> int:
    """
    Registra una venta.
    items_carrito: Debe venir con 'precio_venta_final' y 'precio_lista_base'.
    """
    fecha_iso = datetime.datetime.now().replace(microsecond=0).isoformat()
    
    items_to_store = []
    ganancia_total = 0.0

    for item in items_carrito:
        cantidad = int(item.get("cantidad", 1))
        
        # 1. Precio de Venta Real (lo que pagó el cliente)
        precio_unitario = float(item.get("precio_venta_final", 0)) 
        
        # 2. Costo
        costo_unitario = float(item.get("COSTO", 0))
        
        # 3. Precio Base para Comisiones (CORRECCIÓN CRÍTICA)
        # Priorizamos el dato calculado por el CartService
        precio_base_ref = float(item.get("precio_lista_base", 0))
        
        # Fallback solo si viene en 0 (ej: venta manual o script viejo)
        if precio_base_ref == 0:
             # Intentamos buscar la columna original
             precio_base_ref = float(item.get("EFECTIVO/TRANSF", 0))
        
        # Último recurso: si no hay base, usamos el precio de venta
        if precio_base_ref == 0:
            precio_base_ref = precio_unitario

        ganancia_item = (precio_unitario - costo_unitario) * cantidad
        ganancia_total += ganancia_item

        items_to_store.append({
            "codigo": item.get("CÓDIGO", "S/C"),
            "modelo": item.get("MODELO", "Desconocido"),
            "descripcion": item.get("CARACTERISTICAS", ""),
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "costo_historico": costo_unitario,
            "precio_lista_base": precio_base_ref # <--- Aquí guardamos el dato correcto
        })

    items_json = json.dumps(items_to_store, ensure_ascii=False)

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

def obtener_historial() -> List[Dict]:
    with _get_connection() as con:
        rows = con.execute("SELECT * FROM facturas ORDER BY id DESC").fetchall()
    return [_parse_row(row) for row in rows]

def buscar_por_fecha(fecha_str: str) -> List[Dict]:
    with _get_connection() as con:
        rows = con.execute(
            "SELECT * FROM facturas WHERE fecha LIKE ? ORDER BY id DESC", 
            (f"{fecha_str}%",)
        ).fetchall()
    return [_parse_row(row) for row in rows]

def _parse_row(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    if "items_json" in d and d["items_json"]:
        try:
            d["items"] = json.loads(d["items_json"])
        except json.JSONDecodeError:
            d["items"] = []
    else:
        d["items"] = []
    return d

init_db()