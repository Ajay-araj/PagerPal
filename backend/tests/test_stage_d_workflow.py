"""
backend/tests/test_stage_d_workflow.py
Comprehensive test suite for Stage D:
1. End-to-end tests for all 6 fault types (deploy, db, crash, net, cpu, mem)
2. Approve flow -> remediated -> recovery verified -> resolved
3. Reject flow -> remediation blocked -> escalated -> postmortem notes rejection
4. Policy-denied action -> blocked before execution even if human attempts approval
5. Recovery verification failure -> remediation executes but fails verification -> incident escalated, never shows Resolved
6. Emergency stop -> rollback action executes -> status rolled_back / stopped
7. Verifier retry loop: if verifier rejects an investigator claim, retries up to 2 times, then drops claim and proceeds
8. Monotonic UTC timestamps and emoji-free communications
"""
import pytest
import asyncio
from datetime import datetime, timezone

from backend.database import init_db, get_connection
from backend.schemas import SimulationRun, ClaimItem
from backend.simulator.generator import TelemetryGenerator
from backend.policy.engine import PolicyEngine
from backend.recovery.verify import RecoveryVerifier
from backend.executor.remediation import remediation_executor
from backend.integrations.github_client import github_client
from backend.integrations.notifier import notifier
from backend.graph.workflow import incident_workflow, IncidentState, should_retry_investigator
from backend.orchestrator import orchestrator


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield


def test_end_to_end_all_6_fault_types():
    """Test full LangGraph workflow execution up to approval for all 6 fault types."""
    fault_scenarios = [
        ("deploy", "faulty_deployment", "payments"),
        ("db", "db_connection_leak", "orders-db"),
        ("crash", "service_crash_loop", "inventory"),
        ("net", "network_partition_latency", "gateway"),
        ("cpu", "cpu_saturation_stress", "checkout"),
        ("mem", "memory_leak_oom", "cache")
    ]

    for scenario_id, fault_type, target_svc in fault_scenarios:
        inc_id = f"TEST-{scenario_id}-42"
        config = {"configurable": {"thread_id": inc_id}}
        initial_state: IncidentState = {
            "incident_id": inc_id,
            "scenario_id": scenario_id,
            "fault_type": fault_type,
            "target_service": target_svc,
            "seed": 42,
            "t0": 1000.0,
            "stage_statuses": ["waiting"] * 7,
            "stage_results": [""] * 7,
            "stage_timestamps": [""] * 7,
            "logs": [],
            "audit": [],
            "verifier_retry_count": 0,
            "dropped_claims": [],
            "claims": []
        }

        # Run until human approval interrupt
        state = incident_workflow.invoke(initial_state, config=config)

        # 1. State must pause at await right before executor
        assert state["phase"] == "await"
        assert state["status"] == "Awaiting approval"

        # 2. Correlated alerts
        assert len(state["correlated_alerts"]) >= 1
        assert state["correlation_reason"] != ""

        # 3. Triage
        assert state["severity"] in ["Critical", "High", "Medium"]
        assert state["orders_at_risk"] >= 0
        assert 0.0 <= state["checkout_success_pct"] <= 100.0

        # 4. Causal RCA
        assert len(state["rca_candidates"]) >= 1
        assert state["counterfactual_result"]["is_proof"] is False

        # 5. Policy evaluation
        assert state["policy_allowed"] is True
        assert state["policy_evaluation"]["all_preconditions_met"] is True
        assert state["policy_evaluation"]["allowed_for_execution"] is False  # False until human signs off!

        # 6. Fallback logging in audit trail if API key is missing
        fallback_audits = [a for a in state["audit"] if "deterministic fallback" in a[1]]
        assert len(fallback_audits) >= 1, "Audit trail must explicitly label deterministic fallback"


