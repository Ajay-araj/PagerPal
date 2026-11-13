"""
backend/agents/investigator.py
Investigator Agent: queries observability telemetry via allowlisted tools
and produces factual empirical claims. Supports verifier retry loop.
"""
from typing import Dict, Any, List, Optional
from backend.schemas import SimulationRun
from backend.agents.tools import IncidentToolExecutor
from backend.agents.schemas import InvestigatorFindings, ClaimItem
from backend.agents.prompts import INVESTIGATOR_SYSTEM_PROMPT, wrap_untrusted_telemetry
from backend.agents.llm_client import llm_client


def run_investigator(
    run: SimulationRun,
    candidate_service: str,
    retry_feedback: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes allowlisted diagnostic queries for the candidate service and upstream dependencies.
    Produces structured claims for the Evidence Verifier.
    """
    executor = IncidentToolExecutor(run)

    # 1. Query telemetry for suspect service
    logs = executor.get_pod_logs(candidate_service, limit=15)
    metrics = executor.get_service_metrics(candidate_service)
    traces = executor.get_trace_spans(candidate_service, limit=10)
    deploys = executor.get_deploy_history(candidate_service)
    health = executor.check_health_probes(candidate_service)

    # Telemetry summary
    err_rate = 0.0
    lat_val = 0.0
    if "error_rate_pct" in metrics.get("metrics", {}):
        err_rate = metrics["metrics"]["error_rate_pct"]["latest_value"] or 0.0
    if "p95_latency_ms" in metrics.get("metrics", {}):
        lat_val = metrics["metrics"]["p95_latency_ms"]["latest_value"] or 0.0

    telemetry_summary = (
        f"Service: {candidate_service}. Logs retrieved: {logs['log_count']}. "
        f"p95 latency: {lat_val:.1f}ms, error_rate: {err_rate:.1f}%. "
        f"Recent deploys: {len(deploys['deployments'])}. Health status: {health['status']}."
    )

    user_prompt = f"""Investigate service '{candidate_service}' using retrieved telemetry:
{wrap_untrusted_telemetry(telemetry_summary)}
"""
    if retry_feedback:
        user_prompt += f"\nPrevious verification feedback (adjust claims): {retry_feedback}\n"

    def deterministic_fallback():
        claims = []
        # Add metric claim
        if err_rate > 1.0:
            claims.append(ClaimItem(
                claim_text=f"error_rate_pct elevated at {err_rate:.1f}%",
                source_type="metric",
                service=candidate_service,
                expected_direction="increase"
            ))
        if lat_val > 100.0:
            claims.append(ClaimItem(
                claim_text=f"p95_latency_ms elevated at {lat_val:.1f}ms",
                source_type="metric",
                service=candidate_service,
                expected_direction="increase"
            ))

        # Add deploy claim if recent deploy
        if deploys["deployments"]:
            latest_d = deploys["deployments"][0]
            claims.append(ClaimItem(
                claim_text=f"Recent deployment of {latest_d['version']} (commit {latest_d['commit_sha'][:7]})",
                source_type="deploy",
                service=candidate_service
            ))

        # Add log claim from error logs
        err_logs = [l for l in logs["logs"] if l["level"] in ["ERROR", "CRITICAL"]]
        if err_logs:
            claims.append(ClaimItem(
                claim_text=f"Log errors detected: '{err_logs[0]['message'][:60]}'",
                source_type="log",
                service=candidate_service
            ))

        # Add trace claim if error spans exist
        err_spans = [s for s in traces["spans"] if s["error"]]
        if err_spans:
            status_code = err_spans[0].get("status_code", err_spans[0].get("http_status", 500))
            claims.append(ClaimItem(
                claim_text=f"Trace spans returning HTTP {status_code}",
                source_type="trace",
                service=candidate_service
            ))

        return InvestigatorFindings(
            suspected_service=candidate_service,
            claims=claims,
            evidence_sources_queried=["logs", "metrics", "traces", "deploys", "health_probes"],
            telemetry_summary=telemetry_summary
        )

    res = llm_client.call_structured(
        agent_name="Investigator",
        system_prompt=INVESTIGATOR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=InvestigatorFindings,
        deterministic_fallback_fn=deterministic_fallback
    )
    return res
