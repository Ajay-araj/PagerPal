import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, get_connection
from backend.models import (
    SimulationStartRequest, ApprovalRequest, RejectRequest, StopRequest,
    SettingsUpdateRequest
)
from backend.scenarios import SCENARIOS
from backend.graph import topology
from backend.orchestrator import orchestrator, AGENTS
from backend.policy.engine import PolicyEngine
from backend.recovery.verify import RecoveryVerifier
from backend.memory.kb import kb
from backend.postmortem.generator import PostmortemGenerator
from backend.eval.run_eval import run_evaluation

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="PagerPal API",
    description="Evidence-Driven, Safety-Controlled Autonomous Incident Response API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (supports localhost & Vercel production URLs)
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]
frontend_url_env = os.environ.get("FRONTEND_URL")
if frontend_url_env:
    for u in frontend_url_env.split(","):
        u = u.strip()
        if u and u not in allowed_origins:
            allowed_origins.append(u)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not frontend_url_env else allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app" if frontend_url_env else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def get_health():
    return {
        "status": "healthy",
        "environment": "SIMULATION",
        "message": "PagerPal API running. All data is simulated; no production systems connected.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/dashboard")
def get_dashboard():
    sim_status = orchestrator.get_status()
    is_busy = sim_status["active"] and sim_status["sim"]["phase"] in ["running", "await", "executing", "verifying"]

    conn = get_connection()
    c = conn.cursor()

    # 1. Real active incidents count from SQLite
    c.execute("SELECT COUNT(*) FROM incidents WHERE status != 'Resolved'")
    db_active = c.fetchone()[0]
    active_incidents = max(db_active, 1 if is_busy else 0)

    # 2. Real critical alerts count
    c.execute("SELECT COUNT(*) FROM alerts WHERE severity IN ('Critical', 'High')")
    critical_alerts = c.fetchone()[0]
    if is_busy and critical_alerts == 0:
        critical_alerts = len(sim_status["sim"].get("alerts", []))

    # 3. Real services affected count
    c.execute("SELECT COUNT(DISTINCT service) FROM incidents WHERE status != 'Resolved'")
    services_affected = c.fetchone()[0]
    if is_busy and services_affected == 0:
        services_affected = 1

    # 4. Real MTTR computed from resolved incidents in SQLite (accurately distinguishes measured vs simulated estimate)
    c.execute("SELECT detected_at, resolved_at FROM incidents WHERE status = 'Resolved' AND resolved_at IS NOT NULL")
    resolved_rows = c.fetchall()
    durations = []
    for r in resolved_rows:
        try:
            d_str = r["detected_at"]
            r_str = r["resolved_at"]
            if d_str and r_str:
                d_dt = datetime.fromisoformat(d_str) if "T" in d_str else datetime.strptime(d_str[:16], "%Y-%m-%d %H:%M")
                r_dt = datetime.fromisoformat(r_str) if "T" in r_str else datetime.strptime(r_str[:16], "%Y-%m-%d %H:%M")
                dur = (r_dt - d_dt).total_seconds()
                if dur > 0:
                    durations.append(dur)
        except Exception:
            pass

    if durations:
        avg_sec = sum(durations) / len(durations)
        m = int(avg_sec // 60)
        s = int(avg_sec % 60)
        mttr_value = f"{m}m {s}s"
        mttr_type = "measured"
    else:
        mttr_value = "2m 15s"
        mttr_type = "simulated estimate"

    mttr_display = f"{mttr_value} ({mttr_type})"

    # Service health
    active_svc = sim_status["sim"]["scenario"]["svc"] if is_busy else None
    resolved = not is_busy
    service_health = topology.calculate_health(active_svc, resolved)

    # Recent incidents
    c.execute("""
        SELECT id, title, scenario_id, service, severity, status, phase, detected_at, active_agent
        FROM incidents
        ORDER BY rowid DESC
        LIMIT 6
    """)
    rows = c.fetchall()
    recent_incidents = []
    for r in rows:
        recent_incidents.append({
            "id": r["id"],
            "title": r["title"],
            "scenario_id": r["scenario_id"],
            "service": r["service"],
            "severity": r["severity"],
            "status": r["status"],
            "phase": r["phase"],
            "detected_at": r["detected_at"],
            "active_agent": r["active_agent"],
            "is_live": (sim_status["active"] and sim_status["sim"]["id"] == r["id"])
        })

    # Recent activity logs
    recent_logs = []
    if is_busy and sim_status["sim"]["log"]:
        recent_logs = sim_status["sim"]["log"][-8:][::-1]
    else:
        recent_logs = [
            {"t": "00:00", "a": "System", "m": "All systems nominal. Ready to start Chaos Mode.", "c": "grn"}
        ]

    # 5. Real daily incident trend grouped from SQLite
    c.execute("""
        SELECT substr(detected_at, 1, 10) as dt, COUNT(*) as cnt
        FROM incidents
        GROUP BY substr(detected_at, 1, 10)
        ORDER BY dt DESC
        LIMIT 7
    """)
    trend_rows = c.fetchall()
    trend_data = []
    if trend_rows:
        for tr in reversed(trend_rows):
            dt_str = tr["dt"]
            try:
                dt_obj = datetime.strptime(dt_str, "%Y-%m-%d")
                day_name = dt_obj.strftime("%a")
            except Exception:
                day_name = dt_str[-5:]
            trend_data.append({"day": day_name, "count": tr["cnt"]})
    else:
        trend_data = [
            {"day": "Mon", "count": 1},
            {"day": "Tue", "count": 2},
            {"day": "Today", "count": 1}
        ]

    conn.close()

    return {
        "is_simulation_active": is_busy,
        "active_incidents": active_incidents,
        "critical_alerts": critical_alerts,
        "services_affected": services_affected,
        "mttr": mttr_display,
        "mttr_value": mttr_value,
        "mttr_type": mttr_type,
        "service_health": list(service_health.values()),
        "recent_incidents": recent_incidents,
        "recent_logs": recent_logs,
        "trend_data": trend_data,
        "active_sim": sim_status["sim"] if is_busy else None
    }

@app.get("/api/scenarios")
def get_scenarios():
    return list(SCENARIOS.values())

@app.post("/api/simulations")
async def start_simulation(payload: SimulationStartRequest):
    try:
        res = await orchestrator.start_scenario(payload.scenario_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

@app.get("/api/simulations/active")
def get_active_simulation():
    return orchestrator.get_status()

@app.get("/api/simulations/{sim_id}")
def get_simulation_by_id(sim_id: str):
    status = orchestrator.get_status()
    if status["active"] and status["sim"]["id"] == sim_id:
        return status["sim"]

    # Fallback to DB
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM incidents WHERE id = ?", (sim_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Load agent logs
    c.execute("SELECT agent_name as a, summary as m, color as c, elapsed_str as t FROM agent_events WHERE incident_id = ?", (sim_id,))
    logs = [dict(r) for r in c.fetchall()]

    # Load audit
    c.execute("SELECT timestamp, actor, action, details FROM audit_logs WHERE incident_id = ?", (sim_id,))
    audit = [[r["timestamp"], f"{r['actor']}: {r['action']} {r['details'] or ''}".strip()] for r in c.fetchall()]

    conn.close()
    return {
        "id": row["id"],
        "scenario": SCENARIOS.get(row["scenario_id"], {}),
        "phase": row["phase"],
        "status": row["status"],
        "detected": row["detected_at"],
        "log": logs,
        "audit": audit,
        "orders_at_risk": row["orders_at_risk"],
        "success_rate": row["checkout_success_pct"]
    }

@app.get("/api/incidents")
def list_incidents(
    q: Optional[str] = Query(default=None, description="Search term"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    status: Optional[str] = Query(default=None, description="Filter by status")
):
    # Support both FastAPI dependency injection and direct function calls in tests
    q_val = q if isinstance(q, str) else None
    severity_val = severity if isinstance(severity, str) else None
    status_val = status if isinstance(status, str) else None

    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if severity_val:
        query += " AND severity = ?"
        params.append(severity_val)
    if status_val:
        query += " AND status = ?"
        params.append(status_val)

    query += " ORDER BY rowid DESC"
    c.execute(query, params)
    rows = c.fetchall()

    incidents = []
    sim_status = orchestrator.get_status()
    active_id = sim_status["sim"]["id"] if sim_status["active"] else None

    for r in rows:
        d = dict(r)
        d["is_live"] = (active_id == d["id"] and sim_status["sim"]["phase"] in ["running", "await", "executing", "verifying"])
        if q_val:
            term = q_val.lower()
            if term not in d["id"].lower() and term not in d["title"].lower() and term not in d["service"].lower():
                continue
        incidents.append(d)

    conn.close()
    return incidents

@app.get("/api/incidents/{incident_id}")
def get_incident_detail(incident_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    inc = c.fetchone()
    if not inc:
        conn.close()
        raise HTTPException(status_code=404, detail="Incident not found")

    inc_dict = dict(inc)
    sc = SCENARIOS.get(inc_dict.get("scenario_id") or "deploy", SCENARIOS["deploy"])

    # Correlated alerts
    c.execute("SELECT * FROM alerts WHERE incident_id = ?", (incident_id,))
    alerts = [dict(r) for r in c.fetchall()]
    if not alerts:
        alerts = sc["alerts"]

    # Evidence
    c.execute("SELECT * FROM evidence WHERE incident_id = ?", (incident_id,))
    evidence = [dict(r) for r in c.fetchall()]
    if not evidence:
        evidence = sc["evidence"]

    # Remediation Proposal
    c.execute("SELECT * FROM remediation_proposals WHERE incident_id = ?", (incident_id,))
    prop = c.fetchone()
    proposal = dict(prop) if prop else None
    if proposal and proposal.get("policy_checks_json"):
        proposal["policy_checks"] = json.loads(proposal["policy_checks_json"])

    # Verification results
    c.execute("SELECT * FROM verification_results WHERE incident_id = ?", (incident_id,))
    ver = c.fetchone()
    verification = dict(ver) if ver else None
    if verification:
        if verification.get("checks_json"):
            verification["checks"] = json.loads(verification["checks_json"])
        if verification.get("before_metrics_json"):
            verification["before_metrics"] = json.loads(verification["before_metrics_json"])
        if verification.get("after_metrics_json"):
            verification["after_metrics"] = json.loads(verification["after_metrics_json"])
    else:
        verification = {
            "is_verified": inc_dict["phase"] == "resolved",
            "before_metrics": sc["before_metrics"],
            "after_metrics": sc["after_metrics"],
            "checks": [{"description": ch, "passed": inc_dict["phase"] == "resolved"} for ch in sc["verification_checks"]]
        }

    # Audit Trail
    c.execute("SELECT * FROM audit_logs WHERE incident_id = ? ORDER BY id ASC", (incident_id,))
    audit_rows = c.fetchall()
    audit = [[r["timestamp"], f"{r['actor']}: {r['action']} {r['details'] or ''}".strip()] for r in audit_rows]

    # Postmortem
    c.execute("SELECT * FROM postmortems WHERE incident_id = ?", (incident_id,))
    pm_row = c.fetchone()
    postmortem = dict(pm_row) if pm_row else None

    # Live state if active
    sim_status = orchestrator.get_status()
    is_live = sim_status["active"] and sim_status["sim"]["id"] == incident_id
    if is_live:
        inc_dict["phase"] = sim_status["sim"]["phase"]
        inc_dict["status"] = {
            "running": "Investigating",
            "await": "Awaiting approval",
            "executing": "Remediating",
            "verifying": "Verifying recovery",
            "resolved": "Resolved",
            "rejected": "Escalated",
            "stopped": "Stopped"
        }.get(inc_dict["phase"], inc_dict["status"])

    conn.close()
    return {
        "incident": inc_dict,
        "scenario": sc,
        "alerts": alerts,
        "evidence": evidence,
        "proposal": proposal,
        "verification": verification,
        "audit": audit,
        "postmortem": postmortem,
        "is_live": is_live
    }

@app.get("/api/incidents/{incident_id}/evidence")
def get_incident_evidence(incident_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM evidence WHERE incident_id = ?", (incident_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@app.get("/api/incidents/{incident_id}/timeline")
def get_incident_timeline(incident_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM agent_events WHERE incident_id = ? ORDER BY id ASC", (incident_id,))
    events = [dict(r) for r in c.fetchall()]
    conn.close()
    return events

@app.get("/api/incidents/{incident_id}/graph")
def get_incident_graph(incident_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT service, status, phase FROM incidents WHERE id = ?", (incident_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return topology.get_graph_data(None, True)

    is_resolved = row["phase"] == "resolved"
    is_verified = is_resolved or row["phase"] in ["verifying", "await", "executing"]
    return topology.get_graph_data(row["service"], is_resolved, is_verified)

@app.post("/api/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str, payload: ApprovalRequest = ApprovalRequest()):
    sim_status = orchestrator.get_status()
    if not sim_status["active"] or sim_status["sim"]["id"] != incident_id:
        raise HTTPException(status_code=400, detail="Incident is not currently active for approval")
    try:
        res = await orchestrator.approve_remediation(payload.reviewer)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/incidents/{incident_id}/reject")
async def reject_incident(incident_id: str, payload: RejectRequest = RejectRequest()):
    sim_status = orchestrator.get_status()
    if not sim_status["active"] or sim_status["sim"]["id"] != incident_id:
        raise HTTPException(status_code=400, detail="Incident is not currently active for decision")
    try:
        res = await orchestrator.reject_remediation(payload.reviewer, payload.reason)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/incidents/{incident_id}/stop")
async def stop_incident(incident_id: str, payload: StopRequest = StopRequest()):
    sim_status = orchestrator.get_status()
    if not sim_status["active"] or sim_status["sim"]["id"] != incident_id:
        raise HTTPException(status_code=400, detail="Incident is not currently active")
    try:
        res = await orchestrator.emergency_stop(payload.actor)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/incidents/{incident_id}/postmortem")
def get_postmortem(incident_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM postmortems WHERE incident_id = ?", (incident_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Postmortem not generated yet for this incident")
    return dict(row)

@app.get("/api/knowledge")
def list_knowledge(q: Optional[str] = None):
    q_val = q if isinstance(q, str) else None
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM knowledge_items ORDER BY rowid DESC"
    c.execute(query)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if q_val:
        term = q_val.lower()
        rows = [r for r in rows if term in r["title"].lower() or term in r["symptoms"].lower() or term in r["root_cause"].lower() or term in r["service"].lower()]
    return rows

@app.get("/api/kb/similar")
def get_similar_incidents(
    service: Optional[str] = Query(None, description="Target service ID"),
    fault_type: Optional[str] = Query(None, description="Fault category"),
    symptoms: Optional[str] = Query(None, description="Symptom keywords"),
    limit: int = Query(5, ge=1, le=20)
):
    """
    Returns past incident remediation records as suggestions for operator review.
    Hard Rule 8: NEVER auto-apply past fixes. All results have suggestion_only=True.
    """
    s_val = service if isinstance(service, str) else None
    f_val = fault_type if isinstance(fault_type, str) else None
    sym_val = symptoms if isinstance(symptoms, str) else None
    lim_val = limit if isinstance(limit, int) else 5

    suggestions = kb.search_similar(service=s_val, fault_type=f_val, symptoms=sym_val, limit=lim_val)
    return {
        "query": {
            "service": s_val,
            "fault_type": f_val,
            "symptoms": sym_val
        },
        "count": len(suggestions),
        "suggestions": suggestions,
        "governance": {
            "hard_rule_8_enforced": True,
            "auto_apply_allowed": False,
            "notice": "Past incident fixes are strictly informational suggestions for human review. Never auto-applied."
        }
    }

@app.get("/api/settings")
def get_settings():
    return {
        "simulation_mode": True,
        "environment": "SIMULATION",
        "no_production_connected": True,
        "enforce_human_approval": True,
        "policy_engine_active": True,
        "l1_auto_diagnostics": True,
        "l2_remediation_approval_required": True,
        "webhook_url": "https://hooks.slack.com/services/simulated/pagerpal/incidents",
        "stack_info": {
            "language": "Python 3.14",
            "api_framework": "FastAPI",
            "database": "SQLite",
            "causal_graph": "NetworkX",
            "ui_framework": "React 19 + Tailwind CSS"
        }
    }

@app.post("/api/settings")
def update_settings(payload: SettingsUpdateRequest):
    return {
        "status": "updated",
        "settings": payload.model_dump()
    }

@app.post("/api/evaluate")
def run_evaluation_suite():
    """
    Evaluates chaos scenarios and computes actual measured metrics
    against Section 10 targets from the spec using the evaluation harness.
    """
    return run_evaluation()

# Serve compiled React frontend assets when available
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
assets_dir = os.path.join(frontend_dist, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    if not os.path.exists(frontend_dist):
        return {"message": "PagerPal API running. Frontend not yet built in /frontend/dist."}
    target_file = os.path.join(frontend_dist, full_path)
    if full_path and os.path.isfile(target_file):
        return FileResponse(target_file)
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return {"message": "PagerPal API ready"}

