# tests/test_data_loader.py
"""
Tests de logic/data_loader.py: descarga del catálogo con validación y
reemplazo atómico (hallazgo #2 de la auditoría: antes se pisaba la única
copia local ANTES de validar que lo descargado fuera un Excel real).

Cubre las 4 combinaciones relevantes de (descarga OK/falla) x (había copia
local previa o no).
"""
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import requests

import logic.data_loader as data_loader


def _excel_bytes_valido() -> bytes:
    buf = io.BytesIO()
    pd.DataFrame({"A": [1, 2], "B": [3, 4]}).to_excel(buf, index=False)
    return buf.getvalue()


class _RespuestaFalsa:
    def __init__(self, content: bytes, status_ok: bool = True):
        self.content = content
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.exceptions.HTTPError("500 Server Error")


class TestDescargarArchivo(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_dataloader_")
        self._original_get_base_dir = data_loader.get_base_dir
        data_loader.get_base_dir = lambda: self._tmp_dir

    def tearDown(self):
        data_loader.get_base_dir = self._original_get_base_dir
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _local_path(self):
        return Path(data_loader.get_local_file_path())

    def test_descarga_exitosa_sin_copia_previa(self):
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(_excel_bytes_valido())):
            path, uso_local = data_loader.descargar_archivo()
        self.assertIsNotNone(path)
        self.assertFalse(uso_local)
        self.assertTrue(self._local_path().exists())
        # No debe quedar el archivo temporal
        self.assertFalse((self._local_path().with_suffix(self._local_path().suffix + ".tmp")).exists())

    def test_descarga_exitosa_reemplaza_copia_previa(self):
        # Dejamos una copia local "vieja"
        self._local_path().write_bytes(b"contenido viejo")
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(_excel_bytes_valido())):
            path, uso_local = data_loader.descargar_archivo()
        self.assertFalse(uso_local)
        contenido_nuevo = self._local_path().read_bytes()
        self.assertNotEqual(contenido_nuevo, b"contenido viejo")

    def test_descarga_falla_por_excepcion_de_red_usa_copia_local(self):
        self._local_path().write_bytes(_excel_bytes_valido())
        contenido_original = self._local_path().read_bytes()
        with patch("logic.data_loader.requests.get", side_effect=requests.exceptions.ConnectionError("sin red")):
            path, uso_local = data_loader.descargar_archivo()
        self.assertTrue(uso_local)
        self.assertIsNotNone(path)
        # La copia local NO debe haberse tocado
        self.assertEqual(self._local_path().read_bytes(), contenido_original)

    def test_descarga_falla_por_excepcion_de_red_sin_copia_local_devuelve_none(self):
        with patch("logic.data_loader.requests.get", side_effect=requests.exceptions.ConnectionError("sin red")):
            path, uso_local = data_loader.descargar_archivo()
        self.assertIsNone(path)
        self.assertFalse(uso_local)

    def test_contenido_invalido_NO_pisa_la_copia_local_existente(self):
        """
        EL CASO CRÍTICO: Google (u otro intermediario) devuelve HTTP 200
        pero con contenido basura (ej: una página HTML de error, o una
        descarga cortada). Antes del fix, esto pisaba directamente la
        única copia local persistente con basura. Ahora debe detectarse
        con _es_excel_valido() y conservarse la copia local intacta.
        """
        self._local_path().write_bytes(_excel_bytes_valido())
        contenido_original = self._local_path().read_bytes()
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(b"<html>Error 404</html>")):
            path, uso_local = data_loader.descargar_archivo()
        self.assertTrue(uso_local)
        self.assertEqual(self._local_path().read_bytes(), contenido_original)
        # El archivo temporal de la descarga fallida no debe quedar tirado
        tmp_path = Path(str(self._local_path()) + ".tmp")
        self.assertFalse(tmp_path.exists())

    def test_contenido_invalido_sin_copia_local_devuelve_none(self):
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(b"basura no excel")):
            path, uso_local = data_loader.descargar_archivo()
        self.assertIsNone(path)
        self.assertFalse(self._local_path().exists())

    def test_http_error_usa_copia_local(self):
        self._local_path().write_bytes(_excel_bytes_valido())
        contenido_original = self._local_path().read_bytes()
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(b"no importa", status_ok=False)):
            path, uso_local = data_loader.descargar_archivo()
        self.assertTrue(uso_local)
        self.assertEqual(self._local_path().read_bytes(), contenido_original)


