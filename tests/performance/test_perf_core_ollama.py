import importlib, pytest
from ._perf_utils import time_call, record_result

def _load_selector():
    m = importlib.import_module("src.core.ollama")
    for attr in ["OllamaClient", "Router", "Client", "ModelSelector"]:
        if hasattr(m, attr):
            obj = getattr(m, attr)
            try:
                inst = obj()
                for name in ["select", "route", "choose", "get_client"]:
                    if hasattr(inst, name):
                        fn = getattr(inst, name)
                        return lambda: fn("test-task")
            except Exception:
                pass
    for name in ["select_model", "choose_model", "get_client"]:
        if hasattr(m, name):
            fn = getattr(m, name)
            return lambda: fn("test-task")
    pytest.skip("No obvious selection function/class in src.core.ollama")

def test_ollama_selection_speed(monkeypatch):
    selector = _load_selector()
    def _no_network(*a, **k):
        return {"ok": True, "mock": True}
    try:
        import src.core.ollama as ollama
        for name in ["send", "request", "generate", "chat"]:
            if hasattr(ollama, name):
                monkeypatch.setattr(ollama, name, _no_network, raising=False)
    except Exception:
        pass
    timings = time_call(lambda: selector())
    res = record_result("core", "ollama.select", timings)
    assert res["mean"] < 0.02, f"ollama selection mean {res['mean']:.3f}s"
