import importlib, pytest, inspect

def test_aggregator_merges_dicts():
    m = importlib.import_module("src.engine.aggregator")
    # Prefer class Aggregator; else function aggregate/merge
    Aggregator = getattr(m, "Aggregator", None)
    fn = getattr(m, "aggregate", None) or getattr(m, "merge", None)

    sample = [
        {"title": "A", "tags": ["x"]},
        {"summary": "S", "tags": ["y"]},
    ]

    if Aggregator:
        agg = Aggregator()
        merge = getattr(agg, "merge", None) or getattr(agg, "aggregate", None)
        if not merge:
            pytest.skip("Aggregator has no merge/aggregate method")
        out = merge(sample)
    elif callable(fn):
        # accept either *args or single list param
        if len(inspect.signature(fn).parameters) == 1:
            out = fn(sample)
        else:
            out = fn(*sample)
    else:
        pytest.skip("No Aggregator/aggregate found")

    assert isinstance(out, dict), "Merged output should be a dict"
    assert out.get("title") == "A"
    assert out.get("summary") == "S"
    assert set(out.get("tags", [])) >= {"x", "y"}
