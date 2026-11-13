import pytest
from backend.simulator.generator import generate_simulation
from backend.simulator.faults import FAULT_PROFILES
from backend.correlation.engine import correlation_engine
from backend.rca.causal_graph import causal_rca_engine
from backend.schemas import SimulatedAlert

def test_every_fault_type_collapses_to_one_incident():
    for fault_type in FAULT_PROFILES.keys():
        run = generate_simulation(fault_type=fault_type, seed=42)
        corr = correlation_engine.correlate(run.alerts, incident_id=f"INC-{fault_type}")

        # Check: All alerts collapsed into one incident
        assert corr.incident_id == f"INC-{fault_type}"
        assert len(corr.alerts) > 0
        assert len(corr.services_involved) >= 2
        # Check: Computed reason is dynamic and contains real metrics, not hard-coded text
        assert "Grouped" in corr.correlation_reason
        assert "hop" in corr.correlation_reason
        assert corr.timespan_seconds > 0

def test_alert_deduplication():
    # Duplicate alert with same service and name within 10s
    alerts = [
        SimulatedAlert(alert_id="a1", service="checkout-svc", name="p95 high", severity="High", condition="p95 > 1s", fired_at="2026-11-13T10:00:00Z", value_observed=1200, threshold=1000),
        SimulatedAlert(alert_id="a2", service="checkout-svc", name="p95 high", severity="High", condition="p95 > 1s", fired_at="2026-11-13T10:00:10Z", value_observed=1250, threshold=1000),
        SimulatedAlert(alert_id="a3", service="api-gateway", name="504 upstream", severity="Critical", condition="504 > 10", fired_at="2026-11-13T10:00:15Z", value_observed=25, threshold=10)
    ]
    corr = correlation_engine.correlate(alerts)
    assert corr.total_alerts_received == 3
    assert corr.dedup_count == 1
    assert len(corr.alerts) == 2

def test_rca_finds_underlying_cause_when_first_alerting_is_not_cause_case_1():
    # Case 1: First alert fires on checkout-svc / gateway, but root cause is orders-db
    run = generate_simulation(fault_type="database_connection_failure", seed=101)
    # Confirm first alert in list is on an upstream caller, or target is orders-db
    rca = causal_rca_engine.analyze(run)

    top_ids = [c.service_id for c in rca.top_candidates]
    # Root cause must be orders-db, not checkout or gateway!
    assert "orders-db" in top_ids
    assert rca.primary_root_cause.service_id == "orders-db"
    assert "orders-db" in rca.propagation_path

def test_rca_finds_underlying_cause_when_first_alerting_is_not_cause_case_2():
    # Case 2: First alert fires on checkout-svc (stock check failed), but root cause is inventory
    run = generate_simulation(fault_type="service_crash", target_service="inventory", seed=202)
    rca = causal_rca_engine.analyze(run)

    top_ids = [c.service_id for c in rca.top_candidates]
    assert "inventory" in top_ids
    assert rca.primary_root_cause.service_id == "inventory"

def test_hard_case_1_noisy_unrelated_logs():
    # Injects noisy logs from auth-svc and cache into memory_stress
    run = generate_simulation(fault_type="memory_stress", seed=303, inject_noise=True)
    rca = causal_rca_engine.analyze(run)

    top_ids = [c.service_id for c in rca.top_candidates]
    assert "cache" in top_ids
    assert rca.primary_root_cause.service_id == "cache"

def test_hard_case_2_network_latency_drift():
    # Network transit link degraded on payments
    run = generate_simulation(fault_type="network_latency", target_service="payments", seed=404)
    rca = causal_rca_engine.analyze(run)

    top_ids = [c.service_id for c in rca.top_candidates]
    assert "payments" in top_ids
    assert rca.primary_root_cause.service_id == "payments"

def test_hard_case_3_missing_telemetry_source():
    # Traces missing completely
    run = generate_simulation(fault_type="faulty_deployment", seed=505, missing_telemetry="traces")
    assert len(run.traces) == 0
    rca = causal_rca_engine.analyze(run)

    # Should still identify payments via deployment record + logs + metrics
    top_ids = [c.service_id for c in rca.top_candidates]
    assert "payments" in top_ids

def test_counterfactual_check_is_proof_false():
    run = generate_simulation(fault_type="cpu_stress", seed=606)
    rca = causal_rca_engine.analyze(run)

    cf = rca.counterfactual
    assert cf.is_proof is False  # Never claim counterfactual simulation is proof
    assert cf.supports_hypothesis is True
    assert "p95_latency_ms" in cf.metric_deltas
    assert "error_rate_pct" in cf.metric_deltas
    assert "is_proof=False" in cf.explanation

