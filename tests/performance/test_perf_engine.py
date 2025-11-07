import importlib, pytest, random
from ._perf_utils import time_call, record_result

def _load_merge():
    m = importlib.import_module("src.engine.aggregator")
    Agg = getattr(m, "Aggregator", None)
    if Agg:
        inst = Agg()
        fn = getattr(inst, "merge", None) or getattr(inst, "aggregate", None)
        if fn:
            return lambda payload: fn(payload)
    fn = getattr(m, "aggregate", None) or getattr(m, "merge", None)
    if fn:
        return lambda payload: fn(payload)
    pytest.skip("No aggregator found")

def _load_gate():
    m = importlib.import_module("src.engine.completeness_gate")
    Gate = getattr(m, "CompletenessGate", None)
    if Gate:
        inst = Gate()
        fn = getattr(inst, "is_complete", None) or getattr(inst, "evaluate", None) or getattr(inst, "validate", None)
        if fn:
            return lambda payload: fn(payload)
    for name in ["is_complete", "evaluate", "validate"]:
        fn = getattr(m, name, None)
        if callable(fn):
            return lambda payload: fn(payload)
    pytest.skip("No completeness gate found")

def _sample_docs(n=30):
    rnd = random.Random(42)
    items = []
    for i in range(n):
        items.append({
            "title": f"Doc {i}",
            "summary": "lorem ipsum",
            "tags": ["a","b","c"][0: rnd.randint(1,3)],
            "score": rnd.random(),
        })
    return items

def test_aggregator_throughput():
    merge = _load_merge()
    payload = [{"title": "A", "tags": ["x"]},
               {"summary": "S", "tags": ["y"]},
               {"body": "..."}]
    timings = time_call(lambda: merge(payload))
    res = record_result("engine", "aggregator.merge", timings)
    assert res["mean"] < 0.05, f"aggregator mean {res['mean']:.3f}s"

def test_completeness_gate_speed():
    gate = _load_gate()
    payload = {"artifacts": _sample_docs(30), "meta": {"required": ["title","summary"]}}
    timings = time_call(lambda: gate(payload))
    res = record_result("engine", "completeness_gate", timings)
    assert res["mean"] < 0.05, f"gate mean {res['mean']:.3f}s"
