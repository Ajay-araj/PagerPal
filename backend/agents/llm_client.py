"""
backend/agents/llm_client.py
LLM client supporting Anthropic Claude structured outputs with transparent deterministic fallback.
Logs every call (agent, model, status) to the audit trail.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel

logger = logging.getLogger("pagerpal.llm")

# Check Anthropic API Key on module load
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_KEY:
    print("\n" + "!" * 80)
    print("WARNING: ANTHROPIC_API_KEY is not set in environment.")
    print("PagerPal is running in deterministic fallback mode.")
    print("All agent runs will be explicitly recorded in the audit trail as:")
    print("  'deterministic fallback (ANTHROPIC_API_KEY missing)'")
    print("!" * 80 + "\n")


class LLMClient:
    """Manages LLM invocations with Claude and structured deterministic fallbacks."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client: {e}")
                self.client = None

    def call_structured(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: Type[BaseModel],
        deterministic_fallback_fn
    ) -> Dict[str, Any]:
        """
        Calls Claude with structured output schema.
        Falls back to deterministic_fallback_fn if key is missing or call fails.
        Returns: {
            "result": BaseModel instance,
            "is_fallback": bool,
            "audit_note": str,
            "latency_ms": float,
            "status": "success" | "fallback" | "error"
        }
        """
        t0 = time.time()

        if not self.client:
            # Deterministic fallback mode
            fallback_res = deterministic_fallback_fn()
            latency = (time.time() - t0) * 1000
            return {
                "result": fallback_res,
                "is_fallback": True,
                "audit_note": "deterministic fallback (ANTHROPIC_API_KEY missing)",
                "latency_ms": round(latency, 2),
                "status": "fallback"
            }

        try:
            # Live Anthropic API call with tool calling for structured output
            schema_json = response_schema.model_json_schema()
            tool_definition = {
                "name": "submit_structured_assessment",
                "description": f"Submit structured response for {agent_name}",
                "input_schema": schema_json
            }

            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[tool_definition],
                tool_choice={"type": "tool", "name": "submit_structured_assessment"}
            )

            latency = (time.time() - t0) * 1000
            # Extract tool use block
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_structured_assessment":
                    parsed = response_schema.model_validate(block.input)
                    return {
                        "result": parsed,
                        "is_fallback": False,
                        "audit_note": f"Claude API call ({self.model_name}) succeeded",
                        "latency_ms": round(latency, 2),
                        "status": "success"
                    }

            # If no tool use found, fallback
            fallback_res = deterministic_fallback_fn()
            return {
                "result": fallback_res,
                "is_fallback": True,
                "audit_note": "deterministic fallback (unexpected model response format)",
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "status": "fallback"
            }

        except Exception as ex:
            latency = (time.time() - t0) * 1000
            logger.warning(f"Claude API call failed for {agent_name}: {ex}. Invoking deterministic fallback.")
            fallback_res = deterministic_fallback_fn()
            return {
                "result": fallback_res,
                "is_fallback": True,
                "audit_note": f"deterministic fallback (Claude API error: {str(ex)[:50]})",
                "latency_ms": round(latency, 2),
                "status": "fallback"
            }


# Global singleton
llm_client = LLMClient()