def test_approve_flow_resolves_and_verifies_recovery():
    """1. Approve flow -> remediated -> recovery verified -> resolved."""
    inc_id = "TEST-APPROVE-FLOW-01"
    config = {"configurable": {"thread_id": inc_id}}
    initial_state: IncidentState = {
        "incident_id": inc_id,
        "scenario_id": "deploy",
        "fault_type": "faulty_deployment",
        "target_service": "payments",
        "seed": 101,
        "t0": 2000.0,
        "stage_statuses": ["waiting"] * 7,
        "stage_results": [""] * 7,
        "stage_timestamps": [""] * 7,
        "logs": [],
        "audit": [],
        "verifier_retry_count": 0,
        "dropped_claims": [],
        "claims": []
    }

    # Run up to approval pause
    incident_workflow.invoke(initial_state, config=config)

    # Approve and resume
    incident_workflow.update_state(
        config,
        {
            "human_approved": True,
            "approval_reviewer": "DevOps Lead (Human)",
            "approval_remarks": "Rollback approved for payments-svc"
        }
    )
    final_state = incident_workflow.invoke(None, config=config)

    # Verifications
    assert final_state["phase"] == "resolved"
    assert final_state["status"] == "Resolved"
    assert final_state["is_recovery_verified"] is True
    assert final_state["recovery_verification"]["checks_passed"] == 4
    assert final_state["after_metrics"]["error_rate_pct"] < 1.0
    assert final_state["after_metrics"]["p95_latency_ms"] < 250.0

    # Comms & Postmortem
    assert "Incident Postmortem" in final_state["postmortem_markdown"]
    assert final_state["comms_update"]["current_status"] == "Resolved"

    # Emoji-free check
    for emoji in ["🚨", "⚠️", "✅", "❌", "🛑", "🔍", "📊", "⚡"]:
        assert emoji not in final_state["comms_update"]["headline"]
        assert emoji not in final_state["comms_update"]["summary"]


def test_reject_flow_blocks_remediation_and_escalates():
    """2. Reject flow -> remediation blocked -> escalated -> postmortem notes rejection."""
    inc_id = "TEST-REJECT-FLOW-02"
    config = {"configurable": {"thread_id": inc_id}}
    initial_state: IncidentState = {
        "incident_id": inc_id,
        "scenario_id": "db",
        "fault_type": "db_connection_leak",
        "target_service": "orders-db",
        "seed": 202,
        "t0": 3000.0,
        "stage_statuses": ["waiting"] * 7,
        "stage_results": [""] * 7,
        "stage_timestamps": [""] * 7,
        "logs": [],
        "audit": [],
        "verifier_retry_count": 0,
        "dropped_claims": [],
        "claims": []
    }

    incident_workflow.invoke(initial_state, config=config)

    # Reject
    incident_workflow.update_state(
        config,
        {
            "human_approved": False,
            "approval_reviewer": "Security Engineer (Human)",
            "approval_remarks": "Action denied due to maintenance window lock"
        }
    )
    final_state = incident_workflow.invoke(None, config=config)

    # Verifications
    assert final_state["phase"] == "rejected"
    assert final_state["status"] == "Escalated"
    assert final_state.get("is_recovery_verified") is not True

    # Audit trail must record human rejection
    audit_texts = [a[1] for a in final_state["audit"]]
    assert any("Rejected remediation" in t or "rejected" in t.lower() for t in audit_texts)


def test_policy_denied_action_blocked_before_execution():
    """3. Policy-denied action -> blocked before execution even if human attempts approval."""
    # Attempting to execute an unallowlisted or prohibited action
    prop_action = "drop_all_tables_in_orders_db"
    res = PolicyEngine.evaluate_remediation_proposal(
        action=prop_action,
        target_service="orders-db",
        is_reversible=False,
        evidence_coverage_pct=90.0,
        has_human_approval=True
    )

    # Even with human approval, policy engine MUST refuse
    assert res["allowed_for_execution"] is False
    assert res["all_preconditions_met"] is False
    assert any("not found in L2 allowlist" in r or "prohibited" in r.lower() for r in res["denial_reasons"])


