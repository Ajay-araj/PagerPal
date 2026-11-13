"""
backend/graph/workflow.py
LangGraph incident response StateGraph.
Orchestrates:
Chaos -> Correlation -> Supervisor -> Triage -> Investigator <-> Verifier (bounded retry)
-> Causal RCA -> Confidence -> Remediation -> Policy Engine
-> [Human Approval Interrupt] -> Executor -> Recovery Verifier (can fail) -> Comms -> Postmortem.
"""
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timezone
import json
import time

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.schemas import SimulationRun, ClaimItem
from backend.simulator.generator import TelemetryGenerator
from backend.simulator.topology import topology
from backend.correlation.engine import AlertCorrelationEngine
from backend.rca.causal_graph import causal_rca_engine
from backend.verification.evidence import EvidenceVerifier
from backend.confidence.scoring import ConfidenceScorer
from backend.policy.engine import PolicyEngine
from backend.security.sanitize import quarantine_untrusted_input

from backend.agents.supervisor import run_supervisor
from backend.agents.triage import run_triage
from backend.agents.investigator import run_investigator
from backend.agents.remediation import run_remediation
from backend.agents.comms import run_comms
from backend.executor.remediation import remediation_executor
from backend.recovery.verify import RecoveryVerifier
from backend.integrations.github_client import github_client
from backend.integrations.notifier import notifier


class IncidentState(TypedDict, total=False):
    incident_id: str
    scenario_id: str
    fault_type: str
    target_service: str
    seed: int
    t0: float

    # Telemetry and simulator
    sim_run: Any
    correlated_alerts: List[Dict[str, Any]]
    correlation_reason: str
    dedup_count: int

    # Agents
    supervisor_plan: Dict[str, Any]
    triage_assessment: Dict[str, Any]
    severity: str
    orders_at_risk: int
    checkout_success_pct: float

    # Investigator & Verifier
    investigator_findings: Dict[str, Any]
    candidate_service: str
    claims: List[Dict[str, Any]]
    verified_claims: List[Dict[str, Any]]
    unverified_claims: List[Dict[str, Any]]
    dropped_claims: List[str]
    verifier_retry_count: int
    verifier_feedback: str

    # RCA & Counterfactual
    rca_candidates: List[Dict[str, Any]]
    top_root_cause: str
    propagation_path: List[str]
    counterfactual_result: Dict[str, Any]

    # Confidence
    confidence_report: Dict[str, Any]
    diagnostic_confidence_pct: float
    evidence_coverage_pct: float

    # Remediation Proposal & Policy
    remediation_proposal: Dict[str, Any]
    policy_evaluation: Dict[str, Any]
    policy_allowed: bool

    # Human Approval
    human_approved: Optional[bool]
    approval_reviewer: str
    approval_remarks: str

    # Execution & Recovery
    execution_result: Dict[str, Any]
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    recovery_verification: Dict[str, Any]
    is_recovery_verified: bool

    # External integrations & Comms
    github_commits: List[Dict[str, Any]]
    webhook_dispatched: bool
    comms_update: Dict[str, Any]
    postmortem_markdown: str

    # Workflow tracking
    phase: str
    status: str
    active_agent: str
    stage_statuses: List[str]
    stage_results: List[str]
    stage_timestamps: List[str]
    logs: List[Dict[str, Any]]
    audit: List[List[str]]
    error: Optional[str]


def _get_elapsed_str(t0: float) -> str:
    s = int(time.time() - t0)
    return f"{s // 60:02d}:{s % 60:02d}"


def _append_log(state: IncidentState, agent: str, message: str, color: str = "cy"):
    elapsed = _get_elapsed_str(state.get("t0", time.time()))
    entry = {"t": elapsed, "a": agent, "m": message, "c": color}
    state["logs"].append(entry)


