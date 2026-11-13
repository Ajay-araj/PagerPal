from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class LogRecord(BaseModel):
    timestamp: str
    service: str
    level: str  # INFO, WARN, ERROR, FATAL
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MetricPoint(BaseModel):
    timestamp: str
    service: str
    metric_name: str
    value: float
    unit: str

class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service: str
    operation: str
    start_time: str
    duration_ms: float
    status_code: int
    error: bool = False
    error_message: Optional[str] = None

class DeploymentRecord(BaseModel):
    deploy_id: str
    service: str
    version: str
    deployed_at: str
    commit_sha: str
    commit_message: str
    author: str
    diff_summary: str

class SimulatedAlert(BaseModel):
    alert_id: str
    service: str
    name: str
    severity: str  # Critical, High, Medium, Low
    condition: str
    fired_at: str
    value_observed: float
    threshold: float

class GroundTruth(BaseModel):
    scenario_id: str
    fault_type: str
    target_service: str
    root_cause_explanation: str
    recommended_action: str
    injected_at: str
    propagation_chain: List[str]

class SimulationRun(BaseModel):
    run_id: str
    seed: int
    scenario_id: str
    target_service: str
    logs: List[LogRecord] = Field(default_factory=list)
    metrics: Dict[str, List[MetricPoint]] = Field(default_factory=dict)
    traces: List[TraceSpan] = Field(default_factory=list)
    deployments: List[DeploymentRecord] = Field(default_factory=list)
    alerts: List[SimulatedAlert] = Field(default_factory=list)
    ground_truth: GroundTruth

# Stage B Schemas: Correlation & RCA
class CorrelationResult(BaseModel):
    incident_id: str
    incident_title: str
    severity: str
    primary_service: str
    alerts: List[SimulatedAlert]
    total_alerts_received: int
    dedup_count: int
    services_involved: List[str]
    timespan_seconds: float
    correlation_reason: str

class RCACandidate(BaseModel):
    service_id: str
    service_name: str
    rank: int
    score: float
    confidence_pct: float
    likely_cause: str
    propagation_path: List[str]
    evidence_signals: List[str]

class CounterfactualResult(BaseModel):
    candidate_service: str
    hypothesized_action: str
    supports_hypothesis: bool
    is_proof: bool = False  # Strictly False: simulation is supporting evidence, not mathematical proof
    metric_deltas: Dict[str, Dict[str, Any]]
    explanation: str

class RCAResult(BaseModel):
    top_candidates: List[RCACandidate]
    primary_root_cause: RCACandidate
    propagation_path: List[str]
    counterfactual: CounterfactualResult
    computed_at: str

# Stage C Schemas: Evidence, Confidence, Policy & Security
class ClaimItem(BaseModel):
    type: str  # Deploy, Metric, Log, Trace, Commit, Assertion
    source: str
    claim: str

class ClaimVerification(BaseModel):
    claim: ClaimItem
    status: str  # VERIFIED, CONFLICTS, UNVERIFIED
    role: str  # Supports, Conflicts, Dropped
    evidence_reference: Optional[str] = None
    reason: str

class VerificationReport(BaseModel):
    total_claims: int
    verified_count: int
    conflicting_count: int
    dropped_count: int
    claims: List[ClaimVerification]
    dropped_claims: List[ClaimVerification]
    evidence_coverage_pct: float

    @property
    def verified_claims(self) -> "List[ClaimVerification]":
        """Alias for claims (the verified subset)."""
        return self.claims

class ConfidenceReport(BaseModel):
    diagnostic_confidence_pct: float
    evidence_coverage_pct: float
    data_quality_pct: float
    conflict_penalty_pct: float
    supporting_evidence_count: int
    conflicting_evidence_count: int
    blocks_l2: bool
    rule_breakdown: List[str]

class PolicyCheckItem(BaseModel):
    name: str
    description: str
    passed: bool
    status: str  # PASS, FAIL, PENDING_APPROVAL

class PolicyDecision(BaseModel):
    policy_level: str  # L1, L2, DENIED
    action: str
    target_service: str
    all_preconditions_met: bool
    allowed_for_execution: bool
    status_text: str
    checks: List[PolicyCheckItem]
    summary: str
    denial_reasons: List[str] = []

class SanitizedText(BaseModel):
    original_text: str
    sanitized_text: str
    injection_detected: bool
    quarantined_tokens: List[str]
    flag_reason: Optional[str] = None
