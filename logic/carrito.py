# logic/carrito.py

from logic.constants import METODOS_PAGO
from logic import facturas

carrito = []  # lista de dicts con información de productos
metodo_pago_actual = "EFECTIVO/TRANSF"  # método de pago general del carrito


def set_metodo_pago(metodo: str):
    """
    Define el método de pago general para el carrito.
    """
    global metodo_pago_actual
    if metodo not in METODOS_PAGO:
        raise ValueError(f"Método de pago inválido: {metodo}")
    metodo_pago_actual = metodo


def agregar_producto(producto: dict, cantidad: int = 1):
    """
    Agrega un producto al carrito.
    Si el producto ya existe (por código), solo incrementa la cantidad.
    """
    for item in carrito:
        if item["CÓDIGO"] == producto["CÓDIGO"]:
            item["cantidad"] += cantidad
            if item["cantidad"] <= 0:
                eliminar_producto(producto["CÓDIGO"])
            return
    if cantidad > 0:
        nuevo = producto.copy()
        nuevo["cantidad"] = cantidad
        carrito.append(nuevo)


def eliminar_producto(codigo: str):
    """
    Elimina un producto del carrito por su código.
    """
    global carrito
    carrito = [item for item in carrito if item["CÓDIGO"] != codigo]


def actualizar_cantidad(codigo: str, cantidad: int):
    """
    Actualiza la cantidad de un producto existente.
    Si la cantidad es 0 o menor, elimina el producto.
    """
    for item in carrito:
        if item["CÓDIGO"] == codigo:
            if cantidad <= 0:
                eliminar_producto(codigo)
            else:
                item["cantidad"] = cantidad
            break


def obtener_items():
    """
    Retorna la lista de productos en el carrito.
    """
    return carrito.copy()


def obtener_total():
    """
    Calcula el total del carrito según el método de pago general.
    """
    total = 0
    for item in carrito:
        precio = item.get(metodo_pago_actual, 0)
        total += precio * item["cantidad"]
    return total


def obtener_metodo_pago():
    """
    Retorna el método de pago actual del carrito.
    """
    return metodo_pago_actual


def limpiar_carrito():
    """
    Vacía completamente el carrito.
    """
    global carrito
    carrito = []


# Helper para integrar con la UI
def agregar_y_abrir(producto_dict, abrir_carrito_callback, cantidad: int = 1):
    """
    Agrega un producto al carrito y abre la ventana de carrito usando
    la función callback de UI `abrir_carrito_callback`.
    """
    agregar_producto(producto_dict, cantidad)
    abrir_carrito_callback()

# Facturación
def finalizar_compra():
    """
    Guarda la factura en la base de datos y limpia el carrito.
    Devuelve un dict con la fecha, items, metodo y total.
    Si el carrito está vacío, devuelve None.
    """
    if not carrito:
        return None
    
    items = obtener_items()
    metodo = obtener_metodo_pago()
    total = obtener_total()

    fecha = facturas.guardar_factura(
        items=items,
        metodo_pago=metodo,
        total=total
    )
    limpiar_carrito()

    return {
        "fecha": fecha,
        "items": items,
        "metodo": metodo,
        "total": total
    }
