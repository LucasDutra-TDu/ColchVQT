# tests/__init__.py
"""
Paquete de tests de ColchVQT.

Registra el shim de num2words (ver tests/_optional_deps.py) apenas se
importa el paquete `tests`, ANTES de que cualquier módulo de test
individual llegue a importar logic.financiero. Así ningún archivo de
test necesita acordarse de importarlo por su cuenta.
"""
import tests._optional_deps  # noqa: F401
