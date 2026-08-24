# tests/test_facturas.py
"""
Tests de logic/facturas_db_handler.py.
"""
import sys
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.base import IsolatedDataTestCase
import logic.facturas_db_handler as facturas_db_handler
from logic.facturas_db_handler import (
    registrar_venta,
    obtener_historial,
    buscar_por_fecha,
    actualizar_venta_especial,
)


class TestRegistrarVenta(IsolatedDataTestCase):
    def test_registra_y_devuelve_id_incremental(self):
        items = [self.item_carrito()]
        id1 = registrar_venta(items, "Efectivo / Transferencia", 100000)
        id2 = registrar_venta(items, "Efectivo / Transferencia", 100000)
        self.assertEqual(id2, id1 + 1)

    def test_persiste_metodo_y_total(self):
        items = [self.item_carrito()]
        factura_id = registrar_venta(items, "Tarjeta Debito / Credito", 115000)
        historial = obtener_historial()
        factura = next(f for f in historial if f["id"] == factura_id)
        self.assertEqual(factura["metodo_pago"], "Tarjeta Debito / Credito")
        self.assertEqual(factura["total"], 115000)

    def test_calcula_ganancia_total_como_precio_venta_menos_costo(self):
        items = [
            self.item_carrito(codigo="A", cantidad=2, precio_venta_final=1000, costo=600),
            self.item_carrito(codigo="B", cantidad=1, precio_venta_final=500, costo=100),
        ]
        # ganancia = (1000-600)*2 + (500-100)*1 = 800 + 400 = 1200
        factura_id = registrar_venta(items, "Efectivo / Transferencia", 2500)
        historial = obtener_historial()
        factura = next(f for f in historial if f["id"] == factura_id)
        self.assertAlmostEqual(factura["ganancia"], 1200)

    def test_items_json_guarda_precio_lista_base_correcto(self):
        # precio_lista_base es el dato "correcto" para comisiones, según el
        # comentario "CORRECCIÓN CRÍTICA" del propio código.
        items = [self.item_carrito(codigo="A", precio_venta_final=1000, precio_lista_base=900)]
        factura_id = registrar_venta(items, "Efectivo / Transferencia", 1000)
        historial = obtener_historial()
        factura = next(f for f in historial if f["id"] == factura_id)
        self.assertEqual(factura["items"][0]["precio_lista_base"], 900)

    def test_fallback_precio_lista_base_a_EFECTIVO_TRANSF_si_viene_cero(self):
        item = self.item_carrito(codigo="A", precio_venta_final=1000)
        item["precio_lista_base"] = 0
        item["EFECTIVO/TRANSF"] = 850
        factura_id = registrar_venta([item], "Efectivo / Transferencia", 1000)
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        self.assertEqual(factura["items"][0]["precio_lista_base"], 850)

    def test_ultimo_fallback_precio_lista_base_es_precio_de_venta(self):
        item = self.item_carrito(codigo="A", precio_venta_final=1000)
        item["precio_lista_base"] = 0
        # Sin 'EFECTIVO/TRANSF' tampoco
        factura_id = registrar_venta([item], "Efectivo / Transferencia", 1000)
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        self.assertEqual(factura["items"][0]["precio_lista_base"], 1000)

    def test_codigo_y_modelo_faltantes_usan_default(self):
        item = {"cantidad": 1, "precio_venta_final": 100, "COSTO": 0}
        factura_id = registrar_venta([item], "Efectivo / Transferencia", 100)
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        self.assertEqual(factura["items"][0]["codigo"], "S/C")
        self.assertEqual(factura["items"][0]["modelo"], "Desconocido")

    def test_carrito_vacio_registra_factura_con_ganancia_cero(self):
        factura_id = registrar_venta([], "Efectivo / Transferencia", 0)
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        self.assertEqual(factura["ganancia"], 0)
        self.assertEqual(factura["items"], [])


class TestObtenerHistorialYBusqueda(IsolatedDataTestCase):
    def test_historial_orden_descendente_por_id(self):
        items = [self.item_carrito()]
        id1 = registrar_venta(items, "Efectivo / Transferencia", 100)
        id2 = registrar_venta(items, "Efectivo / Transferencia", 100)
        historial = obtener_historial()
        ids = [f["id"] for f in historial]
        self.assertEqual(ids[:2], [id2, id1])

    def test_buscar_por_fecha_filtra_correctamente(self):
        items = [self.item_carrito()]
        factura_id = registrar_venta(items, "Efectivo / Transferencia", 100)
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        fecha_hoy = factura["fecha"][:10]
        resultados = buscar_por_fecha(fecha_hoy)
        self.assertTrue(any(f["id"] == factura_id for f in resultados))
        resultados_otra_fecha = buscar_por_fecha("1999-01-01")
        self.assertEqual(resultados_otra_fecha, [])

    def test_historial_vacio_no_explota(self):
        self.assertEqual(obtener_historial(), [])


class TestActualizarVentaEspecial(IsolatedDataTestCase):
    def test_actualiza_total_y_override(self):
        items = [self.item_carrito()]
        factura_id = registrar_venta(items, "Efectivo / Transferencia", 100000)
        override = json.dumps({"gerente": 1000, "vendedor": 500, "empresa": 8500})
        actualizar_venta_especial(factura_id, 95000, override)
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        self.assertEqual(factura["total"], 95000)
        self.assertEqual(factura["comisiones_override"], override)


class TestInsertarFacturaTransaccional(IsolatedDataTestCase):
    """
    _insertar_factura no debe hacer commit por su cuenta: si quien la llama
    nunca comitea la conexión, no debe quedar nada persistido. Esto es lo
    que permite compartir transacción con credits_service.
    """
    def test_sin_commit_explicito_no_persiste(self):
        con = facturas_db_handler._get_connection()
        try:
            facturas_db_handler._insertar_factura(con, [self.item_carrito()], "Efectivo / Transferencia", 100)
            # No llamamos con.commit()
        finally:
            con.close()  # cierre sin commit -> rollback implícito

        self.assertEqual(obtener_historial(), [])


if __name__ == "__main__":
    unittest.main()
