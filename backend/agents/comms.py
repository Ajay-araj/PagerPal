"""
backend/agents/comms.py
Comms Agent: drafts status notifications and postmortem summaries without emojis.
"""
from typing import Dict, Any
from backend.agents.schemas import CommsUpdate
from backend.agents.prompts import COMMS_SYSTEM_PROMPT
from backend.agents.llm_client import llm_client


def run_comms(
    incident_id: str,
    service: str,
    severity: str,
    status: str,
    root_cause: str,
    action_taken: str
) -> Dict[str, Any]:
    """Generates an emoji-free status update for stakeholders."""
    user_prompt = f"""Draft an incident communication:
Incident ID: {incident_id}
Affected Service: {service}
Severity: {severity}
Status: {status}
Root Cause: {root_cause}
Remediation: {action_taken}
Enforce: strictly NO emojis anywhere in the text.
"""

    def deterministic_fallback():
        headline = f"[PagerPal {status.upper()}] {incident_id}: {service} degradation"
        summary = (
            f"Incident {incident_id} ({severity}) affecting service '{service}'. "
            f"Identified root cause: {root_cause}. "
            f"Executed remediation: {action_taken}. "
            f"Current status: {status}."
        )
        return CommsUpdate(
            headline=headline,
            affected_service=service,
            severity=severity,
            current_status=status,
            summary=summary,
            next_action="Continue observability monitoring and review automated postmortem."
        )

    res = llm_client.call_structured(
        agent_name="Comms",
        system_prompt=COMMS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=CommsUpdate,
        deterministic_fallback_fn=deterministic_fallback
    )
    return res

