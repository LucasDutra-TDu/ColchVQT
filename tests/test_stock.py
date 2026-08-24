# tests/test_stock.py
"""
Tests de logic/stock_db_handler.py y logic/stock_service.py.
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from tests.base import IsolatedDataTestCase
import logic.stock_db_handler as stock_db_handler
from logic.stock_service import inyectar_stock_a_df, procesar_descuento_por_venta


class TestStockDbHandler(IsolatedDataTestCase):
    def test_stock_articulo_inexistente_devuelve_cero(self):
        self.assertEqual(stock_db_handler.obtener_stock_articulo("NOEXISTE"), 0)

    def test_ingreso_simple(self):
        stock_db_handler.registrar_movimiento_stock("COD1", 10, "INGRESO", "carga inicial")
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD1"), 10)

    def test_venta_descuenta_stock(self):
        stock_db_handler.registrar_movimiento_stock("COD1", 10, "INGRESO")
        stock_db_handler.registrar_movimiento_stock("COD1", -3, "VENTA", "Factura #1")
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD1"), 7)

    def test_movimientos_acumulan_correctamente_en_secuencia(self):
        stock_db_handler.registrar_movimiento_stock("COD1", 5, "INGRESO")
        stock_db_handler.registrar_movimiento_stock("COD1", 5, "INGRESO")
        stock_db_handler.registrar_movimiento_stock("COD1", -2, "VENTA")
        stock_db_handler.registrar_movimiento_stock("COD1", -1, "AJUSTE")
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD1"), 7)

    def test_stock_puede_quedar_negativo(self):
        # Comportamiento ACTUAL: no hay guarda contra sobreventa. Documentado
        # como hallazgo de la auditoría, no como comportamiento deseado.
        stock_db_handler.registrar_movimiento_stock("COD1", 2, "INGRESO")
        stock_db_handler.registrar_movimiento_stock("COD1", -5, "VENTA")
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD1"), -3)

    def test_obtener_stock_todos_devuelve_todos_los_codigos(self):
        stock_db_handler.registrar_movimiento_stock("A", 1, "INGRESO")
        stock_db_handler.registrar_movimiento_stock("B", 2, "INGRESO")
        todos = stock_db_handler.obtener_stock_todos()
        self.assertEqual(todos, {"A": 1, "B": 2})

    def test_historial_de_movimientos_queda_registrado(self):
        stock_db_handler.registrar_movimiento_stock("COD1", 10, "INGRESO", "carga")
        stock_db_handler.registrar_movimiento_stock("COD1", -4, "VENTA", "Factura #7")
        with stock_db_handler._get_connection() as con:
            filas = con.execute(
                "SELECT * FROM movimientos_stock ORDER BY id"
            ).fetchall()
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]["tipo_movimiento"], "INGRESO")
        self.assertEqual(filas[1]["cantidad_alterada"], -4)
        self.assertEqual(filas[1]["detalle"], "Factura #7")


class TestProcesarDescuentoPorVenta(IsolatedDataTestCase):
    def test_descuenta_un_item(self):
        stock_db_handler.registrar_movimiento_stock("COD1", 20, "INGRESO")
        items = [self.item_carrito(codigo="COD1", cantidad=3)]
        procesar_descuento_por_venta(items, id_factura=1)
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD1"), 17)

    def test_descuenta_varios_items(self):
        stock_db_handler.registrar_movimiento_stock("COD1", 20, "INGRESO")
        stock_db_handler.registrar_movimiento_stock("COD2", 20, "INGRESO")
        items = [
            self.item_carrito(codigo="COD1", cantidad=3),
            self.item_carrito(codigo="COD2", cantidad=5),
        ]
        procesar_descuento_por_venta(items, id_factura=1)
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD1"), 17)
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD2"), 15)

    def test_item_sin_codigo_S_C_no_descuenta_nada(self):
        # Items sin código comparten el "código" especial S/C; no deben
        # restarse entre sí (evita que un item genérico afecte el stock
        # de otro item genérico no relacionado).
        item = self.item_carrito(codigo="S/C", cantidad=2)
        procesar_descuento_por_venta([item], id_factura=1)
        self.assertEqual(stock_db_handler.obtener_stock_articulo("S/C"), 0)

    def test_item_con_claves_alternativas_codigo_minuscula(self):
        # procesar_descuento_por_venta tolera tanto 'codigo'/'cantidad' en
        # minúscula (formato interno) como 'CÓDIGO' (formato Excel/carrito).
        stock_db_handler.registrar_movimiento_stock("COD9", 10, "INGRESO")
        item = {"codigo": "COD9", "cantidad": 4, "modelo": "Test"}
        procesar_descuento_por_venta([item], id_factura=2)
        self.assertEqual(stock_db_handler.obtener_stock_articulo("COD9"), 6)


class TestInyectarStockADF(IsolatedDataTestCase):
    def test_df_vacio_se_devuelve_igual(self):
        df = pd.DataFrame()
        resultado = inyectar_stock_a_df(df)
        self.assertTrue(resultado.empty)

    def test_inyecta_columna_stock_actual_por_codigo(self):
        stock_db_handler.registrar_movimiento_stock("1000", 7, "INGRESO")
        df = pd.DataFrame({"CÓDIGO": ["1000", "2000"], "MODELO": ["A", "B"]})
        resultado = inyectar_stock_a_df(df)
        self.assertIn("STOCK_ACTUAL", resultado.columns)
        self.assertEqual(int(resultado.loc[resultado["CÓDIGO"] == "1000", "STOCK_ACTUAL"].iloc[0]), 7)
        # Código sin stock cargado -> 0, no NaN ni error
        self.assertEqual(int(resultado.loc[resultado["CÓDIGO"] == "2000", "STOCK_ACTUAL"].iloc[0]), 0)

    def test_codigo_float_se_normaliza_a_entero_string(self):
        # Pandas a veces castea códigos numéricos a float (1000 -> 1000.0);
        # inyectar_stock_a_df debe limpiar eso para que matchee con la
        # clave guardada en SQLite ("1000", sin ".0").
        stock_db_handler.registrar_movimiento_stock("1000", 5, "INGRESO")
        df = pd.DataFrame({"CÓDIGO": [1000.0]})
        resultado = inyectar_stock_a_df(df)
        self.assertEqual(int(resultado["STOCK_ACTUAL"].iloc[0]), 5)

    def test_no_altera_el_dataframe_original(self):
        stock_db_handler.registrar_movimiento_stock("1000", 3, "INGRESO")
        df_original = pd.DataFrame({"CÓDIGO": ["1000"]})
        inyectar_stock_a_df(df_original)
        self.assertNotIn("STOCK_ACTUAL", df_original.columns)

    def test_sin_columna_de_codigo_devuelve_NA(self):
        df = pd.DataFrame({"OTRA_COL": [1, 2]})
        resultado = inyectar_stock_a_df(df)
        self.assertTrue((resultado["STOCK_ACTUAL"] == "N/A").all())


if __name__ == "__main__":
    unittest.main()
