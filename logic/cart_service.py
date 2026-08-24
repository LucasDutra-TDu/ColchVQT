from typing import List, Dict, Any
from PySide6.QtCore import QObject, Signal
from logic.constants import METODOS_PAGO
from logic.financiero import calcular_plan_credito
from logic.pricing_service import encontrar_precio_base, obtener_precio_unitario

class CartService(QObject):
    cart_updated = Signal()

    def __init__(self):
        super().__init__()
        self._items: Dict[str, Dict[str, Any]] = {}
        self._metodo_pago_actual = "Efectivo / Transferencia"

    def set_metodo_pago(self, metodo: str):
        if metodo not in METODOS_PAGO: return
        self._metodo_pago_actual = metodo
        self.cart_updated.emit()

    def get_metodo_pago(self) -> str:
        return self._metodo_pago_actual

    def agregar_producto(self, producto: Dict[str, Any], cantidad: int = 1):
        raw_codigo = producto.get("CÓDIGO")
        if raw_codigo is None: return
        codigo = str(raw_codigo)

        if codigo in self._items:
            self._items[codigo]["cantidad"] += cantidad
        else:
            nuevo_item = producto.copy()
            nuevo_item["CÓDIGO"] = codigo 
            nuevo_item["cantidad"] = cantidad
            self._items[codigo] = nuevo_item

        if self._items[codigo]["cantidad"] <= 0:
            self.eliminar_producto(codigo)
        else:
            self.cart_updated.emit()

    def eliminar_producto(self, codigo: str):
        if codigo in self._items:
            del self._items[codigo]
            self.cart_updated.emit()

    def actualizar_cantidad(self, codigo: str, nueva_cantidad: int):
        if codigo in self._items:
            if nueva_cantidad <= 0:
                self.eliminar_producto(codigo)
            else:
                self._items[codigo]["cantidad"] = nueva_cantidad
                self.cart_updated.emit()

    def obtener_items(self) -> List[Dict[str, Any]]:
        return list(self._items.values())

    def limpiar_carrito(self):
        self._items.clear()
        self.cart_updated.emit()

    def get_count(self) -> int:
        return len(self._items)

    # --- LÓGICA DE DETECCIÓN DE PRECIO ---
    # Movida a logic/pricing_service.py (Fase 3 de la auditoría) para que
    # cart_window.py y views.py usen exactamente la misma detección y no
    # puedan volver a divergir. Se mantienen estos wrappers privados para
    # no tocar preparar_checkout()/obtener_total() más abajo.

    def _encontrar_valor_base(self, item: Dict[str, Any]) -> float:
        return encontrar_precio_base(item)

    def _obtener_precio_unitario_actual(self, item: Dict[str, Any], p_base: float) -> float:
        return obtener_precio_unitario(item, p_base, self._metodo_pago_actual)

    def preparar_checkout(self) -> List[Dict[str, Any]]:
        """
        Prepara los items para guardar, asegurando que 'precio_lista_base' sea correcto.
        """
        items_checkout = []
        
        for item in self._items.values():
            item_procesado = item.copy()
            
            # 1. DETECCIÓN ROBUSTA DEL PRECIO BASE
            p_base = self._encontrar_valor_base(item)
            
            # 2. Precio de Venta (Unitario)
            p_venta = self._obtener_precio_unitario_actual(item, p_base)
            
            # Si falló la detección de base, asumimos que es el de venta (para no romper, pero generará comisión errónea)
            if p_base == 0: p_base = p_venta

            item_procesado["precio_venta_final"] = p_venta
            item_procesado["precio_lista_base"] = p_base # <--- ESTE ES EL DATO ORO
            
            items_checkout.append(item_procesado)
            
        return items_checkout

    def obtener_total(self) -> float:
        """Calcula el total visual."""
        total = 0.0
        for item in self._items.values():
            p_base = self._encontrar_valor_base(item)
            precio = self._obtener_precio_unitario_actual(item, p_base)
            cantidad = item.get("cantidad", 1)
            total += precio * cantidad
        return total