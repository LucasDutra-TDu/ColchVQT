import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Reutilizamos la ruta de la DB de ventas
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ventas.db"

def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_credits_db():
    """Inicializa las tablas relacionales para el sistema de créditos."""
    schema = """
    -- 1. Tabla de Clientes
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dni TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        telefono TEXT,
        direccion TEXT,
        notas TEXT
    );

    -- 2. Tabla de Planes de Crédito
    CREATE TABLE IF NOT EXISTS creditos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura_id INTEGER NOT NULL,
        cliente_id INTEGER NOT NULL,
        monto_financiado REAL NOT NULL,
        cantidad_cuotas INTEGER NOT NULL,
        fecha_otorgamiento TEXT NOT NULL,
        estado TEXT DEFAULT 'ACTIVO',   -- ACTIVO, FINALIZADO, MOROSO
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    );

    -- 3. Tabla de Cuotas Individuales
    CREATE TABLE IF NOT EXISTS cuotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credito_id INTEGER NOT NULL,
        numero_cuota INTEGER NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        monto REAL NOT NULL,
        fecha_pago TEXT,                -- NULL si no está pagada
        estado TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, PAGADO, VENCIDO
        FOREIGN KEY(credito_id) REFERENCES creditos(id)
    );
    """
    with _get_connection() as con:
        con.executescript(schema)

# --- Operaciones de Escritura (Alta) ---

def buscar_o_crear_cliente(dni: str, nombre: str, telefono: str, direccion: str) -> int:
    """Busca un cliente por DNI, si no existe lo crea. Retorna su ID."""
    with _get_connection() as con:
        cur = con.execute("SELECT id FROM clientes WHERE dni = ?", (dni,))
        row = cur.fetchone()
        
        if row:
            # Actualizamos datos de contacto
            con.execute("""
                UPDATE clientes SET nombre=?, telefono=?, direccion=? WHERE id=?
            """, (nombre, telefono, direccion, row['id']))
            return row['id']
        else:
            cur = con.execute("""
                INSERT INTO clientes (dni, nombre, telefono, direccion) VALUES (?, ?, ?, ?)
            """, (dni, nombre, telefono, direccion))
            con.commit()
            return cur.lastrowid

def registrar_plan_credito(factura_id: int, cliente_data: dict, plan_info: dict):
    """Registra el crédito y sus cuotas."""
    cliente_id = buscar_o_crear_cliente(
        cliente_data['dni'], cliente_data['nombre'], 
        cliente_data.get('telefono', ''), cliente_data.get('direccion', '')
    )
    
    fecha_hoy = datetime.date.today()
    
    with _get_connection() as con:
        # 1. Cabecera
        cur = con.execute("""
            INSERT INTO creditos (factura_id, cliente_id, monto_financiado, cantidad_cuotas, fecha_otorgamiento)
            VALUES (?, ?, ?, ?, ?)
        """, (factura_id, cliente_id, plan_info['precio_final'], plan_info['num_cuotas'], fecha_hoy.isoformat()))
        
        credito_id = cur.lastrowid
        
        # 2. Cuotas
        monto_cuota = plan_info['valor_cuota']
        
        for i in range(1, plan_info['num_cuotas'] + 1):
            fecha_venc = fecha_hoy + datetime.timedelta(days=30 * i)
            con.execute("""
                INSERT INTO cuotas (credito_id, numero_cuota, fecha_vencimiento, monto)
                VALUES (?, ?, ?, ?)
            """, (credito_id, i, fecha_venc.isoformat(), monto_cuota))
        
        con.commit()
        return credito_id

# --- Operaciones de Lectura y Gestión (ESTAS FALTABAN) ---

def obtener_creditos_activos() -> list:
    """Devuelve lista de créditos que NO están finalizados, con datos del cliente."""
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
    """Devuelve info del crédito y sus cuotas."""
    with _get_connection() as con:
        credito = con.execute("SELECT * FROM creditos WHERE id=?", (credito_id,)).fetchone()
        cuotas = con.execute("SELECT * FROM cuotas WHERE credito_id=?", (credito_id,)).fetchall()
        
    return {
        "credito": dict(credito),
        "cuotas": [dict(c) for c in cuotas]
    }

def pagar_cuota(cuota_id: int):
    """Marca una cuota como PAGADA y verifica si el crédito finalizó."""
    hoy = datetime.date.today().isoformat()
    
    with _get_connection() as con:
        # 1. Marcar cuota
        con.execute("UPDATE cuotas SET estado='PAGADO', fecha_pago=? WHERE id=?", (hoy, cuota_id))
        
        # 2. Verificar si quedan cuotas pendientes en ese crédito
        cur = con.execute("SELECT credito_id FROM cuotas WHERE id=?", (cuota_id,))
        row = cur.fetchone()
        if not row: return 
        
        credito_id = row['credito_id']
        
        pendientes = con.execute(
            "SELECT count(*) as count FROM cuotas WHERE credito_id=? AND estado!='PAGADO'", 
            (credito_id,)
        ).fetchone()['count']
        
        if pendientes == 0:
            con.execute("UPDATE creditos SET estado='FINALIZADO' WHERE id=?", (credito_id,))
            print(f"Crédito {credito_id} Finalizado!")
        con.commit()

def anular_pago(cuota_id: int):
    """
    Revierte el pago de una cuota.
    1. Pone la cuota en PENDIENTE y borra fecha de pago.
    2. Si el crédito estaba FINALIZADO, lo devuelve a ACTIVO.
    """
    with _get_connection() as con:
        # 1. Revertir Cuota
        con.execute(
            "UPDATE cuotas SET estado='PENDIENTE', fecha_pago=NULL WHERE id=?", 
            (cuota_id,)
        )
        
        # 2. Revivir Crédito (si estaba finalizado)
        # Obtenemos el ID del crédito padre
        row = con.execute("SELECT credito_id FROM cuotas WHERE id=?", (cuota_id,)).fetchone()
        if row:
            credito_id = row['credito_id']
            con.execute(
                "UPDATE creditos SET estado='ACTIVO' WHERE id=? AND estado='FINALIZADO'", 
                (credito_id,)
            )
            print(f"Pago anulado en cuota {cuota_id}. Crédito {credito_id} reactivado.")
        
        con.commit()

# Inicializar al importar
init_credits_db()