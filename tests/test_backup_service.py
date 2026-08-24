# tests/test_backup_service.py
"""
Tests de logic/backup_service.py: creación de snapshots consistentes y
rotación/retención (Fase 1 de la auditoría, "red de contención").
"""
import sys
import sqlite3
import shutil
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import logic.backup_service as backup_service
import logic.log_service as log_service


class _BackupTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_backup_")
        self._tmp_path = Path(self._tmp_dir)
        self.data_dir = self._tmp_path / "data"
        self.data_dir.mkdir()
        self.backup_dir = self.data_dir / "backups"

        self._originales = {
            "BASE_DIR": backup_service.BASE_DIR,
            "DATA_DIR": backup_service.DATA_DIR,
            "BACKUP_DIR": backup_service.BACKUP_DIR,
        }
        backup_service.BASE_DIR = self._tmp_path
        backup_service.DATA_DIR = self.data_dir
        backup_service.BACKUP_DIR = self.backup_dir

        # backup_service.log_error()/log_warning() delegan en logic.log_service,
        # que escribe a su PROPIO LOG_PATH global. Sin redirigirlo también,
        # los warnings de "no hay nada que respaldar" terminan en el
        # data/app.log REAL del proyecto en vez de en la carpeta temporal.
        self._original_log_base_dir = log_service.BASE_DIR
        self._original_log_path = log_service.LOG_PATH
        log_service.BASE_DIR = self._tmp_path
        log_service.LOG_PATH = self.data_dir / "app.log"

    def tearDown(self):
        for attr, valor in self._originales.items():
            setattr(backup_service, attr, valor)
        log_service.BASE_DIR = self._original_log_base_dir
        log_service.LOG_PATH = self._original_log_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _crear_sqlite_con_datos(self, nombre: str, filas=(("a",), ("b",))):
        path = self.data_dir / nombre
        con = sqlite3.connect(str(path))
        con.execute("CREATE TABLE t (v TEXT)")
        con.executemany("INSERT INTO t (v) VALUES (?)", filas)
        con.commit()
        con.close()
        return path


class TestHacerBackupDatos(_BackupTestCase):
    def test_primer_arranque_sin_archivos_no_falla(self):
        resultado = backup_service.hacer_backup_datos()
        self.assertTrue(resultado)

    def test_respalda_sqlite_con_datos_intactos(self):
        self._crear_sqlite_con_datos("ventas.db", filas=(("x",), ("y",), ("z",)))
        backup_service.hacer_backup_datos()

        carpetas = list(self.backup_dir.iterdir())
        self.assertEqual(len(carpetas), 1)
        backup_db = carpetas[0] / "ventas.db"
        self.assertTrue(backup_db.exists())

        con = sqlite3.connect(str(backup_db))
        filas = con.execute("SELECT v FROM t ORDER BY v").fetchall()
        con.close()
        self.assertEqual([f[0] for f in filas], ["x", "y", "z"])

    def test_original_no_se_modifica(self):
        origen = self._crear_sqlite_con_datos("ventas.db")
        contenido_antes = origen.read_bytes()
        backup_service.hacer_backup_datos()
        self.assertEqual(origen.read_bytes(), contenido_antes)

    def test_respalda_archivo_plano_json(self):
        (self.data_dir / "proveedores.json").write_text('{"1": {"nombre": "Test"}}', encoding="utf-8")
        backup_service.hacer_backup_datos()
        carpetas = list(self.backup_dir.iterdir())
        backup_json = carpetas[0] / "proveedores.json"
        self.assertTrue(backup_json.exists())
        self.assertIn("Test", backup_json.read_text(encoding="utf-8"))

    def test_archivo_sqlite_vacio_0_bytes_se_ignora(self):
        # Un archivo de 0 bytes no es una base SQLite válida todavía
        # (puede pasar si se creó pero nunca se escribió nada) -- no debe
        # intentar respaldarse ni loggear un error de SQLite.
        (self.data_dir / "ventas.db").touch()
        resultado = backup_service.hacer_backup_datos()
        self.assertTrue(resultado)
        carpetas = list(self.backup_dir.iterdir()) if self.backup_dir.exists() else []
        # No debería haberse creado carpeta de backup porque nada era respaldable
        self.assertEqual(len(carpetas), 0)

    def test_respalda_ambas_bases_y_json_en_la_misma_carpeta(self):
        self._crear_sqlite_con_datos("ventas.db")
        self._crear_sqlite_con_datos("inventario.db")
        (self.data_dir / "proveedores.json").write_text("{}", encoding="utf-8")
        backup_service.hacer_backup_datos()
        carpetas = list(self.backup_dir.iterdir())
        self.assertEqual(len(carpetas), 1)
        contenidos = {p.name for p in carpetas[0].iterdir()}
        self.assertEqual(contenidos, {"ventas.db", "inventario.db", "proveedores.json"})


class TestLimpiarBackupsAntiguos(_BackupTestCase):
    def test_conserva_solo_los_mas_recientes(self):
        self.backup_dir.mkdir(parents=True)
        # Nombres ordenables lexicográficamente igual que timestamps reales
        for i in range(35):
            (self.backup_dir / f"2026010100000{i:02d}_000000").mkdir()

        backup_service._limpiar_backups_antiguos()

        restantes = sorted(d.name for d in self.backup_dir.iterdir())
        self.assertEqual(len(restantes), backup_service.MAX_BACKUPS_A_CONSERVAR)
        # Deben ser los 30 con el nombre "más alto" (más reciente)
        todos_ordenados = sorted(f"2026010100000{i:02d}_000000" for i in range(35))
        esperados = todos_ordenados[-30:]
        self.assertEqual(restantes, esperados)

    def test_no_falla_si_no_existe_la_carpeta_de_backups(self):
        # backup_dir nunca se creó
        backup_service._limpiar_backups_antiguos()  # no debe lanzar excepción

    def test_hacer_backup_datos_dispara_la_limpieza_automaticamente(self):
        backup_service.MAX_BACKUPS_A_CONSERVAR, original_max = 2, backup_service.MAX_BACKUPS_A_CONSERVAR
        try:
            self._crear_sqlite_con_datos("ventas.db")
            import time
            for _ in range(4):
                backup_service.hacer_backup_datos()
                # margen para que el timestamp (con microsegundos) no se repita
                time.sleep(0.001)
            carpetas = list(self.backup_dir.iterdir())
            self.assertLessEqual(len(carpetas), 2)
        finally:
            backup_service.MAX_BACKUPS_A_CONSERVAR = original_max


if __name__ == "__main__":
    unittest.main()
