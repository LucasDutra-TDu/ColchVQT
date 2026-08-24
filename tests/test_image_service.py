# tests/test_image_service.py
"""
Tests de logic/image_service.py, con foco en la carga de la tipografía del
flyer (Fase 3 de la auditoría: font_path = "arial.ttf" relativo nunca se
encontraba y siempre caía al font por defecto de Pillow). Ahora se bundlea
Liberation Sans (SIL OFL) en data/recursos/ vía RUTA_FONT_FLYER.
"""
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageFont

import logic.image_service as image_service
import logic.log_service as log_service
from logic.image_service import _cargar_fuentes_flyer, obtener_ruta_imagen, generar_flyer_producto


class TestCargarFuentesFlyer(unittest.TestCase):
    def setUp(self):
        # _cargar_fuentes_flyer() puede llamar a log_warning() (caso de
        # fuente faltante); redirigimos el log a una carpeta temporal para
        # no ensuciar el data/app.log real del proyecto.
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_imglog_")
        self._original_log_base_dir = log_service.BASE_DIR
        self._original_log_path = log_service.LOG_PATH
        log_service.BASE_DIR = Path(self._tmp_dir)
        log_service.LOG_PATH = Path(self._tmp_dir) / "app.log"

    def tearDown(self):
        log_service.BASE_DIR = self._original_log_base_dir
        log_service.LOG_PATH = self._original_log_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_carga_la_fuente_bundleada_si_existe(self):
        # RUTA_FONT_FLYER apunta al Liberation Sans real del proyecto
        # (ver logic/constants.py) -- si el archivo está presente (como
        # debería estarlo tras esta Fase 3), debe cargarse de verdad, con
        # el tamaño pedido, no caer al font por defecto de Pillow.
        font_main, font_title, font_price = _cargar_fuentes_flyer()
        self.assertEqual(font_main.getname()[0], "Liberation Sans")
        self.assertEqual(font_main.size, 32)
        self.assertEqual(font_title.size, 45)
        self.assertEqual(font_price.size, 38)

    def test_cae_al_font_por_defecto_si_no_existe_el_archivo(self):
        ruta_falsa = Path(tempfile.mkdtemp()) / "no_existe.ttf"
        with patch.object(image_service, "RUTA_FONT_FLYER", ruta_falsa):
            font_main, font_title, font_price = _cargar_fuentes_flyer()
            # No debe explotar -- debe devolver el font por defecto de Pillow,
            # que en cualquier versión NO se llama "Liberation Sans".
            self.assertNotEqual(font_main.getname()[0], "Liberation Sans")
            self.assertNotEqual(font_title.getname()[0], "Liberation Sans")
            self.assertNotEqual(font_price.getname()[0], "Liberation Sans")


class TestObtenerRutaImagen(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_img_")
        self._tmp_path = Path(self._tmp_dir)
        self._original_img_dir = image_service.IMG_CATALOGO_DIR
        image_service.IMG_CATALOGO_DIR = self._tmp_path

    def tearDown(self):
        image_service.IMG_CATALOGO_DIR = self._original_img_dir
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_encuentra_imagen_por_codigo(self):
        (self._tmp_path / "1000.png").write_bytes(b"fake png")
        ruta = obtener_ruta_imagen({"CÓDIGO": "1000"})
        self.assertEqual(ruta.name, "1000.png")

    def test_codigo_float_se_normaliza(self):
        (self._tmp_path / "1000.png").write_bytes(b"fake png")
        ruta = obtener_ruta_imagen({"CÓDIGO": 1000.0})
        self.assertEqual(ruta.name, "1000.png")

    def test_sin_imagen_devuelve_none(self):
        ruta = obtener_ruta_imagen({"CÓDIGO": "NOEXISTE"})
        self.assertIsNone(ruta)

    def test_codigo_vacio_devuelve_none(self):
        ruta = obtener_ruta_imagen({"CÓDIGO": ""})
        self.assertIsNone(ruta)


class TestGenerarFlyerProducto(unittest.TestCase):
    """
    Test de integración liviano: genera un flyer real (con la fuente
    bundleada) para confirmar que todo el pipeline de Pillow no explota.
    """
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_flyer_")
        self.ruta_imagen = Path(self._tmp_dir) / "producto.png"
        Image.new("RGB", (300, 300), color="blue").save(self.ruta_imagen)
        self.ruta_logo = Path(self._tmp_dir) / "logo_inexistente.png"  # no existe a propósito

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_genera_flyer_sin_plan_credito(self):
        row = {
            "PROVEEDOR": "Marca Test",
            "MODELO": "Modelo Test",
            "MEDIDA (LARG-ANCH-ESP)": "140x190x25",
            "EFECTIVO/TRANSF": 150000,
        }
        img_io = generar_flyer_producto(row, self.ruta_imagen, ruta_logo=self.ruta_logo)
        self.assertGreater(len(img_io.getvalue()), 0)
        # Confirmamos que es un PNG válido y legible
        img_io.seek(0)
        img = Image.open(img_io)
        self.assertEqual(img.size, (1200, 800))

    def test_genera_flyer_con_plan_credito(self):
        row = {"PROVEEDOR": "Marca Test", "MODELO": "Modelo Test"}
        plan = {"num_cuotas": 3, "valor_cuota": 41400, "precio_final": 124200}
        img_io = generar_flyer_producto(row, self.ruta_imagen, ruta_logo=self.ruta_logo, plan_credito=plan)
        img_io.seek(0)
        img = Image.open(img_io)
        self.assertEqual(img.format, "PNG")


if __name__ == "__main__":
    unittest.main()
