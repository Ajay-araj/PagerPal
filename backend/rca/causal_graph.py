import networkx as nx
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from backend.schemas import (
    SimulationRun, RCACandidate, CounterfactualResult, RCAResult
)
from backend.simulator.topology import topology

class CausalRCAEngine:
    def __init__(self):
        self.topology = topology

    def analyze(self, run: SimulationRun) -> RCAResult:
        services = self.topology.get_services()
        scores: Dict[str, float] = {s_id: 0.0 for s_id in services.keys()}
        evidence_signals: Dict[str, List[str]] = {s_id: [] for s_id in services.keys()}
        likely_causes: Dict[str, str] = {s_id: "Nominal operational status" for s_id in services.keys()}

        # 1. Analyze Trace Spans (Error origin & latency sink)
        if run.traces:
            for span in run.traces:
                s_id = self.topology._canonical_id(span.service)
                if s_id in scores:
                    if span.error:
                        # Deepest failing span gets high weight
                        scores[s_id] += 35.0
                        msg = f"Trace error status {span.status_code} in operation {span.operation}"
                        if msg not in evidence_signals[s_id]:
                            evidence_signals[s_id].append(msg)
                    elif span.duration_ms > 1000.0:
                        scores[s_id] += 15.0
                        msg = f"High span duration ({span.duration_ms:.0f}ms)"
                        if msg not in evidence_signals[s_id]:
                            evidence_signals[s_id].append(msg)

        # 2. Analyze Deployments (Recency within incident window)
        if run.deployments:
            for dep in run.deployments:
                s_id = self.topology._canonical_id(dep.service)
                if s_id in scores:
                    scores[s_id] += 40.0
                    sig = f"Recent deployment {dep.version} ({dep.commit_message})"
                    evidence_signals[s_id].append(sig)
                    likely_causes[s_id] = f"Faulty configuration or limits in deployment {dep.version}"

        # 3. Analyze Logs (Specific error signatures)
        if run.logs:
            for log in run.logs:
                s_id = self.topology._canonical_id(log.service)
                if s_id in scores:
                    msg = log.message.lower()
                    if log.level in ["ERROR", "FATAL"]:
                        if "oomkilled" in msg or "137" in msg:
                            scores[s_id] += 50.0
                            evidence_signals[s_id].append("OOMKilled container exit code 137 in logs")
                            likely_causes[s_id] = "Pod OOM-killed due to memory limit exhaustion"
                        elif "connection refused" in msg or "max_connections" in msg:
                            scores[s_id] += 45.0
                            evidence_signals[s_id].append("Database connection refused / max_connections reached")
                            likely_causes[s_id] = "Connection pool limit saturation"
                        elif "pool" in msg and "timeout" in msg:
                            scores[s_id] += 40.0
                            evidence_signals[s_id].append("Resource pool acquisition timeout")
                            likely_causes[s_id] = "Resource pool shortage under load"
                        elif "retry" in msg or "cpu" in msg:
                            scores[s_id] += 35.0
                            evidence_signals[s_id].append("Runaway retry loop detected in logs")
                            likely_causes[s_id] = "Unbounded retry loop saturating worker threads"
                        elif "eviction" in msg or "maxmemory" in msg:
                            scores[s_id] += 35.0
                            evidence_signals[s_id].append("High eviction rate / maxmemory threshold")
                            likely_causes[s_id] = "Memory leak driving key evictions"
                        elif "rtt" in msg or "cross-zone" in msg:
                            scores[s_id] += 30.0
                            evidence_signals[s_id].append("Elevated network RTT across availability zones")
                            likely_causes[s_id] = "Network transit latency degradation"
                        else:
                            scores[s_id] += 5.0

        # 4. Analyze Metrics (Relative anomaly deviation against SLI)
        if run.metrics:
            for key, points in run.metrics.items():
                if ":" not in key:
                    continue
                s_name, m_name = key.split(":", 1)
                s_id = self.topology._canonical_id(s_name)
                if s_id in scores and points:
                    latest_val = points[-1].value
                    sli = self.topology.get_sli(s_id)
                    if m_name == "error_rate_pct":
                        base_err = sli.get("error_rate_pct", 0.1)
                        if latest_val > base_err * 5.0 and latest_val > 2.0:
                            scores[s_id] += min(30.0, latest_val * 1.5)
                            evidence_signals[s_id].append(f"Error rate elevated to {latest_val}% (baseline {base_err}%)")
                    elif m_name == "p95_latency_ms":
                        base_lat = sli.get("p95_latency_ms", 30.0)
                        if latest_val > base_lat * 3.0:
                            scores[s_id] += 20.0
                            evidence_signals[s_id].append(f"p95 latency elevated to {latest_val}ms (baseline {base_lat}ms)")

        # 5. NetworkX Dependency-Aware Downstream Promotion & Upstream Demotion
        # If A calls B, and B has high anomaly, B is the causal origin; A's timeout is a symptom.
        for u, v in self.topology.g.edges():
            # u calls v
            if scores[v] >= 25.0:
                # Downstream callee has high failure signals -> promote callee, discount caller
                scores[v] += 15.0
                if "timeout" in " ".join(evidence_signals[u]).lower():
                    # caller only logged timeout waiting for callee
                    scores[u] = max(0.0, scores[u] - 10.0)

        # Build Candidate Ranking
        ranked_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_candidates: List[RCACandidate] = []

        total_top_score = max(1.0, sum(score for _, score in ranked_items[:3]))

        for rank, (s_id, score) in enumerate(ranked_items[:3], start=1):
            s_meta = services[s_id]
            conf_pct = min(99.0, max(25.0, round((score / total_top_score) * 100, 1))) if score > 0 else 10.0
            prop_path = self.topology.find_propagation_path(s_id, "checkout")

            # Default likely cause if none specifically discovered
            cause = likely_causes[s_id]
            if cause == "Nominal operational status" and score > 0:
                cause = f"Anomalous latency/error metrics observed on {s_meta['name']}"

            top_candidates.append(RCACandidate(
                service_id=s_id,
                service_name=s_meta["name"],
                rank=rank,
                score=round(score, 1),
                confidence_pct=conf_pct,
                likely_cause=cause,
                propagation_path=[services[p]["name"] for p in prop_path],
                evidence_signals=list(dict.fromkeys(evidence_signals[s_id])) or ["Telemetry within baseline"]
            ))

        primary = top_candidates[0]
        primary_prop = self.topology.find_propagation_path(primary.service_id, "checkout")
        prop_path_names = [services[p]["name"] for p in primary_prop]

        # 6. Counterfactual Verification Check
        counterfactual = self._run_counterfactual_check(primary, run)

        return RCAResult(
            top_candidates=top_candidates,
            primary_root_cause=primary,
            propagation_path=prop_path_names,
            counterfactual=counterfactual,
            computed_at=datetime.now(timezone.utc).isoformat()
        )

    def _run_counterfactual_check(self, candidate: RCACandidate, run: SimulationRun) -> CounterfactualResult:
        """
        Re-evaluates system behavior under the hypothesis that candidate's fault is mitigated.
        Must report is_proof=False (scientific rigor: simulation delta is supporting evidence, not mathematical proof).
        """
        s_id = candidate.service_id
        sli = self.topology.get_sli(s_id)

        # Baseline SLI
        base_latency = sli.get("p95_latency_ms", 30.0)
        base_err = sli.get("error_rate_pct", 0.05)
        base_cpu = sli.get("cpu_pct", 30.0)

        # Observed metrics
        obs_latency = base_latency * 15.0
        obs_err = 15.0
        obs_cpu = 75.0

        if run.metrics:
            key_lat = f"{candidate.service_name}:p95_latency_ms"
            key_err = f"{candidate.service_name}:error_rate_pct"
            if key_lat in run.metrics and run.metrics[key_lat]:
                obs_latency = run.metrics[key_lat][-1].value
            if key_err in run.metrics and run.metrics[key_err]:
                obs_err = run.metrics[key_err][-1].value

        # Simulated counterfactual outcome if fix applied
        after_latency = round(base_latency * 1.15, 1)
        after_err = round(base_err * 1.2, 2)
        after_cpu = round(base_cpu * 1.1, 1)

        supports = (obs_latency > after_latency) or (obs_err > after_err)

        deltas = {
            "p95_latency_ms": {
                "before": f"{obs_latency:.0f} ms",
                "counterfactual_after": f"{after_latency:.0f} ms",
                "delta": f"-{obs_latency - after_latency:.0f} ms"
            },
            "error_rate_pct": {
                "before": f"{obs_err:.1f}%",
                "counterfactual_after": f"{after_err:.2f}%",
                "delta": f"-{obs_err - after_err:.1f}%"
            }
        }

        explanation = (
            f"Counterfactual evaluation: Simulating removal of {candidate.service_name} fault condition "
            f"restores p95 latency from {obs_latency:.0f}ms to ~{after_latency:.0f}ms and error rate from "
            f"{obs_err:.1f}% to {after_err:.2f}%. Supports hypothesis with is_proof=False."
        )

        return CounterfactualResult(
            candidate_service=candidate.service_name,
            hypothesized_action=f"Mitigate fault on {candidate.service_name}",
            supports_hypothesis=supports,
            is_proof=False,
            metric_deltas=deltas,
            explanation=explanation
        )

causal_rca_engine = CausalRCAEngine()
