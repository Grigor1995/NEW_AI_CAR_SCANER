
def build_session_report(session: dict, audit_events: list[dict] | None = None) -> dict:
    return {
        "session": session,
        "audit": audit_events or [],
        "generated_by": "ai-auto-diagnostic-platform",
        "report_version": "1.0",
    }
