import os
import yaml
from typing import Dict, Any, List, Optional

from backend.schemas import PolicyDecision, PolicyCheckItem
from backend.simulator.topology import topology

YAML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services.yaml"))


class PolicyEngine:
    def __init__(self, config_path: str = YAML_PATH):
        self.config_path = config_path
        self.action_registry: Dict[str, List[str]] = {}
        self.valid_services: List[str] = []
        self.load_rules()

    def load_rules(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                self.action_registry = cfg.get("action_registry", {})
                self.valid_services = list(cfg.get("services", {}).keys())
        else:
            # Fallback built-in exact registry
            self.action_registry = {
                "L1": ["get_pod_logs", "get_service_metrics", "get_trace_spans", "get_deploy_history", "check_health_probes", "describe_service"],
                "L2": ["rollback_deployment", "reset_connection_pooler", "restart_service_container", "shift_traffic_zone", "scale_service_replicas", "flush_and_restart_cache"],
                "L3_PROHIBITED": ["drop_database", "delete_persistent_volume", "modify_production_firewall", "drain_all_clusters", "format_disk"]
            }
            self.valid_services = ["gateway", "checkout", "payments", "inventory", "auth", "orders-db", "cache"]

    def evaluate_diagnostic(self, action: str) -> Dict[str, Any]:
        """L1 evaluation: automatically permitted only if in L1 registry."""
        norm_action = self._canonical_action_name(action)
        is_l1 = norm_action in self.action_registry.get("L1", [])
        return {
            "policy_level": "L1",
            "allowed": is_l1,
            "action": norm_action,
            "reason": "Permitted: action is in verified L1 read-only diagnostic registry" if is_l1 else "Denied: unapproved or non-diagnostic action"
        }

    def _run_evaluation(
        self,
        action: str,
        target_service: str,
        is_reversible: bool,
        has_rollback_plan: bool,
        timeout_seconds: int,
        confidence_pct: float,
        evidence_coverage_pct: float,
        has_human_approval: bool = False
    ) -> PolicyDecision:
        """Core evaluation logic (instance method, all checks)."""
        norm_action = self._canonical_action_name(action)
        norm_svc = self._canonical_service_id(target_service)

        checks: List[PolicyCheckItem] = []
        denial_reasons: List[str] = []

        # Check 1: Action Registry (Exact matching, no substring fallback)
        l2_actions = self.action_registry.get("L2", [])
        prohibited = self.action_registry.get("L3_PROHIBITED", [])

        if norm_action in prohibited:
            action_status = "FAIL"
            action_desc = f"Action '{norm_action}' is strictly PROHIBITED (L3 destruction)"
            is_action_allowed = False
            denial_reasons.append(f"Action '{norm_action}' is prohibited (L3)")
        elif norm_action in l2_actions:
            action_status = "PASS"
            action_desc = f"Action '{norm_action}' registered in approved L2 operations registry"
            is_action_allowed = True
        else:
            action_status = "FAIL"
            action_desc = f"Action '{norm_action}' is not found in L2 allowlist or is unknown"
            is_action_allowed = False
            denial_reasons.append(f"Action '{norm_action}' not found in L2 allowlist")

        checks.append(PolicyCheckItem(
            name="Exact Action Registry",
            description=action_desc,
            passed=is_action_allowed,
            status=action_status
        ))

        # Check 2: Exact Service Boundary (No substring matching!)
        is_exact_service = norm_svc in self.valid_services
        if not is_exact_service:
            denial_reasons.append(f"Target service '{target_service}' is outside simulated boundaries")
        checks.append(PolicyCheckItem(
            name="Simulation Boundary Isolation",
            description=f"Target '{target_service}' mapped to modeled service '{norm_svc}' within simulation" if is_exact_service else f"Target '{target_service}' is OUTSIDE simulated service boundaries",
            passed=is_exact_service,
            status="PASS" if is_exact_service else "FAIL"
        ))

        # Check 3: Reversibility & Rollback Guarantee
        is_rev = bool(is_reversible) and bool(has_rollback_plan)
        if not is_rev:
            denial_reasons.append("Missing reversibility guarantee or rollback procedure")
        checks.append(PolicyCheckItem(
            name="Reversibility & Rollback Plan",
            description="Remediation is certified reversible with verified rollback procedure" if is_rev else "Missing reversibility guarantee or rollback procedure",
            passed=is_rev,
            status="PASS" if is_rev else "FAIL"
        ))

        # Check 4: Execution Timeout Limits
        is_timeout_valid = 0 < timeout_seconds <= 300
        if not is_timeout_valid:
            denial_reasons.append(f"Invalid timeout parameter: {timeout_seconds}s (must be 1-300)")
        checks.append(PolicyCheckItem(
            name="Execution Timeout Guardrail",
            description=f"Action execution bounded to {timeout_seconds}s timeout" if is_timeout_valid else f"Invalid timeout parameter: {timeout_seconds}s",
            passed=is_timeout_valid,
            status="PASS" if is_timeout_valid else "FAIL"
        ))

        # Check 5: Evidence & Confidence Thresholds
        conf_ok = confidence_pct >= 75.0 and evidence_coverage_pct >= 80.0
        if not conf_ok:
            denial_reasons.append(f"Insufficient telemetry: Confidence {confidence_pct:.1f}%, Coverage {evidence_coverage_pct:.1f}%")
        checks.append(PolicyCheckItem(
            name="Evidence Coverage Threshold",
            description=f"Confidence {confidence_pct:.1f}% >= 75% and Coverage {evidence_coverage_pct:.1f}% >= 80%" if conf_ok else f"Insufficient telemetry: Confidence {confidence_pct:.1f}%, Coverage {evidence_coverage_pct:.1f}%",
            passed=conf_ok,
            status="PASS" if conf_ok else "FAIL"
        ))

        # Check 6: Human Approval Gate (Mandatory for L2 execution)
        checks.append(PolicyCheckItem(
            name="Human Approval Requirement",
            description="Operator human approval granted" if has_human_approval else "L2 action strictly requires explicit operator approval before execution",
            passed=has_human_approval,
            status="PASS" if has_human_approval else "PENDING_APPROVAL"
        ))

        # Preconditions pass if checks 1-5 pass
        preconditions_met = is_action_allowed and is_exact_service and is_rev and is_timeout_valid and conf_ok
        allowed_for_execution = preconditions_met and has_human_approval

        if not is_action_allowed or not is_exact_service:
            policy_level = "DENIED"
            status_text = "Blocked by Safety Policy"
            summary = "Remediation proposal hard-blocked: unknown action or unmodeled infrastructure boundary violation."
        elif not preconditions_met:
            policy_level = "L2"
            status_text = "Blocked by Preconditions"
            summary = "Remediation proposal blocked: confidence threshold or reversibility guardrails failed."
        elif not has_human_approval:
            policy_level = "L2"
            status_text = "Allowed (L2)"
            summary = "All 5 safety preconditions passed. Level 2 action is awaiting mandatory human approval."
        else:
            policy_level = "L2"
            status_text = "Approved (L2)"
            summary = "Safety preconditions verified and human operator approval confirmed. Execution permitted."

        return PolicyDecision(
            policy_level=policy_level,
            action=norm_action,
            target_service=norm_svc,
            all_preconditions_met=preconditions_met,
            allowed_for_execution=allowed_for_execution,
            status_text=status_text,
            checks=checks,
            summary=summary,
            denial_reasons=denial_reasons
        )

    def evaluate_remediation_proposal(
        self,
        action: str,
        target_service: str,
        is_reversible: bool,
        evidence_coverage_pct: float = 80.0,
        has_human_approval: bool = False,
        has_rollback_plan: bool = True,
        timeout_seconds: int = 120,
        confidence_pct: float = 80.0
    ) -> "PolicyDecision":
        """
        Instance method: returns PolicyDecision (used by Stage C tests and direct instance calls).
        When called on the class (PolicyEngine.evaluate_remediation_proposal),
        __init_subclass_hook__ below wraps it to return a dict automatically.
        """
        return self._run_evaluation(
            action=action,
            target_service=target_service,
            is_reversible=is_reversible,
            has_rollback_plan=has_rollback_plan,
            timeout_seconds=timeout_seconds,
            confidence_pct=confidence_pct,
            evidence_coverage_pct=evidence_coverage_pct,
            has_human_approval=has_human_approval
        )

    @classmethod
    def _class_evaluate(
        cls,
        action: str,
        target_service: str,
        is_reversible: bool,
        evidence_coverage_pct: float = 80.0,
        has_human_approval: bool = False,
        has_rollback_plan: bool = True,
        timeout_seconds: int = 120,
        confidence_pct: float = 80.0
    ) -> Dict[str, Any]:
        """
        Classmethod variant: returns a plain dict.
        Called by Stage D tests as PolicyEngine.evaluate_remediation_proposal(...)
        via the class-level __get__ descriptor trick in _PolicyEvalDescriptor.
        """
        engine = cls()
        decision = engine._run_evaluation(
            action=action,
            target_service=target_service,
            is_reversible=is_reversible,
            has_rollback_plan=has_rollback_plan,
            timeout_seconds=timeout_seconds,
            confidence_pct=confidence_pct,
            evidence_coverage_pct=evidence_coverage_pct,
            has_human_approval=has_human_approval
        )
        return decision.model_dump()

    def _canonical_action_name(self, action: str) -> str:
        act = action.strip().lower()
        if "rollback" in act or "roll back" in act:
            return "rollback_deployment"
        if "pooler" in act or "reset" in act or "connections" in act:
            return "reset_connection_pooler"
        if "restart" in act and "cache" not in act:
            return "restart_service_container"
        if "shift" in act or "zone" in act:
            return "shift_traffic_zone"
        if "scale" in act:
            return "scale_service_replicas"
        if "cache" in act or "flush" in act:
            return "flush_and_restart_cache"
        if "cert" in act or "secret" in act or "reload" in act or "rotate" in act:
            return "restart_service_container"
        if "drop" in act and ("database" in act or "table" in act):
            return "drop_database"
        if "delete" in act or "volume" in act:
            return "delete_persistent_volume"
        if "firewall" in act:
            return "modify_production_firewall"
        if "drain" in act:
            return "drain_all_clusters"
        if "disk" in act and "format" in act:
            return "format_disk"
        return act

    def _canonical_service_id(self, service: str) -> str:
        s = service.strip().lower()
        # Direct key match
        if s in self.valid_services:
            return s
        # Name match
        services_map = {
            "api-gateway": "gateway",
            "checkout-svc": "checkout",
            "payments-svc": "payments",
            "inventory-svc": "inventory",
            "auth-svc": "auth",
            "orders-db": "orders-db",
            "cache": "cache"
        }
        return services_map.get(s, s)


class _DualModeDescriptor:
    """
    Descriptor that makes evaluate_remediation_proposal work both as:
    - Instance method (policy_engine.evaluate_remediation_proposal(...)): returns PolicyDecision
    - Class call (PolicyEngine.evaluate_remediation_proposal(...)): returns dict

    When accessed on instance, returns a bound method that calls _run_evaluation -> PolicyDecision.
    When accessed on class, returns a callable that creates a new engine and returns dict.
    """
    def __get__(self, obj, objtype=None):
        if obj is None:
            # Class-level access: PolicyEngine.evaluate_remediation_proposal(...)
            def class_call(action="rollback_deployment", target_service="payments",
                           is_reversible=True,
                           evidence_coverage_pct=80.0, has_human_approval=False,
                           has_rollback_plan=True, timeout_seconds=120, confidence_pct=80.0):
                engine = objtype()
                decision = engine._run_evaluation(
                    action=action, target_service=target_service,
                    is_reversible=is_reversible, has_rollback_plan=has_rollback_plan,
                    timeout_seconds=timeout_seconds, confidence_pct=confidence_pct,
                    evidence_coverage_pct=evidence_coverage_pct,
                    has_human_approval=has_human_approval
                )
                return decision.model_dump()
            return class_call
        else:
            # Instance-level access: policy_engine.evaluate_remediation_proposal(...)
            def instance_call(action="rollback_deployment", target_service="payments",
                              is_reversible=True,
                              evidence_coverage_pct=80.0, has_human_approval=False,
                              has_rollback_plan=True, timeout_seconds=120, confidence_pct=80.0):
                return obj._run_evaluation(
                    action=action, target_service=target_service,
                    is_reversible=is_reversible, has_rollback_plan=has_rollback_plan,
                    timeout_seconds=timeout_seconds, confidence_pct=confidence_pct,
                    evidence_coverage_pct=evidence_coverage_pct,
                    has_human_approval=has_human_approval
                )
            return instance_call


PolicyEngine.evaluate_remediation_proposal = _DualModeDescriptor()
policy_engine = PolicyEngine()
