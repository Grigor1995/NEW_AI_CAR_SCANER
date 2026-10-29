
from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus, Vehicle
from diagnostic.session_persistence import DiagnosticSessionPersistence


def test_session_persistence_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostic.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    store = DiagnosticSessionPersistence()
    try:
        session = DiagnosticSession(
            vehicle=Vehicle(
                make="Mercedes-Benz",
                model="W211",
                year=2006,
                engine="M272 3.5",
                fuel=["petrol", "LPG"],
                ecu="ME 9.7",
            )
        )
        session.evidence.append(
            Evidence(
                fact="P0302",
                source=EvidenceSource.USER_REPORTED,
                status=EvidenceStatus.REPORTED,
            )
        )

        sessions = {str(session.session_id): session}
        store.save_all(sessions)

        restored = store.load()
        assert str(session.session_id) in restored
        assert restored[str(session.session_id)].vehicle == session.vehicle
        assert restored[str(session.session_id)].evidence[0].fact == "P0302"
    finally:
        store.close()
