import os, random, pytest

def pytest_configure(config):
    os.environ.setdefault("PYTHONHASHSEED", "42")
    random.seed(42)
    os.environ.setdefault("NO_NETWORK", "1")
    os.environ.setdefault("PERF_RESULTS_PATH", "reports/perf_results.json")
    os.environ.setdefault("PERF_ITERS", "10")
    os.environ.setdefault("PERF_WARMUP", "3")

@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _block(*a, **k):
        raise RuntimeError("Network disabled in perf tests")
    try:
        import socket
        monkeypatch.setattr(socket, "create_connection", _block, raising=False)
    except Exception:
        pass
