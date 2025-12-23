# logic/credits_service.py
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reutilizamos la ruta de la DB de ventas
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "ventas.db"

def _get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_credits_db():
    """Inicializa las tablas relacionales para el sistema de créditos."""
    schema = """
    -- 1. Tabla de Clientes (Indispensable para seguimiento de morosos)
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dni TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        telefono TEXT,
        direccion TEXT,
        notas TEXT
    );

    -- 2. Tabla de Planes de Crédito (Vincula una Factura con un Cliente)
    CREATE TABLE IF NOT EXISTS creditos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura_id INTEGER NOT NULL,    -- Link a la tabla 'facturas'
        cliente_id INTEGER NOT NULL,    -- Link a la tabla 'clientes'
        monto_financiado REAL NOT NULL, -- El total a pagar (con intereses)
        cantidad_cuotas INTEGER NOT NULL,
        fecha_otorgamiento TEXT NOT NULL,
        estado TEXT DEFAULT 'ACTIVO',   -- ACTIVO, FINALIZADO, MOROSO
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    );

    -- 3. Tabla de Cuotas Individuales (Para imprimir y marcar pagadas)
    CREATE TABLE IF NOT EXISTS cuotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credito_id INTEGER NOT NULL,
        numero_cuota INTEGER NOT NULL,  -- Cuota 1 de 6, 2 de 6...
        fecha_vencimiento TEXT NOT NULL,
        monto REAL NOT NULL,
        fecha_pago TEXT,                -- NULL si no está pagada
        estado TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, PAGADO, VENCIDO
        FOREIGN KEY(credito_id) REFERENCES creditos(id)
    );
    """
    with _get_connection() as con:
        con.executescript(schema)

# --- Operaciones de Cliente ---

def buscar_o_crear_cliente(dni: str, nombre: str, telefono: str, direccion: str) -> int:
    """Busca un cliente por DNI, si no existe lo crea. Retorna su ID."""
    with _get_connection() as con:
        cur = con.execute("SELECT id FROM clientes WHERE dni = ?", (dni,))
        row = cur.fetchone()
        
        if row:
            # Actualizamos datos de contacto por si cambiaron
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

# --- Operaciones de Creación de Crédito ---

def registrar_plan_credito(factura_id: int, cliente_data: dict, plan_info: dict):
    """
    Registra todo el paquete de crédito tras una venta.
    
    Args:
        factura_id: ID de la venta en la tabla facturas.
        cliente_data: dict {dni, nombre, telefono, direccion}
        plan_info: dict {precio_final, num_cuotas, valor_cuota} (viene de financiero.py)
    """
    cliente_id = buscar_o_crear_cliente(
        cliente_data['dni'], cliente_data['nombre'], 
        cliente_data.get('telefono', ''), cliente_data.get('direccion', '')
    )
    
    fecha_hoy = datetime.date.today()
    
    with _get_connection() as con:
        # 1. Crear el Crédito Cabecera
        cur = con.execute("""
            INSERT INTO creditos (factura_id, cliente_id, monto_financiado, cantidad_cuotas, fecha_otorgamiento)
            VALUES (?, ?, ?, ?, ?)
        """, (factura_id, cliente_id, plan_info['precio_final'], plan_info['num_cuotas'], fecha_hoy.isoformat()))
        
        credito_id = cur.lastrowid
        
        # 2. Generar las Cuotas
        # Asumimos vencimiento el día 10 de cada mes siguiente, o cada 30 días.
        # Por simplicidad: cada 30 días a partir de hoy.
        monto_cuota = plan_info['valor_cuota']
        
        for i in range(1, plan_info['num_cuotas'] + 1):
            fecha_venc = fecha_hoy + datetime.timedelta(days=30 * i)
            con.execute("""
                INSERT INTO cuotas (credito_id, numero_cuota, fecha_vencimiento, monto)
                VALUES (?, ?, ?, ?)
            """, (credito_id, i, fecha_venc.isoformat(), monto_cuota))
        
        con.commit()
        return credito_id

# Inicializar al importar
init_credits_db()