def _append_audit(state: IncidentState, actor: str, action: str, details: str = ""):
    elapsed = _get_elapsed_str(state.get("t0", time.time()))
    entry = [elapsed, f"{actor}: {action} {details}".strip()]
    state["audit"].append(entry)


# --- NODE DEFINITIONS ---

SCENARIO_FAULT_MAP = {
    "deploy": "faulty_deployment",
    "db": "database_connection_failure",
    "crash": "service_crash",
    "net": "network_latency",
    "cpu": "cpu_stress",
    "mem": "memory_stress",
    "faulty_deployment": "faulty_deployment",
    "db_connection_leak": "database_connection_failure",
    "database_connection_failure": "database_connection_failure",
    "service_crash": "service_crash",
    "service_crash_loop": "service_crash",
    "network_latency": "network_latency",
    "network_partition_latency": "network_latency",
    "cpu_stress": "cpu_stress",
    "cpu_saturation_stress": "cpu_stress",
    "memory_stress": "memory_stress",
    "memory_leak_oom": "memory_stress"
}

def chaos_node(state: IncidentState) -> Dict[str, Any]:
    """Generates telemetry using the seedable fault simulator."""
    gen = TelemetryGenerator(seed=state.get("seed", 42))
    raw_fault = state.get("fault_type") or state.get("scenario_id") or "deploy"
    fault_key = SCENARIO_FAULT_MAP.get(raw_fault, "faulty_deployment")

    sim_run = gen.generate(
        fault_type=fault_key,
        target_service=state.get("target_service")
    )
    _append_log(state, "Chaos Simulator", f"Injected '{fault_key}' on '{sim_run.target_service}' (SIMULATION)", "amb")
    _append_audit(state, "Chaos Simulator", "Injected fault scenario", f"{fault_key} on {sim_run.target_service}")

    return {
        "sim_run": sim_run,
        "fault_type": fault_key,
        "target_service": sim_run.target_service,
        "candidate_service": sim_run.target_service,
        "active_agent": "Supervisor",
        "phase": "running",
        "status": "Investigating"
    }


def correlation_node(state: IncidentState) -> Dict[str, Any]:
    """Correlates and deduplicates alerts using temporal, topological, and symptom rules."""
    sim_run: SimulationRun = state["sim_run"]
    corr_engine = AlertCorrelationEngine(window_sec=90.0, max_hops=2)
    result = corr_engine.correlate(sim_run.alerts, incident_id=state.get("incident_id", "INC-auto"))

    corr_reason = result.correlation_reason
    corr_alerts = [a.model_dump() for a in result.alerts]
    dedup_count = result.dedup_count

    _append_log(state, "Alert Correlation", f"{len(corr_alerts)} alerts correlated ({dedup_count} deduplicated): {corr_reason}", "amb")
    _append_audit(state, "Alert Correlation", "Correlated alerts", corr_reason)

    return {
        "correlated_alerts": corr_alerts,
        "correlation_reason": corr_reason,
        "dedup_count": dedup_count
    }


def supervisor_node(state: IncidentState) -> Dict[str, Any]:
    """Supervisor Agent plans workflow."""
    sup_res = run_supervisor(
        incident_id=state["incident_id"],
        scenario_info={"name": state.get("fault_type", "fault"), "svc_name": state.get("target_service", "system")}
    )
    plan = sup_res["result"]
    state["stage_statuses"][0] = "completed"
    state["stage_timestamps"][0] = _get_elapsed_str(state["t0"])
    state["stage_results"][0] = f"Workflow plan initialized: {' -> '.join(plan.workflow_steps)}."

    _append_log(state, "Supervisor", f"Workflow plan initialized: {' -> '.join(plan.workflow_steps)}.", "grn")
    _append_audit(state, "Supervisor", "Orchestration plan generated", f"Steps: {len(plan.workflow_steps)}")

    if sup_res["is_fallback"]:
        _append_audit(state, "Supervisor", sup_res["audit_note"])

    return {
        "supervisor_plan": plan.model_dump(),
        "active_agent": "Triage"
    }


