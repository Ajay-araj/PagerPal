"""
backend/agents/triage.py
Triage Agent: computes severity, checkout success rate, and orders at risk from telemetry.
"""
from typing import Dict, Any, List
from backend.schemas import SimulationRun
from backend.agents.schemas import TriageAssessment
from backend.agents.prompts import TRIAGE_SYSTEM_PROMPT, wrap_untrusted_telemetry
from backend.agents.llm_client import llm_client


def run_triage(
    run: SimulationRun,
    correlated_alerts: List[Dict[str, Any]],
    nominal_orders: int = 100
) -> Dict[str, Any]:
    """
    Computes business impact:
    simulated_orders_at_risk = round(nominal_orders * (1 - success_rate/100))
    """
    # 1. Determine checkout / gateway error rate
    max_err = 0.0
    if run.metrics:
        for key, points in run.metrics.items():
            if ("checkout" in key.lower() or "gateway" in key.lower()) and "error_rate_pct" in key:
                if points:
                    max_err = max(max_err, max(p.value for p in points))

    success_rate = round(max(0.0, min(100.0, 100.0 - max_err)), 1)
    orders_at_risk = round(nominal_orders * (1.0 - (success_rate / 100.0)))

    # 2. Determine severity
    if success_rate < 85.0 or max_err >= 15.0:
        severity = "Critical"
    elif success_rate < 95.0 or max_err >= 5.0:
        severity = "High"
    else:
        severity = "Medium"

    # 3. Determine blast radius
    alert_services = list({a.get("service") for a in correlated_alerts if a.get("service")})
    if "checkout" not in alert_services and max_err > 0.0:
        alert_services.append("checkout")

    telemetry_summary = (
        f"Correlated alerts: {len(correlated_alerts)}. Services alerting: {alert_services}. "
        f"Observed user-facing error rate: {max_err:.1f}%. "
        f"Calculated checkout success: {success_rate}%. "
        f"Simulated orders at risk: ~{orders_at_risk} orders/min (simulated estimate)."
    )

    user_prompt = f"""Assess the business impact and severity based on current alerts:
{wrap_untrusted_telemetry(telemetry_summary)}
Provide structured TriageAssessment.
"""

    def deterministic_fallback():
        return TriageAssessment(
            severity=severity,
            nominal_orders_per_min=nominal_orders,
            orders_at_risk=orders_at_risk,
            checkout_success_pct=success_rate,
            blast_radius=alert_services,
            summary=f"Severity {severity}: {telemetry_summary}"
        )

    res = llm_client.call_structured(
        agent_name="Triage",
        system_prompt=TRIAGE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=TriageAssessment,
        deterministic_fallback_fn=deterministic_fallback
    )
    return res
