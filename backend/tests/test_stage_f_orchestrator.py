"""
backend/tests/test_stage_f_orchestrator.py
Comprehensive lifecycle and failure-path tests for SimulationOrchestrator:
1. Complete lifecycle: run -> await -> approve -> resolved with recovery verification
2. Rejection lifecycle: run -> await -> reject -> escalated with postmortem
3. Emergency stop: run -> stop -> rolled_back status
4. Invalid scenario handling
5. Multi-run monotonic incident ID generation
"""
import pytest
from backend.database import init_db, get_connection
from backend.orchestrator import orchestrator


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    orchestrator.active_sim = None
    if orchestrator.step_task and not orchestrator.step_task.done():
        orchestrator.step_task.cancel()
    yield


def test_orchestrator_full_lifecycle_approve():
    """Verify full synchronous lifecycle: start -> await -> approve -> resolved."""
    # 1. Start simulation
    status = orchestrator.run_scenario_sync("deploy")
    assert status["active"] is True
    assert status["sim"]["id"].startswith("INC-")
    inc_id = status["sim"]["id"]
    assert status["sim"]["phase"] == "await"
    assert status["sim"]["stages"][0]["status"] == "completed"  # Supervisor
    assert status["sim"]["stages"][1]["status"] == "completed"  # Triage
    assert status["sim"]["stages"][2]["status"] == "completed"  # Investigator
    assert status["sim"]["stages"][3]["status"] == "completed"  # Causal RCA
    assert status["sim"]["stages"][4]["status"] == "completed"  # Evidence Verifier
    assert status["sim"]["stages"][5]["status"] == "review"     # Remediation awaiting human review

    # Verify intermediate persistence
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT status, phase FROM incidents WHERE id = ?", (inc_id,))
    row = c.fetchone()
    assert row["status"] == "Awaiting approval"
    assert row["phase"] == "await"

    # 2. Approve remediation
    approved_status = orchestrator.approve_remediation_sync(reviewer="Senior SRE Lead")
    assert approved_status["sim"]["phase"] == "resolved"
    assert approved_status["sim"]["stages"][5]["status"] == "completed"
    assert approved_status["sim"]["stages"][6]["status"] == "completed"

    # Verify final persistence in SQLite
    c.execute("SELECT status, phase, resolved_at FROM incidents WHERE id = ?", (inc_id,))
    final_inc = c.fetchone()
    assert final_inc["status"] == "Resolved"
    assert final_inc["phase"] == "resolved"
    assert final_inc["resolved_at"] is not None

    # Verify postmortem in DB
    c.execute("SELECT title, content_markdown FROM postmortems WHERE incident_id = ?", (inc_id,))
    pm = c.fetchone()
    assert pm is not None
    assert inc_id in pm["title"]
    assert "Incident Postmortem" in pm["content_markdown"]
    assert "Senior SRE Lead" in pm["content_markdown"]

    # Verify Knowledge Base insertion
    c.execute("SELECT id, title, approval_status, recovery_status FROM knowledge_items WHERE id = ?", (inc_id,))
    kb_item = c.fetchone()
    assert kb_item is not None
    assert kb_item["approval_status"] == "Approved"
    assert kb_item["recovery_status"] == "Verified"

    conn.close()


def test_orchestrator_rejection_lifecycle():
    """Verify rejection lifecycle: start -> await -> reject -> escalated."""
    status = orchestrator.run_scenario_sync("db")
    inc_id = status["sim"]["id"]
    assert status["sim"]["phase"] == "await"

    # Reject
    rejected_status = orchestrator.reject_remediation_sync(
        reviewer="Incident Commander",
        reason="Change window closed due to flash sale"
    )
    assert rejected_status["sim"]["phase"] == "rejected"
    assert rejected_status["sim"]["stages"][5]["status"] == "failed"

    # Verify DB status
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT status, phase FROM incidents WHERE id = ?", (inc_id,))
    inc_row = c.fetchone()
    assert inc_row["status"] == "Escalated"
    assert inc_row["phase"] == "rejected"

    # Postmortem must note rejection and escalation
    c.execute("SELECT content_markdown FROM postmortems WHERE incident_id = ?", (inc_id,))
    pm = c.fetchone()
    assert pm is not None
    assert "Incident Commander" in pm["content_markdown"]
    assert "Change window closed due to flash sale" in pm["content_markdown"]
    conn.close()


def test_orchestrator_emergency_stop():
    """Verify emergency stop triggers rollback and sets phase stopped."""
    status = orchestrator.run_scenario_sync("crash")
    inc_id = status["sim"]["id"]
    assert status["sim"]["phase"] == "await"

    # Emergency stop
    stopped_status = orchestrator.emergency_stop_sync(actor="Security Lead")
    assert stopped_status["sim"]["phase"] == "stopped"

    # Verify DB status
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT status, phase FROM incidents WHERE id = ?", (inc_id,))
    row = c.fetchone()
    assert row["status"] == "Stopped"
    assert row["phase"] == "stopped"
    conn.close()


def test_orchestrator_invalid_scenario_raises_value_error():
    """Verify that unknown scenario ID raises ValueError."""
    with pytest.raises(ValueError, match="Unknown scenario ID"):
        orchestrator.run_scenario_sync("non_existent_chaos_scenario")


def test_orchestrator_monotonic_id_generation():
    """Verify monotonic ID generation strictly increases without collision."""
    st1 = orchestrator.run_scenario_sync("cpu")
    id1 = st1["sim"]["id"]
    num1 = int(id1.split("-")[1])

    orchestrator.active_sim = None
    st2 = orchestrator.run_scenario_sync("mem")
    id2 = st2["sim"]["id"]
    num2 = int(id2.split("-")[1])

    assert num2 > num1