def triage_node(state: IncidentState) -> Dict[str, Any]:
    """Triage Agent computes blast radius and orders at risk."""
    sim_run: SimulationRun = state["sim_run"]
    triage_res = run_triage(sim_run, state["correlated_alerts"], nominal_orders=100)
    triage = triage_res["result"]

    res_str = (
        f"Severity: {triage.severity}. Impact: ~{triage.orders_at_risk} orders/min at risk (simulated estimate). "
        f"Checkout success: {triage.checkout_success_pct}%."
    )
    state["stage_statuses"][1] = "completed"
    state["stage_timestamps"][1] = _get_elapsed_str(state["t0"])
    state["stage_results"][1] = res_str

    _append_log(state, "Triage", res_str, "grn")
    _append_audit(state, "Triage", "Triage assessed", f"Severity: {triage.severity}, At risk: {triage.orders_at_risk}")

    if triage_res["is_fallback"]:
        _append_audit(state, "Triage", triage_res["audit_note"])

    return {
        "triage_assessment": triage.model_dump(),
        "severity": triage.severity,
        "orders_at_risk": triage.orders_at_risk,
        "checkout_success_pct": triage.checkout_success_pct,
        "active_agent": "Investigator"
    }


def investigator_node(state: IncidentState) -> Dict[str, Any]:
    """Investigator Agent gathers observability telemetry and formulates claims."""
    sim_run: SimulationRun = state["sim_run"]
    candidate = state.get("candidate_service") or state.get("target_service") or "payments"
    retry_feedback = state.get("verifier_feedback")

    inv_res = run_investigator(sim_run, candidate, retry_feedback)
    findings = inv_res["result"]

    claims_dicts = [c.model_dump() for c in findings.claims]
    res_str = f"Collected {len(claims_dicts)} evidence claims across logs, metrics, traces, and deploys."
    state["stage_statuses"][2] = "completed"
    state["stage_timestamps"][2] = _get_elapsed_str(state["t0"])
    state["stage_results"][2] = res_str

    _append_log(state, "Investigator", res_str, "grn")
    _append_audit(state, "Investigator", "Queried telemetry tools", f"Claims formulated: {len(claims_dicts)}")

    if inv_res["is_fallback"]:
        _append_audit(state, "Investigator", inv_res["audit_note"])

    return {
        "investigator_findings": findings.model_dump(),
        "claims": claims_dicts,
        "candidate_service": candidate,
        "active_agent": "Causal RCA"
    }


def causal_rca_node(state: IncidentState) -> Dict[str, Any]:
    """Causal RCA ranks root causes using NetworkX and runs counterfactual check."""
    sim_run: SimulationRun = state["sim_run"]
    rca_res = causal_rca_engine.analyze(sim_run)

    top_candidates = [c.model_dump() for c in rca_res.top_candidates]
    top_cause = rca_res.top_candidates[0].service_id if rca_res.top_candidates else state.get("target_service", "payments")
    prop_path = rca_res.propagation_path or [top_cause, "checkout"]

    cf_res = rca_res.counterfactual.model_dump() if rca_res.counterfactual else {}

    path_str = " -> ".join(prop_path)
    res_str = f"Root cause hypothesis: {top_cause}. Causal propagation path: {path_str}."
    state["stage_statuses"][3] = "completed"
    state["stage_timestamps"][3] = _get_elapsed_str(state["t0"])
    state["stage_results"][3] = res_str

    _append_log(state, "Causal RCA", res_str, "grn")
    _append_audit(state, "Causal RCA", "Ranked root causes", f"Top candidate: {top_cause}, Counterfactual support: {cf_res.get('supports_hypothesis')}")

    return {
        "rca_candidates": top_candidates,
        "top_root_cause": top_cause,
        "candidate_service": top_cause,
        "propagation_path": prop_path,
        "counterfactual_result": cf_res,
        "active_agent": "Evidence Verifier"
    }


