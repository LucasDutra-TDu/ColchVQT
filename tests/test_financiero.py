# tests/test_financiero.py
"""
Tests de logic/financiero.py: funciones puras (sin persistencia), así que
no heredan de IsolatedDataTestCase.

Incluye un test deliberado de CONSISTENCIA CRUZADA entre
calcular_plan_credito / calcular_plan_cuotas / calcular_plan_cuotas_detallado,
que son tres implementaciones separadas de la misma regla de negocio
(detectado en la auditoría). Si algún día alguien edita una sin tocar las
otras, este test lo detecta.
"""
import sys
import unittest
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.financiero import (
    format_currency,
    calcular_plan_credito,
    calcular_comisiones,
    calcular_precio_final,
    calcular_plan_cuotas_detallado,
    calcular_plan_cuotas,
    numero_a_letras,
    generar_texto_clipboard,
)
from logic.constants import TASA_INTERES_MENSUAL


class TestCalcularPlanCredito(unittest.TestCase):
    def test_valores_exactos_3_cuotas(self):
        # precio_base=100000, 3 cuotas: tasa=24%, financiado=124000,
        # cuota_raw=41333.33 -> redondeo a 100 hacia arriba -> 41400
        plan = calcular_plan_credito(100000, 3)
        self.assertEqual(plan["valor_cuota"], 41400)
        self.assertEqual(plan["precio_final"], 124200)
        self.assertEqual(plan["interes_total"], 124200 - 100000)
        self.assertEqual(plan["num_cuotas"], 3)
        self.assertEqual(plan["precio_base"], 100000)

    def test_valores_exactos_12_cuotas(self):
        # tasa = 0.08*12 = 96% -> financiado = 100000*1.96 = 196000
        # cuota_raw = 196000/12 = 16333.33 -> redondeo a 16400
        plan = calcular_plan_credito(100000, 12)
        self.assertEqual(plan["valor_cuota"], 16400)
        self.assertEqual(plan["precio_final"], 16400 * 12)

    def test_precio_base_cero(self):
        plan = calcular_plan_credito(0, 6)
        self.assertEqual(plan["valor_cuota"], 0)
        self.assertEqual(plan["precio_final"], 0)
        self.assertEqual(plan["interes_total"], 0)

    def test_precio_final_siempre_multiplo_de_valor_cuota(self):
        for num_cuotas in range(3, 13):
            plan = calcular_plan_credito(73450, num_cuotas)
            self.assertEqual(plan["precio_final"], plan["valor_cuota"] * num_cuotas)

    def test_valor_cuota_siempre_multiplo_de_100(self):
        for num_cuotas in range(3, 13):
            plan = calcular_plan_credito(123456, num_cuotas)
            self.assertEqual(plan["valor_cuota"] % 100, 0)

    def test_redondeo_es_siempre_hacia_arriba(self):
        # El precio final redondeado nunca puede ser MENOR al financiado sin redondear
        for num_cuotas in range(3, 13):
            for base in [1000, 55555, 999999]:
                plan = calcular_plan_credito(base, num_cuotas)
                tasa_total = TASA_INTERES_MENSUAL * num_cuotas
                financiado_sin_redondear = base * (1 + tasa_total)
                self.assertGreaterEqual(plan["precio_final"], financiado_sin_redondear - 1e-6)


class TestConsistenciaEntreImplementacionesDePlan(unittest.TestCase):
    """
    calcular_plan_credito, calcular_plan_cuotas y calcular_plan_cuotas_detallado
    son 3 funciones separadas que deberían calcular EXACTAMENTE lo mismo
    (precio_base, num_cuotas, valor_cuota, precio_final). Este test las
    compara entre sí para detectar si alguna vez se desincronizan.
    """

    def test_las_tres_funciones_coinciden_en_todo_el_rango(self):
        for num_cuotas in range(3, 13):
            for base in [0, 1, 100000, 999999.99, 45000.5]:
                a = calcular_plan_credito(base, num_cuotas)
                b = calcular_plan_cuotas(base, num_cuotas)
                c = calcular_plan_cuotas_detallado(base, num_cuotas)

                self.assertAlmostEqual(a["valor_cuota"], b["valor_cuota"], places=6,
                                        msg=f"valor_cuota difiere entre calcular_plan_credito y calcular_plan_cuotas (base={base}, cuotas={num_cuotas})")
                self.assertAlmostEqual(a["valor_cuota"], c["valor_cuota"], places=6,
                                        msg=f"valor_cuota difiere entre calcular_plan_credito y calcular_plan_cuotas_detallado (base={base}, cuotas={num_cuotas})")
                self.assertAlmostEqual(a["precio_final"], b["precio_final"], places=6)
                self.assertAlmostEqual(a["precio_final"], c["precio_final"], places=6)


