"""
backend/agents/supervisor.py
Supervisor Agent: plans and coordinates the multi-agent incident workflow.
"""
from typing import Dict, Any
from backend.agents.schemas import SupervisorPlan
from backend.agents.prompts import SUPERVISOR_SYSTEM_PROMPT
from backend.agents.llm_client import llm_client


def run_supervisor(incident_id: str, scenario_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generates structured supervisor workflow plan."""
    user_prompt = f"""An incident has been detected on PagerPal:
Incident ID: {incident_id}
Scenario: {scenario_info.get('name', 'Unknown')}
Affected Service: {scenario_info.get('svc_name', 'Unknown')}
Generate an execution plan coordinating Triage, Investigator, Causal RCA, Evidence Verifier, Remediation, and Comms.
"""

    def deterministic_fallback():
        return SupervisorPlan(
            workflow_steps=[
                "Triage",
                "Investigator",
                "Causal RCA",
                "Evidence Verifier",
                "Remediation",
                "Comms"
            ],
            rationale=(
                f"Autonomous incident workflow for {incident_id}: "
                f"Triage assesses blast radius -> Investigator queries telemetry -> "
                f"Causal RCA traces propagation -> Verifier validates claims -> "
                f"Remediation formulates L2 proposal -> Comms archives postmortem."
            )
        )

    res = llm_client.call_structured(
        agent_name="Supervisor",
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=SupervisorPlan,
        deterministic_fallback_fn=deterministic_fallback
    )
    return res