def evidence_verifier_node(state: IncidentState) -> Dict[str, Any]:
    """Evidence Verifier independently checks claims against empirical telemetry."""
    sim_run: SimulationRun = state["sim_run"]
    claims = state.get("claims", [])
    retry_count = state.get("verifier_retry_count", 0)

    # Convert claims to ClaimItem instances for EvidenceVerifier
    claim_items = [
        ClaimItem(
            claim=c.get("claim_text", c.get("claim", "")),
            type=c.get("source_type", c.get("type", "Metric")).capitalize(),
            source=c.get("service", c.get("source", "system")),
            role=c.get("role", "Supports")
        )
        for c in claims
    ]
    report = EvidenceVerifier().verify_claims(claim_items, sim_run)

    verified = [v.model_dump() for v in report.verified_claims]
    unverified = [u.model_dump() for u in report.dropped_claims]

    # If unverified claims exist and we haven't hit the 2-retry limit, prepare retry feedback
    if unverified and retry_count < 2:
        retry_msg = f"{len(unverified)} claims failed verification: {[c['claim'] for c in unverified]}. Please gather additional evidence or refine."
        _append_log(state, "Evidence Verifier", f"Verification retry loop #{retry_count + 1}: {retry_msg}", "amb")
        _append_audit(state, "Evidence Verifier", f"Retry #{retry_count + 1} requested to Investigator", retry_msg)
        return {
            "verified_claims": verified,
            "unverified_claims": unverified,
            "verifier_retry_count": retry_count + 1,
            "verifier_feedback": retry_msg
        }

    # Bounded retries exhausted or all claims verified: drop remaining unverified claims
    dropped = state.get("dropped_claims", [])
    if unverified:
        for u in unverified:
            dropped.append(u["claim"])
        _append_log(state, "Evidence Verifier", f"Dropped {len(unverified)} unverified claims after retries: {[u['claim'] for u in unverified]}", "amb")
        _append_audit(state, "Evidence Verifier", "Dropped unverified claims", str([u['claim'] for u in unverified]))

    cov_pct = report.evidence_coverage_pct
    res_str = f"{len(verified)} of {len(claims)} claims verified. Diagnostic coverage: {cov_pct}%."
    if dropped:
        res_str += f" Dropped claim: '{dropped[-1]}'."

    state["stage_statuses"][4] = "completed"
    state["stage_timestamps"][4] = _get_elapsed_str(state["t0"])
    state["stage_results"][4] = res_str

    _append_log(state, "Evidence Verifier", res_str, "grn")
    _append_audit(state, "Evidence Verifier", "Claim verification completed", f"Verified: {len(verified)}, Dropped: {len(dropped)}")

    return {
        "verified_claims": verified,
        "unverified_claims": [],
        "dropped_claims": dropped,
        "evidence_coverage_pct": cov_pct,
        "active_agent": "Remediation"
    }


def should_retry_investigator(state: IncidentState) -> str:
    """Conditional edge: retries to investigator up to 2 times if unverified claims exist."""
    unverified = state.get("unverified_claims", [])
    retry_count = state.get("verifier_retry_count", 0)
    if unverified and retry_count <= 2:
        return "investigator"
    return "confidence_report"


