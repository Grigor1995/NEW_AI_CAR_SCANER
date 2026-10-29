from time import perf_counter

from diagnostic.models import DiagnosticSession, DTC, Symptom, Vehicle
from ai.reasoning.engine import DiagnosticIntelligenceEngine


def _case_session() -> DiagnosticSession:
    return DiagnosticSession(
        vehicle=Vehicle(
            make="Mercedes-Benz",
            model="W211 E350",
            year=2006,
            engine="M272 3.5",
            fuel=["petrol", "LPG"],
            ecu="ME 9.7",
        ),
        symptoms=[Symptom(raw_text="Engine shakes on LPG below 2000 RPM under load; petrol is normal.")],
        dtcs=[DTC(code="P0302")],
    )


def test_deterministic_analysis_performance_budget():
    engine = DiagnosticIntelligenceEngine()
    session = _case_session()
    for _ in range(10):
        engine.analyze(session.model_copy(deep=True))

    timings = []
    for _ in range(100):
        started = perf_counter()
        engine.analyze(session.model_copy(deep=True))
        timings.append((perf_counter() - started) * 1000)

    timings.sort()
    p50 = timings[len(timings) // 2]
    p95 = timings[max(0, int(len(timings) * 0.95) - 1)]
    print(f"PERF deterministic_analysis_ms p50={p50:.2f} p95={p95:.2f} min={min(timings):.2f} max={max(timings):.2f}")
    assert p95 < 90.0, f"p50={p50:.2f}ms p95={p95:.2f}ms"
