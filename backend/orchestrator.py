"""
backend/orchestrator.py
Production simulation orchestrator powered by LangGraph.
Coordinates seedable fault simulation, causal RCA, evidence verification,
policy engine enforcement, human approval interrupts, and independent recovery verification.
Maintains backward compatibility with React frontend API endpoints and SQLite database.
"""
import asyncio
import time
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.database import get_connection
from backend.scenarios import SCENARIOS
from backend.graph.workflow import incident_workflow, IncidentState, SCENARIO_FAULT_MAP
from backend.policy.engine import PolicyEngine
from backend.executor.remediation import remediation_executor
from backend.recovery.verify import RecoveryVerifier

AGENTS = [
    "Supervisor",
    "Triage",
    "Investigator",
    "Causal RCA",
    "Evidence Verifier",
    "Remediation",
    "Comms"
]

TASKS = [
    "Plan and route the investigation workflow",
    "Classify severity and business impact",
    "Gather logs, metrics, traces, and commit history",
    "Rank root causes using NetworkX dependency graph",
    "Verify claims against evidence and eliminate false positives",
    "Evaluate policy rules and propose reversible remediation",
    "Dispatch notifications and generate postmortem report"
]


class SimulationOrchestrator:
    """Orchestrates LangGraph incident response with state synchronization to SQLite."""

    def __init__(self):
        self.active_sim: Optional[Dict[str, Any]] = None
        self.lock = asyncio.Lock()
        self.step_task: Optional[asyncio.Task] = None
        self.thread_config: Optional[Dict[str, Any]] = None

    def get_elapsed_str(self) -> str:
        if not self.active_sim:
            return "00:00"
        s = int(time.time() - self.active_sim["t0"])
        return f"{s // 60:02d}:{s % 60:02d}"

    def log(self, agent: str, message: str, color: str = "cy"):
        if not self.active_sim:
            return
        entry = {
            "t": self.get_elapsed_str(),
            "a": agent,
            "m": message,
            "c": color
        }
        self.active_sim["log"].append(entry)

        try:
            conn = get_connection()
            conn.execute(
                "INSERT INTO agent_events (incident_id, agent_name, status, summary, color, created_at, elapsed_str) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.active_sim["id"], agent, "log", message, color, datetime.now(timezone.utc).isoformat(), entry["t"])
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print("Failed to persist log:", e)

    def audit(self, actor: str, action: str, details: str = ""):
        if not self.active_sim:
            return
        entry = [self.get_elapsed_str(), f"{actor}: {action} {details}".strip()]
        self.active_sim["audit"].append(entry)
        try:
            conn = get_connection()
            conn.execute(
                "INSERT INTO audit_logs (incident_id, timestamp, actor, action, details) VALUES (?, ?, ?, ?, ?)",
                (self.active_sim["id"], entry[0], actor, action, details)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print("Failed to persist audit:", e)

    async def start_scenario(self, scenario_id: str) -> Dict[str, Any]:
        async with self.lock:
            # If a simulation was already running, cancel the previous background task cleanly
            if self.step_task and not self.step_task.done():
                self.step_task.cancel()

            if scenario_id not in SCENARIOS:
                raise ValueError(f"Unknown scenario ID: {scenario_id}")

            sc = SCENARIOS[scenario_id]

            # Generate next monotonic incident ID by finding max numeric suffix
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM incidents WHERE id LIKE 'INC-%'")
            max_num = 2040
            for row in c.fetchall():
                try:
                    n = int(row["id"].split("-")[1])
                    if n > max_num:
                        max_num = n
                except (ValueError, IndexError):
                    pass

            inc_id = f"INC-{max_num + 1}"
            now_iso = datetime.now(timezone.utc).isoformat()
            detected_str = "Today " + datetime.now().strftime("%H:%M")

            # Persist initial incident record (using INSERT OR REPLACE to prevent any primary key collision)
            conn.execute("""
                INSERT OR REPLACE INTO incidents (id, title, scenario_id, service, severity, status, phase, detected_at, impact_summary, orders_at_risk, checkout_success_pct, active_agent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (inc_id, sc["name"], sc["id"], sc["svc"], sc["sev"], "Investigating", "running", detected_str, sc["sym"], sc["orders_at_risk"], sc["success_rate"], "Supervisor", now_iso))
            conn.commit()
            conn.close()

            # Initialize active simulation tracking
            self.thread_config = {"configurable": {"thread_id": inc_id}}
            t0 = time.time()
            self.active_sim = {
                "id": inc_id,
                "sc": sc,
                "st": ["waiting"] * 7,
                "res": [""] * 7,
                "ts": [""] * 7,
                "log": [],
                "audit": [],
                "t0": t0,
                "phase": "running",
                "det": detected_str,
                "orders_at_risk": sc["orders_at_risk"],
                "success_rate": sc["success_rate"],
                "policy": None,
                "state": None
            }

            # Launch background LangGraph execution
            self.step_task = asyncio.create_task(self._run_workflow_execution(inc_id, scenario_id, sc, t0))

            return self.get_status()

    async def _run_workflow_execution(self, inc_id: str, scenario_id: str, sc: Dict[str, Any], t0: float):
        """Drives the LangGraph execution in background."""
        try:
            fault_key = SCENARIO_FAULT_MAP.get(scenario_id, sc.get("fault_type", "faulty_deployment"))
            initial_state: IncidentState = {
                "incident_id": inc_id,
                "scenario_id": scenario_id,
                "fault_type": fault_key,
                "target_service": sc["svc"],
                "seed": 42,
                "t0": t0,
                "stage_statuses": ["waiting"] * 7,
                "stage_results": [""] * 7,
                "stage_timestamps": [""] * 7,
                "logs": self.active_sim["log"],
                "audit": self.active_sim["audit"],
                "verifier_retry_count": 0,
                "dropped_claims": [],
                "claims": []
            }

            # Run LangGraph until interrupt (paused right before executor)
            loop = asyncio.get_running_loop()
            final_state = await loop.run_in_executor(
                None,
                lambda: incident_workflow.invoke(initial_state, config=self.thread_config)
            )

            # Sync active_sim with graph state
            self._sync_state_to_sim(final_state)

            # Persist intermediate state (alerts, evidence, proposal) to DB
            self._persist_intermediate_records(final_state)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("Error in LangGraph workflow execution:", e)

    def _sync_state_to_sim(self, state: IncidentState):
        """Synchronizes LangGraph state to in-memory active_sim."""
        if not self.active_sim:
            return
        self.active_sim["state"] = state
        self.active_sim["phase"] = state.get("phase", "running")
        self.active_sim["st"] = state.get("stage_statuses", self.active_sim["st"])
        self.active_sim["res"] = state.get("stage_results", self.active_sim["res"])
        self.active_sim["ts"] = state.get("stage_timestamps", self.active_sim["ts"])
        self.active_sim["orders_at_risk"] = state.get("orders_at_risk", self.active_sim["orders_at_risk"])
        self.active_sim["success_rate"] = state.get("checkout_success_pct", self.active_sim["success_rate"])
        self.active_sim["policy"] = state.get("policy_evaluation")

    def _persist_intermediate_records(self, state: IncidentState):
        """Persists alerts, evidence, and remediation proposal to SQLite."""
        inc_id = state["incident_id"]
        try:
            conn = get_connection()
            # Alerts
            for a in state.get("correlated_alerts", []):
                alt_id = f"ALT-{int(time.time()*1000)%100000}-{a.get('service', 'svc')}"
                conn.execute("""
                    INSERT OR REPLACE INTO alerts (id, incident_id, service, name, severity, condition, fired_at, correlation_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (alt_id, inc_id, a.get("service", "system"), a.get("alert_name", "Alert"), a.get("severity", "High"),
                      f"Metric > threshold", state.get("detected_str", "Today"), state.get("correlation_reason", "Correlated by dependency")))

            # Evidence
            for v in state.get("verified_claims", []):
                ev_id = f"EV-{int(time.time()*1000)%100000}-{v.get('source_type', 'src')}"
                conn.execute("""
                    INSERT OR REPLACE INTO evidence (id, incident_id, type, source, claim, role, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ev_id, inc_id, v.get("source_type", "metric"), v.get("service", "system"), v.get("claim_text", "Claim"), "Supports", "Today"))

            # Remediation Proposal
            prop = state.get("remediation_proposal")
            if prop:
                policy_eval = state.get("policy_evaluation", {})
                conn.execute("""
                    INSERT OR REPLACE INTO remediation_proposals 
                    (id, incident_id, action, target_service, risk_level, is_reversible, timeout_seconds, rollback_plan, expected_effect, policy_level, policy_allowed, policy_checks_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"PROP-{inc_id}", inc_id, prop["action"], prop["target_service"],
                    prop.get("risk_level", "Low"), 1 if prop.get("is_reversible", True) else 0,
                    prop.get("timeout_seconds", 120), prop.get("rollback_plan", "rollback"),
                    prop.get("expected_effect", "recover"), "L2",
                    1 if state.get("policy_allowed") else 0,
                    json.dumps(policy_eval.get("checks", {}))
                ))

            # Update incident status
            db_status = "Awaiting approval" if state.get("phase") == "await" else "Investigating"
            conn.execute("UPDATE incidents SET status = ?, phase = ?, active_agent = ? WHERE id = ?",
                         (db_status, state.get("phase", "running"), state.get("active_agent", "Supervisor"), inc_id))

            conn.commit()
            conn.close()
        except Exception as e:
            print("Failed to persist intermediate records:", e)

    async def approve_remediation(self, reviewer: str = "Operator (Human)") -> Dict[str, Any]:
        """
        Enforces human approval inside backend.
        Evaluates policy engine with has_human_approval=True.
        Resumes LangGraph execution across Executor, Recovery Verifier, and Comms.
        """
        async with self.lock:
            if not self.active_sim or self.active_sim["phase"] != "await":
                raise ValueError("No remediation is currently awaiting approval.")

            state = self.active_sim.get("state") or incident_workflow.get_state(self.thread_config).values
            prop = state.get("remediation_proposal", {})

            # Policy Engine evaluation with human approval
            policy_res = PolicyEngine.evaluate_remediation_proposal(
                action=prop.get("action", "unknown"),
                target_service=prop.get("target_service", "system"),
                is_reversible=prop.get("is_reversible", True),
                evidence_coverage_pct=state.get("evidence_coverage_pct", 83.0),
                has_human_approval=True
            )

            if not policy_res["allowed_for_execution"]:
                reasons = policy_res.get("denial_reasons", ["Policy check failed"])
                raise ValueError(f"Approval rejected by policy engine: {'; '.join(reasons)}")

            self.active_sim["phase"] = "executing"

            # Persist approval record in DB
            conn = get_connection()
            conn.execute("INSERT INTO approvals (incident_id, decision, decided_at, reviewer) VALUES (?, ?, ?, ?)",
                         (self.active_sim["id"], "Approved", datetime.now(timezone.utc).isoformat(), reviewer))
            conn.execute("UPDATE incidents SET status = 'Remediating', phase = 'executing' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()

            # Resume LangGraph workflow execution
            asyncio.create_task(self._resume_workflow_execution(reviewer))
            return self.get_status()

    async def _resume_workflow_execution(self, reviewer: str):
        """Resumes LangGraph after human approval."""
        try:
            loop = asyncio.get_running_loop()

            # Update state with human approval
            incident_workflow.update_state(
                self.thread_config,
                {
                    "human_approved": True,
                    "approval_reviewer": reviewer,
                    "approval_remarks": "Approved by human operator"
                }
            )

            # Invoke resumption
            final_state = await loop.run_in_executor(
                None,
                lambda: incident_workflow.invoke(None, config=self.thread_config)
            )

            self._sync_state_to_sim(final_state)
            self._persist_final_records(final_state)

        except Exception as e:
            print("Error resuming LangGraph execution:", e)

    def _persist_final_records(self, state: IncidentState):
        """Persists recovery verification, postmortem, knowledge item, and audit logs."""
        inc_id = state["incident_id"]
        try:
            conn = get_connection()
            rec_ver = state.get("recovery_verification", {})
            before_m = state.get("before_metrics", {})
            after_m = state.get("after_metrics", {})

            # 1. Verification results
            conn.execute("""
                INSERT OR REPLACE INTO verification_results 
                (incident_id, is_verified, checks_passed, total_checks, checks_json, before_metrics_json, after_metrics_json, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inc_id,
                1 if state.get("is_recovery_verified") else 0,
                rec_ver.get("checks_passed", 0),
                rec_ver.get("total_checks", 4),
                json.dumps(rec_ver.get("checks", [])),
                json.dumps(before_m),
                json.dumps(after_m),
                datetime.now(timezone.utc).isoformat()
            ))

            # 2. Postmortem
            pm_md = state.get("postmortem_markdown", "")
            conn.execute("""
                INSERT OR REPLACE INTO postmortems (incident_id, title, content_markdown, created_at)
                VALUES (?, ?, ?, ?)
            """, (inc_id, f"{inc_id} Postmortem", pm_md, datetime.now(timezone.utc).isoformat()))

            # 3. Knowledge Base item (only if recovery verified)
            if state.get("is_recovery_verified"):
                prop = state.get("remediation_proposal", {})
                conn.execute("""
                    INSERT OR REPLACE INTO knowledge_items (id, title, service, symptoms, root_cause, fix, approval_status, recovery_status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inc_id,
                    f"Incident on {state.get('target_service', 'service')}",
                    state.get("target_service", "service"),
                    state.get("sim_run").alerts[0].alert_name if state.get("sim_run") and state.get("sim_run").alerts else "Telemetry degradation",
                    state.get("top_root_cause", "Root cause identified"),
                    prop.get("action", "Remediation executed"),
                    "Approved",
                    "Verified",
                    "Today " + datetime.now().strftime("%H:%M")
                ))

            # 4. Incident final status
            final_status = state.get("status", "Resolved")
            final_phase = state.get("phase", "resolved")
            resolved_at = datetime.now(timezone.utc).isoformat() if final_status == "Resolved" else None

            conn.execute("""
                UPDATE incidents 
                SET status = ?, phase = ?, resolved_at = ?, active_agent = ?
                WHERE id = ?
            """, (final_status, final_phase, resolved_at, state.get("active_agent", "Comms"), inc_id))

            conn.commit()
            conn.close()
        except Exception as e:
            print("Failed to persist final records:", e)

    async def reject_remediation(self, reviewer: str = "Operator (Human)", reason: str = "Rejected by operator"):
        """Rejects remediation, transitions to Escalated, logs human-rejected, and halts."""
        async with self.lock:
            if not self.active_sim or self.active_sim["phase"] != "await":
                raise ValueError("No remediation is currently awaiting approval.")

            self.active_sim["phase"] = "rejected"
            self.active_sim["st"][5] = "failed"
            self.active_sim["res"][5] = f"Rejected by operator ({reviewer}). Escalated to on-call engineering lead."
            self.audit(reviewer, "human-rejected remediation proposal", reason)
            self.log(reviewer, f"Remediation rejected. Reason: {reason}", "red")
            self.log("Supervisor", "Escalating incident to Level 3 on-call engineer page.", "amb")

            conn = get_connection()
            conn.execute("INSERT INTO approvals (incident_id, decision, decided_at, reviewer, remarks) VALUES (?, ?, ?, ?, ?)",
                         (self.active_sim["id"], "Rejected", datetime.now(timezone.utc).isoformat(), reviewer, reason))
            conn.execute("UPDATE incidents SET status = 'Escalated', phase = 'rejected', active_agent = 'Supervisor' WHERE id = ?", (self.active_sim["id"],))

            # Store rejection postmortem
            pm_md = f"""# Incident Postmortem: {self.active_sim['id']} (SIMULATION)

**Status:** Escalated (Remediation Rejected by Operator)  
**Reviewer:** {reviewer}  
**Rejection Reason:** {reason}  

Remediation was evaluated by Policy Engine but explicitly rejected by human operator.
Incident has been escalated to on-call incident response team.
"""
            conn.execute("INSERT OR REPLACE INTO postmortems (incident_id, title, content_markdown, created_at) VALUES (?, ?, ?, ?)",
                         (self.active_sim["id"], f"{self.active_sim['id']} - Rejected", pm_md, datetime.now(timezone.utc).isoformat()))

            conn.commit()
            conn.close()
            return self.get_status()

    async def emergency_stop(self, actor: str = "Operator (Human)"):
        """Triggers emergency stop, runs rollback action on simulator, and logs human_override."""
        async with self.lock:
            if not self.active_sim:
                raise ValueError("No active simulation to stop.")

            self.active_sim["phase"] = "stopped"
            if self.step_task and not self.step_task.done():
                self.step_task.cancel()

            # Execute real simulator rollback
            sim_data = {"status": "stopped"}
            rb_res = remediation_executor.emergency_rollback(sim_data)

            self.audit(actor, "human_override: Emergency stop triggered! Rollback executed", rb_res.get("rollback_action", ""))
            self.log(actor, "EMERGENCY STOP initiated. All active agent executions terminated.", "red")
            self.log("Remediation Agent", f"Rollback action '{rb_res.get('rollback_action')}' executed on {rb_res.get('target_service')}.", "amb")

            conn = get_connection()
            conn.execute("UPDATE incidents SET status = 'Stopped', phase = 'stopped', active_agent = 'Operator' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()
            return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        if not self.active_sim:
            return {"active": False, "sim": None}

        s = self.active_sim
        return {
            "active": True,
            "sim": {
                "id": s["id"],
                "scenario": s["sc"],
                "stages": [
                    {
                        "agent": AGENTS[i],
                        "task": TASKS[i],
                        "status": s["st"][i],
                        "result": s["res"][i],
                        "timestamp": s["ts"][i]
                    }
                    for i in range(7)
                ],
                "phase": s["phase"],
                "elapsed": self.get_elapsed_str(),
                "detected": s["det"],
                "orders_at_risk": s["orders_at_risk"],
                "success_rate": s["success_rate"],
                "log": s["log"],
                "audit": s["audit"],
                "policy": s.get("policy")
            }
        }


# Global singleton
orchestrator = SimulationOrchestrator()
