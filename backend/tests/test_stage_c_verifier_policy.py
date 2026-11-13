import pytest
from backend.simulator.generator import generate_simulation
from backend.schemas import ClaimItem
from backend.verification.evidence import evidence_verifier
from backend.confidence.scoring import confidence_scorer
from backend.policy.engine import policy_engine
from backend.security.sanitize import sanitizer

def test_evidence_verifier_identifies_verified_and_dropped_claims():
    run = generate_simulation(fault_type="faulty_deployment", seed=42)

    claims = [
        ClaimItem(type="Deploy", source="deploy-log", claim="Deploy v3.8.1 cut connection pool limits"),
        ClaimItem(type="Metric", source="metrics/payments-svc", claim="Error rate rose from baseline"),
        ClaimItem(type="Log", source="logs/payments-svc", claim="timeout waiting for database connection pool"),
        ClaimItem(type="Trace", source="trace:span", claim="Trace span confirms 2450ms delay"),
        ClaimItem(type="Metric", source="metrics/orders-db", claim="Database CPU is normal, rules out hardware saturation"),
        ClaimItem(type="Assertion", source="investigator", claim="Network partition between us-east-1a and us-east-1b") # False claim!
    ]

    report = evidence_verifier.verify_claims(claims, run)
    assert report.total_claims == 6
    assert report.verified_count >= 3
    assert report.conflicting_count >= 1  # CPU normal
    assert report.dropped_count >= 1      # False network partition claim dropped!

    dropped_texts = [d.claim.claim for d in report.dropped_claims]
    assert any("Network partition" in t for t in dropped_texts)

def test_confidence_scorer_rules_and_conflict_penalty():
    run = generate_simulation(fault_type="faulty_deployment", seed=42)

    # 1. High quality claims
    claims_good = [
        ClaimItem(type="Deploy", source="deploy-log", claim="Deploy v3.8.1"),
        ClaimItem(type="Metric", source="metrics/payments-svc", claim="Error rate rose"),
        ClaimItem(type="Log", source="logs/payments-svc", claim="timeout waiting"),
        ClaimItem(type="Trace", source="trace:span", claim="Trace span delay"),
    ]
    report_good = evidence_verifier.verify_claims(claims_good, run)
    conf_good = confidence_scorer.calculate(report_good, run)

    assert conf_good.evidence_coverage_pct == 100.0
    assert conf_good.diagnostic_confidence_pct >= 80.0
    assert conf_good.blocks_l2 is False

    # 2. Add conflicting and dropped claims -> confidence drops
    claims_mixed = claims_good + [
        ClaimItem(type="Metric", source="metrics/orders-db", claim="Database CPU is normal"),
        ClaimItem(type="Assertion", source="investigator", claim="Network partition between us-east-1a and us-east-1b"),
        ClaimItem(type="Assertion", source="investigator", claim="Disk space exhaustion on db volume")
    ]
    report_mixed = evidence_verifier.verify_claims(claims_mixed, run)
    conf_mixed = confidence_scorer.calculate(report_mixed, run)

    assert conf_mixed.conflicting_evidence_count >= 1
    assert conf_mixed.conflict_penalty_pct > 0
    # Mixed confidence must be lower than good confidence
    assert conf_mixed.diagnostic_confidence_pct < conf_good.diagnostic_confidence_pct

def test_policy_engine_exact_action_registry():
    # Valid L2 action
    dec_l2 = policy_engine.evaluate_remediation_proposal(
        action="rollback_deployment",
        target_service="payments-svc",
        is_reversible=True,
        has_rollback_plan=True,
        timeout_seconds=120,
        confidence_pct=85.0,
        evidence_coverage_pct=85.0,
        has_human_approval=False
    )
    assert dec_l2.policy_level == "L2"
    assert dec_l2.all_preconditions_met is True
    assert dec_l2.allowed_for_execution is False  # Must await approval!

    # L3 prohibited action
    dec_l3 = policy_engine.evaluate_remediation_proposal(
        action="drop_database",
        target_service="orders-db",
        is_reversible=False,
        has_rollback_plan=False,
        timeout_seconds=60,
        confidence_pct=90.0,
        evidence_coverage_pct=90.0,
        has_human_approval=True
    )
    assert dec_l3.policy_level == "DENIED"
    assert dec_l3.all_preconditions_met is False
    assert dec_l3.allowed_for_execution is False

    # Unknown arbitrary action
    dec_unknown = policy_engine.evaluate_remediation_proposal(
        action="execute_custom_bash_script",
        target_service="checkout-svc",
        is_reversible=True,
        has_rollback_plan=True,
        timeout_seconds=60,
        confidence_pct=90.0,
        evidence_coverage_pct=90.0,
        has_human_approval=True
    )
    assert dec_unknown.policy_level == "DENIED"
    assert dec_unknown.allowed_for_execution is False

def test_policy_engine_exact_service_boundary_rejection():
    # Attempting to target an unmodeled external service
    dec = policy_engine.evaluate_remediation_proposal(
        action="rollback_deployment",
        target_service="external-payment-vendor-prod",
        is_reversible=True,
        has_rollback_plan=True,
        timeout_seconds=120,
        confidence_pct=85.0,
        evidence_coverage_pct=85.0,
        has_human_approval=True
    )
    assert dec.policy_level == "DENIED"
    assert dec.allowed_for_execution is False
    assert any("Simulation Boundary Isolation" in c.name and c.passed is False for c in dec.checks)

def test_policy_engine_human_approval_gate():
    # Human approval = True allows execution
    dec = policy_engine.evaluate_remediation_proposal(
        action="rollback_deployment",
        target_service="payments-svc",
        is_reversible=True,
        has_rollback_plan=True,
        timeout_seconds=120,
        confidence_pct=85.0,
        evidence_coverage_pct=85.0,
        has_human_approval=True
    )
    assert dec.all_preconditions_met is True
    assert dec.allowed_for_execution is True
    assert dec.status_text == "Approved (L2)"

def test_security_sanitizer_quarantines_injection_text():
    # Injected prompt injection text
    raw_log = sanitizer.create_injection_demo_scenario_log("payments-svc")
    result = sanitizer.sanitize_log_message(raw_log)

    assert result.injection_detected is True
    assert len(result.quarantined_tokens) >= 1
    assert "[QUARANTINED_UNTRUSTED_INJECTION:" in result.sanitized_text
    assert "Ignore previous instructions" not in result.sanitized_text

def test_security_sanitizer_preserves_benign_logs():
    benign_log = "INFO: payments-svc acquired database pool connection in 14ms"
    result = sanitizer.sanitize_log_message(benign_log)

    assert result.injection_detected is False
    assert result.sanitized_text == benign_log
    assert len(result.quarantined_tokens) == 0
