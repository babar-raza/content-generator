import importlib
import pytest

@pytest.mark.parametrize("mod", [
    "src.core.config",
    "src.core.event_bus",
    "src.core.ollama",
    "src.engine.aggregator",
    "src.engine.completeness_gate",
])
def test_modules_import(mod):
    importlib.import_module(mod)