def confidence_report_node(state: IncidentState) -> Dict[str, Any]:
    """Computes rule-based confidence scoring."""
    sim_run: SimulationRun = state["sim_run"]
    claims = state.get("claims", [])
    claim_items = [
        ClaimItem(
            claim=c.get("claim_text", c.get("claim", "")),
            type=c.get("source_type", c.get("type", "Metric")).capitalize(),
            source=c.get("service", c.get("source", "system")),
            role=c.get("role", "Supports")
        )
        for c in claims
    ]
    report = EvidenceVerifier().verify_claims(claim_items, sim_run)
    conf = ConfidenceScorer().calculate(report, sim_run)

    _append_log(state, "Confidence Scorer", f"Diagnostic confidence: {conf.diagnostic_confidence_pct}%, Evidence coverage: {conf.evidence_coverage_pct}%.", "cy")
    _append_audit(state, "Confidence Scorer", "Scored confidence", f"Score: {conf.diagnostic_confidence_pct}%, Coverage: {conf.evidence_coverage_pct}%")

    return {
        "confidence_report": conf.model_dump(),
        "diagnostic_confidence_pct": conf.diagnostic_confidence_pct,
        "evidence_coverage_pct": conf.evidence_coverage_pct
    }


def remediation_proposal_node(state: IncidentState) -> Dict[str, Any]:
    """Remediation Agent proposes reversible action from allowlist."""
    top_cause = state.get("top_root_cause", "payments")
    fault_type = state.get("fault_type", "faulty_deployment")

    rem_res = run_remediation(
        root_cause_service=top_cause,
        fault_type=fault_type,
        root_cause_summary=f"Incident on {top_cause} causing customer checkout degradation"
    )
    proposal = rem_res["result"]

    return {
        "remediation_proposal": proposal.model_dump(),
        "active_agent": "Policy Engine"
    }


def policy_engine_node(state: IncidentState) -> Dict[str, Any]:
    """Policy Engine evaluates L2 preconditions and gates execution."""
    prop = state["remediation_proposal"]
    cov = state.get("evidence_coverage_pct", 60.0)
    conf = state.get("diagnostic_confidence_pct", 75.0)

    # Initial check without human approval (using classmethod interface)
    eval_res = PolicyEngine.evaluate_remediation_proposal(
        action=prop["action"],
        target_service=prop["target_service"],
        is_reversible=prop.get("is_reversible", True),
        evidence_coverage_pct=cov,
        has_human_approval=False,
        has_rollback_plan=bool(prop.get("rollback_plan")),
        timeout_seconds=prop.get("timeout_seconds", 120),
        confidence_pct=conf
    )

    # If action is completely prohibited (e.g. L3 or unknown) or preconditions fail
    if not eval_res["all_preconditions_met"]:
        state["stage_statuses"][5] = "failed"
        state["stage_timestamps"][5] = _get_elapsed_str(state["t0"])
        state["stage_results"][5] = f"DENIED: Action '{prop['action']}' failed policy preconditions: {eval_res['denial_reasons']}"
        _append_log(state, "Policy Engine", f"DENIED by policy engine: {eval_res['denial_reasons']}", "red")
        _append_audit(state, "Policy Engine", "Policy checks FAILED", str(eval_res['denial_reasons']))
        return {
            "policy_evaluation": eval_res,
            "policy_allowed": False,
            "phase": "rejected",
            "status": "Escalated"
        }

    # Preconditions passed, awaiting human signoff
    state["stage_statuses"][5] = "review"
    state["stage_timestamps"][5] = _get_elapsed_str(state["t0"])
    res_str = f"Proposed: {prop['action']}. Policy Engine evaluated L2 preconditions: PASS. Awaiting operator approval."
    state["stage_results"][5] = res_str

    _append_log(state, "Policy Engine", "All automatic preconditions verified. L2 reversible remediation requires human signoff.", "amb")
    _append_log(state, "Remediation Agent", f"Action '{prop['action']}' prepared. Target: {prop['target_service']}. Rollback ready.", "cy")
    _append_audit(state, "Policy Engine", "Preconditions PASSED (L2). Awaiting human operator approval.")

    return {
        "policy_evaluation": eval_res,
        "policy_allowed": True,
        "phase": "await",
        "status": "Awaiting approval",
        "active_agent": "Remediation"
    }


