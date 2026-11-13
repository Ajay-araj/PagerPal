# PagerPal Live Demo Script (5-Minute Walkthrough)

**Pitch:** "PagerPal turns a 30-minute, 3 a.m. scramble into a 2-minute, evidence-backed approve-and-resolve."

**Target Display:** Optimized for 1366x768 widescreen console layout.  
**Environment:** SIMULATION (All telemetry, traces, and metrics are simulated).

---

## Pre-Flight Check

1. Start backend server:
   ```bash
   python run.py
   ```
   Or independently:
   ```bash
   uvicorn backend.main:app --port 8000
   ```
2. Open browser at `http://localhost:8000` (FastAPI serves compiled React console) or `http://localhost:5173` (Vite dev server).
3. If `ANTHROPIC_API_KEY` is unset, PagerPal automatically runs in deterministic fallback mode with full audit trail logging.

---

## 5-Minute Demo Flow

### Step 1: Overview & Baseline (0:00 - 0:30)
- Navigate to **Operations Overview**.
- Observe cluster topology of 7 simulated microservices (`api-gateway`, `checkout-svc`, `payments-svc`, `inventory-svc`, `auth-svc`, `orders-db`, `cache`).
- Note real SQLite metrics: active incidents, critical alerts, and MTTR labeled as **simulated estimate**.

### Step 2: Inject Chaos Fault (0:30 - 1:00)
- Click **Start Chaos Mode** button in the header.
- Select Scenario: `Faulty Canary Deployment (payments-svc)`.
- Click **Trigger Chaos Event**.
- Observe live transition:
  - Synthetic fault injected on `payments-svc`.
  - Alert Correlation Engine clusters 4 raw alerts into 1 incident by topological distance and symptom similarity.
  - Triage Agent computes customer blast radius: ~180 orders/min at risk, checkout success dropping to ~18%.

### Step 3: Multi-Agent Investigation & Causal RCA (1:00 - 2:00)
- Navigate to **Live Investigation** tab.
- Watch LangGraph StateGraph orchestration:
  - **Supervisor Agent** plans investigation phases.
  - **Investigator Agent** queries allowlisted read-only diagnostic tools (`get_pod_logs`, `get_service_metrics`, `get_trace_spans`, `get_deploy_history`).
  - **Causal RCA Engine** uses NetworkX graph to rank top root cause candidates and compute causal propagation path (`payments-svc` -> `checkout-svc` -> `api-gateway`).
  - Counterfactual simulation check confirms hypothesis with `is_proof=False`.

### Step 4: Evidence Verifier & Policy Engine Gate (2:00 - 2:45)
- Inspect **Evidence Claims**:
  - Evidence Verifier checks every claim against empirical telemetry.
  - Corroborated claims marked `Verified`; speculative claims `Dropped`.
  - Confidence Scorer calculates diagnostic confidence and coverage using deterministic rules (never LLM).
- Inspect **Policy Engine clearance**:
  - Action: `rollback_deployment` on `payments-svc`.
  - Evaluated against exact static L2 allowlist.
  - Preconditions certified (reversibility, rollback plan, 120s timeout, confidence >= 75%, coverage >= 80%).
  - Workflow pauses at LangGraph interrupt gate: **Human Approval Required**.

### Step 5: Operator Approval & Execution (2:45 - 3:30)
- Click **Approve Remediation**.
- Backend receives approval and resumes LangGraph state:
  - Real external GitHub API call queries recent commits for `payments-svc` (falling back to audit-logged mock if unauthenticated).
  - Remediation Executor executes simulated rollback to previous stable container image.
- Point out safety guarantee: Clicking **Reject** would have cleanly escalated to on-call with remediation blocked.

### Step 6: Independent Recovery Verification (3:30 - 4:15)
- Watch **Recovery Verifier**:
  - Compares before vs after metrics: p95 latency restored from 650ms to 12ms; error rate reduced from 18.5% to 0.05%.
  - Confirms 3 consecutive HTTP 200 synthetic health probes.
  - Highlight Hard Rule 6: If metrics had remained degraded, recovery would FAIL, escalating immediately without ever displaying "Resolved".

### Step 7: Postmortem & Knowledge Base (4:15 - 5:00)
- Navigate to **Postmortem Report**:
  - Review dynamic Markdown report with actual timeline, propagation path, and metrics.
  - Note preventive action items: specific to canary testing and release validation (not generic database pool actions).
- Navigate to **Knowledge Base**:
  - Point out newly archived incident.
  - Demonstrate `/api/kb/similar?service=payments`: past fixes are returned strictly as informational suggestions for human review (Hard Rule 8: never auto-applied).
- Check outgoing webhook dispatch: completely clean of raw emojis.

