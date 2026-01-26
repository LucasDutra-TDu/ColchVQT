import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ventas.db"

def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_credits_db():
    schema = """
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dni TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        telefono TEXT,
        direccion TEXT,
        notas TEXT
    );

    CREATE TABLE IF NOT EXISTS creditos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura_id INTEGER NOT NULL,
        cliente_id INTEGER NOT NULL,
        monto_financiado REAL NOT NULL, -- Total con interés
        monto_base REAL DEFAULT 0,      -- Capital original (sin interés) [NUEVO]
        cantidad_cuotas INTEGER NOT NULL,
        fecha_otorgamiento TEXT NOT NULL,
        estado TEXT DEFAULT 'ACTIVO',
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    );

    CREATE TABLE IF NOT EXISTS cuotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credito_id INTEGER NOT NULL,
        numero_cuota INTEGER NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        monto REAL NOT NULL,
        fecha_pago TEXT,
        estado TEXT DEFAULT 'PENDIENTE',
        FOREIGN KEY(credito_id) REFERENCES creditos(id)
    );
    """
    with _get_connection() as con:
        con.executescript(schema)
        
        # Migración: Agregar columna monto_base si no existe
        try:
            con.execute("ALTER TABLE creditos ADD COLUMN monto_base REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Ya existe

# --- Operaciones de Escritura ---

def buscar_o_crear_cliente(dni: str, nombre: str, telefono: str, direccion: str) -> int:
    with _get_connection() as con:
        cur = con.execute("SELECT id FROM clientes WHERE dni = ?", (dni,))
        row = cur.fetchone()
        
        if row:
            con.execute("UPDATE clientes SET nombre=?, telefono=?, direccion=? WHERE id=?", 
                       (nombre, telefono, direccion, row['id']))
            return row['id']
        else:
            cur = con.execute("INSERT INTO clientes (dni, nombre, telefono, direccion) VALUES (?, ?, ?, ?)", 
                             (dni, nombre, telefono, direccion))
            con.commit()
            return cur.lastrowid

def registrar_plan_credito(factura_id: int, cliente_data: dict, plan_info: dict):
    cliente_id = buscar_o_crear_cliente(
        cliente_data['dni'], cliente_data['nombre'], 
        cliente_data.get('telefono', ''), cliente_data.get('direccion', '')
    )
    
    fecha_hoy = datetime.date.today()
    
    with _get_connection() as con:
        # 1. Cabecera (Guardamos ahora el PRECIO BASE también)
        cur = con.execute("""
            INSERT INTO creditos (factura_id, cliente_id, monto_financiado, monto_base, cantidad_cuotas, fecha_otorgamiento)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (factura_id, cliente_id, plan_info['precio_final'], plan_info['precio_base'], plan_info['num_cuotas'], fecha_hoy.isoformat()))
        
        credito_id = cur.lastrowid
        
        # 2. Cuotas (La #1 se paga HOY)
        monto_cuota = plan_info['valor_cuota']
        
        for i in range(1, plan_info['num_cuotas'] + 1):
            if i == 1:
                # Cuota 1: Vence hoy y se paga hoy automáticamente
                fecha_venc = fecha_hoy
                estado = 'PAGADO'
                fecha_pago = fecha_hoy.isoformat()
            else:
                # Cuota 2 en adelante: 30 días, 60 días... desde hoy
                # (i-1) porque la cuota 2 es a 30 días, la 3 a 60, etc.
                fecha_venc = fecha_hoy + datetime.timedelta(days=30 * (i - 1))
                estado = 'PENDIENTE'
                fecha_pago = None

            con.execute("""
                INSERT INTO cuotas (credito_id, numero_cuota, fecha_vencimiento, monto, estado, fecha_pago)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (credito_id, i, fecha_venc.isoformat(), monto_cuota, estado, fecha_pago))
        
        con.commit()
        return credito_id

# --- Operaciones de Lectura y Gestión ---

def obtener_creditos_activos() -> list:
    with _get_connection() as con:
        sql = """
            SELECT cr.*, cl.nombre, cl.dni 
            FROM creditos cr
            JOIN clientes cl ON cr.cliente_id = cl.id
            WHERE cr.estado != 'FINALIZADO'
            ORDER BY cr.fecha_otorgamiento DESC
        """
        rows = con.execute(sql).fetchall()
    return [dict(r) for r in rows]

def obtener_detalle_credito(credito_id: int) -> dict:
    """Devuelve info del crédito, cliente, productos y cuotas."""
    with _get_connection() as con:
        # 1. Obtenemos datos del Crédito + Cliente Completo + Items de la Factura
        sql_credito = """
            SELECT cr.*, 
                   cl.nombre, cl.dni, cl.telefono, cl.direccion, 
                   f.items_json 
            FROM creditos cr
            JOIN clientes cl ON cr.cliente_id = cl.id
            JOIN facturas f ON cr.factura_id = f.id
            WHERE cr.id=?
        """
        row = con.execute(sql_credito, (credito_id,)).fetchone()
        
        # 2. Obtenemos las cuotas
        cuotas = con.execute("SELECT * FROM cuotas WHERE credito_id=?", (credito_id,)).fetchall()
        
    credito_dict = dict(row)
    
    # Parseamos los productos desde el JSON de la factura
    try:
        items = json.loads(credito_dict['items_json'])
    except:
        items = []

    return {
        "credito": credito_dict,
        "items": items, # <--- Nueva lista de productos
        "cuotas": [dict(c) for c in cuotas]
    }

def pagar_cuota(cuota_id: int):
    hoy = datetime.date.today().isoformat()
    with _get_connection() as con:
        con.execute("UPDATE cuotas SET estado='PAGADO', fecha_pago=? WHERE id=?", (hoy, cuota_id))
        
        # Verificar finalización
        cur = con.execute("SELECT credito_id FROM cuotas WHERE id=?", (cuota_id,))
        credito_id = cur.fetchone()['credito_id']
        pendientes = con.execute("SELECT count(*) as count FROM cuotas WHERE credito_id=? AND estado!='PAGADO'", (credito_id,)).fetchone()['count']
        
        if pendientes == 0:
            con.execute("UPDATE creditos SET estado='FINALIZADO' WHERE id=?", (credito_id,))
        con.commit()

def anular_pago(cuota_id: int):
    with _get_connection() as con:
        con.execute("UPDATE cuotas SET estado='PENDIENTE', fecha_pago=NULL WHERE id=?", (cuota_id,))
        row = con.execute("SELECT credito_id FROM cuotas WHERE id=?", (cuota_id,)).fetchone()
        if row:
            con.execute("UPDATE creditos SET estado='ACTIVO' WHERE id=? AND estado='FINALIZADO'", (row['credito_id'],))
        con.commit()

def obtener_id_credito_por_factura(factura_id: int) -> int:
    """Retorna el ID del crédito asociado a una factura, o None si no existe."""
    with _get_connection() as con:
        row = con.execute("SELECT id FROM creditos WHERE factura_id = ?", (factura_id,)).fetchone()
        return row['id'] if row else None

init_credits_db()