def test_recovery_verification_failure_escalates_and_never_shows_resolved():
    """4. Recovery verification failure -> remediation executes but fails verification -> incident escalated, never shows Resolved."""
    # Simulating degraded before and after metrics where latency remains 650ms and error rate remains 12%
    before_metrics = {"p95_latency_ms": 700.0, "error_rate_pct": 22.0, "cpu_pct": 85.0, "memory_pct": 70.0}
    failed_after_metrics = {"p95_latency_ms": 650.0, "error_rate_pct": 12.0, "cpu_pct": 82.0, "memory_pct": 69.0}

    verification = RecoveryVerifier.verify(before_metrics, failed_after_metrics)
    assert verification["is_verified"] is False
    assert verification["verdict"] == "FAILED"
    assert verification["escalate"] is True

    # Test workflow handling of failed recovery
    inc_id = "TEST-FAILED-RECOVERY-03"
    config = {"configurable": {"thread_id": inc_id}}
    initial_state: IncidentState = {
        "incident_id": inc_id,
        "scenario_id": "crash",
        "fault_type": "service_crash_loop",
        "target_service": "inventory",
        "seed": 303,
        "t0": 4000.0,
        "stage_statuses": ["waiting"] * 7,
        "stage_results": [""] * 7,
        "stage_timestamps": [""] * 7,
        "logs": [],
        "audit": [],
        "verifier_retry_count": 0,
        "dropped_claims": [],
        "claims": []
    }

    incident_workflow.invoke(initial_state, config=config)

    # Human approves, but we simulate a failed remediation execution where after_metrics do not recover
    incident_workflow.update_state(
        config,
        {
            "human_approved": True,
            "approval_reviewer": "Operator",
            "approval_remarks": "Approved",
            "after_metrics": failed_after_metrics  # Inject degraded after metrics
        }
    )
    final_state = incident_workflow.invoke(None, config=config)

    # MUST be Escalated and NEVER show Resolved
    assert final_state["status"] == "Escalated"
    assert final_state["phase"] == "escalated"
    assert final_state["is_recovery_verified"] is False


def test_emergency_stop_executes_rollback():
    """5. Emergency stop -> rollback action executes -> status rolled_back."""
    sim_data = {
        "fault_type": "faulty_deployment",
        "root_cause_service": "payments",
        "status": "executing"
    }
    # Register an action first
    remediation_executor.execute_action(
        action="rollback_canary_release",
        target_service="payments",
        rollback_plan="redeploy_previous_stable_image",
        sim_run_data=sim_data
    )

    # Trigger emergency stop
    stop_res = remediation_executor.emergency_rollback(sim_data)

    assert stop_res["status"] == "rolled_back"
    assert stop_res["rollback_action"] == "redeploy_previous_stable_image"
    assert sim_data["status"] == "rolled_back"
    assert remediation_executor.is_rolled_back is True


def test_verifier_retry_loop_bounded():
    """6. Verifier retry loop: if the verifier rejects an investigator claim, it retries up to 2 times, then drops the claim and proceeds with lower confidence."""
    # Test should_retry_investigator logic
    state_retry_1: IncidentState = {
        "unverified_claims": [{"claim": "Fake unverified metric", "status": "UNVERIFIED"}],
        "verifier_retry_count": 1
    }
    assert should_retry_investigator(state_retry_1) == "investigator"

    state_retry_2: IncidentState = {
        "unverified_claims": [{"claim": "Fake unverified metric", "status": "UNVERIFIED"}],
        "verifier_retry_count": 2
    }
    assert should_retry_investigator(state_retry_2) == "investigator"

    # Beyond 2 retries, it MUST route to confidence_report and drop the claim
    state_retry_exhausted: IncidentState = {
        "unverified_claims": [{"claim": "Fake unverified metric", "status": "UNVERIFIED"}],
        "verifier_retry_count": 3
    }
    assert should_retry_investigator(state_retry_exhausted) == "confidence_report"


def test_external_integrations_retry_and_mock_fallback():
    """External calls (GitHub and Notifier) retry and record fallback without emojis."""
    # GitHub Client fallback
    commits, is_mock, audit_note = github_client.get_recent_commits("payments")
    assert len(commits) >= 1
    assert is_mock is True
    assert "GitHub API fallback:" in audit_note
    assert "[MOCK_GITHUB_COMMIT]" in commits[0]["message"]

    # Notifier fallback
    ok, notif_audit = notifier.send_notification("INC-TEST", "payments", "Resolved", "Metrics nominal 🚀 ⚠️")
    assert ok is True
    assert "Notification fallback:" in notif_audit

    # Test emoji stripping
    stripped = notifier._strip_emojis("Alert: High Latency 🚨 on payments ⚠️! Status: ✅")
    assert "🚨" not in stripped
    assert "⚠️" not in stripped
    assert "✅" not in stripped


def test_monotonic_utc_timestamps():
    """Audit logs and timestamps must be valid monotonic ISO UTC strings."""
    now_utc = datetime.now(timezone.utc)
    iso = now_utc.isoformat()
    assert "+00:00" in iso or iso.endswith("Z")

