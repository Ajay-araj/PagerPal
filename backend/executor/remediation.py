"""
backend/executor/remediation.py
Simulated remediation executor and emergency rollback handler.
Mutates the active simulation state and registers rollback handlers.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class RemediationExecutor:
    """Executes simulated L2 remediation actions and manages emergency rollback."""

    def __init__(self):
        self.last_action: Optional[Dict[str, Any]] = None
        self.is_rolled_back: bool = False

    def execute_action(
        self,
        action: str,
        target_service: str,
        rollback_plan: str,
        sim_run_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes the simulated remediation on the target service.
        Mutates sim_run_data to reflect remediated state.
        """
        self.last_action = {
            "action": action,
            "target_service": target_service,
            "rollback_plan": rollback_plan,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
        self.is_rolled_back = False

        # Apply simulated resolution to telemetry state
        # Nominal baseline levels
        remediated_metrics = {
            "p95_latency_ms": 12.5,
            "error_rate_pct": 0.05,
            "cpu_pct": 24.0,
            "memory_pct": 38.0
        }

        # Check if the remediation matches the root cause fault
        ground_truth_fault = sim_run_data.get("fault_type", "")
        ground_truth_svc = sim_run_data.get("root_cause_service", "")

        # A remediation is effective if it targets the root cause service
        # and corresponds to the fault type
        is_effective = (target_service == ground_truth_svc)

        if not is_effective:
            # Remediation on wrong service does NOT normalize metrics
            remediated_metrics["error_rate_pct"] = sim_run_data.get("current_error_rate", 18.5)
            remediated_metrics["p95_latency_ms"] = sim_run_data.get("current_latency", 620.0)

        sim_run_data["is_remediated"] = is_effective
        sim_run_data["remediated_metrics"] = remediated_metrics

        return {
            "status": "success",
            "action": action,
            "target_service": target_service,
            "is_effective": is_effective,
            "remediated_metrics": remediated_metrics,
            "executed_at": self.last_action["executed_at"]
        }

    def emergency_rollback(self, sim_run_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the registered rollback plan, restoring previous configuration
        and marking simulation state as rolled_back.
        """
        if not self.last_action:
            rollback_action = "default_restore_previous_state"
            target_svc = "system"
        else:
            rollback_action = self.last_action.get("rollback_plan", "restore_previous_spec")
            target_svc = self.last_action.get("target_service", "system")

        self.is_rolled_back = True
        sim_run_data["is_remediated"] = False
        sim_run_data["status"] = "rolled_back"
        sim_run_data["phase"] = "stopped"

        return {
            "status": "rolled_back",
            "rollback_action": rollback_action,
            "target_service": target_svc,
            "rolled_back_at": datetime.now(timezone.utc).isoformat()
        }


# Global singleton
remediation_executor = RemediationExecutor()

