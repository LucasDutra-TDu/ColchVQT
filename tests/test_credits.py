# tests/test_credits.py
"""
Tests de logic/credits_service.py, con foco especial en la atomicidad de
registrar_venta_a_credito (el fix central de la Fase 2 de la auditoría).
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.base import IsolatedDataTestCase
import logic.credits_service as credits_service
from logic.credits_service import (
    buscar_o_crear_cliente,
    registrar_plan_credito,
    registrar_venta_a_credito,
    obtener_creditos_activos,
    obtener_creditos_finalizados,
    obtener_detalle_credito,
    pagar_cuota,
    anular_pago,
    obtener_id_credito_por_factura,
)
from logic.facturas_db_handler import obtener_historial
from logic.financiero import calcular_plan_credito


CLIENTE_DEMO = {"dni": "30111222", "nombre": "Juan Pérez", "telefono": "1122334455", "direccion": "Calle Falsa 123"}


class TestBuscarOCrearCliente(IsolatedDataTestCase):
    def test_crea_cliente_nuevo(self):
        cliente_id = buscar_o_crear_cliente("111", "Ana", "555", "Calle 1")
        self.assertIsInstance(cliente_id, int)

    def test_mismo_dni_no_duplica_y_actualiza_datos(self):
        id1 = buscar_o_crear_cliente("111", "Ana", "555", "Calle 1")
        id2 = buscar_o_crear_cliente("111", "Ana María", "999", "Calle 2")
        self.assertEqual(id1, id2)
        with credits_service._get_connection() as con:
            row = con.execute("SELECT * FROM clientes WHERE id=?", (id1,)).fetchone()
        self.assertEqual(row["nombre"], "Ana María")
        self.assertEqual(row["telefono"], "999")

    def test_dni_distinto_crea_cliente_distinto(self):
        id1 = buscar_o_crear_cliente("111", "Ana", "555", "Calle 1")
        id2 = buscar_o_crear_cliente("222", "Beto", "666", "Calle 2")
        self.assertNotEqual(id1, id2)


class TestRegistrarPlanCredito(IsolatedDataTestCase):
    """
    registrar_plan_credito() por sí sola asume que ya existe una factura con
    ese id (obtener_detalle_credito hace un INNER JOIN contra facturas).
    En el flujo real de la app esto siempre se cumple porque se usa junto
    con registrar_venta_a_credito() (ver TestRegistrarVentaACreditoAtomicidad
    más abajo), así que acá creamos primero una factura real vía
    registrar_venta() para que obtener_detalle_credito() no rompa.
    """
    def setUp(self):
        super().setUp()
        from logic.facturas_db_handler import registrar_venta
        self.factura_id = registrar_venta([self.item_carrito()], "Crédito de la Casa", 100000)

    def test_crea_credito_y_cuotas(self):
        plan = calcular_plan_credito(100000, 3)
        credito_id = registrar_plan_credito(self.factura_id, CLIENTE_DEMO, plan)
        detalle = obtener_detalle_credito(credito_id)
        self.assertEqual(len(detalle["cuotas"]), 3)
        self.assertEqual(detalle["credito"]["cantidad_cuotas"], 3)
        self.assertEqual(detalle["credito"]["monto_financiado"], plan["precio_final"])
        self.assertEqual(detalle["credito"]["monto_base"], plan["precio_base"])

    def test_primera_cuota_queda_pagada_automaticamente(self):
        plan = calcular_plan_credito(100000, 3)
        credito_id = registrar_plan_credito(self.factura_id, CLIENTE_DEMO, plan)
        detalle = obtener_detalle_credito(credito_id)
        cuota_1 = next(c for c in detalle["cuotas"] if c["numero_cuota"] == 1)
        self.assertEqual(cuota_1["estado"], "PAGADO")
        self.assertIsNotNone(cuota_1["fecha_pago"])

    def test_cuotas_siguientes_quedan_pendientes(self):
        plan = calcular_plan_credito(100000, 3)
        credito_id = registrar_plan_credito(self.factura_id, CLIENTE_DEMO, plan)
        detalle = obtener_detalle_credito(credito_id)
        for c in detalle["cuotas"]:
            if c["numero_cuota"] != 1:
                self.assertEqual(c["estado"], "PENDIENTE")
                self.assertIsNone(c["fecha_pago"])

    def test_vencimientos_espaciados_30_dias(self):
        import datetime
        plan = calcular_plan_credito(100000, 3)
        credito_id = registrar_plan_credito(self.factura_id, CLIENTE_DEMO, plan)
        detalle = obtener_detalle_credito(credito_id)
        cuotas_ordenadas = sorted(detalle["cuotas"], key=lambda c: c["numero_cuota"])
        f1 = datetime.date.fromisoformat(cuotas_ordenadas[0]["fecha_vencimiento"])
        f2 = datetime.date.fromisoformat(cuotas_ordenadas[1]["fecha_vencimiento"])
        f3 = datetime.date.fromisoformat(cuotas_ordenadas[2]["fecha_vencimiento"])
        self.assertEqual((f2 - f1).days, 30)
        self.assertEqual((f3 - f1).days, 60)

    def test_todas_las_cuotas_valen_lo_mismo(self):
        plan = calcular_plan_credito(100000, 6)
        credito_id = registrar_plan_credito(self.factura_id, CLIENTE_DEMO, plan)
        detalle = obtener_detalle_credito(credito_id)
        montos = {c["monto"] for c in detalle["cuotas"]}
        self.assertEqual(montos, {plan["valor_cuota"]})


class TestRegistrarVentaACreditoAtomicidad(IsolatedDataTestCase):
    """
    El caso central: registrar_venta_a_credito debe crear la factura Y el
    plan de crédito en la MISMA transacción. Si el plan falla (datos
    incompletos, error de negocio, lo que sea), no debe quedar ninguna
    factura "huérfana" sin cliente ni cronograma asociado.
    """

    def test_caso_exitoso_crea_factura_y_credito_coherentes(self):
        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000)]
        plan = calcular_plan_credito(100000, 3)
        factura_id, credito_id = registrar_venta_a_credito(
            items, "Crédito de la Casa", plan["precio_final"], CLIENTE_DEMO, plan
        )
        # La factura existe
        factura = next(f for f in obtener_historial() if f["id"] == factura_id)
        self.assertEqual(factura["metodo_pago"], "Crédito de la Casa")
        # El crédito apunta a esa factura
        self.assertEqual(obtener_id_credito_por_factura(factura_id), credito_id)
        detalle = obtener_detalle_credito(credito_id)
        self.assertEqual(detalle["credito"]["factura_id"], factura_id)
        self.assertEqual(len(detalle["cuotas"]), 3)

    def test_fallo_en_plan_credito_no_deja_factura_huerfana(self):
        """
        Test de ROLLBACK: si plan_info viene incompleto (falta una key que
        _insertar_plan_credito necesita), la excepción debe propagarse y,
        gracias a compartir la misma conexión/transacción, NO debe quedar
        ninguna factura registrada tampoco. Antes de este fix (ver
        auditoría, hallazgo crítico #1), la factura SÍ quedaba guardada
        porque registrar_venta() hacía su propio commit independiente.
        """
        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000)]
        plan_incompleto = {
            "num_cuotas": 3,
            "valor_cuota": 41400,
            # falta 'precio_final' y 'precio_base' a propósito
        }
        with self.assertRaises(KeyError):
            registrar_venta_a_credito(
                items, "Crédito de la Casa", 124200, CLIENTE_DEMO, plan_incompleto
            )

        # Nada debe haber quedado persistido: ni factura, ni crédito, ni cliente.
        self.assertEqual(obtener_historial(), [])
        self.assertEqual(obtener_creditos_activos(), [])
        with credits_service._get_connection() as con:
            clientes = con.execute("SELECT * FROM clientes").fetchall()
        self.assertEqual(len(clientes), 0)

    def test_fallo_en_plan_credito_no_deja_cliente_huerfano_si_ya_existia(self):
        # Caso más sutil: el cliente YA existía de una venta anterior. Si el
        # segundo intento de venta a crédito falla, el cliente preexistente
        # debe seguir intacto (no se borra), pero no debe crearse un
        # crédito/factura nuevos asociados al intento fallido.
        buscar_o_crear_cliente(CLIENTE_DEMO["dni"], CLIENTE_DEMO["nombre"], "000", "Vieja Dir")

        items = [self.item_carrito(precio_venta_final=100000, precio_lista_base=100000)]
        plan_incompleto = {"num_cuotas": 3, "valor_cuota": 41400}
        with self.assertRaises(KeyError):
            registrar_venta_a_credito(
                items, "Crédito de la Casa", 124200, CLIENTE_DEMO, plan_incompleto
            )

        with credits_service._get_connection() as con:
            clientes = con.execute("SELECT * FROM clientes WHERE dni=?", (CLIENTE_DEMO["dni"],)).fetchall()
        self.assertEqual(len(clientes), 1)  # el cliente preexistente sigue ahí, sin duplicar
        self.assertEqual(obtener_historial(), [])  # pero ninguna factura nueva


class TestPagarYAnularCuota(IsolatedDataTestCase):
    def setUp(self):
        super().setUp()
        from logic.facturas_db_handler import registrar_venta
        factura_id = registrar_venta([self.item_carrito()], "Crédito de la Casa", 100000)
        plan = calcular_plan_credito(100000, 3)
        self.credito_id = registrar_plan_credito(factura_id, CLIENTE_DEMO, plan)
        detalle = obtener_detalle_credito(self.credito_id)
        self.cuotas = sorted(detalle["cuotas"], key=lambda c: c["numero_cuota"])

    def test_pagar_todas_las_cuotas_finaliza_el_credito(self):
        for c in self.cuotas:
            if c["estado"] != "PAGADO":
                pagar_cuota(c["id"])
        activos = [c["id"] for c in obtener_creditos_activos()]
        self.assertNotIn(self.credito_id, activos)
        finalizados = [c["id"] for c in obtener_creditos_finalizados()]
        self.assertIn(self.credito_id, finalizados)

    def test_pagar_parcial_mantiene_credito_activo(self):
        # Solo pagamos la cuota 2, dejando la 3 pendiente.
        cuota_2 = next(c for c in self.cuotas if c["numero_cuota"] == 2)
        pagar_cuota(cuota_2["id"])
        activos = [c["id"] for c in obtener_creditos_activos()]
        self.assertIn(self.credito_id, activos)

    def test_anular_pago_revierte_estado_pagado(self):
        cuota_2 = next(c for c in self.cuotas if c["numero_cuota"] == 2)
        pagar_cuota(cuota_2["id"])
        anular_pago(cuota_2["id"])
        detalle = obtener_detalle_credito(self.credito_id)
        cuota_2_actualizada = next(c for c in detalle["cuotas"] if c["numero_cuota"] == 2)
        self.assertEqual(cuota_2_actualizada["estado"], "PENDIENTE")
        self.assertIsNone(cuota_2_actualizada["fecha_pago"])

    def test_anular_pago_reabre_credito_finalizado(self):
        for c in self.cuotas:
            if c["estado"] != "PAGADO":
                pagar_cuota(c["id"])
        # El crédito quedó FINALIZADO. Anulamos una cuota.
        cuota_2 = next(c for c in self.cuotas if c["numero_cuota"] == 2)
        anular_pago(cuota_2["id"])
        activos = [c["id"] for c in obtener_creditos_activos()]
        self.assertIn(self.credito_id, activos)
        finalizados = [c["id"] for c in obtener_creditos_finalizados()]
        self.assertNotIn(self.credito_id, finalizados)


if __name__ == "__main__":
    unittest.main()