class TestReemplazarConReintentos(unittest.TestCase):
    """
    Hallazgo 24/08/2026: os.replace() del .tmp descargado sobre el .xlsx
    persistente falló en producción con "[WinError 32] El proceso no tiene
    acceso al archivo porque está siendo utilizado por otro proceso"
    (típico de una carpeta sincronizada por OneDrive bloqueando el archivo
    un instante). _reemplazar_con_reintentos reintenta unas pocas veces
    antes de rendirse.
    """

    def setUp(self):
        self._sleep_patcher = patch("logic.data_loader.time.sleep", return_value=None)
        self._sleep_patcher.start()

    def tearDown(self):
        self._sleep_patcher.stop()

    def test_exito_al_primer_intento_no_reintenta(self):
        with patch("logic.data_loader.os.replace") as mock_replace:
            data_loader._reemplazar_con_reintentos("origen", "destino")
        mock_replace.assert_called_once_with("origen", "destino")

    def test_bloqueo_transitorio_se_recupera_con_reintentos(self):
        efectos = [PermissionError("[WinError 32] archivo en uso")] * 2 + [None]
        with patch("logic.data_loader.os.replace", side_effect=efectos) as mock_replace:
            data_loader._reemplazar_con_reintentos("origen", "destino")
        self.assertEqual(mock_replace.call_count, 3)

    def test_bloqueo_persistente_agota_reintentos_y_relanza(self):
        error = PermissionError("[WinError 32] archivo en uso")
        with patch("logic.data_loader.os.replace", side_effect=error) as mock_replace:
            with self.assertRaises(PermissionError):
                data_loader._reemplazar_con_reintentos("origen", "destino")
        self.assertEqual(mock_replace.call_count, data_loader.REEMPLAZO_MAX_INTENTOS)


class TestDescargarArchivoConBloqueoTransitorio(unittest.TestCase):
    """
    Integración: el bloqueo transitorio del archivo destino no debería
    forzar innecesariamente el camino de "usando archivo local" si el
    bloqueo se libera dentro de los reintentos.
    """

    def setUp(self):
        import tempfile
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_dataloader_lock_")
        self._original_get_base_dir = data_loader.get_base_dir
        data_loader.get_base_dir = lambda: self._tmp_dir
        self._sleep_patcher = patch("logic.data_loader.time.sleep", return_value=None)
        self._sleep_patcher.start()

    def tearDown(self):
        data_loader.get_base_dir = self._original_get_base_dir
        self._sleep_patcher.stop()
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_bloqueo_transitorio_no_forza_fallback_a_local(self):
        local_path = Path(data_loader.get_local_file_path())
        local_path.write_bytes(_excel_bytes_valido())

        efectos = [PermissionError("[WinError 32] archivo en uso")] * 2 + [None]
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(_excel_bytes_valido())), \
             patch("logic.data_loader.os.replace", side_effect=efectos):
            path, uso_local = data_loader.descargar_archivo()

        self.assertFalse(uso_local)
        self.assertIsNotNone(path)

    def test_bloqueo_persistente_cae_a_local_como_antes(self):
        local_path = Path(data_loader.get_local_file_path())
        local_path.write_bytes(_excel_bytes_valido())
        contenido_original = local_path.read_bytes()

        error = PermissionError("[WinError 32] archivo en uso")
        with patch("logic.data_loader.requests.get", return_value=_RespuestaFalsa(_excel_bytes_valido())), \
             patch("logic.data_loader.os.replace", side_effect=error):
            path, uso_local = data_loader.descargar_archivo()

        self.assertTrue(uso_local)
        self.assertEqual(local_path.read_bytes(), contenido_original)


class TestEsExcelValido(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_excelcheck_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_excel_real_es_valido(self):
        path = Path(self._tmp_dir) / "test.xlsx"
        path.write_bytes(_excel_bytes_valido())
        self.assertTrue(data_loader._es_excel_valido(str(path)))

    def test_archivo_no_excel_es_invalido(self):
        path = Path(self._tmp_dir) / "test.xlsx"
        path.write_bytes(b"esto no es un excel")
        self.assertFalse(data_loader._es_excel_valido(str(path)))

    def test_archivo_inexistente_es_invalido(self):
        self.assertFalse(data_loader._es_excel_valido(str(Path(self._tmp_dir) / "no_existe.xlsx")))


if __name__ == "__main__":
    unittest.main()
