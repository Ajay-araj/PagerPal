"""
backend/agents/schemas.py
Pydantic schemas for structured agent outputs.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SupervisorPlan(BaseModel):
    workflow_steps: List[str] = Field(default_factory=lambda: [
        "Triage", "Investigator", "Causal RCA", "Evidence Verifier", "Remediation", "Comms"
    ])
    rationale: str = Field(..., description="High-level orchestration strategy")


class TriageAssessment(BaseModel):
    severity: str = Field(..., description="Calculated severity (Critical, High, Medium, Low)")
    nominal_orders_per_min: int = Field(default=100, description="Nominal transaction baseline")
    orders_at_risk: int = Field(..., description="Estimated simulated orders at risk per minute")
    checkout_success_pct: float = Field(..., description="Observed or projected checkout success rate")
    blast_radius: List[str] = Field(default_factory=list, description="Services in direct blast radius")
    summary: str = Field(..., description="Brief triage summary")


class ClaimItem(BaseModel):
    claim_text: str = Field(..., description="Specific empirical claim made by investigator")
    source_type: str = Field(..., description="Telemetry source (log, metric, trace, deploy)")
    service: str = Field(..., description="Service ID associated with the claim")
    expected_direction: Optional[str] = Field(default=None, description="Expected metric trend or log pattern")


class InvestigatorFindings(BaseModel):
    suspected_service: str = Field(..., description="Service identified as leading investigation candidate")
    claims: List[ClaimItem] = Field(default_factory=list, description="Empirical claims to be verified")
    evidence_sources_queried: List[str] = Field(default_factory=list)
    telemetry_summary: str = Field(..., description="Summary of observability telemetry")


class RemediationProposalOutput(BaseModel):
    action: str = Field(..., description="Specific remediation action from allowlist")
    target_service: str = Field(..., description="Service to execute the remediation on")
    risk_level: str = Field(default="Low", description="Risk level (Low, Medium, High)")
    is_reversible: bool = Field(default=True, description="Whether action can be rolled back safely")
    timeout_seconds: int = Field(default=120, description="Execution timeout in seconds")
    rollback_plan: str = Field(..., description="Deterministic automated rollback command/step")
    expected_effect: str = Field(..., description="Expected system improvement upon execution")
    policy_level: str = Field(default="L2", description="Policy level (L1, L2, L3)")


class CommsUpdate(BaseModel):
    headline: str = Field(..., description="Incident status title (no emojis)")
    affected_service: str = Field(..., description="Primary affected service")
    severity: str = Field(..., description="Incident severity level")
    current_status: str = Field(..., description="Current status of incident")
    summary: str = Field(..., description="Calm, evidence-backed narrative without emojis")
    next_action: str = Field(..., description="Next operational step or monitoring guidance")