class TestCalcularComisiones(unittest.TestCase):
    def test_credito_de_la_casa(self):
        # base_capital=100000, monto_total=124200 (con interés)
        comis = calcular_comisiones("Crédito de la Casa", 100000, 124200)
        interes = 124200 - 100000
        gerente_esperado = 100000 * 0.04 + interes * 0.10
        vendedor_esperado = 100000 * 0.03 + interes * 0.08
        empresa_esperada = 124200 - (gerente_esperado + vendedor_esperado)
        self.assertAlmostEqual(comis["gerente"], gerente_esperado, places=6)
        self.assertAlmostEqual(comis["vendedor"], vendedor_esperado, places=6)
        self.assertAlmostEqual(comis["empresa"], empresa_esperada, places=6)
        # Invariante: la suma de las 3 partes siempre da el monto total
        self.assertAlmostEqual(comis["gerente"] + comis["vendedor"] + comis["empresa"], 124200, places=6)

    def test_efectivo(self):
        comis = calcular_comisiones("Efectivo / Transferencia", 100000, 100000)
        self.assertAlmostEqual(comis["gerente"], 4000)
        self.assertAlmostEqual(comis["vendedor"], 3000)
        self.assertAlmostEqual(comis["empresa"], 93000)

    def test_tarjeta_debito_credito_NO_se_confunde_con_credito_de_la_casa(self):
        # "Tarjeta Debito / Credito" contiene la palabra "credito" pero
        # también "tarjeta" -> debe ir por la rama de tarjeta, no la de
        # crédito de la casa (el guard es "credito" in metodo and "tarjeta" not in metodo).
        comis = calcular_comisiones("Tarjeta Debito / Credito", 100000, 115000)
        # En la rama de tarjeta, la comisión se calcula SOLO sobre la base,
        # ignorando el recargo (115000), a diferencia de la rama de crédito de la casa.
        self.assertAlmostEqual(comis["gerente"], 100000 * 0.04)
        self.assertAlmostEqual(comis["vendedor"], 100000 * 0.03)

    def test_6_cuotas(self):
        comis = calcular_comisiones("6 Cuotas", 100000, 118000)
        self.assertAlmostEqual(comis["gerente"], 4000)
        self.assertAlmostEqual(comis["vendedor"], 3000)

    def test_monto_total_menor_a_base_no_da_interes_negativo(self):
        # Caso borde: si por algún motivo monto_total < base_capital en un
        # crédito de la casa, el interés se clampea a 0 (max(0, ...)), no
        # queda negativo.
        comis = calcular_comisiones("Crédito de la Casa", 100000, 90000)
        gerente_esperado = 100000 * 0.04  # interes=0
        self.assertAlmostEqual(comis["gerente"], gerente_esperado)


class TestCalcularPrecioFinal(unittest.TestCase):
    def test_credito_de_la_casa_aplica_interes(self):
        precio = calcular_precio_final(100000, "Crédito de la Casa", cuotas=3)
        self.assertAlmostEqual(precio, 100000 * (1 + TASA_INTERES_MENSUAL * 3))

    def test_otros_metodos_pasan_igual(self):
        precio = calcular_precio_final(100000, "Efectivo / Transferencia")
        self.assertEqual(precio, 100000)

    def test_cuotas_minimo_1(self):
        # Si cuotas viene en 0 o negativo, se fuerza a mínimo 1 (max(1, cuotas))
        precio = calcular_precio_final(100000, "Crédito de la Casa", cuotas=0)
        self.assertAlmostEqual(precio, 100000 * (1 + TASA_INTERES_MENSUAL * 1))


class TestFormatCurrency(unittest.TestCase):
    def test_numero_entero(self):
        self.assertEqual(format_currency(1000), "$1.000")

    def test_numero_grande_con_separador_de_miles(self):
        self.assertEqual(format_currency(1234567), "$1.234.567")

    def test_redondea_a_entero(self):
        self.assertEqual(format_currency(999.6), "$1.000")

    def test_nan_devuelve_vacio(self):
        self.assertEqual(format_currency(float("nan")), "")

    def test_valor_no_numerico_devuelve_vacio(self):
        self.assertEqual(format_currency("no es un numero"), "")

    def test_none_devuelve_vacio(self):
        self.assertEqual(format_currency(None), "")

    def test_negativo(self):
        # No debería explotar con valores negativos (ej: ajustes)
        resultado = format_currency(-500)
        self.assertIn("500", resultado)


class TestNumeroALetras(unittest.TestCase):
    def test_no_explota_y_devuelve_texto(self):
        texto = numero_a_letras(150000)
        self.assertIsInstance(texto, str)
        self.assertTrue(len(texto) > 0)
        self.assertTrue(texto.isupper() or not texto.isalpha())


class TestGenerarTextoClipboard(unittest.TestCase):
    def test_incluye_plan_y_campos_mapeados(self):
        fila = {"PROVEEDOR": "Marca X", "MODELO": "Modelo Y"}
        plan = calcular_plan_credito(100000, 6)
        mapeo = [("PROVEEDOR", "Marca"), ("MODELO", "Modelo")]
        texto = generar_texto_clipboard(fila, plan, mapeo)
        self.assertIn("Marca X", texto)
        self.assertIn("Modelo Y", texto)
        self.assertIn(str(plan["num_cuotas"]), texto)


if __name__ == "__main__":
    unittest.main()
