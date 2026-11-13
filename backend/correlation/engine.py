import networkx as nx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.schemas import SimulatedAlert, CorrelationResult
from backend.simulator.topology import topology

SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

class AlertCorrelationEngine:
    def __init__(self, window_sec: float = 90.0, max_hops: int = 2):
        self.window_sec = window_sec
        self.max_hops = max_hops
        # Undirected view for distance calculations
        self.undirected_g = topology.g.to_undirected()

    def correlate(self, alerts: List[SimulatedAlert], incident_id: str = "INC-auto") -> CorrelationResult:
        if not alerts:
            return CorrelationResult(
                incident_id=incident_id,
                incident_title="No active alerts",
                severity="Low",
                primary_service="none",
                alerts=[],
                total_alerts_received=0,
                dedup_count=0,
                services_involved=[],
                timespan_seconds=0.0,
                correlation_reason="Zero alerts received"
            )

        # 1. Parse timestamps and sort
        parsed_alerts = []
        for a in alerts:
            dt = self._parse_iso(a.fired_at)
            parsed_alerts.append((dt, a))
        parsed_alerts.sort(key=lambda x: x[0])

        # 2. Deduplication (same service + condition within 30s)
        deduped: List[SimulatedAlert] = []
        dedup_count = 0
        seen_keys: Dict[str, datetime] = {}

        for dt, alert in parsed_alerts:
            key = f"{alert.service}:{alert.name}"
            if key in seen_keys:
                last_dt = seen_keys[key]
                if abs((dt - last_dt).total_seconds()) <= 30.0:
                    dedup_count += 1
                    continue
            seen_keys[key] = dt
            deduped.append(alert)

        # 3. Analyze graph distance and temporal clustering
        earliest_dt = parsed_alerts[0][0]
        latest_dt = parsed_alerts[-1][0]
        timespan = max(1.0, round((latest_dt - earliest_dt).total_seconds(), 1))

        services_involved = list(dict.fromkeys(a.service for a in deduped))

        # Calculate max graph distance between services involved
        max_dist = 0
        service_ids = [topology._canonical_id(s) for s in services_involved]
        for i in range(len(service_ids)):
            for j in range(i + 1, len(service_ids)):
                u, v = service_ids[i], service_ids[j]
                if nx.has_path(self.undirected_g, u, v):
                    d = nx.shortest_path_length(self.undirected_g, u, v)
                    if d > max_dist:
                        max_dist = d

        # Highest severity
        highest_sev = "Low"
        for a in deduped:
            if SEVERITY_ORDER.get(a.severity, 0) > SEVERITY_ORDER.get(highest_sev, 0):
                highest_sev = a.severity

        # Identify symptom category
        all_text = " ".join([f"{a.name} {a.condition}" for a in deduped]).lower()
        symptom_cat = "performance and availability degradation"
        if "timeout" in all_text or "504" in all_text or "502" in all_text or "p95" in all_text:
            symptom_cat = "upstream timeout and latency cascade"
        elif "connection refused" in all_text or "max_connections" in all_text or "socket" in all_text:
            symptom_cat = "datastore connection pool exhaustion"
        elif "oom" in all_text or "crash" in all_text or "terminated" in all_text or "137" in all_text:
            symptom_cat = "pod container crash and restart loop"
        elif "cpu" in all_text or "queue" in all_text:
            symptom_cat = "thread queueing and CPU saturation"
        elif "eviction" in all_text or "memory" in all_text:
            symptom_cat = "memory pressure and cache key eviction churn"

        # Determine primary candidate service (deepest callee or highest error count)
        service_alert_counts: Dict[str, int] = {}
        for a in deduped:
            service_alert_counts[a.service] = service_alert_counts.get(a.service, 0) + 1

        primary_service = services_involved[0]
        # Prefer downstream dependencies over edge gateway
        for s_name in services_involved:
            canonical = topology._canonical_id(s_name)
            if canonical not in ["gateway", "checkout"]:
                primary_service = s_name
                break

        # Compute dynamic, explainable correlation reason
        reason = (
            f"Grouped {len(deduped)} alerts (deduplicated from {len(alerts)}) across "
            f"{len(services_involved)} services ({', '.join(services_involved)}) over a {timespan}s window. "
            f"Max topology distance is {max_dist} hop{'s' if max_dist != 1 else ''} along the service graph "
            f"with shared {symptom_cat}."
        )

        # Title
        incident_title = f"{primary_service} {highest_sev.lower()} incident ({symptom_cat})"

        return CorrelationResult(
            incident_id=incident_id,
            incident_title=incident_title,
            severity=highest_sev,
            primary_service=primary_service,
            alerts=deduped,
            total_alerts_received=len(alerts),
            dedup_count=dedup_count,
            services_involved=services_involved,
            timespan_seconds=timespan,
            correlation_reason=reason
        )

    def _parse_iso(self, ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)

correlation_engine = AlertCorrelationEngine()
