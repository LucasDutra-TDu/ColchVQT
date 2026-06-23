# logic/proveedores_service.py
import json
import uuid
import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from logic.facturas_db_handler import BASE_DIR

# --- Enums ---
class FormaPago(Enum):
    NINGUNA = "Ninguna"
    EFECTIVO = "Efectivo"
    TRANSFERENCIA = "Transferencia"

# --- Models ---
class MovimientoProveedor:
    """Movimiento específico para Proveedores."""
    def __init__(self,
                 fecha: datetime.datetime,
                 debe: float = 0.0,
                 haber: float = 0.0,
                 descripcion: str = "",
                 forma_pago: FormaPago = FormaPago.NINGUNA,
                 id: str = None):
        self.fecha = fecha
        self.debe = debe
        self.haber = haber
        self.descripcion = descripcion
        self.forma_pago = forma_pago
        self.id = id if id is not None else str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fecha": self.fecha.isoformat(),
            "debe": self.debe,
            "haber": self.haber,
            "descripcion": self.descripcion,
            "forma_pago": self.forma_pago.value,
        }

    @classmethod
    def from_dict(cls, data: dict):
        forma_pago_value = data.get('forma_pago', FormaPago.NINGUNA.value)
        try:
            forma_pago_enum = FormaPago(forma_pago_value)
        except ValueError:
            forma_pago_enum = FormaPago.NINGUNA
        return cls(
            fecha=datetime.datetime.fromisoformat(data.get('fecha')),
            debe=float(data.get('debe', 0.0)),
            haber=float(data.get('haber', 0.0)),
            descripcion=data.get('descripcion', ''),
            forma_pago=forma_pago_enum,
            id=data.get('id')
        )

