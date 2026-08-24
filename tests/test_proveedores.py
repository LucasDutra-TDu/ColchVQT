# tests/test_proveedores.py
"""
Tests de logic/proveedores_service.py: CRUD de proveedores/movimientos y,
sobre todo, la escritura atómica de proveedores.json (hallazgo #3 de la
auditoría: antes se escribía directo sobre el archivo real, y un corte a
mitad de escritura dejaba un JSON corrupto perdiendo todo el historial).
"""
import sys
import json
import datetime
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import logic.proveedores_service as proveedores_service
import logic.log_service as log_service
from logic.proveedores_service import ProveedoresService, FormaPago


class _ProveedoresTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_proveedores_")
        self._tmp_path = Path(self._tmp_dir)
        self._original_base_dir = proveedores_service.BASE_DIR
        proveedores_service.BASE_DIR = self._tmp_path

        # proveedores_service.log_error() delega en logic.log_service, que
        # escribe a su PROPIO LOG_PATH (no al BASE_DIR de proveedores_service).
        # Si no lo redirigimos también, los tests que fuerzan errores
        # (ver TestPersistenciaJSON) terminan escribiendo en el
        # data/app.log REAL del proyecto en vez de en la carpeta temporal.
        self._original_log_base_dir = log_service.BASE_DIR
        self._original_log_path = log_service.LOG_PATH
        log_service.BASE_DIR = self._tmp_path
        log_service.LOG_PATH = self._tmp_path / "data" / "app.log"

        self.service = ProveedoresService()

    def tearDown(self):
        proveedores_service.BASE_DIR = self._original_base_dir
        log_service.BASE_DIR = self._original_log_base_dir
        log_service.LOG_PATH = self._original_log_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestCrudProveedores(_ProveedoresTestCase):
    def test_crear_proveedor(self):
        prov = self.service.crear_proveedor("Espumas SA", "1122334455")
        self.assertIsNotNone(prov)
        self.assertIn(prov.id, self.service.proveedores)

    def test_no_permite_nombre_duplicado(self):
        self.service.crear_proveedor("Espumas SA", "111")
        resultado = self.service.crear_proveedor("espumas sa", "222")  # case-insensitive
        self.assertIsNone(resultado)
        self.assertEqual(len(self.service.proveedores), 1)

    def test_editar_proveedor(self):
        prov = self.service.crear_proveedor("Espumas SA", "111")
        ok = self.service.editar_proveedor(prov.id, {"nombre": "Espumas SRL", "num_tel": "999"})
        self.assertTrue(ok)
        actualizado = self.service.obtener_proveedor_por_id(prov.id)
        self.assertEqual(actualizado.nombre, "Espumas SRL")
        self.assertEqual(actualizado.num_tel, "999")

    def test_editar_proveedor_a_nombre_duplicado_falla(self):
        self.service.crear_proveedor("Espumas SA", "111")
        prov2 = self.service.crear_proveedor("Telas SA", "222")
        ok = self.service.editar_proveedor(prov2.id, {"nombre": "Espumas SA"})
        self.assertFalse(ok)

    def test_eliminar_proveedor(self):
        prov = self.service.crear_proveedor("Espumas SA", "111")
        ok = self.service.eliminar_proveedor(prov.id)
        self.assertTrue(ok)
        self.assertIsNone(self.service.obtener_proveedor_por_id(prov.id))

    def test_eliminar_proveedor_inexistente_devuelve_false(self):
        self.assertFalse(self.service.eliminar_proveedor("id-fantasma"))

    def test_obtener_proveedores_filtra_por_query(self):
        self.service.crear_proveedor("Espumas SA", "111")
        self.service.crear_proveedor("Telas del Sur", "222")
        resultado = self.service.obtener_proveedores(query="espum")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].nombre, "Espumas SA")


