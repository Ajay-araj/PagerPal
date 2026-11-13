"""
backend/tests/test_stage_e_kb_postmortem.py
Stage E Verification:
1. SQLite-backed Knowledge Base storing and retrieving resolved incidents.
2. Similar incident search enforcing Hard Rule 8 (suggestions only, auto_apply=False).
3. Postmortems generated dynamically with distinct preventive action items for all 6 fault types
   (verifying Known Defect 7 fix: never hard-coding database pools for every incident).
4. Unrecovered or rejected incident postmortems correctly reflect Escalated / Unresolved status.
5. FastAPI /api/kb/similar endpoint integration test.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.database import init_db
from backend.main import get_similar_incidents
from backend.memory.kb import KnowledgeBase, kb
from backend.postmortem.generator import PostmortemGenerator, FAULT_SPECIFIC_PREVENTIVE_ACTIONS


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield


def test_store_resolved_incident_in_kb():
    """Verify storing and retrieving an incident record from the Knowledge Base."""
    custom_kb = KnowledgeBase()
    inc_id = "INC-TEST-STORE-001"
    now_iso = datetime.now(timezone.utc).isoformat()

    stored = custom_kb.store_incident(
        incident_id=inc_id,
        timestamp=now_iso,
        service="payments-svc",
        fault_type="faulty_deployment",
        root_cause="payments",
        fix_action="rollback_deployment",
        resolution_time_sec=115.5,
        verified_recovery=True,
        symptoms="High 5xx error rate on checkout",
        summary="Canary deployment v2.4.1 rolled back to v2.4.0"
    )

    assert stored["incident_id"] == inc_id
    assert stored["service"] == "payments-svc"
    assert stored["fault_type"] == "faulty_deployment"
    assert stored["verified_recovery"] is True
    assert stored["resolution_time_sec"] == 115.5

    # Retrieve record
    retrieved = custom_kb.get_incident(inc_id)
    assert retrieved is not None
    assert retrieved["incident_id"] == inc_id
    assert retrieved["root_cause"] == "payments"
    assert retrieved["fix_action"] == "rollback_deployment"
    assert retrieved["suggestion_only"] is True
    assert retrieved["auto_apply"] is False


def test_search_similar_incidents_suggestions_only():
    """Hard Rule 8: KB search results must strictly be suggestions for human review."""
    results = kb.search_similar(service="payments", limit=5)
    assert len(results) >= 1

    for item in results:
        # Enforce Hard Rule 8
        assert item["suggestion_only"] is True
        assert item["auto_apply"] is False
        assert item["review_required"] is True
        assert "reference only" in item["guidance"].lower()

    # Search by symptom keyword
    symptom_results = kb.search_similar(symptoms="pool", limit=5)
    assert len(symptom_results) >= 1
    assert any("pool" in r["symptoms"].lower() or "pool" in r["summary"].lower() for r in symptom_results)


def test_postmortem_distinct_for_all_6_fault_types():
    """
    Known Defect 7 Fix: Verify distinct preventive action items for all 6 fault types.
    Postmortems must NEVER hardcode database pool actions for unrelated faults.
    """
    fault_scenarios = [
        ("faulty_deployment", "payments", "rollback_deployment", ["canary", "smoke", "rollback"]),
        ("database_connection_failure", "orders-db", "reset_connection_pooler", ["pool", "connection", "hikaricp"]),
        ("service_crash", "inventory", "restart_service_container", ["memory", "oom", "probe"]),
        ("network_latency", "gateway", "shift_traffic_zone", ["circuit breaker", "timeout", "zone"]),
        ("cpu_stress", "checkout", "scale_service_replicas", ["autoscaler", "rate-limiting", "hpa"]),
        ("memory_stress", "cache", "flush_and_restart_cache", ["lru", "eviction", "warming"])
    ]

    generated_postmortems = {}

    for fault_type, service, action, expected_keywords in fault_scenarios:
        pm = PostmortemGenerator.generate(
            incident_id=f"INC-{fault_type.upper()}-99",
            service=service,
            fault_type=fault_type,
            status="Resolved",
            severity="High",
            root_cause=service,
            propagation_path=[service, "checkout", "gateway"],
            remediation_action=action,
            before_metrics={"p95_latency_ms": 650.0, "error_rate_pct": 18.5},
            after_metrics={"p95_latency_ms": 12.0, "error_rate_pct": 0.05},
            verified_claims=[{"claim": f"{service} elevated telemetry"}],
            dropped_claims=[],
            policy_checks=[],
            is_recovery_verified=True,
            operator_reviewer="SRE On-Call (Human)",
            operator_approved=True
        )

        assert "Incident Postmortem" in pm
        assert "Resolved" in pm
        assert service in pm
        assert fault_type in pm
        assert action in pm

        # Verify fault-specific action items (Defect 7 fix!)
        pm_lower = pm.lower()
        keyword_matches = sum(1 for kw in expected_keywords if kw in pm_lower)
        assert keyword_matches >= 1, f"Postmortem for {fault_type} missing fault-specific action items: {expected_keywords}"

        # CPU, deployment, network, crash postmortems MUST NOT have database pool actions
        if fault_type not in ["database_connection_failure"]:
            assert "hikaricp" not in pm_lower, f"{fault_type} should not contain HikariCP pool actions!"

        generated_postmortems[fault_type] = pm

    # Ensure all 6 generated postmortems are distinct text documents
    unique_pms = set(generated_postmortems.values())
    assert len(unique_pms) == 6, "All 6 fault postmortems must be distinct documents!"


def test_postmortem_unrecovered_or_rejected_incident():
    """Unrecovered or rejected incidents must reflect Escalated / Unresolved and never claim Resolved."""
    # 1. Recovery verification failed
    pm_unverified = PostmortemGenerator.generate(
        incident_id="INC-FAIL-01",
        service="inventory",
        fault_type="service_crash",
        status="Escalated",
        severity="Critical",
        root_cause="inventory",
        propagation_path=["inventory", "checkout"],
        remediation_action="restart_service_container",
        before_metrics={"p95_latency_ms": 720.0, "error_rate_pct": 25.0},
        after_metrics={"p95_latency_ms": 680.0, "error_rate_pct": 15.0},
        verified_claims=[],
        dropped_claims=[],
        policy_checks=[],
        is_recovery_verified=False,  # Failed!
        operator_reviewer="Operator (Human)",
        operator_approved=True
    )

    assert "Escalated / Unresolved" in pm_unverified
    assert "Recovery Status: UNRESOLVED / ESCALATED" in pm_unverified
    assert "Recovery verification did NOT confirm" in pm_unverified
    assert "Incident Status: **Resolved**" not in pm_unverified
    # Escalation emergency actions
    assert "emergency incident bridge" in pm_unverified.lower()

    # 2. Operator rejected
    pm_rejected = PostmortemGenerator.generate(
        incident_id="INC-REJECT-02",
        service="orders-db",
        fault_type="database_connection_failure",
        status="Escalated",
        severity="High",
        root_cause="orders-db",
        propagation_path=["orders-db"],
        remediation_action="reset_connection_pooler",
        before_metrics={"p95_latency_ms": 900.0, "error_rate_pct": 30.0},
        after_metrics={},
        verified_claims=[],
        dropped_claims=[],
        policy_checks=[],
        is_recovery_verified=False,
        operator_reviewer="Security Lead (Human)",
        operator_approved=False  # Rejected!
    )

    assert "Escalated / Unresolved" in pm_rejected
    assert "Operator rejected proposal" in pm_rejected
    assert "Incident Status: **Resolved**" not in pm_rejected


def test_api_kb_similar_endpoint():
    """Integration test for FastAPI /api/kb/similar endpoint."""
    data = get_similar_incidents(service="payments", limit=3)

    assert data["query"]["service"] == "payments"
    assert data["governance"]["hard_rule_8_enforced"] is True
    assert data["governance"]["auto_apply_allowed"] is False
    assert len(data["suggestions"]) >= 1

    for sug in data["suggestions"]:
        assert sug["suggestion_only"] is True
        assert sug["auto_apply"] is False
        assert "payments" in sug["service"].lower()

