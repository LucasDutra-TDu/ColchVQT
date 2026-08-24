# tests/test_stats_service.py
"""
Tests de integración de logic/stats_service.py: reporte mensual de
ganancias/comisiones que combina facturas directas y cuotas de crédito.

Es el módulo con más lógica de negocio "cruzada" (facturas + créditos +
comisiones), así que estos tests son más de integración: registran ventas
reales (vía registrar_venta / registrar_venta_a_credito) contra las bases
temporales y verifican el reporte resultante.
"""
import sys
import json
import datetime
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.base import IsolatedDataTestCase
from logic.facturas_db_handler import registrar_venta, actualizar_venta_especial
from logic.credits_service import registrar_venta_a_credito, pagar_cuota, obtener_detalle_credito
from logic.financiero import calcular_plan_credito
from logic.stats_service import obtener_reporte_mensual

CLIENTE_DEMO = {"dni": "30111222", "nombre": "Juan Pérez", "telefono": "", "direccion": ""}


def _mes_anio_actual():
    hoy = datetime.date.today()
    return hoy.month, hoy.year


class TestVentasDirectas(IsolatedDataTestCase):
    def test_venta_en_efectivo_aparece_en_el_reporte(self):
        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000, costo=60000)]
        registrar_venta(items, "Efectivo / Transferencia", 100000)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)

        self.assertEqual(len(reporte["ventas"]), 1)
        venta = reporte["ventas"][0]
        self.assertEqual(venta["tipo_origen"], "FACTURA")
        self.assertEqual(venta["monto"], 100000)

    def test_comision_efectivo_calculada_sobre_base_menos_costo(self):
        # base=100000, costo=60000 -> comision gerente = 100000*0.04=4000,
        # ganancia_empresa = (100000 - comis_gerente - comis_vendedor) - costo
        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000, costo=60000)]
        registrar_venta(items, "Efectivo / Transferencia", 100000)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)
        venta = reporte["ventas"][0]

        self.assertAlmostEqual(venta["comis_gerente"], 4000)
        self.assertAlmostEqual(venta["comis_vendedor"], 3000)
        # empresa_bruta = 100000 - 4000 - 3000 = 93000; neta = 93000 - 60000 = 33000
        self.assertAlmostEqual(venta["ganancia_empresa"], 33000)

    def test_mes_distinto_no_aparece_en_el_reporte(self):
        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000)]
        registrar_venta(items, "Efectivo / Transferencia", 100000)

        # Preguntamos por un mes que casi seguro no es el actual
        mes_futuro = datetime.date.today().month % 12 + 1
        anio = datetime.date.today().year + (1 if mes_futuro == 1 and datetime.date.today().month == 12 else 0)
        reporte = obtener_reporte_mensual(mes_futuro, anio)
        self.assertEqual(reporte["ventas"], [])

    def test_reporte_vacio_no_explota(self):
        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)
        self.assertEqual(reporte["ventas"], [])
        self.assertEqual(reporte["totales"]["total_bruto"], 0)

    def test_venta_con_comisiones_override_usa_el_override_no_el_calculo(self):
        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000, costo=60000)]
        factura_id = registrar_venta(items, "Efectivo / Transferencia", 100000)
        override = json.dumps({"gerente": 1000, "vendedor": 500, "empresa": 98500})
        actualizar_venta_especial(factura_id, 100000, override)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)
        venta = reporte["ventas"][0]
        self.assertEqual(venta["comis_gerente"], 1000)
        self.assertEqual(venta["comis_vendedor"], 500)
        # OJO: a diferencia de la rama sin override, acá NO se resta el costo
        # histórico -- es un hallazgo/comportamiento a tener presente, no algo
        # que este test deba "arreglar", solo documentar.
        self.assertEqual(venta["ganancia_empresa"], 98500)