class TestMovimientosProveedor(_ProveedoresTestCase):
    def setUp(self):
        super().setUp()
        self.prov = self.service.crear_proveedor("Espumas SA", "111")

    def _mov_data(self, debe=0.0, haber=0.0, descripcion="pago"):
        return {
            "fecha": datetime.datetime(2026, 1, 15).isoformat(),
            "debe": debe,
            "haber": haber,
            "descripcion": descripcion,
            "forma_pago": FormaPago.EFECTIVO.value,
        }

    def test_agregar_movimiento(self):
        mov = self.service.agregar_movimiento(self.prov.id, self._mov_data(debe=1000))
        self.assertIsNotNone(mov)
        prov_actualizado = self.service.obtener_proveedor_por_id(self.prov.id)
        self.assertEqual(len(prov_actualizado.movimientos), 1)

    def test_saldo_es_haber_menos_debe(self):
        self.service.agregar_movimiento(self.prov.id, self._mov_data(haber=5000))
        self.service.agregar_movimiento(self.prov.id, self._mov_data(debe=2000))
        prov_actualizado = self.service.obtener_proveedor_por_id(self.prov.id)
        self.assertEqual(prov_actualizado.saldo, 3000)

    def test_editar_movimiento(self):
        mov = self.service.agregar_movimiento(self.prov.id, self._mov_data(debe=1000))
        self.service.editar_movimiento(self.prov.id, mov.id, {"debe": 1500})
        prov_actualizado = self.service.obtener_proveedor_por_id(self.prov.id)
        mov_actualizado = next(m for m in prov_actualizado.movimientos if m.id == mov.id)
        self.assertEqual(mov_actualizado.debe, 1500)

    def test_eliminar_movimiento(self):
        mov = self.service.agregar_movimiento(self.prov.id, self._mov_data(debe=1000))
        ok = self.service.eliminar_movimiento(self.prov.id, mov.id)
        self.assertTrue(ok)
        prov_actualizado = self.service.obtener_proveedor_por_id(self.prov.id)
        self.assertEqual(len(prov_actualizado.movimientos), 0)


class TestPersistenciaJSON(_ProveedoresTestCase):
    def test_guardar_y_recargar_preserva_datos(self):
        self.service.crear_proveedor("Espumas SA", "111")
        self.service.agregar_movimiento(
            list(self.service.proveedores.keys())[0],
            {
                "fecha": datetime.datetime(2026, 1, 1).isoformat(),
                "debe": 500,
                "haber": 0,
                "descripcion": "compra de telas",
                "forma_pago": FormaPago.TRANSFERENCIA.value,
            },
        )
        # Nueva instancia del servicio, misma carpeta -> debe recargar todo desde disco
        service2 = ProveedoresService()
        self.assertEqual(len(service2.proveedores), 1)
        prov2 = list(service2.proveedores.values())[0]
        self.assertEqual(prov2.nombre, "Espumas SA")
        self.assertEqual(len(prov2.movimientos), 1)
        self.assertEqual(prov2.movimientos[0].descripcion, "compra de telas")

    def test_archivo_json_es_valido_tras_guardar(self):
        self.service.crear_proveedor("Espumas SA", "111")
        contenido = self.service.data_file.read_text(encoding="utf-8")
        data = json.loads(contenido)  # no debe explotar
        self.assertEqual(len(data), 1)

    def test_no_queda_archivo_temporal_tras_guardar_exitoso(self):
        self.service.crear_proveedor("Espumas SA", "111")
        tmp_file = self.service.data_file.parent / f"{self.service.data_file.name}.tmp"
        self.assertFalse(tmp_file.exists())

    def test_fallo_de_escritura_no_corrompe_el_archivo_real(self):
        """
        EL CASO CRÍTICO: si json.dump() explota a mitad de camino (ej: un
        objeto no serializable, disco lleno, etc.), el archivo REAL
        (proveedores.json) no debe tocarse -- solo se escribe sobre el
        temporal, y recién se hace el swap atómico si todo salió bien.
        """
        self.service.crear_proveedor("Espumas SA", "111")  # deja un JSON real válido
        contenido_original = self.service.data_file.read_text(encoding="utf-8")

        with patch("logic.proveedores_service.json.dump", side_effect=TypeError("no serializable")):
            # crear_proveedor llama a guardar_proveedores() internamente;
            # el error se loggea y se traga (no debe propagar ni crashear).
            self.service.crear_proveedor("Telas SA", "222")

        # El archivo real sigue teniendo el contenido de ANTES del intento fallido
        self.assertEqual(self.service.data_file.read_text(encoding="utf-8"), contenido_original)
        # Y el temporal fallido no debe quedar abandonado
        tmp_file = self.service.data_file.parent / f"{self.service.data_file.name}.tmp"
        self.assertFalse(tmp_file.exists())

    def test_archivo_vacio_o_corrupto_al_cargar_no_crashea(self):
        self.service.data_file.write_text("esto no es json valido {{{", encoding="utf-8")
        self.service.cargar_proveedores()
        self.assertEqual(self.service.proveedores, {})


if __name__ == "__main__":
    unittest.main()
