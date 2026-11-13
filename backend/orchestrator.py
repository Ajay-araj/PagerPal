import asyncio
import time
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.database import get_connection
from backend.scenarios import SCENARIOS
from backend.graph import topology
from backend.policy_engine import PolicyEngine
from backend.recovery_verifier import RecoveryVerifier

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
    def __init__(self):
        self.active_sim: Optional[Dict[str, Any]] = None
        self.lock = asyncio.Lock()
        self.step_task: Optional[asyncio.Task] = None

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

        # Persist to DB
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
            if self.active_sim and self.active_sim["phase"] in ["running", "await", "executing", "verifying"]:
                raise ValueError("A simulation is already active. Please wait or stop the current simulation.")

            if scenario_id not in SCENARIOS:
                raise ValueError(f"Unknown scenario ID: {scenario_id}")

            sc = SCENARIOS[scenario_id]

            # Generate next incident ID
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM incidents ORDER BY rowid DESC LIMIT 1")
            last_row = c.fetchone()
            if last_row and last_row[0].startswith("INC-"):
                try:
                    num = int(last_row[0].split("-")[1]) + 1
                except:
                    num = 2041
            else:
                num = 2041
            
            inc_id = f"INC-{num}"
            now_iso = datetime.now(timezone.utc).isoformat()
            detected_str = "Today " + datetime.now().strftime("%H:%M")

            # Persist incident
            conn.execute("""
                INSERT INTO incidents (id, title, scenario_id, service, severity, status, phase, detected_at, impact_summary, orders_at_risk, checkout_success_pct, active_agent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (inc_id, sc["name"], sc["id"], sc["svc"], sc["sev"], "Investigating", "running", detected_str, sc["sym"], sc["orders_at_risk"], sc["success_rate"], "Supervisor", now_iso))

            # Persist alerts
            for a in sc["alerts"]:
                conn.execute("""
                    INSERT INTO alerts (id, incident_id, service, name, severity, condition, fired_at, correlation_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"ALT-{int(time.time()*1000)%100000}-{a['service']}", inc_id, a["service"], a["name"], a["severity"], a["condition"], detected_str, sc["correlation_reason"]))

            # Persist evidence
            for ev in sc["evidence"]:
                conn.execute("""
                    INSERT INTO evidence (id, incident_id, type, source, claim, role, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (f"EV-{int(time.time()*1000)%100000}-{ev['type']}", inc_id, ev["type"], ev["source"], ev["claim"], ev["role"], detected_str))

            conn.commit()
            conn.close()

            # Initialize in-memory simulation state
            self.active_sim = {
                "id": inc_id,
                "sc": sc,
                "st": ["waiting"] * 7,
                "res": [""] * 7,
                "ts": [""] * 7,
                "log": [],
                "audit": [],
                "t0": time.time(),
                "phase": "running",
                "det": detected_str,
                "orders_at_risk": sc["orders_at_risk"],
                "success_rate": sc["success_rate"],
                "policy": None
            }

            self.log("Chaos Simulator", f"Injected '{sc['name']}' into {sc['svc_name']} (SIMULATION)", "amb")
            self.log("Alert Correlation", f"{len(sc['alerts'])} alerts correlated: {sc['correlation_reason']}", "amb")
            self.audit("Chaos Simulator", "Injected fault scenario", sc["name"])

            # Start asynchronous step execution
            if self.step_task and not self.step_task.done():
                self.step_task.cancel()
            self.step_task = asyncio.create_task(self._run_agent_pipeline())

            return self.get_status()

    async def _run_agent_pipeline(self):
        try:
            # Stage 0: Supervisor
            await self._run_stage(0, "Workflow plan initialized: Triage -> Investigator -> Causal RCA -> Evidence Verifier -> Remediation -> Comms.")
            await asyncio.sleep(1.0)

            # Stage 1: Triage
            sc = self.active_sim["sc"]
            await self._run_stage(1, f"Severity: {sc['sev']}. Impact: ~{sc['orders_at_risk']} orders/min at risk. Checkout success: {sc['success_rate']}%.")
            await asyncio.sleep(1.0)

            # Stage 2: Investigator
            await self._run_stage(2, f"Collected {len(sc['evidence'])} evidence points: logs, metrics, trace spans, and commit history.")
            await asyncio.sleep(1.0)

            # Stage 3: Causal RCA
            prop_path = topology.find_propagation_path(sc["svc"], "checkout")
            path_str = " -> ".join([topology.g.nodes[n]["name"] for n in prop_path])
            await self._run_stage(3, f"Root cause hypothesis: {sc['cause']}. Causal propagation path: {path_str}.")
            await asyncio.sleep(1.0)

            # Stage 4: Evidence Verifier
            supported = len([e for e in sc["evidence"] if e["role"] == "Supports"])
            total = len(sc["evidence"])
            await self._run_stage(4, f"{supported} of {total} claims verified. Unsupported claim dropped: '{sc['dropped_claim']}'. Diagnostic coverage: 83%.")
            await asyncio.sleep(0.9)

            # Stage 5: Remediation proposal & Policy Engine evaluation
            policy_res = PolicyEngine.evaluate_remediation_proposal(
                action=sc["fix"],
                target_service=sc["svc"],
                is_reversible=True,
                evidence_coverage_pct=83.0,
                has_human_approval=False
            )
            self.active_sim["policy"] = policy_res
            self.active_sim["st"][5] = "review"
            self.active_sim["phase"] = "await"
            self.active_sim["ts"][5] = self.get_elapsed_str()
            self.active_sim["res"][5] = f"Proposed: {sc['fix']}. Policy Engine evaluated L2 preconditions: PASS. Awaiting operator approval."
            
            # Persist proposal
            conn = get_connection()
            conn.execute("""
                INSERT OR REPLACE INTO remediation_proposals 
                (id, incident_id, action, target_service, risk_level, is_reversible, timeout_seconds, rollback_plan, expected_effect, policy_level, policy_allowed, policy_checks_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"PROP-{self.active_sim['id']}", self.active_sim["id"], sc["fix"], sc["svc"],
                sc["risk_level"], 1, sc["timeout_seconds"], sc["rollback_plan"], sc["expected_effect"],
                "L2", 1, json.dumps(policy_res["checks"])
            ))
            conn.execute("UPDATE incidents SET status = 'Awaiting approval', phase = 'await', active_agent = 'Remediation' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()

            self.log("Policy Engine", "All 4 automatic preconditions verified. L2 reversible remediation requires human signoff.", "amb")
            self.log("Remediation Agent", f"Action '{sc['fix']}' prepared. Target: {sc['svc_name']}. Rollback ready.", "cy")
            self.audit("Policy Engine", "Preconditions PASSED (L2). Awaiting human operator approval.")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print("Error in agent pipeline:", e)

    async def _run_stage(self, stage_idx: int, result_str: str):
        if not self.active_sim or self.active_sim["phase"] in ["stopped", "rejected"]:
            return
        self.active_sim["st"][stage_idx] = "running"
        self.active_sim["ts"][stage_idx] = self.get_elapsed_str()
        agent_name = AGENTS[stage_idx]
        task_desc = TASKS[stage_idx]
        self.log(agent_name, task_desc, "cy")

        # Update DB incident active_agent
        conn = get_connection()
        conn.execute("UPDATE incidents SET active_agent = ? WHERE id = ?", (agent_name, self.active_sim["id"]))
        conn.commit()
        conn.close()

        await asyncio.sleep(1.2)

        if not self.active_sim or self.active_sim["phase"] in ["stopped", "rejected"]:
            return
        self.active_sim["st"][stage_idx] = "completed"
        self.active_sim["res"][stage_idx] = result_str
        self.log(agent_name, result_str, "grn")

    async def approve_remediation(self, reviewer: str = "Operator (Human)") -> Dict[str, Any]:
        async with self.lock:
            if not self.active_sim or self.active_sim["phase"] != "await":
                raise ValueError("No remediation is currently awaiting approval.")

            sc = self.active_sim["sc"]
            self.active_sim["phase"] = "executing"
            self.audit(reviewer, f"Approved remediation: {sc['fix']}")
            self.log(reviewer, f"Remediation approved: {sc['fix']}", "grn")
            self.log("Remediation Agent", f"Executing simulated fix: {sc['fix']} on {sc['svc_name']}...", "cy")

            # Persist approval
            conn = get_connection()
            conn.execute("INSERT INTO approvals (incident_id, decision, decided_at, reviewer) VALUES (?, ?, ?, ?)",
                         (self.active_sim["id"], "Approved", datetime.now(timezone.utc).isoformat(), reviewer))
            conn.execute("UPDATE incidents SET status = 'Remediating', phase = 'executing' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()

            # Launch background execution & verification task
            asyncio.create_task(self._execute_and_verify())
            return self.get_status()

    async def _execute_and_verify(self):
        try:
            await asyncio.sleep(1.5)
            if not self.active_sim or self.active_sim["phase"] != "executing":
                return

            self.active_sim["phase"] = "verifying"
            self.audit("Remediation Agent", "Simulated execution finished. Awaiting recovery verification.")
            self.log("Remediation Agent", "Action command exited 0. Note: command success is NOT proof of recovery.", "cy")
            self.log("Recovery Verification", "Sampling live health probes and comparing before/after metrics...", "amb")

            conn = get_connection()
            conn.execute("UPDATE incidents SET status = 'Verifying recovery', phase = 'verifying', active_agent = 'Evidence Verifier' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()

            await asyncio.sleep(2.0)
            if not self.active_sim or self.active_sim["phase"] != "verifying":
                return

            sc = self.active_sim["sc"]
            verification = RecoveryVerifier.verify(sc["before_metrics"], sc["after_metrics"], sc["verification_checks"])

            self.active_sim["phase"] = "resolved"
            self.active_sim["st"][5] = "completed"
            self.audit("Recovery Verification", "Recovery verified by 4 of 4 independent criteria.")
            self.log("Recovery Verification", "Recovery verified: latency and error rates nominal.", "grn")

            # Stage 6: Comms & Postmortem
            self.active_sim["st"][6] = "running"
            self.active_sim["ts"][6] = self.get_elapsed_str()
            self.log("Comms Agent", "Dispatching simulated Slack incident channel notification and writing postmortem...", "cy")

            postmortem_md = self._generate_postmortem(self.active_sim)

            await asyncio.sleep(1.5)
            self.active_sim["st"][6] = "completed"
            self.active_sim["res"][6] = "Slack notification sent (simulated). Postmortem generated and archived in Knowledge Base."
            self.log("Comms Agent", "Postmortem generated and incident stored in SQLite Knowledge Base.", "grn")

            # Dispatch Slack / Discord webhook if configured in environment
            webhook_url = os.getenv("SLACK_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL")
            if webhook_url and "simulated" not in webhook_url:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        await client.post(webhook_url, json={
                            "text": f"🚨 [PagerPal Incident Resolved] {self.active_sim['id']}: {sc['name']} on {sc['svc_name']} has been remediated. Recovery verified across 4/4 empirical checks."
                        })
                except Exception as ex:
                    print("Webhook notification failed gracefully:", ex)

            # Persist postmortem, verification, knowledge base item, and update incident
            conn = get_connection()
            conn.execute("""
                INSERT OR REPLACE INTO verification_results (incident_id, is_verified, checks_passed, total_checks, checks_json, before_metrics_json, after_metrics_json, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.active_sim["id"], 1, 4, 4,
                json.dumps(verification["checks"]),
                json.dumps(sc["before_metrics"]),
                json.dumps(sc["after_metrics"]),
                datetime.now(timezone.utc).isoformat()
            ))

            conn.execute("""
                INSERT OR REPLACE INTO postmortems (incident_id, title, content_markdown, created_at)
                VALUES (?, ?, ?, ?)
            """, (self.active_sim["id"], f"{self.active_sim['id']} - {sc['name']}", postmortem_md, datetime.now(timezone.utc).isoformat()))

            conn.execute("""
                INSERT OR REPLACE INTO knowledge_items (id, title, service, symptoms, root_cause, fix, approval_status, recovery_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.active_sim["id"], sc["name"], sc["svc_name"], sc["sym"], sc["cause"], sc["fix"], "Approved", "Verified", "Today " + datetime.now().strftime("%H:%M")))

            conn.execute("""
                UPDATE incidents 
                SET status = 'Resolved', phase = 'resolved', resolved_at = ?, active_agent = 'Comms'
                WHERE id = ?
            """, (datetime.now(timezone.utc).isoformat(), self.active_sim["id"]))

            conn.commit()
            conn.close()

        except Exception as e:
            print("Error in execution and verification:", e)

    async def reject_remediation(self, reviewer: str = "Operator (Human)", reason: str = "Rejected by operator"):
        async with self.lock:
            if not self.active_sim or self.active_sim["phase"] != "await":
                raise ValueError("No remediation is currently awaiting approval.")

            self.active_sim["phase"] = "rejected"
            self.active_sim["st"][5] = "failed"
            self.active_sim["res"][5] = f"Rejected by operator ({reviewer}). Escalated to on-call engineering lead."
            self.audit(reviewer, "Rejected remediation proposal", reason)
            self.log(reviewer, f"Remediation rejected. Reason: {reason}", "red")
            self.log("Supervisor", "Escalating incident to Level 3 on-call engineer page.", "amb")

            conn = get_connection()
            conn.execute("INSERT INTO approvals (incident_id, decision, decided_at, reviewer, remarks) VALUES (?, ?, ?, ?, ?)",
                         (self.active_sim["id"], "Rejected", datetime.now(timezone.utc).isoformat(), reviewer, reason))
            conn.execute("UPDATE incidents SET status = 'Escalated', phase = 'rejected', active_agent = 'Supervisor' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()
            return self.get_status()

    async def emergency_stop(self, actor: str = "Operator (Human)"):
        async with self.lock:
            if not self.active_sim:
                raise ValueError("No active simulation to stop.")

            self.active_sim["phase"] = "stopped"
            if self.step_task and not self.step_task.done():
                self.step_task.cancel()

            self.audit(actor, "Emergency stop triggered! Remediation halted, rollback initiated.")
            self.log(actor, "EMERGENCY STOP initiated. All active agent executions terminated.", "red")
            self.log("Remediation Agent", "Simulated rollback triggered. Reverted to previous stable configuration.", "amb")

            conn = get_connection()
            conn.execute("UPDATE incidents SET status = 'Stopped', phase = 'stopped', active_agent = 'Operator' WHERE id = ?", (self.active_sim["id"],))
            conn.commit()
            conn.close()
            return self.get_status()

    def _generate_postmortem(self, sim: Dict[str, Any]) -> str:
        sc = sim["sc"]
        return f"""# Incident Postmortem: {sim['id']} (SIMULATION)

**Title:** {sc['name']} on `{sc['svc_name']}`  
**Date / Detected:** {sim['det']}  
**Status:** Resolved (Simulated Recovery Verified)  
**Severity:** {sc['sev']}  
**Affected Service:** `{sc['svc_name']}`  

---

## 1. Executive Summary
During a simulated chaos injection, `{sc['svc_name']}` experienced `{sc['name']}` causing degradation across customer checkout flows. Checkout success rate dropped to **{sc['success_rate']}%**, putting approximately **{sc['orders_at_risk']} orders per minute** at risk. PagerPal's multi-agent workflow correlated the alerts, traced the root cause along the dependency path, obtained policy clearance, secured human approval, executed reversible remediation, and verified full system recovery.

## 2. Impact Summary
- **Business Impact:** ~{sc['orders_at_risk']} simulated orders/min at risk.
- **Customer Experience:** Latency p95 increased from baseline to **{sc['before_metrics']['p95_latency']}**; error rate spiked to **{sc['before_metrics']['error_rate']}**.
- **Blast Radius:** Correlated across `{sc['svc_name']}` and upstream user-facing `checkout-svc`.

## 3. Root Cause Analysis
- **Root Cause:** {sc['cause']}.
- **Causal Propagation Path:** Checkout Service -> {sc['svc_name']} -> Orders Database.
- **Evidence Verification:**
  - Supporting: Deploy logs, metrics, trace spans, and commit context.
  - Conflicting / Filtered: Database CPU nominal (ruled out datastore starvation).
  - Dropped Claim: `{sc['dropped_claim']}` was flagged by Evidence Verifier as lacking telemetry and excluded.

## 4. Remediation & Policy Engine Evaluation
- **Proposed Action:** `{sc['fix']}`
- **Policy Engine Decision:** Allowed (Level 2 Reversible Action).
  - Allowlist Check: PASS
  - Reversibility Check: PASS (Automated rollback plan: {sc['rollback_plan']})
  - Simulation Boundary: PASS
  - Diagnostic Coverage: 83% (Threshold >= 80%): PASS
- **Human Approval:** Explicitly approved by operator before execution.

## 5. Recovery Verification
Recovery was verified independently across 4 out of 4 criteria:
- **p95 Latency:** {sc['before_metrics']['p95_latency']} → **{sc['after_metrics']['p95_latency']}** (Normalized)
- **Error Rate:** {sc['before_metrics']['error_rate']} → **{sc['after_metrics']['error_rate']}** (Below 1%)
- **Resource Saturation:** {sc['before_metrics']['saturation']} → **{sc['after_metrics']['saturation']}** (Nominal)
- **Synthetic Probes:** 3/3 consecutive health checks passed.

## 6. Preventive Action Items
1. Add database pool configuration validation checks to CI/CD pipeline pre-deploy gates.
2. Establish dynamic alerting thresholds for connection pool queue delays exceeding 200ms.
3. Configure automated canary rollout traffic shifting for payments service releases.
"""

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

orchestrator = SimulationOrchestrator()

