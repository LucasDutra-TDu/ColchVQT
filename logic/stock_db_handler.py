# logic/stock_db_handler.py

import sqlite3
import datetime
import sys
from pathlib import Path
from typing import Dict, List, Any

# --- INICIO DE LA BRÚJULA UNIVERSAL (Heredada de tu arquitectura) ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_path()

# Creamos una base de datos exclusiva para el inventario
DB_PATH = BASE_DIR / "data" / "inventario.db"
# -------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    schema_stock = """
    CREATE TABLE IF NOT EXISTS stock_actual (
        codigo TEXT PRIMARY KEY,
        cantidad INTEGER NOT NULL
    )
    """
    schema_movimientos = """
    CREATE TABLE IF NOT EXISTS movimientos_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        codigo TEXT NOT NULL,
        cantidad_alterada INTEGER NOT NULL,
        tipo_movimiento TEXT NOT NULL, 
        detalle TEXT
    )
    """
    with _get_connection() as con:
        con.execute(schema_stock)
        con.execute(schema_movimientos)

def obtener_stock_todos() -> Dict[str, int]:
    """
    Devuelve un diccionario con todo el stock actual.
    Formato: {'COD123': 5, 'COD456': 0, ...}
    Ideal para inyectar rápido en el DataFrame de Pandas.
    """
    with _get_connection() as con:
        rows = con.execute("SELECT codigo, cantidad FROM stock_actual").fetchall()
    return {row['codigo']: row['cantidad'] for row in rows}

def obtener_stock_articulo(codigo: str) -> int:
    """Devuelve el stock de un artículo específico. Retorna 0 si no existe."""
    with _get_connection() as con:
        row = con.execute("SELECT cantidad FROM stock_actual WHERE codigo = ?", (codigo,)).fetchone()
    return row['cantidad'] if row else 0

def registrar_movimiento_stock(codigo: str, cantidad_alterada: int, tipo_movimiento: str, detalle: str = ""):
    """
    Registra un ingreso, venta o ajuste. 
    Ajusta el stock_actual automáticamente y deja un registro en el historial.
    - cantidad_alterada: Positiva para ingresos, Negativa para ventas/salidas.
    - tipo_movimiento: Ej. 'INGRESO', 'VENTA', 'AJUSTE'.
    """
    fecha_iso = datetime.datetime.now().replace(microsecond=0).isoformat()
    
    with _get_connection() as con:
        # 1. Obtenemos el stock actual (0 si no existe el registro)
        row = con.execute("SELECT cantidad FROM stock_actual WHERE codigo = ?", (codigo,)).fetchone()
        stock_previo = row['cantidad'] if row else 0
        
        # 2. Calculamos el nuevo stock
        nuevo_stock = stock_previo + cantidad_alterada
        
        # 3. Actualizamos la tabla de stock actual (Upsert)
        con.execute(
            """
            INSERT INTO stock_actual (codigo, cantidad) 
            VALUES (?, ?)
            ON CONFLICT(codigo) DO UPDATE SET cantidad = ?
            """, 
            (codigo, nuevo_stock, nuevo_stock)
        )
        
        # 4. Guardamos el historial del movimiento
        con.execute(
            """
            INSERT INTO movimientos_stock (fecha, codigo, cantidad_alterada, tipo_movimiento, detalle)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fecha_iso, codigo, cantidad_alterada, tipo_movimiento, detalle)
        )
        con.commit()

# Inicializamos las tablas al cargar el módulo
init_db()