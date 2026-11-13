import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from backend.schemas import (
    LogRecord, MetricPoint, TraceSpan, DeploymentRecord,
    SimulatedAlert, GroundTruth, SimulationRun
)
from backend.simulator.topology import topology
from backend.simulator.faults import FAULT_PROFILES

class TelemetryGenerator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else 42
        self.rng = random.Random(self.seed)

    def generate(
        self,
        fault_type: str,
        target_service: Optional[str] = None,
        inject_noise: bool = False,
        missing_telemetry: Optional[str] = None,  # e.g., 'traces', 'metrics', 'logs', 'deployments'
        time_offset_minutes: int = 5
    ) -> SimulationRun:
        if fault_type not in FAULT_PROFILES:
            raise ValueError(f"Unknown fault type '{fault_type}'. Available: {list(FAULT_PROFILES.keys())}")

        profile = FAULT_PROFILES[fault_type]
        service_id = target_service or profile["default_service"]
        service_meta = topology.get_service(service_id)
        if not service_meta:
            raise ValueError(f"Target service '{service_id}' does not exist in topology.")

        service_name = service_meta["name"]
        now_dt = datetime.now(timezone.utc)
        t0 = now_dt - timedelta(minutes=time_offset_minutes)

        # Ground truth formulation
        prop_path = topology.find_propagation_path(service_id, "checkout")
        root_cause_text = profile["root_cause_template"].format(
            service_name=service_name,
            version="v3.8.1"
        )
        recommended_action = profile["recommended_action"]

        ground_truth = GroundTruth(
            scenario_id=f"SCN-{fault_type}-{self.seed}",
            fault_type=fault_type,
            target_service=service_id,
            root_cause_explanation=root_cause_text,
            recommended_action=recommended_action,
            injected_at=t0.isoformat(),
            propagation_chain=prop_path
        )

        run = SimulationRun(
            run_id=f"RUN-{int(t0.timestamp())}-{self.seed}",
            seed=self.seed,
            scenario_id=fault_type,
            target_service=service_id,
            ground_truth=ground_truth
        )

        # 1. Deployments
        if missing_telemetry != "deployments":
            run.deployments = self._generate_deployments(profile, service_id, service_name, t0)

        # 2. Metrics Time Series
        if missing_telemetry != "metrics":
            run.metrics = self._generate_metrics(profile, service_id, prop_path, t0)

        # 3. Traces
        if missing_telemetry != "traces":
            run.traces = self._generate_traces(profile, service_id, prop_path, t0)

        # 4. Logs
        if missing_telemetry != "logs":
            run.logs = self._generate_logs(profile, service_id, service_name, prop_path, t0, inject_noise)

        # 5. Alerts
        run.alerts = self._generate_alerts(profile, service_id, service_name, prop_path, t0)

        return run

    def _generate_deployments(
        self, profile: Dict[str, Any], service_id: str, service_name: str, t0: datetime
    ) -> List[DeploymentRecord]:
        deploys = []
        # Target deployment if applicable
        if profile.get("has_deployment"):
            dep_time = t0 - timedelta(minutes=3, seconds=self.rng.randint(10, 45))
            deploys.append(DeploymentRecord(
                deploy_id=f"dep-{self.rng.randint(1000, 9999)}",
                service=service_name,
                version="v3.8.1",
                deployed_at=dep_time.isoformat(),
                commit_sha=f"{self.rng.getrandbits(24):06x}",
                commit_message=f"perf: tune {service_name} resource allocation and connection limits",
                author="alex.dev@internal",
                diff_summary="pool_size: 40 -> 5; timeout: 2500ms; memory_limit: 256Mi"
            ))

        # Background baseline deployment for other service
        other_svc = "auth-svc" if service_name != "auth-svc" else "inventory-svc"
        bg_dep_time = t0 - timedelta(hours=14)
        deploys.append(DeploymentRecord(
            deploy_id=f"dep-{self.rng.randint(1000, 9999)}",
            service=other_svc,
            version="v2.4.0",
            deployed_at=bg_dep_time.isoformat(),
            commit_sha=f"{self.rng.getrandbits(24):06x}",
            commit_message=f"feat: update telemetry exporter for {other_svc}",
            author="sam.sre@internal",
            diff_summary="Add prometheus counter hooks for grpc endpoints"
        ))
        return deploys

    def _generate_metrics(
        self, profile: Dict[str, Any], service_id: str, prop_path: List[str], t0: datetime
    ) -> Dict[str, List[MetricPoint]]:
        metrics_dict: Dict[str, List[MetricPoint]] = {}
        all_services = topology.get_services()

        # Generate 10 time slices (-5m to +5m around injection time)
        for step in range(-5, 6):
            pt_time = t0 + timedelta(minutes=step)
            pt_iso = pt_time.isoformat()
            is_post_fault = step >= 0

            for s_id, s_meta in all_services.items():
                s_name = s_meta["name"]
                sli = topology.get_sli(s_id)

                base_latency = sli.get("p95_latency_ms", 30.0)
                base_err = sli.get("error_rate_pct", 0.05)
                base_cpu = sli.get("cpu_pct", 25.0)
                base_mem = sli.get("mem_pct", 35.0)

                # Add baseline jitter
                lat = base_latency + self.rng.uniform(-2.0, 3.0)
                err = max(0.0, base_err + self.rng.uniform(-0.02, 0.04))
                cpu = base_cpu + self.rng.uniform(-2.0, 3.0)
                mem = base_mem + self.rng.uniform(-1.0, 2.0)

                if is_post_fault:
                    if s_id == service_id:
                        # Direct fault target impact
                        lat = base_latency * profile["metric_impact"]["p95_latency_mult"] + self.rng.uniform(-50, 100)
                        err = profile["metric_impact"]["error_rate_spike"] + self.rng.uniform(-0.5, 1.0)
                        if profile["recommended_action"] == "scale_service_replicas":
                            cpu = 97.4 + self.rng.uniform(-0.8, 1.2)
                        if profile["recommended_action"] == "flush_and_restart_cache":
                            mem = 98.8 + self.rng.uniform(-0.5, 0.8)
                    elif s_id in prop_path or s_id == "checkout":
                        # Cascaded impact on upstream callers
                        lat = base_latency * max(2.5, profile["metric_impact"]["p95_latency_mult"] * 0.45)
                        err = max(err, profile["metric_impact"]["error_rate_spike"] * 0.6)

                # Record points
                for m_name, val, unit in [
                    ("p95_latency_ms", max(1.0, lat), "ms"),
                    ("error_rate_pct", min(100.0, max(0.0, err)), "%"),
                    ("cpu_pct", min(100.0, max(1.0, cpu)), "%"),
                    ("mem_pct", min(100.0, max(1.0, mem)), "%")
                ]:
                    key = f"{s_name}:{m_name}"
                    if key not in metrics_dict:
                        metrics_dict[key] = []
                    metrics_dict[key].append(MetricPoint(
                        timestamp=pt_iso,
                        service=s_name,
                        metric_name=m_name,
                        value=round(val, 2),
                        unit=unit
                    ))
        return metrics_dict

    def _generate_traces(
        self, profile: Dict[str, Any], service_id: str, prop_path: List[str], t0: datetime
    ) -> List[TraceSpan]:
        spans: List[TraceSpan] = []
        # Generate 4 representative transaction trace spans
        for trace_idx in range(4):
            trace_id = f"trace-{self.rng.getrandbits(32):08x}"
            t_span_start = t0 + timedelta(seconds=trace_idx * 30 + self.rng.randint(5, 20))
            is_failing_trace = trace_idx >= 1

            parent_span_id = None
            current_time = t_span_start

            # Edge gateway span
            gw_span_id = f"span-{self.rng.getrandbits(24):06x}"
            gw_duration = 2450.0 if is_failing_trace else 45.0
            spans.append(TraceSpan(
                trace_id=trace_id,
                span_id=gw_span_id,
                parent_span_id=None,
                service="api-gateway",
                operation="POST /v1/checkout/process",
                start_time=current_time.isoformat(),
                duration_ms=gw_duration,
                status_code=504 if is_failing_trace else 200,
                error=is_failing_trace,
                error_message="Gateway timeout from upstream checkout-svc" if is_failing_trace else None
            ))

            # Checkout span
            chk_span_id = f"span-{self.rng.getrandbits(24):06x}"
            chk_duration = gw_duration - 15.0
            spans.append(TraceSpan(
                trace_id=trace_id,
                span_id=chk_span_id,
                parent_span_id=gw_span_id,
                service="checkout-svc",
                operation="CheckoutHandler.execute",
                start_time=current_time.isoformat(),
                duration_ms=chk_duration,
                status_code=500 if is_failing_trace else 200,
                error=is_failing_trace,
                error_message=f"Downstream dependency {service_id} timeout" if is_failing_trace else None
            ))

            # Target service span
            target_meta = topology.get_service(service_id)
            target_name = target_meta["name"] if target_meta else service_id
            tgt_span_id = f"span-{self.rng.getrandbits(24):06x}"
            tgt_duration = chk_duration - 10.0
            spans.append(TraceSpan(
                trace_id=trace_id,
                span_id=tgt_span_id,
                parent_span_id=chk_span_id,
                service=target_name,
                operation=f"{target_name}.handle_request",
                start_time=current_time.isoformat(),
                duration_ms=tgt_duration,
                status_code=503 if is_failing_trace else 200,
                error=is_failing_trace,
                error_message=profile["log_signatures"][0].format(service_name=target_name) if is_failing_trace else None
            ))
        return spans

    def _generate_logs(
        self, profile: Dict[str, Any], service_id: str, service_name: str,
        prop_path: List[str], t0: datetime, inject_noise: bool
    ) -> List[LogRecord]:
        logs: List[LogRecord] = []

        # 1. Healthy pre-incident logs
        logs.append(LogRecord(
            timestamp=(t0 - timedelta(minutes=4)).isoformat(),
            service=service_name,
            level="INFO",
            message="Health probe check passed: latency 12ms, connection pool active: 40/40"
        ))
        logs.append(LogRecord(
            timestamp=(t0 - timedelta(minutes=2)).isoformat(),
            service="checkout-svc",
            level="INFO",
            message="Order processed successfully (order_id=ord_9182, amount=84.50)"
        ))

        # 2. Incident root cause signatures
        for i, sig in enumerate(profile["log_signatures"]):
            ts = t0 + timedelta(seconds=i * 22 + self.rng.randint(2, 10))
            logs.append(LogRecord(
                timestamp=ts.isoformat(),
                service=service_name,
                level="ERROR" if i < len(profile["log_signatures"]) - 1 else "FATAL",
                message=sig.format(service_name=service_name),
                trace_id=f"trace-{self.rng.getrandbits(32):08x}",
                span_id=f"span-{self.rng.getrandbits(24):06x}"
            ))

        # 3. Upstream propagated error logs
        if "checkout" in prop_path or service_id != "checkout":
            logs.append(LogRecord(
                timestamp=(t0 + timedelta(seconds=65)).isoformat(),
                service="checkout-svc",
                level="ERROR",
                message=f"Upstream call to {service_name} failed: connection timeout after 2500ms; 504 returned to client",
                trace_id=f"trace-{self.rng.getrandbits(32):08x}",
                span_id=f"span-{self.rng.getrandbits(24):06x}"
            ))

        logs.append(LogRecord(
            timestamp=(t0 + timedelta(seconds=78)).isoformat(),
            service="api-gateway",
            level="WARN",
            message=f"HTTP 502/504 surge detected on route /checkout: 34 errors in last 30s"
        ))

        # 4. Optional background noise / unrelated logs
        if inject_noise:
            logs.append(LogRecord(
                timestamp=(t0 + timedelta(seconds=12)).isoformat(),
                service="auth-svc",
                level="WARN",
                message="User authentication failed: invalid refresh token for user_7718"
            ))
            logs.append(LogRecord(
                timestamp=(t0 + timedelta(seconds=35)).isoformat(),
                service="cache",
                level="INFO",
                message="Background key expiry sweeper cleaned 12 expired session keys"
            ))

        # Sort logs chronologically
        logs.sort(key=lambda l: l.timestamp)
        return logs

    def _generate_alerts(
        self, profile: Dict[str, Any], service_id: str, service_name: str,
        prop_path: List[str], t0: datetime
    ) -> List[SimulatedAlert]:
        alerts: List[SimulatedAlert] = []
        alert_t = t0 + timedelta(seconds=45)

        # Primary alert on root cause service
        alerts.append(SimulatedAlert(
            alert_id=f"ALT-{service_name}-01",
            service=service_name,
            name=f"{service_name} {profile['primary_symptom'].split(',')[0].strip()}",
            severity=profile["severity"],
            condition="sli_violation > 60s",
            fired_at=alert_t.isoformat(),
            value_observed=profile["metric_impact"]["error_rate_spike"],
            threshold=5.0
        ))

        # Cascaded alert on upstream checkout-svc
        if service_id != "checkout":
            alerts.append(SimulatedAlert(
                alert_id="ALT-checkout-svc-p95",
                service="checkout-svc",
                name="checkout-svc p95 latency above 1500ms",
                severity="Critical",
                condition="p95_latency > 1500ms for 45s",
                fired_at=(alert_t + timedelta(seconds=15)).isoformat(),
                value_observed=2150.0,
                threshold=1500.0
            ))
            alerts.append(SimulatedAlert(
                alert_id="ALT-checkout-svc-5xx",
                service="checkout-svc",
                name="checkout-svc 5xx error rate above 5%",
                severity="Critical",
                condition="error_rate > 5% for 30s",
                fired_at=(alert_t + timedelta(seconds=25)).isoformat(),
                value_observed=18.4,
                threshold=5.0
            ))

        # Edge gateway alert
        alerts.append(SimulatedAlert(
            alert_id="ALT-api-gateway-502",
            service="api-gateway",
            name="api-gateway upstream 502/504 Bad Gateway responses",
            severity="High",
            condition="502_rate > 50 in 1m",
            fired_at=(alert_t + timedelta(seconds=35)).isoformat(),
            value_observed=64.0,
            threshold=50.0
        ))

        return alerts

def generate_simulation(
    fault_type: str,
    target_service: Optional[str] = None,
    seed: int = 42,
    inject_noise: bool = False,
    missing_telemetry: Optional[str] = None
) -> SimulationRun:
    gen = TelemetryGenerator(seed=seed)
    return gen.generate(
        fault_type=fault_type,
        target_service=target_service,
        inject_noise=inject_noise,
        missing_telemetry=missing_telemetry
    )

