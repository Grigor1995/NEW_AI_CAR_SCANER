from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Body, Request
from diagnostic.models import DiagnosticSession, Vehicle, Symptom, DTC, Evidence, EvidenceSource, EvidenceStatus
from diagnostic.localization import localize_session_analysis
from ai.reasoning.engine import DiagnosticIntelligenceEngine
from diagnostic.rules import DiagnosticReasoningEngine
from diagnostic.decision import DiagnosticDecisionEngine
from api.client_features_routes import router as client_features_router
from api.platform_routes import router as platform_router
from api.intelligence_routes import router as intelligence_router
from api.state import sessions, load_persisted_sessions, persist_sessions
from api.obd_routes import router as obd_router
from api.advanced_obd_routes import router as advanced_obd_router
from api.vehicle_reference_routes import router as reference_router
from api.ai_routes import router as ai_router
from api.knowledge_routes import router as knowledge_router
from api.rag_routes import router as rag_router
from api.decision_routes import router as decision_router
from api.telemetry_routes import router as telemetry_router
from api.acquisition_routes import router as acquisition_router
from api.vehicle_diagnostic_routes import router as vehicle_diagnostic_router
from api.multi_ecu_routes import router as multi_ecu_router
from api.multi_bus_routes import router as multi_bus_router
from api.network_discovery_routes import router as network_discovery_router
from api.active_discovery_routes import router as active_discovery_router
from api.device_routes import router as device_router
from api.vehicle_catalog_routes import router as vehicle_catalog_router
from api.vehicle_registry_routes import router as vehicle_registry_router
from api.global_data_routes import router as global_data_router
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Restore persisted sessions before serving requests."""
    if not ecosystem_enabled():
        load_persisted_sessions()
    try:
        yield
    finally:
        from api.state import vci_manager
        from api.acquisition_routes import service as acquisition
        await acquisition.shutdown()
        await vci_manager.shutdown()


app = FastAPI(title="AI Auto Diagnostic Platform", version="0.1.0", lifespan=lifespan)

@app.middleware("http")
async def persist_diagnostic_sessions(request: Request, call_next):
    try:
        return await call_next(request)
    finally:
        if not ecosystem_enabled():
            persist_sessions()
engine=DiagnosticReasoningEngine()
intelligence_engine=DiagnosticIntelligenceEngine()
decision_engine=DiagnosticDecisionEngine()
app.include_router(client_features_router)
app.include_router(obd_router)
app.include_router(advanced_obd_router)
app.include_router(reference_router)
app.include_router(platform_router)
app.include_router(intelligence_router)
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(rag_router)
app.include_router(decision_router)
app.include_router(telemetry_router)
app.include_router(acquisition_router)
app.include_router(vehicle_diagnostic_router)
app.include_router(multi_ecu_router)
app.include_router(multi_bus_router)
app.include_router(network_discovery_router)
app.include_router(active_discovery_router)
app.include_router(device_router)
app.include_router(vehicle_catalog_router)
app.include_router(vehicle_registry_router)
app.include_router(global_data_router)
@app.get('/health')
def health(): return {'status':'ok','service':'diagnostic-api','version':'0.1.0'}
@app.post('/api/v1/sessions',response_model=DiagnosticSession)
def create_session(vehicle:dict | None=Body(default=None)):
    # Accept both the canonical vehicle object and an empty JSON body for
    # legacy clients that create a session before vehicle identification.
    parsed_vehicle = Vehicle(**vehicle) if vehicle else None
    s=DiagnosticSession(vehicle=parsed_vehicle); sessions[str(s.session_id)]=s; return s

@app.get('/api/v1/sessions',response_model=list[DiagnosticSession])
def list_sessions(limit: int = 50):
    limit = max(1, min(limit, 200))
    return sorted(
        sessions.values(),
        key=lambda item: item.session_id.hex,
        reverse=True,
    )[:limit]

@app.get('/api/v1/sessions/{session_id}',response_model=DiagnosticSession)
def read_session(session_id: str, language: str = 'en'):
    return localize_session_analysis(get_session(session_id), language)


def get_session(session_id:str):
    if session_id not in sessions: raise HTTPException(404,'Session not found')
    return sessions[session_id]

@app.put('/api/v1/sessions/{session_id}/vehicle',response_model=DiagnosticSession)
def update_vehicle(session_id:str,vehicle:Vehicle):
    s=get_session(session_id)
    s.vehicle=vehicle
    s.audit_log.append({"event":"VEHICLE_UPDATED"})
    return s
@app.post('/api/v1/sessions/{session_id}/symptoms',response_model=DiagnosticSession)
def add_symptom(session_id:str,symptom:Symptom):
    """Add a user-reported symptom using the canonical raw_text payload."""
    if not symptom.raw_text.strip():
        raise HTTPException(422,'Symptom text must not be empty')
    s=get_session(session_id)
    s.symptoms.append(symptom)
    s.evidence.append(Evidence(fact=symptom.raw_text,source=EvidenceSource.USER_REPORTED,status=EvidenceStatus.REPORTED))
    s.audit_log.append({"event":"SYMPTOM_ADDED","symptom_id":str(symptom.id)})
    return s

@app.put('/api/v1/sessions/{session_id}/symptoms/{symptom_id}',response_model=DiagnosticSession)
def update_symptom(session_id:str,symptom_id:str,symptom:Symptom):
    """Update an existing user-reported symptom without replacing its identity."""
    if not symptom.raw_text.strip():
        raise HTTPException(422,'Symptom text must not be empty')
    s=get_session(session_id)
    target=next((item for item in s.symptoms if str(item.id)==symptom_id),None)
    if target is None:
        raise HTTPException(404,'Symptom not found')
    old_text=target.raw_text
    target.raw_text=symptom.raw_text.strip()
    target.normalized=symptom.normalized
    target.symptom=symptom.symptom
    for evidence in s.evidence:
        if evidence.source == EvidenceSource.USER_REPORTED and evidence.fact == old_text:
            evidence.fact=target.raw_text
            break
    s.audit_log.append({"event":"SYMPTOM_UPDATED","symptom_id":symptom_id})
    return s

@app.delete('/api/v1/sessions/{session_id}/symptoms/{symptom_id}',response_model=DiagnosticSession)
def delete_symptom(session_id:str,symptom_id:str):
    """Delete an existing user-reported symptom and its direct evidence."""
    s=get_session(session_id)
    index=next((i for i,item in enumerate(s.symptoms) if str(item.id)==symptom_id),None)
    if index is None:
        raise HTTPException(404,'Symptom not found')
    removed=s.symptoms.pop(index)
    s.evidence=[e for e in s.evidence if not (e.source == EvidenceSource.USER_REPORTED and e.fact == removed.raw_text)]
    s.audit_log.append({"event":"SYMPTOM_DELETED","symptom_id":symptom_id})
    return s
def _invalidate_analysis(s: DiagnosticSession) -> None:
    s.hypotheses=[]
    s.recommendations=[]

@app.post('/api/v1/sessions/{session_id}/dtcs',response_model=DiagnosticSession)
def add_dtc(session_id:str,dtc:DTC):
    code=dtc.code.strip().upper()
    if not code:
        raise HTTPException(422,'DTC code must not be empty')
    s=get_session(session_id)
    dtc.code=code
    s.dtcs.append(dtc)
    status=EvidenceStatus.MEASURED if dtc.source==EvidenceSource.ECU_REPORTED else EvidenceStatus.REPORTED
    s.evidence.append(Evidence(fact=dtc.code,source=dtc.source,status=status))
    _invalidate_analysis(s)
    s.audit_log.append({"event":"DTC_ADDED","dtc_id":str(dtc.id)})
    return s

@app.put('/api/v1/sessions/{session_id}/dtcs/{dtc_id}',response_model=DiagnosticSession)
def update_dtc(session_id:str,dtc_id:str,dtc:DTC):
    code=dtc.code.strip().upper()
    if not code:
        raise HTTPException(422,'DTC code must not be empty')
    s=get_session(session_id)
    target=next((item for item in s.dtcs if str(item.id)==dtc_id),None)
    if target is None:
        raise HTTPException(404,'DTC not found')
    old_code=target.code
    old_source=target.source
    target.code=code
    target.description=dtc.description
    target.source=dtc.source
    for evidence in s.evidence:
        if evidence.fact == old_code and evidence.source == old_source:
            evidence.fact=target.code
            evidence.source=target.source
            evidence.status=EvidenceStatus.MEASURED if target.source==EvidenceSource.ECU_REPORTED else EvidenceStatus.REPORTED
            break
    _invalidate_analysis(s)
    s.audit_log.append({"event":"DTC_UPDATED","dtc_id":dtc_id})
    return s

@app.delete('/api/v1/sessions/{session_id}/dtcs/{dtc_id}',response_model=DiagnosticSession)
def delete_dtc(session_id:str,dtc_id:str):
    s=get_session(session_id)
    index=next((i for i,item in enumerate(s.dtcs) if str(item.id)==dtc_id),None)
    if index is None:
        raise HTTPException(404,'DTC not found')
    removed=s.dtcs.pop(index)
    for i in range(len(s.evidence)-1,-1,-1):
        evidence=s.evidence[i]
        if evidence.fact == removed.code and evidence.source == removed.source:
            s.evidence.pop(i)
            break
    _invalidate_analysis(s)
    s.audit_log.append({"event":"DTC_DELETED","dtc_id":dtc_id})
    return s

def _analyze_session(session_id: str, language: str = 'en') -> DiagnosticSession:
    s = get_session(session_id)
    engine.analyze(s)
    # Add evidence-linked confidence and missing-question context used by the
    # detailed mobile Analysis screen without changing the deterministic rules.
    intelligence_engine._annotate_scores(s)
    intelligence_engine._apply_test_history(s)
    intelligence_engine._add_missing_questions(s)
    # Rules generate fresh UUIDs on every analysis. Match completed tests by
    # canonical name as well, using only their latest recorded outcome so an
    # INCOMPLETE correction can reopen the test.
    latest_results = {
        DiagnosticDecisionEngine._recommendation_key(item.test_name): item.result
        for item in s.test_results if item.test_name
    }
    completed_names = {name for name, outcome in latest_results.items() if outcome in {"PASS", "FAIL"}}
    rule_recommendations = [
        item for item in s.recommendations
        if DiagnosticDecisionEngine._recommendation_key(item.name) not in completed_names
    ]
    decision_engine.refresh_recommendations(s)

    # Keep rule-driven tests that are not represented in the decision catalog,
    # while enriching their decision fields so the UI never shows meaningless
    # zero information-gain / zero-cost values.
    decision_recommendations = list(s.recommendations)
    decision_names = {item.name.strip().lower() for item in decision_recommendations}
    categories = {item.category for item in s.hypotheses if not item.status.startswith("rejected")}
    category_count = max(len(categories), 1)

    def enrich_rule_test(item):
        target_matches = len(set(item.target_hypotheses) & categories)
        coverage = target_matches / category_count if category_count else 0.0
        if target_matches == 0:
            information_gain = 0.15
        elif 0.0 < coverage < 1.0:
            entropy = -(coverage * __import__("math").log2(coverage) + (1.0 - coverage) * __import__("math").log2(1.0 - coverage))
            information_gain = max(0.25, entropy)
        else:
            information_gain = 0.25

        item.expected_information_gain = round(min(information_gain, 0.95), 4)
        if item.estimated_cost <= 0:
            cost_by_risk = {"LOW": 1.0, "MEDIUM": 2.0, "HIGH": 4.0}
            item.estimated_cost = cost_by_risk.get(item.risk_level.upper(), 1.0)
        if item.priority_score <= 0:
            item.priority_score = round(min(
                0.65 * item.expected_information_gain
                + 0.35 * (1.0 if item.risk_level.upper() == "LOW" else 0.75 if item.risk_level.upper() == "MEDIUM" else 0.5),
                1.0,
            ), 4)
        return item

    s.recommendations = decision_recommendations
    for item in rule_recommendations:
        if item.name.strip().lower() not in decision_names:
            s.recommendations.append(enrich_rule_test(item))

    if not s.recommendations and rule_recommendations:
        s.recommendations = [enrich_rule_test(item) for item in rule_recommendations]

    return localize_session_analysis(s, language)

@app.post('/api/v1/sessions/{session_id}/analyze',response_model=DiagnosticSession)
def analyze(session_id:str, language: str = 'en'):
    return _analyze_session(session_id, language)

@app.post('/api/v1/analysis/{session_id}',response_model=DiagnosticSession)
def analyze_compat(session_id:str, language: str = 'en'):
    return _analyze_session(session_id, language)


# Register last so the opt-in ownership boundary wraps legacy middleware/routes.
from ecosystem.api import install as install_ecosystem, enabled as ecosystem_enabled  # noqa: E402
install_ecosystem(app)
