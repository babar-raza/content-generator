import importlib, pytest

def _get(bus, names):
    for n in names:
        if hasattr(bus, n):
            return getattr(bus, n)
    return None

def test_event_bus_basic():
    m = importlib.import_module("src.core.event_bus")
    Bus = getattr(m, "EventBus", None) or getattr(m, "MessageBus", None)
    if not Bus:
        pytest.skip("No EventBus-like class found")
    bus = Bus()

    calls = []
    subscribe = _get(bus, ["subscribe", "on", "add_listener"])
    publish  = _get(bus, ["publish", "emit", "send", "post"])
    unsubscribe = _get(bus, ["unsubscribe", "off", "remove_listener"])

    if not (subscribe and publish):
        pytest.skip("subscribe/publish not found on bus")

    def handler(data=None, **_):
        calls.append(data if data is not None else True)

    topic = "unit.test"
    subscribe(topic, handler)
    publish(topic, {"ok": True})

    assert calls, "Handler was not called after publish()"

    if unsubscribe:
        unsubscribe(topic, handler)
        calls.clear()
        publish(topic, {"ok": False})
        assert not calls, "Handler called after unsubscribe()"
