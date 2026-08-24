# tests/_optional_deps.py
"""
Shim para dependencias externas opcionales, SOLO para el entorno de tests.

`num2words` es una dependencia real de logic/financiero.py y está
instalada en el entorno de producción (la app ya corre con ella). En
algunos entornos de testing/CI sin acceso a internet puede no estar
disponible para instalar. Para no bloquear la suite completa por eso,
si no está instalada se registra acá un stub mínimo en sys.modules
ANTES de que logic.financiero la importe.

Este shim NUNCA se ejecuta en producción: si num2words está instalado
(como debe estar), el import real tiene éxito y este módulo no hace
nada. Los tests que dependen del contenido textual exacto de
numero_a_letras deben ser agnósticos al shim (solo validan forma, no
la traducción en español real) — ver tests/test_financiero.py.

Importar este módulo (una sola vez, al principio de cualquier test que
toque logic.financiero) ANTES de importar logic.financiero.
"""
import sys
import types

try:
    import num2words  # noqa: F401
    NUM2WORDS_DISPONIBLE = True
except ImportError:
    NUM2WORDS_DISPONIBLE = False
    _stub = types.ModuleType("num2words")

    def _num2words_stub(numero, lang="es"):
        return f"NUM2WORDS-STUB-{numero}"

    _stub.num2words = _num2words_stub
    sys.modules["num2words"] = _stub
