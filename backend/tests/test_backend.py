import pytest
import os
import sys

# Ensure backend package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.policy_engine import PolicyEngine
from backend.recovery_verifier import RecoveryVerifier
from backend.graph import topology
from backend.scenarios import SCENARIOS
from backend.database import init_db, get_connection
from backend.main import (
    get_health, get_dashboard, get_scenarios, list_incidents,
    get_incident_detail, get_incident_graph, list_knowledge,
    get_settings, run_evaluation_suite
)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()

def test_policy_engine_enforces_human_approval():
    # Preconditions met, but without approval -> cannot execute
    eval_pending = PolicyEngine.evaluate_remediation_proposal(
        action="Roll back payments-svc to v3.8.0",
        target_service="payments-svc",
        is_reversible=True,
        evidence_coverage_pct=83.0,
        has_human_approval=False
    )
    assert eval_pending["all_preconditions_met"] is True
    assert eval_pending["allowed_for_execution"] is False
    assert eval_pending["policy_level"] == "L2"
    assert any(c["name"] == "Human Approval Requirement" and c["passed"] is False for c in eval_pending["checks"])

    # With explicit human approval -> permitted for execution
    eval_approved = PolicyEngine.evaluate_remediation_proposal(
        action="Roll back payments-svc to v3.8.0",
        target_service="payments-svc",
        is_reversible=True,
        evidence_coverage_pct=83.0,
        has_human_approval=True
    )
    assert eval_approved["allowed_for_execution"] is True
    assert any(c["name"] == "Human Approval Requirement" and c["passed"] is True for c in eval_approved["checks"])

def test_policy_engine_blocks_insufficient_evidence():
    # If evidence coverage is under 80%, policy MUST block
    eval_low_cov = PolicyEngine.evaluate_remediation_proposal(
        action="Roll back payments-svc to v3.8.0",
        target_service="payments-svc",
        is_reversible=True,
        evidence_coverage_pct=65.0,
        has_human_approval=True
    )
    assert eval_low_cov["all_preconditions_met"] is False
    assert eval_low_cov["allowed_for_execution"] is False
    assert any(c["name"] == "Evidence Coverage Threshold" and c["passed"] is False for c in eval_low_cov["checks"])

def test_recovery_verifier_requires_all_checks():
    before = {"p95_latency": "2,840 ms", "error_rate": "18.4%", "saturation": "98%"}
    after = {"p95_latency": "212 ms", "error_rate": "0.6%", "saturation": "41%"}
    checks = [
        "Healthy on 3 consecutive probes",
        "Error rate below 1.0%",
        "Latency within 20% of baseline",
        "No new related alerts"
    ]
    res = RecoveryVerifier.verify(before, after, checks)
    assert res["is_verified"] is True
    assert res["checks_passed"] == 4
    assert res["total_checks"] == 4

def test_networkx_causal_path():
    path = topology.find_propagation_path("orders-db", "checkout")
    assert path == ["checkout", "payments", "orders-db"]

    health = topology.calculate_health("payments", is_resolved=False)
    assert health["payments"]["status"] == "Failing"
    assert health["checkout"]["status"] == "Degraded"
    assert health["cache"]["status"] == "Healthy"

def test_health_endpoint():
    data = get_health()
    assert data["status"] == "healthy"
    assert data["environment"] == "SIMULATION"

def test_dashboard_endpoint():
    data = get_dashboard()
    assert "active_incidents" in data
    assert "service_health" in data
    assert "recent_incidents" in data
    assert len(data["service_health"]) == 7

def test_scenarios_endpoint():
    scenarios = get_scenarios()
    assert len(scenarios) == 12
    ids = [s["id"] for s in scenarios]
    assert "deploy" in ids
    assert "db" in ids
    assert "cert" in ids
    assert "queue" in ids

def test_incidents_listing():
    incidents = list_incidents()
    assert len(incidents) >= 3
    first = incidents[0]
    assert "id" in first
    assert "title" in first
    assert "status" in first

def test_incident_graph():
    graph_data = get_incident_graph("INC-2037")
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert len(graph_data["nodes"]) == 7

def test_knowledge_endpoint():
    items = list_knowledge()
    assert len(items) >= 3

def test_settings_endpoint():
    settings = get_settings()
    assert settings["simulation_mode"] is True
    assert settings["enforce_human_approval"] is True

def test_evaluation_suite_endpoint():
    data = run_evaluation_suite()
    assert data["scenarios_tested_count"] == 12
    assert data["metrics"]["human_approval_enforced_pct"] == 100.0
    assert data["metrics"]["recovery_verification_pct"] == 100.0
    assert data["metrics"]["top1_accuracy_pct"] >= 80.0
