# logic/cart_service.py

from typing import List, Dict, Any
from PySide6.QtCore import QObject, Signal  # <--- IMPORTANTE
from logic.constants import METODOS_PAGO

# Heredamos de QObject para poder usar Señales
class CartService(QObject):
    # Definimos la señal que se emitirá cuando algo cambie
    cart_updated = Signal()

    def __init__(self):
        super().__init__() # Inicializamos QObject
        self._items: Dict[str, Dict[str, Any]] = {}
        self._metodo_pago_actual = "Efectivo / Transferencia" # Default según tus constantes nuevas

    def set_metodo_pago(self, metodo: str):
        if metodo not in METODOS_PAGO:
            # Fallback seguro o manejo de error
            print(f"Método no válido: {metodo}")
            return
        self._metodo_pago_actual = metodo
        self.cart_updated.emit() # <--- AVISAMOS CAMBIO

    def get_metodo_pago(self) -> str:
        return self._metodo_pago_actual

    def agregar_producto(self, producto: Dict[str, Any], cantidad: int = 1):
        # FUERZA BRUTA: Convertimos a string inmediatamente para evitar conflictos de tipos
        raw_codigo = producto.get("CÓDIGO")
        if raw_codigo is None: return
        
        codigo = str(raw_codigo) # <--- LA SOLUCIÓN MÁGICA

        if codigo in self._items:
            self._items[codigo]["cantidad"] += cantidad
        else:
            nuevo_item = producto.copy()
            # Aseguramos que dentro del item también el código sea string
            nuevo_item["CÓDIGO"] = codigo 
            nuevo_item["cantidad"] = cantidad
            self._items[codigo] = nuevo_item

        if self._items[codigo]["cantidad"] <= 0:
            self.eliminar_producto(codigo)
        else:
            self.cart_updated.emit() # <--- AVISAMOS CAMBIO

    def eliminar_producto(self, codigo: str):
        if codigo in self._items:
            del self._items[codigo]
            self.cart_updated.emit() # <--- AVISAMOS CAMBIO

    def actualizar_cantidad(self, codigo: str, nueva_cantidad: int):
        if codigo in self._items:
            if nueva_cantidad <= 0:
                self.eliminar_producto(codigo)
            else:
                self._items[codigo]["cantidad"] = nueva_cantidad
                self.cart_updated.emit() # <--- AVISAMOS CAMBIO

    def obtener_items(self) -> List[Dict[str, Any]]:
        return list(self._items.values())

    def obtener_total(self) -> float:
        from logic.financiero import calcular_precio_final # Import local para evitar ciclos
        total = 0.0
        for item in self._items.values():
            # Usamos lógica financiera centralizada
            precio_base = float(item.get("EFECTIVO/TRANSF", 0)) # O la columna base que uses
            # Nota: Si tu Excel ya tiene columnas pre-calculadas, úsalas.
            # Si no, usa el precio base y aplica la tasa:
            
            # Estrategia simple: buscar precio en columna coincidente con método
            # Si no existe columna, calcular.
            # Por ahora mantengo tu lógica de obtener precio directo del dict si existe:
            precio = float(item.get(self._metodo_pago_actual, 0))
            
            # Fallback si devuelve 0 (ej: Crédito de la Casa no es una columna en Excel)
            if precio == 0 and "EFECTIVO/TRANSF" in item:
                 base = float(item.get("EFECTIVO/TRANSF", 0))
                 # Aquí asumimos 1 cuota por defecto para totales rápidos
                 precio = calcular_precio_final(base, self._metodo_pago_actual, 1)

            cantidad = item.get("cantidad", 1)
            total += precio * cantidad
        return total

    def limpiar_carrito(self):
        self._items.clear()
        self.cart_updated.emit() # <--- AVISAMOS CAMBIO

    def get_count(self) -> int:
        return len(self._items)

    def preparar_checkout(self) -> List[Dict[str, Any]]:
        from logic.financiero import calcular_precio_final
        items_checkout = []
        for item in self._items.values():
            item_procesado = item.copy()
            
            # Lógica de precio para factura
            precio_base = float(item.get("EFECTIVO/TRANSF", 0))
            precio_unitario = float(item.get(self._metodo_pago_actual, 0))
            
            if precio_unitario == 0:
                precio_unitario = calcular_precio_final(precio_base, self._metodo_pago_actual, 1)

            item_procesado["precio_venta_final"] = precio_unitario
            items_checkout.append(item_procesado)
        return items_checkout
 