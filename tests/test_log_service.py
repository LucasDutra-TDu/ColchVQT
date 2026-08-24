# tests/test_log_service.py
"""
Tests de logic/log_service.py: logging a archivo con rotación por tamaño
(Fase 1 de la auditoría -- la app se compila --windowed, sin consola, así
que sin esto los errores silenciosos no quedaban rastro en ningún lado).
"""
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import logic.log_service as log_service


class _LogServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_log_")
        self._tmp_path = Path(self._tmp_dir)
        self._original_base_dir = log_service.BASE_DIR
        self._original_log_path = log_service.LOG_PATH
        log_service.BASE_DIR = self._tmp_path
        log_service.LOG_PATH = self._tmp_path / "data" / "app.log"

    def tearDown(self):
        log_service.BASE_DIR = self._original_base_dir
        log_service.LOG_PATH = self._original_log_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestEscribirLog(_LogServiceTestCase):
    def test_crea_el_archivo_si_no_existe(self):
        log_service.log_info("primer mensaje")
        self.assertTrue(log_service.LOG_PATH.exists())

    def test_formato_incluye_nivel_timestamp_y_mensaje(self):
        log_service.log_error("algo se rompió")
        contenido = log_service.LOG_PATH.read_text(encoding="utf-8")
        self.assertIn("[ERROR]", contenido)
        self.assertIn("algo se rompió", contenido)
        # Timestamp con formato YYYY-MM-DD HH:MM:SS entre corchetes
        import re
        self.assertRegex(contenido, r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]")

    def test_niveles_correctos(self):
        log_service.log_info("info msg")
        log_service.log_warning("warning msg")
        log_service.log_error("error msg")
        contenido = log_service.LOG_PATH.read_text(encoding="utf-8")
        self.assertIn("[INFO] info msg", contenido)
        self.assertIn("[WARNING] warning msg", contenido)
        self.assertIn("[ERROR] error msg", contenido)

    def test_mensajes_se_acumulan_sin_pisarse(self):
        log_service.log_info("uno")
        log_service.log_info("dos")
        log_service.log_info("tres")
        contenido = log_service.LOG_PATH.read_text(encoding="utf-8")
        self.assertEqual(contenido.count("\n"), 3)


class TestRotacionDeLog(_LogServiceTestCase):
    def test_no_rota_si_esta_por_debajo_del_limite(self):
        log_service.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        log_service.LOG_PATH.write_text("x" * 1000, encoding="utf-8")
        log_service.log_info("mensaje corto")
        backup_path = log_service.LOG_PATH.with_suffix(".log.bak")
        self.assertFalse(backup_path.exists())

    def test_rota_a_bak_cuando_supera_el_limite(self):
        log_service.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Simulamos un log ya pesado, por encima de MAX_LOG_BYTES
        log_service.LOG_PATH.write_bytes(b"x" * (log_service.MAX_LOG_BYTES + 1))

        log_service.log_info("esto dispara la rotación")

        backup_path = log_service.LOG_PATH.with_suffix(".log.bak")
        self.assertTrue(backup_path.exists())
        # El .bak tiene el contenido viejo (pesado), el log activo es nuevo y chico
        self.assertGreater(backup_path.stat().st_size, log_service.MAX_LOG_BYTES)
        self.assertLess(log_service.LOG_PATH.stat().st_size, log_service.MAX_LOG_BYTES)

    def test_log_activo_tras_rotar_contiene_solo_el_mensaje_nuevo(self):
        log_service.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        log_service.LOG_PATH.write_bytes(b"x" * (log_service.MAX_LOG_BYTES + 1))
        log_service.log_info("mensaje post-rotacion")
        contenido_nuevo = log_service.LOG_PATH.read_text(encoding="utf-8")
        self.assertIn("mensaje post-rotacion", contenido_nuevo)
        self.assertNotIn("x" * 100, contenido_nuevo)

    def test_rotacion_no_pierde_una_segunda_rotacion_previa(self):
        # Si ya existía un .bak de una rotación anterior, la nueva rotación
        # lo reemplaza (Path.replace sobreescribe el destino). Documentamos
        # el comportamiento actual: solo se conserva UN nivel de backup.
        log_service.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        backup_path = log_service.LOG_PATH.with_suffix(".log.bak")
        backup_path.write_text("backup viejo", encoding="utf-8")
        log_service.LOG_PATH.write_bytes(b"x" * (log_service.MAX_LOG_BYTES + 1))

        log_service.log_info("nueva rotacion")

        contenido_bak = backup_path.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("backup viejo", contenido_bak)


class TestLoggingNuncaExplotaLaApp(_LogServiceTestCase):
    def test_directorio_no_escribible_no_lanza_excepcion(self):
        # Apuntamos LOG_PATH a una ruta imposible de crear (un archivo
        # existente usado como si fuera carpeta) para forzar un error de
        # IO, y confirmamos que log_xxx() no propaga la excepción.
        archivo_bloqueante = self._tmp_path / "no_es_carpeta"
        archivo_bloqueante.write_text("soy un archivo, no una carpeta", encoding="utf-8")
        log_service.LOG_PATH = archivo_bloqueante / "app.log"

        try:
            log_service.log_error("esto no debería crashear la app")
        except Exception as e:
            self.fail(f"log_error() propagó una excepción cuando no debía: {e}")


if __name__ == "__main__":
    unittest.main()
