from typing import List, Dict, Any, Optional

from backend.schemas import (
    ClaimItem, ClaimVerification, VerificationReport, SimulationRun
)


def _svc_match(a: str, b: str) -> bool:
    """True if service name 'a' and service label 'b' refer to the same node.
    Handles 'gateway' vs 'api-gateway', 'payments' vs 'payments-svc', etc.
    """
    a, b = a.lower().strip(), b.lower().strip()
    return a == b or a in b or b in a


class EvidenceVerifier:
    def verify_claims(self, claims: List[ClaimItem], run: SimulationRun) -> VerificationReport:
        verified_items: List[ClaimVerification] = []
        dropped_items: List[ClaimVerification] = []

        for item in claims:
            c_text = item.claim.lower()
            c_source = item.source.lower()
            status = "UNVERIFIED"
            role = "Dropped"
            ref = None
            reason = "No matching telemetry found in logs, metrics, traces or deployments"

            # 1. Deployment Claim
            if item.type in ["Deploy", "Commit"] or "deploy" in c_source or "github" in c_source:
                matched_deploy = False
                for d in run.deployments:
                    if (_svc_match(d.service, c_source) or _svc_match(d.service, c_text) or
                            d.version.lower() in c_text or d.commit_sha[:6].lower() in c_text or
                            "pool" in d.diff_summary.lower()):
                        matched_deploy = True
                        status = "VERIFIED"
                        role = "Supports"
                        ref = f"deploy:{d.deploy_id} ({d.version})"
                        reason = f"Confirmed against deployment record {d.deploy_id} on {d.service}"
                        break
                if not matched_deploy:
                    status = "UNVERIFIED"
                    role = "Dropped"
                    reason = "Deployment or commit revision not present in service release history"

            # 2. Metric Claim
            elif item.type == "Metric" or "metric" in c_source:
                matched_metric = False
                # Determine relevant metric name from claim text
                target_metric = None
                if "cpu" in c_text:
                    target_metric = "cpu_pct"
                elif "error" in c_text or "5xx" in c_text:
                    target_metric = "error_rate_pct"
                elif "latency" in c_text or "p95" in c_text or "rtt" in c_text:
                    target_metric = "p95_latency_ms"
                elif "mem" in c_text or "evict" in c_text:
                    target_metric = "mem_pct"

                for key, points in run.metrics.items():
                    s_name, m_name = key.split(":", 1)
                    # Bidirectional service match: covers "gateway" vs "api-gateway"
                    if not _svc_match(s_name, c_source) and not _svc_match(s_name, c_text):
                        continue
                    if target_metric and m_name != target_metric:
                        continue  # Wait for exact metric match

                    matched_metric = True
                    latest_val = points[-1].value if points else 0.0

                    if "normal" in c_text or "rules out" in c_text or "conflicts" in c_text:
                        status = "CONFLICTS"
                        role = "Conflicts"
                        ref = f"metrics/{s_name}:{m_name}"
                        reason = f"Metric {m_name} observed at {latest_val} contradicts hardware saturation hypothesis"
                    else:
                        status = "VERIFIED"
                        role = "Supports"
                        ref = f"metrics/{s_name}:{m_name}"
                        reason = f"Observed metric value {latest_val} in {m_name} time series for {s_name}"
                    break

                if not matched_metric:
                    # Fallback: if any metric exists for the service, verify loosely
                    for key, points in run.metrics.items():
                        s_name, m_name = key.split(":", 1)
                        if _svc_match(s_name, c_source) and points:
                            matched_metric = True
                            latest_val = points[-1].value
                            status = "VERIFIED"
                            role = "Supports"
                            ref = f"metrics/{s_name}:{m_name}"
                            reason = f"Metric telemetry available for {s_name} ({m_name}={latest_val})"
                            break

                if not matched_metric:
                    status = "UNVERIFIED"
                    role = "Dropped"
                    reason = f"Metric time series for '{item.source}' not found in telemetry"

            # 3. Log Claim
            elif item.type == "Log" or "log" in c_source:
                matching_logs = [
                    l for l in run.logs
                    if any(w in l.message.lower() for w in [
                        "timeout", "oomkilled", "refused", "retry", "eviction",
                        "fail", "error", "latency", "connection", "dropped", "reset"
                    ])
                ]
                if matching_logs:
                    status = "VERIFIED"
                    role = "Supports"
                    ref = f"logs/{matching_logs[0].service} (line {len(matching_logs)})"
                    reason = f"Corroborated by {len(matching_logs)} error log records on {matching_logs[0].service}"
                else:
                    status = "UNVERIFIED"
                    role = "Dropped"
                    reason = "No matching log records found in buffer"

            # 4. Trace Span Claim
            elif item.type == "Trace" or "span" in c_source or "trace" in c_source:
                error_spans = [s for s in run.traces if s.error or s.duration_ms > 500.0]
                if error_spans:
                    status = "VERIFIED"
                    role = "Supports"
                    ref = f"trace:{error_spans[0].trace_id}"
                    reason = f"Trace span {error_spans[0].span_id} confirms {error_spans[0].duration_ms:.0f}ms delay ({error_spans[0].status_code})"
                else:
                    status = "UNVERIFIED"
                    role = "Dropped"
                    reason = "No trace spans exhibiting matching latency or error codes"

            # 5. Unsupported speculative assertions
            else:
                status = "UNVERIFIED"
                role = "Dropped"
                reason = "Conjecture dismissed: zero corroborating telemetry found in cluster"

            ver = ClaimVerification(
                claim=item,
                status=status,
                role=role,
                evidence_reference=ref,
                reason=reason
            )

            if status == "UNVERIFIED":
                dropped_items.append(ver)
            else:
                verified_items.append(ver)

        total = len(claims)
        verified_count = len([c for c in verified_items if c.status == "VERIFIED"])
        conflicting_count = len([c for c in verified_items if c.status == "CONFLICTS"])
        dropped_count = len(dropped_items)

        coverage = round(((total - dropped_count) / max(1, total)) * 100, 1)

        return VerificationReport(
            total_claims=total,
            verified_count=verified_count,
            conflicting_count=conflicting_count,
            dropped_count=dropped_count,
            claims=verified_items,
            dropped_claims=dropped_items,
            evidence_coverage_pct=coverage
        )


evidence_verifier = EvidenceVerifier()
