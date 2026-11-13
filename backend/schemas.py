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