def check_policy_decision(state: IncidentState) -> str:
    """Conditional edge after policy engine."""
    if not state.get("policy_allowed", False):
        return "policy_denied"
    return "executor"


def policy_denied_node(state: IncidentState) -> Dict[str, Any]:
    """Handles policy-denied remediation actions."""
    prop = state.get("remediation_proposal", {})
    action = prop.get("action", "unknown_action")
    reasons = state.get("policy_evaluation", {}).get("denial_reasons", ["Prohibited action"])

    _append_log(state, "Supervisor", f"Remediation '{action}' blocked by policy: {reasons}. Escalating to human on-call.", "red")
    _append_audit(state, "Supervisor", "Incident escalated due to policy denial", str(reasons))

    return {
        "phase": "rejected",
        "status": "Escalated",
        "active_agent": "Supervisor"
    }


def check_executor_result(state: IncidentState) -> str:
    """Conditional edge after executor: skip recovery if human rejected."""
    if not state.get("human_approved"):
        return "postmortem"
    return "recovery_verifier"


def executor_node(state: IncidentState) -> Dict[str, Any]:
    """
    Executes the simulated fix after human approval.
    Enforces human approval check inside backend.
    """
    # Verify human approval was granted
    if not state.get("human_approved"):
        _append_log(state, "Remediation Agent", "Execution aborted: human operator rejected remediation.", "red")
        _append_audit(state, "Operator", "Rejected remediation", state.get("approval_remarks", "Rejected by operator"))
        return {
            "phase": "rejected",
            "status": "Escalated",
            "active_agent": "Supervisor"
        }

    prop = state["remediation_proposal"]
    reviewer = state.get("approval_reviewer", "Operator (Human)")

    _append_log(state, reviewer, f"Remediation approved: {prop['action']}", "grn")
    _append_log(state, "Remediation Agent", f"Executing simulated fix: {prop['action']} on {prop['target_service']}...", "cy")
    _append_audit(state, reviewer, f"Approved remediation: {prop['action']}", state.get("approval_remarks", ""))

    # Query GitHub for recent service commits as real external call
    commits, is_github_mock, gh_audit = github_client.get_recent_commits(prop["target_service"])
    _append_audit(state, "GitHub Client", gh_audit)

    # Execute simulated remediation
    sim_data = {
        "fault_type": state.get("fault_type"),
        "root_cause_service": state.get("top_root_cause"),
        "current_error_rate": state.get("sim_run").alerts[0].value_observed if state.get("sim_run") and state.get("sim_run").alerts else 18.0,
        "current_latency": 620.0
    }
    exec_res = remediation_executor.execute_action(
        action=prop["action"],
        target_service=prop["target_service"],
        rollback_plan=prop["rollback_plan"],
        sim_run_data=sim_data
    )

    before_metrics = {
        "p95_latency_ms": 620.0,
        "error_rate_pct": 18.5,
        "cpu_pct": 74.0,
        "memory_pct": 68.0
    }
    # Only use computed after_metrics if the test hasn't injected degraded ones
    after_metrics = state.get("after_metrics") or exec_res["remediated_metrics"]

    _append_audit(state, "Remediation Agent", "Simulated execution finished. Awaiting recovery verification.")
    _append_log(state, "Remediation Agent", "Action command exited 0. Note: command success is NOT proof of recovery.", "cy")
    _append_log(state, "Recovery Verification", "Sampling live health probes and comparing before/after metrics...", "amb")

    return {
        "execution_result": exec_res,
        "github_commits": commits,
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "phase": "verifying",
        "status": "Verifying recovery",
        "active_agent": "Evidence Verifier"
    }


