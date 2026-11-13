from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SimulationStartRequest(BaseModel):
    scenario_id: str = Field(..., description="ID of chaos scenario: deploy, db, crash, net, cpu, mem")

class ApprovalRequest(BaseModel):
    reviewer: str = Field(default="Operator (Human)", description="Name or role of approving engineer")
    remarks: Optional[str] = Field(default=None, description="Optional approval comments")

class RejectRequest(BaseModel):
    reviewer: str = Field(default="Operator (Human)", description="Name or role of rejecting engineer")
    reason: str = Field(default="Rejected by operator", description="Reason for rejection and escalation")

class StopRequest(BaseModel):
    actor: str = Field(default="Operator (Human)", description="Actor initiating emergency stop")

class ServiceHealth(BaseModel):
    id: str
    name: str
    display: str
    status: str
    color: str
    badge: str
    is_root: bool

class IncidentSummary(BaseModel):
    id: str
    title: str
    scenario_id: Optional[str] = None
    service: str
    severity: str
    status: str
    phase: str
    detected_at: str
    resolved_at: Optional[str] = None
    impact_summary: Optional[str] = None
    orders_at_risk: int = 0
    checkout_success_pct: float = 100.0
    active_agent: str = "Supervisor"

class EvidenceItem(BaseModel):
    type: str
    source: str
    claim: str
    role: str
    timestamp: str

class AlertItem(BaseModel):
    id: str
    service: str
    name: str
    severity: str
    condition: Optional[str] = None
    fired_at: str
    correlation_reason: Optional[str] = None

class KnowledgeItem(BaseModel):
    id: str
    title: str
    service: str
    symptoms: str
    root_cause: str
    fix: str
    approval_status: str
    recovery_status: str
    created_at: str

class SettingsUpdateRequest(BaseModel):
    webhook_url: Optional[str] = None
    auto_diagnostics: Optional[bool] = True
    require_human_approval: Optional[bool] = True

