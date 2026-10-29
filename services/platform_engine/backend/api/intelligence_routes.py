from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from uuid import UUID
from diagnostic.models import EvidenceSource
from ai.reasoning.engine import DiagnosticIntelligenceEngine
from api.state import sessions
from diagnostic.localization import localize_session_analysis

router = APIRouter(prefix="/api/v1/intelligence", tags=["diagnostic-intelligence"])
engine = DiagnosticIntelligenceEngine()

class IngestTextRequest(BaseModel):
    text: str
    source: EvidenceSource = EvidenceSource.USER_REPORTED

class TestResultRequest(BaseModel):
    test_id: UUID
    result: str
    measurements: dict = {}
    notes: str | None = None

@router.post("/sessions/{session_id}/evidence/text")
def ingest_text(session_id: str, request: IngestTextRequest):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return engine.ingest_text(sessions[session_id], request.text, request.source)

@router.post("/sessions/{session_id}/analyze")
def analyze(session_id: str, language: str = Query("en")):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    result = engine.analyze(sessions[session_id])
    return localize_session_analysis(result, language)

@router.post("/sessions/{session_id}/test-results")
def add_test_result(
    session_id: str,
    request: TestResultRequest,
    language: str = Query("en"),
):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    result_status = request.result.strip().upper()
    # Backward compatibility: older Android builds sent UNKNOWN. Normalize it
    # to the single cross-platform status instead of persisting a fourth value.
    if result_status == "UNKNOWN":
        result_status = "INCOMPLETE"
    if result_status not in {"PASS", "FAIL", "INCOMPLETE"}:
        raise HTTPException(422, "Result must be PASS, FAIL, or INCOMPLETE")
    result = engine.record_test_result(
        sessions[session_id],
        request.test_id,
        result_status,
        request.measurements,
        request.notes,
    )
    return localize_session_analysis(result, language)
