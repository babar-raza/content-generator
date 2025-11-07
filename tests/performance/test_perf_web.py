import pytest
from ._perf_utils import time_call, record_result

def _load_app():
    import importlib
    for mod in ["start_web_ui", "app", "main"]:
        try:
            m = importlib.import_module(mod)
        except Exception:
            continue
        app = getattr(m, "app", None)
        if app is None and hasattr(m, "create_app"):
            try:
                app = m.create_app()
            except Exception:
                app = None
        if app is not None:
            return app
    pytest.skip("No FastAPI app module found (start_web_ui/app/main)")

def test_fastapi_latency_smoke():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        pytest.skip("fastapi not installed for tests")

    app = _load_app()
    client = TestClient(app)
    candidates = ["/health", "/ping", "/"]
    target = None
    for p in candidates:
        try:
            r = client.get(p)
            if 200 <= r.status_code < 300:
                target = p
                break
        except Exception:
            pass
    if not target:
        pytest.skip("No 2xx health-like endpoint found")

    timings = time_call(lambda: client.get(target))
    res = record_result("web", f"GET {target}", timings)
    assert res["mean"] < 0.25, f"web mean latency too high: {res['mean']:.3f}s"
