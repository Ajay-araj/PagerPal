# PagerPal · Incident Response Console

> **Evidence-Driven, Safety-Controlled Autonomous Incident Response Platform**  
> *Problem Track: On-Call Incident Agent (Engineering)*

PagerPal is a simulated, AI-powered incident-response platform built to turn slow, manual incident investigations into a fast, evidence-backed, human-approved workflow.

---

##  Core Features & Non-Negotiable Boundaries

- **Simulated Monitoring Data:** Clearly labeled as `SIMULATION`. No production infrastructure is touched.
- **7-Stage Multi-Agent Workflow:**
  1. **Supervisor:** Coordinates workflow state and routes tasks
  2. **Triage:** Classifies severity, blast radius, and simulated checkout revenue/orders at risk
  3. **Investigator:** Correlates synthetic logs, metrics, trace spans, and commit history
  4. **Causal RCA:** Traverses a NetworkX dependency graph to isolate root causes and trace causal paths
  5. **Evidence Verifier:** Validates claims against telemetry and drops unsupported claims (e.g. false network partition)
  6. **Remediation:** Evaluates allowlisted reversible actions with timeout and rollback guarantees
  7. **Comms:** Dispatches team notifications and compiles detailed Markdown postmortems
- **Independent Rule-Based Policy Engine (L2):** The LLM is never the safety authority. 5 safety checks are enforced, requiring explicit human operator approval before simulated remediation executes.
- **Empirical Recovery Verification:** 4 of 4 independent health probes must pass before resolving an incident. Command completion is never confused with recovery.
- **SQLite Knowledge Base:** Persists historical runbooks, symptoms, verified causes, and recovery outcomes.
- **Dark SRE Operations Console:** Built with React 19, Lucide icons, and high-contrast dark ops aesthetics.

---

##  Architecture & Technology Stack

| Area | Technology | Responsibility |
| :--- | :--- | :--- |
| **Backend API** | FastAPI (Python 3.14) | REST API, simulation engine, agent orchestration |
| **Causal Graph** | NetworkX | Service dependency graph and causal propagation paths |
| **Safety Engine** | Rule-Based Policy Engine | Allowlist, reversibility, simulation boundary & approval enforcement |
| **Recovery Engine** | Empirical Recovery Verifier | 4-point health probe validation (p95 latency, error rate, saturation) |
| **Persistence** | SQLite | Incidents, alerts, evidence, audit logs, and knowledge base |
| **Frontend UI** | React 19 + Vite | Responsive SRE operations console matching dark design system |

---

##  Quick Start

### 1. Run Everything (Backend + Built React Frontend)

The compiled React frontend is embedded directly into FastAPI:

```bash
# Run the combined server
python run.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.  
API documentation is available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

### 2. Run in Development Mode

If you wish to run the Vite dev server with Hot Module Replacement (HMR):

**Terminal 1 (FastAPI Backend):**
```bash
python -m uvicorn backend.main:app --port 8000 --reload
```

**Terminal 2 (React Vite Frontend):**
```bash
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser. All API requests are proxied automatically to port 8000.

---

##  Running the Test Suite

Run the full pytest suite to verify policy enforcement, approval gates, recovery verification, and API endpoints:

```bash
python -m pytest backend/tests/test_backend.py -v
```

All 12 unit and integration tests pass:
- `test_policy_engine_enforces_human_approval`
- `test_policy_engine_blocks_insufficient_evidence`
- `test_recovery_verifier_requires_all_checks`
- `test_networkx_causal_path`
- `test_health_endpoint`
- `test_dashboard_endpoint`
- `test_scenarios_endpoint`
- `test_incidents_listing`
- `test_incident_graph`
- `test_knowledge_endpoint`
- `test_settings_endpoint`
- `test_evaluation_suite_endpoint`

---

##  5-Minute Live Demo Walkthrough

1. **Overview Dashboard:**
   - Observe KPI cards (Active incidents, Critical alerts, Affected services, MTTR)
   - Review the incident trend chart and service health matrix
2. **Inject Chaos Scenario (Chaos Mode):**
   - Click ** Start Chaos Mode** in the top navigation or overview
   - Select **Faulty deployment** (payments-svc) and confirm
3. **Live Multi-Agent Investigation:**
   - Navigate to **Live investigation**
   - Watch the 7 agent stages execute in sequence:
     - Triage calculates ~340 orders/min at risk
     - Investigator collects 6 evidence items
     - Causal RCA traces path: `checkout-svc → payments-svc → orders-db`
     - Evidence Verifier drops unsupported network partition claim
     - Remediation Agent proposes rollback to `v3.8.0`
4. **Safety & Policy Review (Incident Detail):**
   - Policy Engine confirms 4 preconditions pass as **Allowed (L2)**
   - Click **Approve & execute** to provide the required human approval
5. **Recovery Verification:**
   - Watch the before vs. after health metrics:
     - p95 latency drops from `2,840 ms` to `212 ms`
     - Error rate drops from `18.4%` to `0.6%`
   - 4 of 4 verification probes pass
6. **Postmortem & Knowledge Base:**
   - Review the auto-generated Postmortem under **Postmortems** (with one-click "Copy as Markdown" and download)
   - View the incident archived in the SQLite **Knowledge Base**