class Proveedor:
    """Entidad Proveedor"""
    def __init__(self,
                 nombre: str,
                 num_tel: str,
                 movimientos: List[MovimientoProveedor] = None,
                 id: str = None):
        self.nombre = nombre
        self.num_tel = num_tel
        self.movimientos = movimientos if movimientos is not None else []
        self.id = id if id is not None else str(uuid.uuid4())

    @property
    def total_debe(self) -> float: return sum(mov.debe for mov in self.movimientos)
    @property
    def total_haber(self) -> float: return sum(mov.haber for mov in self.movimientos)
    @property
    def saldo(self) -> float: return self.total_debe - self.total_haber
    @property
    def ultimo_movimiento_fecha(self) -> Optional[datetime.datetime]:
        if not self.movimientos: return None
        return max(mov.fecha for mov in self.movimientos)
    
    def obtener_movimientos_ordenados(self) -> list: return sorted(self.movimientos, key=lambda mov: mov.fecha, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, 
            "nombre": self.nombre, 
            "num_tel": self.num_tel,
            "movimientos": [mov.to_dict() for mov in self.movimientos],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        movs = [MovimientoProveedor.from_dict(m) for m in data.get("movimientos", [])]
        return cls(data.get("nombre", ""), data.get("num_tel", ""), movs, data.get("id"))

# --- Service ---
class ProveedoresService:
    """Gestiona la lógica de negocio para los proveedores."""
    def __init__(self):
        self.data_file = BASE_DIR / "data" / "proveedores.json"
        self.proveedores: dict[str, Proveedor] = {}
        self._asegurar_directorio_y_archivo()
        self.cargar_proveedores()

    def _asegurar_directorio_y_archivo(self):
        directorio = self.data_file.parent
        if not directorio.exists():
            directorio.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def guardar_proveedores(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                data_a_guardar = {
                    prov_id: prov.to_dict()
                    for prov_id, prov in self.proveedores.items()
                }
                json.dump(data_a_guardar, f, indent=4, ensure_ascii=False)
        except (IOError, TypeError) as e:
            print(f"Error al guardar los proveedores: {e}")

    def cargar_proveedores(self):
        if not self.data_file.exists() or self.data_file.stat().st_size == 0:
            self.proveedores = {}
            return
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.proveedores = {
                    prov_id: Proveedor.from_dict(prov_data)
                    for prov_id, prov_data in data.items()
                }
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error al cargar o decodificar proveedores: {e}")
            self.proveedores = {}
    
    def nombre_existe(self, nombre: str) -> bool:
        nombre_a_verificar = nombre.lower().strip()
        for proveedor in self.proveedores.values():
            if proveedor.nombre.lower().strip() == nombre_a_verificar:
                return True
        return False

    def crear_proveedor(self, nombre: str, num_tel: str) -> Optional[Proveedor]:
        if self.nombre_existe(nombre):
             print(f"Advertencia: Ya existe un proveedor con el nombre {nombre}")
             return None 
        nuevo_proveedor = Proveedor(nombre=nombre, num_tel=num_tel)
        self.proveedores[nuevo_proveedor.id] = nuevo_proveedor
        self.guardar_proveedores()
        return nuevo_proveedor

    def obtener_proveedor_por_id(self, proveedor_id: str) -> Optional[Proveedor]:
        return self.proveedores.get(proveedor_id)

    def obtener_proveedores(self, query: str = None) -> list[Proveedor]:
        lista_proveedores = list(self.proveedores.values())
        if query:
            query = query.lower().strip()
            lista_proveedores = [p for p in lista_proveedores if query in p.nombre.lower()]
        lista_proveedores.sort(
            key=lambda p: p.ultimo_movimiento_fecha if p.ultimo_movimiento_fecha is not None else datetime.datetime.min,
            reverse=True
        )
        return lista_proveedores

    def editar_proveedor(self, proveedor_id: str, nuevos_datos: dict) -> bool:
        proveedor = self.obtener_proveedor_por_id(proveedor_id)
        if not proveedor: return False
        if 'nombre' in nuevos_datos:
             nuevo_nombre = nuevos_datos['nombre']
             if self.nombre_existe(nuevo_nombre) and \
                next((p for p_id, p in self.proveedores.items() if p.nombre.lower().strip() == nuevo_nombre.lower().strip() and p_id != proveedor_id), None):
                 print(f"Advertencia: Ya existe otro proveedor con el nombre {nuevo_nombre}")
                 return False
             proveedor.nombre = nuevo_nombre
        if 'num_tel' in nuevos_datos:
            proveedor.num_tel = nuevos_datos['num_tel']
        self.guardar_proveedores()
        return True

    def eliminar_proveedor(self, proveedor_id: str) -> bool:
        if proveedor_id in self.proveedores:
            del self.proveedores[proveedor_id]
            self.guardar_proveedores()
            return True
        return False
        
    def agregar_movimiento(self, proveedor_id: str, movimiento_data: dict) -> Optional[MovimientoProveedor]:
        proveedor = self.obtener_proveedor_por_id(proveedor_id)
        if not proveedor: return None
        try:
             nuevo_movimiento = MovimientoProveedor.from_dict(movimiento_data)
             proveedor.movimientos.append(nuevo_movimiento)
             self.guardar_proveedores()
             return nuevo_movimiento
        except Exception as e:
             print(f"Error al crear MovimientoProveedor desde dict: {e}")
             return None
        
    def editar_movimiento(self, proveedor_id: str, movimiento_id: str, nuevos_datos: dict):
        proveedor = self.obtener_proveedor_por_id(proveedor_id)
        if not proveedor: return

        movimiento = next((m for m in proveedor.movimientos if m.id == movimiento_id), None)
        if not movimiento: return

        for key, value in nuevos_datos.items():
            if key == 'forma_pago' and isinstance(value, str):
                try:
                    setattr(movimiento, key, FormaPago(value))
                except ValueError:
                    print(f"Advertencia: Valor de forma_pago inválido '{value}'")
            elif key == 'fecha' and isinstance(value, str):
                setattr(movimiento, key, datetime.datetime.fromisoformat(value))
            elif hasattr(movimiento, key):
                setattr(movimiento, key, value)
        
        self.guardar_proveedores()
        
    def eliminar_movimiento(self, proveedor_id: str, movimiento_id: str) -> bool:
        proveedor = self.obtener_proveedor_por_id(proveedor_id)
        if not proveedor: return False
        
        movimiento_encontrado = next((m for m in proveedor.movimientos if m.id == movimiento_id), None)
        if movimiento_encontrado:
            proveedor.movimientos.remove(movimiento_encontrado)
            self.guardar_proveedores()
            return True
        return False