class TestFacturasDeCreditoExcluidasDeDirectas(IsolatedDataTestCase):
    def test_venta_a_credito_NO_aparece_como_venta_directa(self):
        items = [self.item_carrito(precio_venta_final=124200, precio_lista_base=100000, costo=50000)]
        plan = calcular_plan_credito(100000, 3)
        factura_id, credito_id = registrar_venta_a_credito(
            items, "Crédito de la Casa", plan["precio_final"], CLIENTE_DEMO, plan
        )

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)

        # No debe existir ninguna entrada de tipo FACTURA para esta venta
        entradas_factura = [v for v in reporte["ventas"] if v["tipo_origen"] == "FACTURA"]
        self.assertEqual(entradas_factura, [])

    def test_solo_la_cuota_1_pagada_hoy_aparece_como_CUOTA_CREDITO(self):
        items = [self.item_carrito(precio_venta_final=124200, precio_lista_base=100000, costo=50000)]
        plan = calcular_plan_credito(100000, 3)
        registrar_venta_a_credito(items, "Crédito de la Casa", plan["precio_final"], CLIENTE_DEMO, plan)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)

        entradas_credito = [v for v in reporte["ventas"] if v["tipo_origen"] == "CREDITO"]
        # La cuota 1 se marca PAGADO automáticamente al crear el plan (ver
        # credits_service._insertar_plan_credito), así que debe aparecer.
        self.assertEqual(len(entradas_credito), 1)
        self.assertEqual(entradas_credito[0]["monto"], plan["valor_cuota"])

    def test_pagar_una_cuota_mas_la_suma_al_reporte_del_mes_de_pago(self):
        items = [self.item_carrito(precio_venta_final=124200, precio_lista_base=100000, costo=50000)]
        plan = calcular_plan_credito(100000, 3)
        factura_id, credito_id = registrar_venta_a_credito(
            items, "Crédito de la Casa", plan["precio_final"], CLIENTE_DEMO, plan
        )
        detalle = obtener_detalle_credito(credito_id)
        cuota_2 = next(c for c in detalle["cuotas"] if c["numero_cuota"] == 2)
        pagar_cuota(cuota_2["id"])  # se paga "hoy" -> mes actual

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)
        entradas_credito = [v for v in reporte["ventas"] if v["tipo_origen"] == "CREDITO"]
        self.assertEqual(len(entradas_credito), 2)  # cuota 1 (automática) + cuota 2 (recién pagada)

    def test_prorrateo_capital_interes_de_la_cuota_es_coherente(self):
        items = [self.item_carrito(precio_venta_final=124200, precio_lista_base=100000, costo=0)]
        plan = calcular_plan_credito(100000, 3)  # precio_base=100000, precio_final=124200
        registrar_venta_a_credito(items, "Crédito de la Casa", plan["precio_final"], CLIENTE_DEMO, plan)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)
        entrada_cuota_1 = next(v for v in reporte["ventas"] if v["tipo_origen"] == "CREDITO")

        # ratio_base = 100000/124200; parte_capital = monto_cuota * ratio_base
        ratio_base = plan["precio_base"] / plan["precio_final"]
        parte_capital = plan["valor_cuota"] * ratio_base
        parte_interes = plan["valor_cuota"] - parte_capital
        comis_gerente_esperada = parte_capital * 0.04 + parte_interes * 0.10
        self.assertAlmostEqual(entrada_cuota_1["comis_gerente"], comis_gerente_esperada, places=4)


class TestInvarianteSumaDeTotales(IsolatedDataTestCase):
    """
    Invariante de negocio: cuando NO hay recargo (base == total, ej. pago en
    efectivo o crédito de la casa con su interés ya incluido en 'monto'),
    gerente + vendedor + empresa debe sumar exactamente el monto de la
    venta -- el 100% del bruto se reparte entre esas tres bolsas, ni más ni
    menos.
    """
    def test_invariante_sin_recargo_suma_exactamente_el_bruto(self):
        casos = [
            ("Efectivo / Transferencia", 100000, 100000),
            ("3 Cuotas", 200000, 200000),  # sin recargo: base == total
        ]
        for metodo, base, total in casos:
            items = [self.item_carrito(precio_venta_final=total, precio_lista_base=base, costo=0)]
            registrar_venta(items, metodo, total)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)

        for venta in reporte["ventas"]:
            suma = venta["comis_gerente"] + venta["comis_vendedor"] + venta["ganancia_empresa"]
            self.assertAlmostEqual(suma, venta["monto"], places=4)

    def test_HALLAZGO_venta_con_tarjeta_y_recargo_el_recargo_no_se_reparte_ni_se_cuenta(self):
        """
        Documenta un comportamiento real (no necesariamente un bug a
        arreglar acá, pero sí un hallazgo a tener en cuenta): en la rama
        "tarjeta" de calcular_comisiones(), gerente/vendedor/empresa se
        calculan SOLO sobre 'base_capital', ignorando 'monto_total'. Si el
        método de pago tiene recargo (ej: Tarjeta con +15% sobre la base),
        ese recargo queda registrado como 'monto' de la venta en el
        reporte, pero NINGUNA de las tres bolsas (gerente/vendedor/empresa)
        lo refleja: desaparece de la sumatoria interna del reporte, aunque
        sí impacta 'total_bruto'. Vale la pena confirmarlo con el dueño del
        negocio: ¿el recargo debería ir 100% a "empresa" (cubre el costo
        de la tarjeta) en vez de no aparecer en ningún lado?
        """
        base, total = 100000, 115000  # 15% de recargo por tarjeta
        items = [self.item_carrito(precio_venta_final=total, precio_lista_base=base, costo=0)]
        registrar_venta(items, "Tarjeta Debito / Credito", total)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)
        venta = reporte["ventas"][0]

        suma_reparto = venta["comis_gerente"] + venta["comis_vendedor"] + venta["ganancia_empresa"]
        self.assertAlmostEqual(suma_reparto, base)      # el reparto interno ignora el recargo
        self.assertAlmostEqual(venta["monto"], total)   # pero el monto bruto reportado SÍ lo incluye
        self.assertNotAlmostEqual(suma_reparto, venta["monto"])

    def test_totales_del_reporte_son_la_suma_de_cada_venta(self):
        items1 = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000, costo=0)]
        items2 = [self.item_carrito(precio_venta_final=50000, precio_lista_base=50000, costo=0)]
        registrar_venta(items1, "Efectivo / Transferencia", 100000)
        registrar_venta(items2, "Efectivo / Transferencia", 50000)

        mes, anio = _mes_anio_actual()
        reporte = obtener_reporte_mensual(mes, anio)

        suma_bruto = sum(v["monto"] for v in reporte["ventas"])
        suma_gerente = sum(v["comis_gerente"] for v in reporte["ventas"])
        self.assertAlmostEqual(reporte["totales"]["total_bruto"], suma_bruto)
        self.assertAlmostEqual(reporte["totales"]["gerente"], suma_gerente)


if __name__ == "__main__":
    unittest.main()
