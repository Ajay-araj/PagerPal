from typing import Dict, Any, List, Tuple

# Approved actions allowlist for simulation
ALLOWLIST_ACTIONS = [
    "rollback",
    "restart",
    "scale",
    "flush",
    "shift_traffic",
    "roll back payments-svc to v3.8.0",
    "restart connection pooler & cycle idle connections",
    "restart inventory-svc with previous memory limit (1024mb)",
    "shift traffic to healthy availability zone (us-east-1a)",
    "scale checkout-svc to 6 replicas & apply circuit breaker rate-limiting",
    "flush volatile keys and restart the cache node"
]

SIMULATED_SERVICES_ALLOWLIST = [
    "api-gateway", "checkout-svc", "payments-svc", "inventory-svc", 
    "auth-svc", "orders-db", "cache", "gateway", "checkout", "payments", "inventory", "auth"
]

class PolicyEngine:
    """
    Independent Rule-Based Safety Authority.
    Does not rely on LLM for safety decisions.
    """

    @classmethod
    def evaluate_remediation_proposal(
        cls,
        action: str,
        target_service: str,
        is_reversible: bool,
        evidence_coverage_pct: float,
        has_human_approval: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates an L2 remediation proposal against strict safety rules.
        """
        checks: List[Dict[str, Any]] = []

        # 1. Allowlist Check
        clean_action = action.strip().lower()
        allowed_keywords = ["rollback", "roll back", "restart", "scale", "flush", "shift", "revert", "cycle", "rotate", "vacuum"]
        is_allowed = any(kw in clean_action for kw in allowed_keywords)
        checks.append({
            "name": "Action Allowlist",
            "description": "Proposed action matches safe operational runbook allowlist",
            "passed": is_allowed,
            "status": "PASS" if is_allowed else "FAIL"
        })

        # 2. Reversibility Check
        checks.append({
            "name": "Reversibility Guarantee",
            "description": "Action is strictly reversible with defined rollback plan",
            "passed": bool(is_reversible),
            "status": "PASS" if is_reversible else "FAIL"
        })

        # 3. Environment Boundary Check
        clean_svc = target_service.strip().lower()
        in_sim = any(clean_svc in s for s in SIMULATED_SERVICES_ALLOWLIST)
        checks.append({
            "name": "Simulation Boundary",
            "description": "Target is isolated within simulated environment (no prod access)",
            "passed": in_sim,
            "status": "PASS" if in_sim else "FAIL"
        })

        # 4. Evidence Coverage Check (Min 80%)
        cov_pass = evidence_coverage_pct >= 80.0
        checks.append({
            "name": "Evidence Coverage Threshold",
            "description": f"Diagnostic evidence coverage at least 80% (measured {evidence_coverage_pct:.0f}%)",
            "passed": cov_pass,
            "status": "PASS" if cov_pass else "FAIL"
        })

        # 5. Human Approval Requirement (L2)
        checks.append({
            "name": "Human Approval Requirement",
            "description": "L2 remediation requires explicit operator approval before execution",
            "passed": bool(has_human_approval),
            "status": "PASS" if has_human_approval else "PENDING_APPROVAL"
        })

        # Overall policy result:
        # Pre-execution policy check (before approval): checks 1-4 must pass.
        # Execution policy check: all 5 checks must pass.
        all_preconditions_met = is_allowed and is_reversible and in_sim and cov_pass
        allowed_for_execution = all_preconditions_met and has_human_approval

        return {
            "policy_level": "L2",
            "all_preconditions_met": all_preconditions_met,
            "allowed_for_execution": allowed_for_execution,
            "status_text": "Allowed (L2)" if all_preconditions_met else "Blocked by Policy",
            "checks": checks,
            "summary": "Policy Engine evaluated 5 safety assertions. Preconditions verified. Awaiting human approval." if (all_preconditions_met and not has_human_approval) else ("Permitted and approved for execution." if allowed_for_execution else "Action blocked by safety policy.")
        }

    @classmethod
    def evaluate_diagnostic(cls, command: str) -> Dict[str, Any]:
        """
        L1 Read-Only Diagnostics Evaluation.
        """
        read_only_verbs = ["get", "describe", "logs", "top", "trace", "metrics"]
        is_safe = any(command.strip().lower().startswith(v) for v in read_only_verbs)
        return {
            "policy_level": "L1",
            "allowed": is_safe,
            "reason": "Read-only diagnostic permitted automatically" if is_safe else "Disallowed write command"
        }