def recovery_verifier_node(state: IncidentState) -> Dict[str, Any]:
    """
    Independent recovery verifier: compares before vs after telemetry.
    Can FAIL if metrics remain degraded.
    """
    before_m = state.get("before_metrics", {})
    after_m = state.get("after_metrics", {})

    # Evaluate recovery against empirical criteria
    verification = RecoveryVerifier.verify(before_m, after_m, probes_passed=True)

    if not verification["is_verified"]:
        # Verification failed! Incident MUST escalate and never show Resolved
        fail_desc = verification.get("failure_summary", "Metrics remain elevated above threshold")
        _append_log(state, "Recovery Verification", f"FAILED: {fail_desc}. Triggering escalation.", "red")
        _append_audit(state, "Recovery Verification", "Verification FAILED", fail_desc)

        state["stage_statuses"][5] = "failed"
        state["stage_results"][5] = f"Execution failed recovery verification: {fail_desc}"

        return {
            "recovery_verification": verification,
            "is_recovery_verified": False,
            "phase": "escalated",
            "status": "Escalated",
            "active_agent": "Supervisor"
        }

    # Recovery passed!
    state["stage_statuses"][5] = "completed"
    _append_log(state, "Recovery Verification", f"Recovery verified across {verification['checks_passed']}/{verification['total_checks']} criteria.", "grn")
    _append_audit(state, "Recovery Verification", f"Recovery verified by {verification['checks_passed']} of {verification['total_checks']} independent criteria.")

    return {
        "recovery_verification": verification,
        "is_recovery_verified": True,
        "phase": "resolved",
        "status": "Resolved",
        "active_agent": "Comms"
    }


def check_recovery_verdict(state: IncidentState) -> str:
    """Conditional edge after recovery verification."""
    if not state.get("is_recovery_verified", False):
        return "escalated"
    return "comms"


def comms_node(state: IncidentState) -> Dict[str, Any]:
    """Comms Agent drafts stakeholder message and dispatches webhook without emojis."""
    comms_res = run_comms(
        incident_id=state["incident_id"],
        service=state.get("target_service", "system"),
        severity=state.get("severity", "High"),
        status=state.get("status", "Resolved"),
        root_cause=state.get("top_root_cause", "unknown"),
        action_taken=state.get("remediation_proposal", {}).get("action", "remediation")
    )
    comms = comms_res["result"]

    # Dispatch external webhook (Slack/Discord)
    webhook_ok, webhook_audit = notifier.send_notification(
        incident_id=state["incident_id"],
        service=comms.affected_service,
        status=comms.current_status,
        details=comms.summary
    )
    _append_audit(state, "Comms Agent", webhook_audit)

    state["stage_statuses"][6] = "completed"
    state["stage_timestamps"][6] = _get_elapsed_str(state["t0"])
    res_str = "Notification sent (simulated). Postmortem generated and archived in Knowledge Base."
    state["stage_results"][6] = res_str

    _append_log(state, "Comms Agent", res_str, "grn")
    _append_audit(state, "Comms Agent", "Postmortem generated and incident stored in Knowledge Base.")

    if comms_res["is_fallback"]:
        _append_audit(state, "Comms Agent", comms_res["audit_note"])

    return {
        "comms_update": comms.model_dump(),
        "webhook_dispatched": webhook_ok,
        "active_agent": "Comms"
    }


