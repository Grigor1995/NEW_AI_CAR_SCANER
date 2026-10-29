from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator

class SessionState(str, Enum):
    CREATED="CREATED"; VEHICLE_IDENTIFIED="VEHICLE_IDENTIFIED"; SYMPTOMS_COLLECTED="SYMPTOMS_COLLECTED"; INITIAL_ANALYSIS="INITIAL_ANALYSIS"; QUESTIONS_PENDING="QUESTIONS_PENDING"; DATA_COLLECTION="DATA_COLLECTION"; TESTING="TESTING"; HYPOTHESIS_VALIDATION="HYPOTHESIS_VALIDATION"; ROOT_CAUSE_FOUND="ROOT_CAUSE_FOUND"; REPAIR="REPAIR"; POST_REPAIR_VERIFICATION="POST_REPAIR_VERIFICATION"; CLOSED="CLOSED"
class EvidenceSource(str, Enum):
    USER_REPORTED="USER_REPORTED"; TECHNICIAN_OBSERVED="TECHNICIAN_OBSERVED"; VEHICLE_MEASURED="VEHICLE_MEASURED"; ECU_REPORTED="ECU_REPORTED"; DATABASE="DATABASE"; OEM_DOCUMENT="OEM_DOCUMENT"; RULE="RULE"; ML_MODEL="ML_MODEL"; LLM_INFERENCE="LLM_INFERENCE"; HISTORICAL_CASE="HISTORICAL_CASE"; SIMULATOR="SIMULATOR"
class EvidenceStatus(str, Enum):
    REPORTED="reported"; MEASURED="measured"; CALCULATED="calculated"; INFERRED="inferred"; CONFIRMED="confirmed"; REJECTED="rejected"; SIMULATED="simulated"
class Vehicle(BaseModel):
    make: str; model: str; chassis: str | None = None; year: int | None=None; engine: str | None=None; fuel: list[str]=Field(default_factory=list); ecu: str | None=None; metadata: dict=Field(default_factory=dict)
class Symptom(BaseModel):
    id: UUID=Field(default_factory=uuid4)
    raw_text: str = ""
    normalized: dict=Field(default_factory=dict)
    symptom: str | None = None

    @model_validator(mode="after")
    def normalize_legacy_payload(self):
        if not self.raw_text.strip() and self.symptom:
            self.raw_text = self.symptom.strip()
        if not self.raw_text.strip():
            raise ValueError("Symptom text must not be empty")
        return self

class DTC(BaseModel):
    id: UUID=Field(default_factory=uuid4)
    code: str
    description: str | None=None
    source: EvidenceSource=EvidenceSource.USER_REPORTED
class Evidence(BaseModel):
    id: UUID=Field(default_factory=uuid4); fact: str; source: EvidenceSource; status: EvidenceStatus; confidence: float | None=Field(default=None, ge=0, le=1); source_ref: str | None=None; metadata: dict=Field(default_factory=dict); created_at: datetime=Field(default_factory=lambda: datetime.now(timezone.utc))
class Hypothesis(BaseModel):
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    id: UUID=Field(default_factory=uuid4); category: str; statement: str; supporting_evidence_ids: list[UUID]=Field(default_factory=list); contradicting_evidence_ids: list[UUID]=Field(default_factory=list); status: str="possible"
class DiagnosticTest(BaseModel):
    id: UUID=Field(default_factory=uuid4)
    name: str
    purpose: str
    expected_observation: str | None=None
    safety_notes: list[str]=Field(default_factory=list)
    priority_score: float=Field(default=0.0, ge=0.0, le=1.0)
    expected_information_gain: float=Field(default=0.0, ge=0.0, le=1.0)
    estimated_cost: float=Field(default=0.0, ge=0.0)
    risk_level: str="LOW"
    prerequisites: list[str]=Field(default_factory=list)
    target_hypotheses: list[str]=Field(default_factory=list)
class TestResult(BaseModel):
    target_hypotheses: list[str] = Field(default_factory=list)
    result_label: str | None = None
    __test__ = False
    test_id: UUID; result: str; measurements: dict=Field(default_factory=dict); notes: str | None=None; test_name: str | None=None
class DiagnosticSession(BaseModel):
    session_id: UUID=Field(default_factory=uuid4)
    state: SessionState=SessionState.CREATED
    vehicle: Vehicle | None=None
    symptoms: list[Symptom]=Field(default_factory=list)
    dtcs: list[DTC]=Field(default_factory=list)
    evidence: list[Evidence]=Field(default_factory=list)
    hypotheses: list[Hypothesis]=Field(default_factory=list)
    recommendations: list[DiagnosticTest]=Field(default_factory=list)
    test_results: list[TestResult]=Field(default_factory=list)
    measurements: list[dict]=Field(default_factory=list)
    live_data: list[dict]=Field(default_factory=list)
    connected_device_id: str | None=None
    connection_type: str | None=None
    audit_log: list[dict]=Field(default_factory=list)
