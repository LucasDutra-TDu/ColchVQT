# tests/test_pricing_service.py
"""
Tests de logic/pricing_service.py -- la fuente única de detección de
precio por método de pago (Fase 3 de la auditoría, unificando 3
implementaciones divergentes: cart_service.py, cart_window.py, views.py).
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.pricing_service import encontrar_precio_base, obtener_precio_unitario


class TestEncontrarPrecioBase(unittest.TestCase):
    def test_columna_exacta_efectivo_transf(self):
        item = {"EFECTIVO/TRANSF": 100000}
        self.assertEqual(encontrar_precio_base(item), 100000)

    def test_fallback_a_columna_con_nombre_alternativo(self):
        # Este es el caso del hallazgo: si EFECTIVO/TRANSF no está pero hay
        # una columna con un nombre "parecido", debe encontrarla igual.
        item = {"PRECIO LISTA": 85000}
        self.assertEqual(encontrar_precio_base(item), 85000)

    def test_prioriza_efectivo_transf_sobre_alternativas(self):
        item = {"EFECTIVO/TRANSF": 100000, "PRECIO": 999}
        self.assertEqual(encontrar_precio_base(item), 100000)

    def test_efectivo_transf_en_cero_usa_fallback(self):
        item = {"EFECTIVO/TRANSF": 0, "CONTADO": 50000}
        self.assertEqual(encontrar_precio_base(item), 50000)

    def test_sin_ninguna_columna_reconocible_devuelve_cero(self):
        item = {"MODELO": "Producto X", "COLOR": "Azul"}
        self.assertEqual(encontrar_precio_base(item), 0.0)

    def test_valor_no_numerico_en_columna_alternativa_no_rompe(self):
        item = {"PRECIO": "no es un numero", "BASE": 45000}
        self.assertEqual(encontrar_precio_base(item), 45000)

    def test_valor_negativo_no_se_toma_como_base_valida(self):
        # val > 0 es la condición -- un valor negativo o cero no cuenta,
        # sigue buscando en las columnas siguientes.
        item = {"EFECTIVO/TRANSF": -100, "PRECIO": 30000}
        self.assertEqual(encontrar_precio_base(item), 30000)


class TestObtenerPrecioUnitario(unittest.TestCase):
    def test_efectivo_usa_precio_base(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, "Efectivo / Transferencia"), 100000)

    def test_credito_de_la_casa_usa_precio_base_sin_interes(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, "Crédito de la Casa"), 100000)

    def test_6_cuotas_usa_columna_especifica(self):
        item = {"6 CUOTAS": 118000}
        self.assertEqual(obtener_precio_unitario(item, 100000, "6 Cuotas"), 118000)

    def test_6_cuotas_sin_columna_cae_a_base(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, "6 Cuotas"), 100000)

    def test_tarjeta_usa_columna_debit_credit(self):
        item = {"DEBIT/CREDIT": 115000}
        self.assertEqual(obtener_precio_unitario(item, 100000, "Tarjeta Debito / Credito"), 115000)

    def test_tarjeta_encuentra_columna_con_nombre_alternativo(self):
        # Caso real: la columna de tarjeta a veces se llama distinto
        # (ej. "LISTA/TARJETA" en vez de "DEBIT/CREDIT").
        item = {"LISTA/TARJETA": 112000}
        self.assertEqual(obtener_precio_unitario(item, 100000, "Tarjeta"), 112000)

    def test_tarjeta_sin_columna_cae_a_base(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, "Tarjeta Debito / Credito"), 100000)

    def test_metodo_desconocido_cae_a_base(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, "Metodo Raro"), 100000)

    def test_metodo_vacio_no_rompe(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, ""), 100000)

    def test_metodo_none_no_rompe(self):
        item = {}
        self.assertEqual(obtener_precio_unitario(item, 100000, None), 100000)


class TestConsistenciaFlujoCompleto(unittest.TestCase):
    """
    Simula el flujo real: encontrar_precio_base() + obtener_precio_unitario()
    en cadena, para varios métodos de pago, sobre un mismo producto con el
    precio base en una columna NO estándar -- el caso exacto del hallazgo.
    """
    def test_producto_con_columna_no_estandar_funciona_en_todos_los_metodos(self):
        item = {"PRECIO LISTA": 90000, "6 CUOTAS": 106200, "DEBIT/CREDIT": 103500}
        base = encontrar_precio_base(item)
        self.assertEqual(base, 90000)

        self.assertEqual(obtener_precio_unitario(item, base, "Efectivo / Transferencia"), 90000)
        self.assertEqual(obtener_precio_unitario(item, base, "Crédito de la Casa"), 90000)
        self.assertEqual(obtener_precio_unitario(item, base, "6 Cuotas"), 106200)
        self.assertEqual(obtener_precio_unitario(item, base, "Tarjeta"), 103500)


if __name__ == "__main__":
    unittest.main()
