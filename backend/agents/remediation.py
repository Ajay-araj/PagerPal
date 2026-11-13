"""
backend/agents/remediation.py
Remediation Agent: proposes reversible Level-2 remediation actions
strictly from the services.yaml action allowlist.
"""
from typing import Dict, Any
from backend.agents.schemas import RemediationProposalOutput
from backend.agents.prompts import REMEDIATION_SYSTEM_PROMPT
from backend.agents.llm_client import llm_client

FAULT_TO_ACTION_MAP = {
    "faulty_deployment": {
        "action": "rollback_deployment",
        "rollback_plan": "Re-enable canary release v2.4.1 if rollback fails",
        "expected_effect": "Revert payments-svc to previous stable container image v2.4.0",
        "risk_level": "Low"
    },
    "database_connection_failure": {
        "action": "reset_connection_pooler",
        "rollback_plan": "Restore original pool connection limits",
        "expected_effect": "Flush leaked connections and restart connection pooler on orders-db",
        "risk_level": "Low"
    },
    "db_connection_leak": {
        "action": "reset_connection_pooler",
        "rollback_plan": "Restore original pool connection limits",
        "expected_effect": "Flush leaked connections and restart connection pooler on orders-db",
        "risk_level": "Low"
    },
    "service_crash": {
        "action": "restart_service_container",
        "rollback_plan": "Scale deployment replicas back to 1",
        "expected_effect": "Drain failing pod and schedule clean replica with clean memory",
        "risk_level": "Low"
    },
    "service_crash_loop": {
        "action": "restart_service_container",
        "rollback_plan": "Scale deployment replicas back to 1",
        "expected_effect": "Drain failing pod and schedule clean replica with clean memory",
        "risk_level": "Low"
    },
    "network_latency": {
        "action": "shift_traffic_zone",
        "rollback_plan": "Re-apply traffic route if latency was synthetic",
        "expected_effect": "Shift traffic to healthy availability zone (us-east-1a)",
        "risk_level": "Low"
    },
    "network_partition_latency": {
        "action": "shift_traffic_zone",
        "rollback_plan": "Re-apply traffic route if latency was synthetic",
        "expected_effect": "Shift traffic to healthy availability zone (us-east-1a)",
        "risk_level": "Low"
    },
    "cpu_stress": {
        "action": "scale_service_replicas",
        "rollback_plan": "Resume nominal replica count",
        "expected_effect": "Scale service replicas and apply circuit breaker rate-limiting",
        "risk_level": "Low"
    },
    "cpu_saturation_stress": {
        "action": "scale_service_replicas",
        "rollback_plan": "Resume nominal replica count",
        "expected_effect": "Scale service replicas and apply circuit breaker rate-limiting",
        "risk_level": "Low"
    },
    "memory_stress": {
        "action": "flush_and_restart_cache",
        "rollback_plan": "Warm cache from read-replica datastore",
        "expected_effect": "Flush volatile keys and restart the cache node",
        "risk_level": "Low"
    },
    "memory_leak_oom": {
        "action": "flush_and_restart_cache",
        "rollback_plan": "Warm cache from read-replica datastore",
        "expected_effect": "Flush volatile keys and restart the cache node",
        "risk_level": "Low"
    }
}


def run_remediation(
    root_cause_service: str,
    fault_type: str,
    root_cause_summary: str
) -> Dict[str, Any]:
    """Generates a structured remediation proposal targeting root_cause_service."""
    default_rec = FAULT_TO_ACTION_MAP.get(fault_type, {
        "action": "restart_service_container",
        "rollback_plan": "Restore original pod container spec",
        "expected_effect": f"Restart {root_cause_service} container gracefully",
        "risk_level": "Low"
    })

    user_prompt = f"""Formulate a Level-2 reversible remediation proposal:
Root cause service: {root_cause_service}
Fault category: {fault_type}
Hypothesis: {root_cause_summary}
Action candidate: {default_rec['action']}
"""

    def deterministic_fallback():
        return RemediationProposalOutput(
            action=default_rec["action"],
            target_service=root_cause_service,
            risk_level=default_rec["risk_level"],
            is_reversible=True,
            timeout_seconds=120,
            rollback_plan=default_rec["rollback_plan"],
            expected_effect=default_rec["expected_effect"],
            policy_level="L2"
        )

    res = llm_client.call_structured(
        agent_name="Remediation",
        system_prompt=REMEDIATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=RemediationProposalOutput,
        deterministic_fallback_fn=deterministic_fallback
    )
    return res
