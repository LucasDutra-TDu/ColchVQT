"""Gestión de facturas con SQLite para un sistema PySide6.

Este módulo centraliza el acceso a la tabla `facturas` en `data/facturas.db`.

Requisitos cubiertos:
- Creación automática de la tabla si no existe.
- Funciones públicas:
    - guardar_factura(items: list, metodo_pago: str, total: float) -> str
    - listar_facturas() -> list[dict]
    - obtener_factura(id: int) -> dict | None
    - buscar_por_fecha(fecha: str) -> list[dict]
- Serialización/deserialización JSON del campo `items`.
- Cálculo y registro de ganancia total de la factura.
- Normalización de ítems para consistencia.
- Diseño preparado para futuros filtros (método de pago, rangos de fechas).

Nota: `fecha` se guarda en formato ISO 8601 con precisión de segundos
(p.ej., "2025-08-20T14:33:27"). Para filtrar por día se usa el prefijo
`YYYY-MM-DD`.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

# Ruta a la base de datos: <raiz_proyecto>/data/facturas.db
# Suponiendo que este archivo vive en logic/facturas.py
_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "facturas.db"

# --- Utilidades internas ----------------------------------------------------

def _ensure_db_dir() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    """Devuelve una conexión a SQLite con row_factory para dict-like acceso."""
    _ensure_db_dir()
    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _init_db() -> None:
    """Crea la tabla `facturas` si no existe y asegura columna ganancia."""
    with _get_connection() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS facturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                metodo_pago TEXT NOT NULL,
                total REAL NOT NULL,
                items TEXT NOT NULL,
                ganancia REAL DEFAULT 0
            )
            """
        )
        # Intentar agregar la columna ganancia si no existe (migración)
        try:
            con.execute("ALTER TABLE facturas ADD COLUMN ganancia REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # La columna ya existe
        con.commit()


def _iso_now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = {
        "id": row["id"],
        "fecha": row["fecha"],
        "metodo_pago": row["metodo_pago"],
        "total": float(row["total"]) if row["total"] is not None else None,
        "ganancia": float(row["ganancia"]) if row["ganancia"] is not None else 0.0,
        "items": json.loads(row["items"]) if row["items"] else [],
    }
    return d


# Inicializamos la tabla al importar el módulo.
_init_db()

# --- API pública -------------------------------------------------------------

__all__ = [
    "guardar_factura",
    "listar_facturas",
    "obtener_factura",
    "buscar_por_fecha",
]


# --- Normalización de ítems --------------------------------------------------

def normalizar_item(raw_item: dict, metodo_pago: str) -> dict:
    """
    Convierte un producto del formato de base de datos (fila_to_dict_con_costo)
    a un formato estándar para facturación.
    """
    descripcion = f"{raw_item.get('MODELO', '')} {raw_item.get('CARACTERISTICAS', '')}".strip()
    costo = float(raw_item.get("COSTO", 0))

    # Selección del precio según método de pago
    metodo_lower = metodo_pago.lower()
    if "efectivo" in metodo_lower or "transferencia" in metodo_lower:
        precio = float(raw_item.get("EFECTIVO/TRANSF", 0))
    elif "debito" in metodo_lower or "crédito" in metodo_lower or "tarjeta" in metodo_lower:
        precio = float(raw_item.get("DEBIT/CREDIT", 0))
    elif "3" in metodo_lower:
        precio = float(raw_item.get("3 CUOTAS", 0))
    elif "6" in metodo_lower:
        precio = float(raw_item.get("6 CUOTAS", 0))
    else:
        precio = float(raw_item.get("EFECTIVO/TRANSF", 0))  # fallback

    return {
        "descripcion": descripcion or f"Producto {raw_item.get('CÓDIGO')}",
        "cantidad": raw_item.get("cantidad", 1),
        "precio": precio,
        "costo": costo,
    }


# --- Funciones de facturación ------------------------------------------------

def guardar_factura(items: list, metodo_pago: str, total: float) -> str:
    """Guarda una nueva factura con su ganancia y devuelve la fecha (ISO)."""
    if not isinstance(metodo_pago, str) or not metodo_pago:
        raise ValueError("metodo_pago debe ser un str no vacío")

    # Normalizar ítems
    try:
        items_list = [normalizar_item(i, metodo_pago) for i in items]
        items_json = json.dumps(items_list, ensure_ascii=False)
    except Exception as exc:
        raise ValueError("items no son válidos para facturación") from exc

    # Calcular ganancia: sum(precio - costo)
    ganancia_total = sum((float(i["precio"]) - float(i["costo"])) for i in items_list)

    fecha = _iso_now()

    with _get_connection() as con:
        con.execute(
            """
            INSERT INTO facturas (fecha, metodo_pago, total, items, ganancia)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fecha, metodo_pago, float(total), items_json, ganancia_total),
        )
        con.commit()

    return fecha


def listar_facturas() -> list[dict]:
    with _get_connection() as con:
        cur = con.execute("SELECT * FROM facturas ORDER BY id DESC")
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def obtener_factura(id: int) -> Optional[dict]:
    with _get_connection() as con:
        cur = con.execute("SELECT * FROM facturas WHERE id = ?", (int(id),))
        row = cur.fetchone()
    return _row_to_dict(row) if row else None


def buscar_por_fecha(fecha: str) -> list[dict]:
    if not isinstance(fecha, str) or len(fecha) != 10:
        raise ValueError("'fecha' debe tener formato 'YYYY-MM-DD'")

    like_pattern = f"{fecha}%"
    with _get_connection() as con:
        cur = con.execute(
            "SELECT * FROM facturas WHERE fecha LIKE ? ORDER BY id DESC",
            (like_pattern,),
        )
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


# --- Extensión futura (ejemplo de API prevista) -----------------------------

def _buscar_avanzado(
    *,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    metodo_pago: Optional[str] = None,
) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []

    if metodo_pago:
        clauses.append("metodo_pago = ?")
        params.append(metodo_pago)

    if fecha_desde:
        clauses.append("fecha >= ?")
        params.append(fecha_desde)

    if fecha_hasta:
        clauses.append("fecha <= ?")
        params.append(fecha_hasta)

    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM facturas{where_sql} ORDER BY id DESC"

    with _get_connection() as con:
        cur = con.execute(sql, tuple(params))
        rows = cur.fetchall()

    return [_row_to_dict(r) for r in rows]
