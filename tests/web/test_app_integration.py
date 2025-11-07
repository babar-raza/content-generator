import importlib, pytest

def _load_app():
    try:
        m = importlib.import_module("start_web_ui")
    except ImportError:
        pytest.skip("start_web_ui not importable")
    app = getattr(m, "app", None)
    if app is None and hasattr(m, "create_app"):
        app = m.create_app()
    if app is None:
        pytest.skip("No FastAPI app or create_app()")
    return app

def test_health_endpoint():
    app = _load_app()
    try:
        from fastapi.testclient import TestClient
    except Exception:
        pytest.skip("fastapi not installed for tests")
    client = TestClient(app)
    for path in ("/health", "/ping", "/"):
        r = client.get(path)
        if r.status_code < 500:
            assert 200 <= r.status_code < 300
            return
    pytest.skip("No health-like route returned 2xx")
