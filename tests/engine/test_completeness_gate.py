import importlib, pytest, inspect

def test_completeness_gate_minimal():
    m = importlib.import_module("src.engine.completeness_gate")
    Gate = getattr(m, "CompletenessGate", None)
    fn = getattr(m, "is_complete", None) or getattr(m, "evaluate", None) or getattr(m, "validate", None)

    # minimal payload; Kilo can expand with real required fields after reading code
    payload = {"artifacts": [], "meta": {}}

    if Gate:
        gate = Gate()
        check = getattr(gate, "is_complete", None) or getattr(gate, "evaluate", None) or getattr(gate, "validate", None)
        if not check:
            pytest.skip("Gate has no is_complete/evaluate/validate")
        res = check(payload)
    elif callable(fn):
        params = inspect.signature(fn).parameters
        res = fn(payload) if len(params) == 1 else fn(**{"state": payload})
    else:
        pytest.skip("No completeness gate found")

    assert isinstance(res, (bool, dict)), "Gate should return bool or result dict"
