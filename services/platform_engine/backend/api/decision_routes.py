from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from diagnostic.decision import DiagnosticDecisionEngine, DiagnosticDecisionPlan
from api.state import sessions
from diagnostic.localization import localize_decision_plan

router = APIRouter(prefix="/api/v1/decision", tags=["diagnostic-decision"])
engine = DiagnosticDecisionEngine()

class ConfirmTestRequest(BaseModel):
    test_id: str
    safety_confirmed: bool = False

@router.get("/sessions/{session_id}/plan", response_model=DiagnosticDecisionPlan)
def decision_plan(session_id: str, language: str = "en"):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return localize_decision_plan(engine.build_plan(sessions[session_id]), language)

@router.post("/sessions/{session_id}/refresh", response_model=DiagnosticDecisionPlan)
def refresh_decision_plan(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return engine.refresh_recommendations(sessions[session_id])

@router.post("/sessions/{session_id}/select")
def select_test(session_id: str, request: ConfirmTestRequest):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = sessions[session_id]
    plan = engine.build_plan(session)
    candidate = next((c for c in plan.candidates if str(c.test_id) == request.test_id), None)
    if candidate is None:
        raise HTTPException(404, "Test candidate not found")
    test = next((x for x in session.recommendations if x.name == candidate.name), None)
    safety_level = getattr(test, "risk_level", "LOW") if test else "LOW"
    if safety_level in {"HIGH", "MEDIUM"} and not request.safety_confirmed:
        raise HTTPException(409, "Safety confirmation required before selecting this test")
    session.audit_log.append({"event": "TEST_SELECTED", "test_id": request.test_id, "name": candidate.name, "risk_level": safety_level})
    return {"selected_test_id": request.test_id, "name": candidate.name, "risk_level": safety_level, "safety_notes": candidate.safety_notes}
