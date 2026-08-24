# tests/base.py
"""
Base común para todos los tests de ColchVQT.

REGLA DE ORO: ningún test debe tocar la carpeta data/ real del proyecto
(ventas, stock, proveedores reales del negocio). IsolatedDataTestCase
redirige TODAS las rutas de persistencia (ventas.db, inventario.db,
proveedores.json, data/backups/, data/app.log, catálogo descargado) a una
carpeta temporal única por test, y la borra al terminar — sin importar
desde qué directorio se invoque `python -m unittest`.

Cómo correr toda la suite:
    cd ColchVQT
    python -m unittest discover -s tests -v

Cómo correr un solo archivo:
    python -m unittest tests.test_financiero -v

No requiere instalar nada: usa solo la librería estándar. Si en algún
momento se instala pytest, estas mismas clases basadas en unittest.TestCase
son compatibles y pytest las puede correr igual.
"""
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import logic.facturas_db_handler as facturas_db_handler
import logic.credits_service as credits_service
import logic.stock_db_handler as stock_db_handler
import logic.proveedores_service as proveedores_service
import logic.backup_service as backup_service
import logic.log_service as log_service
import logic.data_loader as data_loader


class IsolatedDataTestCase(unittest.TestCase):
    """
    TestCase base que aísla cada test en su propia carpeta temporal.

    Qué hace en setUp():
    1. Crea un directorio temporal descartable (tmp_path) con una
       subcarpeta data/ (data_dir).
    2. Redirige BASE_DIR/DB_PATH/DATA_DIR/BACKUP_DIR/LOG_PATH de cada
       módulo de logic/ hacia esa carpeta temporal (guardando los valores
       originales para restaurarlos después).
    3. Reconstruye el esquema de las bases SQLite en la ubicación temporal
       (init_db()/init_credits_db() son idempotentes: CREATE TABLE IF NOT
       EXISTS, así que esto nunca borra ni pisa nada real).

    Qué hace en tearDown():
    - Restaura todos los valores originales de los módulos.
    - Borra la carpeta temporal por completo.

    Subclases: usar self.data_dir para inspeccionar archivos generados
    (ej: self.data_dir / "ventas.db"), y self.tmp_path como raíz general.
    """

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="colchvqt_test_")
        self.tmp_path = Path(self._tmp_dir)
        self.data_dir = self.tmp_path / "data"
        self.data_dir.mkdir()

        ventas_db = self.data_dir / "ventas.db"
        inventario_db = self.data_dir / "inventario.db"

        parches = [
            (facturas_db_handler, "BASE_DIR", self.tmp_path),
            (facturas_db_handler, "DB_PATH", ventas_db),
            (credits_service, "BASE_DIR", self.tmp_path),
            (credits_service, "DB_PATH", ventas_db),
            (stock_db_handler, "BASE_DIR", self.tmp_path),
            (stock_db_handler, "DB_PATH", inventario_db),
            (proveedores_service, "BASE_DIR", self.tmp_path),
            (backup_service, "BASE_DIR", self.tmp_path),
            (backup_service, "DATA_DIR", self.data_dir),
            (backup_service, "BACKUP_DIR", self.data_dir / "backups"),
            (log_service, "BASE_DIR", self.tmp_path),
            (log_service, "LOG_PATH", self.data_dir / "app.log"),
        ]

        self._originales = []
        for modulo, attr, valor_nuevo in parches:
            self._originales.append((modulo, attr, getattr(modulo, attr)))
            setattr(modulo, attr, valor_nuevo)

        # data_loader no usa constantes de módulo sino una función
        # get_base_dir(); la reemplazamos igual.
        self._data_loader_get_base_dir_original = data_loader.get_base_dir
        data_loader.get_base_dir = lambda: str(self.tmp_path)

        facturas_db_handler.init_db()
        credits_service.init_credits_db()
        stock_db_handler.init_db()

    def tearDown(self):
        for modulo, attr, valor_original in self._originales:
            setattr(modulo, attr, valor_original)
        data_loader.get_base_dir = self._data_loader_get_base_dir_original
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    # --- Helpers comunes para construir datos de prueba ---

    def item_carrito(self, codigo="COD1", modelo="Producto Test", cantidad=1,
                      precio_venta_final=100000, precio_lista_base=None, costo=50000,
                      medida=""):
        """Construye un ítem de carrito con la forma que espera registrar_venta()."""
        if precio_lista_base is None:
            precio_lista_base = precio_venta_final
        return {
            "CÓDIGO": codigo,
            "MODELO": modelo,
            "CARACTERISTICAS": "",
            "cantidad": cantidad,
            "precio_venta_final": precio_venta_final,
            "precio_lista_base": precio_lista_base,
            "COSTO": costo,
            "MEDIDA (LARG-ANCH-ESP)": medida,
        }
