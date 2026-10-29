from backend.observability.metrics import MetricsRegistry
from backend.observability.tracing import span

def test_metrics():
    m=MetricsRegistry(); m.inc("diagnostic.sessions"); m.inc("diagnostic.sessions",2)
    assert m.snapshot()["diagnostic.sessions"] == 3

def test_span():
    with span("DTC_READ", protocol="OBD") as s: pass
    assert s.duration_ms >= 0
