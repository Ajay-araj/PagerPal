import pytest
from backend.simulator.generator import generate_simulation, TelemetryGenerator
from backend.simulator.faults import FAULT_PROFILES
from backend.simulator.topology import topology

def test_all_fault_types_generate_valid_telemetry():
    for fault_type in FAULT_PROFILES.keys():
        run = generate_simulation(fault_type=fault_type, seed=42)
        assert run.run_id.startswith("RUN-")
        assert run.scenario_id == fault_type
        assert len(run.alerts) >= 2
        assert len(run.logs) >= 3
        assert len(run.metrics) > 0
        assert len(run.traces) >= 3
        assert run.ground_truth is not None
        assert run.ground_truth.fault_type == fault_type
        assert run.ground_truth.target_service == run.target_service
        assert len(run.ground_truth.propagation_chain) >= 1

def test_generator_is_reproducible_with_seed():
    run1 = generate_simulation(fault_type="database_connection_failure", seed=1337)
    run2 = generate_simulation(fault_type="database_connection_failure", seed=1337)

    assert run1.run_id == run2.run_id
    assert len(run1.logs) == len(run2.logs)
    assert [l.message for l in run1.logs] == [l.message for l in run2.logs]
    assert [a.alert_id for a in run1.alerts] == [a.alert_id for a in run2.alerts]
    assert run1.ground_truth.root_cause_explanation == run2.ground_truth.root_cause_explanation

def test_different_seeds_produce_variation():
    run1 = generate_simulation(fault_type="cpu_stress", seed=11)
    run2 = generate_simulation(fault_type="cpu_stress", seed=99)

    # Commit shas, trace IDs or log timings will vary
    trace_ids_1 = [t.trace_id for t in run1.traces]
    trace_ids_2 = [t.trace_id for t in run2.traces]
    assert trace_ids_1 != trace_ids_2

def test_arbitrary_target_service_override():
    # Inject service_crash on 'payments' rather than default 'inventory'
    run_payments = generate_simulation(fault_type="service_crash", target_service="payments", seed=50)
    assert run_payments.target_service == "payments"
    assert run_payments.ground_truth.target_service == "payments"
    assert "payments-svc" in run_payments.ground_truth.root_cause_explanation

    # Inject cpu_stress on 'auth' rather than default 'checkout'
    run_auth = generate_simulation(fault_type="cpu_stress", target_service="auth", seed=51)
    assert run_auth.target_service == "auth"
    assert run_auth.ground_truth.target_service == "auth"

def test_missing_telemetry_toggle():
    # Verify generator gracefully simulates missing trace or metrics telemetry
    run_no_traces = generate_simulation(fault_type="network_latency", seed=42, missing_telemetry="traces")
    assert len(run_no_traces.traces) == 0
    assert len(run_no_traces.logs) > 0

    run_no_metrics = generate_simulation(fault_type="network_latency", seed=42, missing_telemetry="metrics")
    assert len(run_no_metrics.metrics) == 0

def test_noisy_logs_injection():
    run_clean = generate_simulation(fault_type="memory_stress", seed=42, inject_noise=False)
    run_noisy = generate_simulation(fault_type="memory_stress", seed=42, inject_noise=True)
    assert len(run_noisy.logs) > len(run_clean.logs)
    assert any("auth-svc" in l.service for l in run_noisy.logs)

def test_ground_truth_isolation():
    run = generate_simulation(fault_type="faulty_deployment", seed=42)
    # Ground truth is isolated in ground_truth object and not in the raw telemetry payloads
    assert hasattr(run, "ground_truth")
    assert run.ground_truth.recommended_action == "rollback_deployment"
    # The string "rollback_deployment" should not be present in raw log messages
    for log in run.logs:
        assert "rollback_deployment" not in log.message