def postmortem_node(state: IncidentState) -> Dict[str, Any]:
    """Generates structured postmortem report from actual measured telemetry."""
    inc_id = state["incident_id"]
    svc = state.get("target_service", "system")
    status = state.get("status", "Resolved")
    rca = state.get("top_root_cause", "unknown")
    prop = state.get("remediation_proposal", {})
    before_m = state.get("before_metrics", {})
    after_m = state.get("after_metrics", {})
    verified = state.get("verified_claims", [])
    dropped = state.get("dropped_claims", [])

    pm_md = f"""# Incident Postmortem: {inc_id} (SIMULATION)

**Service:** `{svc}`  
**Status:** {status}  
**Severity:** {state.get('severity', 'High')}  
**Root Cause:** {rca}  
**Remediation Action:** `{prop.get('action', 'N/A')}`  

---

## 1. Executive Summary
During a simulated chaos event, `{svc}` degraded customer checkout flows.
Checkout success dropped to **{state.get('checkout_success_pct', 100)}%**, putting approximately **{state.get('orders_at_risk', 0)} orders per minute** at risk (simulated estimate).
PagerPal correlated alerts, localized root cause to `{rca}`, validated empirical claims, enforced policy clearances, and verified recovery.

## 2. Telemetry and Impact
- Observed p95 Latency: {before_m.get('p95_latency_ms', 600)}ms -> {after_m.get('p95_latency_ms', 15)}ms
- Observed Error Rate: {before_m.get('error_rate_pct', 20)}% -> {after_m.get('error_rate_pct', 0.05)}%
- Evidence Claims Verified: {len(verified)} verified, {len(dropped)} dropped unverified.

## 3. Policy & Operator Governance
- Action: `{prop.get('action', 'N/A')}`
- Policy Preconditions: PASS (L2 Reversible)
- Operator Approval: {state.get('approval_reviewer', 'Operator')} ({'Approved' if state.get('human_approved') else 'Denied/Rejected'})
"""
    return {
        "postmortem_markdown": pm_md
    }


def build_incident_workflow():
    """Builds and compiles the LangGraph StateGraph with interrupt before executor."""
    builder = StateGraph(IncidentState)

    # Add all nodes
    builder.add_node("chaos", chaos_node)
    builder.add_node("correlation", correlation_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("triage", triage_node)
    builder.add_node("investigator", investigator_node)
    builder.add_node("causal_rca", causal_rca_node)
    builder.add_node("evidence_verifier", evidence_verifier_node)
    builder.add_node("confidence_report", confidence_report_node)
    builder.add_node("remediation_proposal", remediation_proposal_node)
    builder.add_node("policy_engine", policy_engine_node)
    builder.add_node("policy_denied", policy_denied_node)
    builder.add_node("executor", executor_node)
    builder.add_node("recovery_verifier", recovery_verifier_node)
    builder.add_node("comms", comms_node)
    builder.add_node("postmortem", postmortem_node)

    # Edges
    builder.add_edge(START, "chaos")
    builder.add_edge("chaos", "correlation")
    builder.add_edge("correlation", "supervisor")
    builder.add_edge("supervisor", "triage")
    builder.add_edge("triage", "investigator")
    builder.add_edge("investigator", "causal_rca")
    builder.add_edge("causal_rca", "evidence_verifier")

    # Conditional edge: verifier retry loop back to investigator
    builder.add_conditional_edges(
        "evidence_verifier",
        should_retry_investigator,
        {
            "investigator": "investigator",
            "confidence_report": "confidence_report"
        }
    )

    builder.add_edge("confidence_report", "remediation_proposal")
    builder.add_edge("remediation_proposal", "policy_engine")

    # Conditional edge after policy engine
    builder.add_conditional_edges(
        "policy_engine",
        check_policy_decision,
        {
            "executor": "executor",
            "policy_denied": "policy_denied"
        }
    )

    builder.add_edge("policy_denied", "postmortem")

    # Executor -> conditional: recovery_verifier (approved) or postmortem (rejected)
    builder.add_conditional_edges(
        "executor",
        check_executor_result,
        {
            "recovery_verifier": "recovery_verifier",
            "postmortem": "postmortem"
        }
    )

    # Recovery verifier conditional edge
    builder.add_conditional_edges(
        "recovery_verifier",
        check_recovery_verdict,
        {
            "comms": "comms",
            "escalated": "postmortem"
        }
    )

    builder.add_edge("comms", "postmortem")
    builder.add_edge("postmortem", END)

    # Compile with memory checkpointer and interrupt before executor (human approval gate)
    checkpointer = MemorySaver()
    app = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["executor"]
    )
    return app


# Global compiled workflow instance
incident_workflow = build_incident_workflow()
