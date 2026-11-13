# PagerPal ---- Incident Response Console

> **Evidence-Driven, Safety-Controlled Autonomous Incident Response Platform**  
> *One-line pitch:* "PagerPal turns a 30-minute, 3 a.m. scramble into a 2-minute, evidence-backed approve-and-resolve."

> 🌐 **Live Demo:** [https://pagerpal.vercel.app](https://pagerpal.vercel.app/)

PagerPal transforms incident management from manual playback into a multi-agent system powered by LangGraph, Claude structured outputs, NetworkX causal inference, and strict Python policy guardrails.

---

## Core Features and Safety Boundaries

- **Simulated Monitoring Telemetry:** All metrics, logs, traces, and deployments are labelled `SIMULATION`. No real customer or financial data is touched.
- **LangGraph Multi-Agent Orchestration:**
  1. **Supervisor Agent:** Orchestrates state machine and routes investigation phases.
  2. **Triage Agent:** Calculates blast radius and simulated checkout orders at risk.
  3. **Investigator Agent:** Queries allowlisted read-only diagnostic tools. Untrusted telemetry is sanitized and isolated.
  4. **Causal RCA Engine:** Traverses a NetworkX dependency graph to isolate root causes and trace causal paths (counterfactual checks with `is_proof=False`).
  5. **Evidence Verifier:** Validates claims against empirical telemetry, dropping uncorroborated claims through bounded retry loops.
  6. **Confidence Scorer:** Deterministic rule-based scoring (never LLM-generated).
  7. **Remediation Agent:** Proposes reversible Level-2 actions strictly from an exact allowlist.
  8. **Comms Agent:** Dispatches notifications via external webhooks (Slack/Discord) and generates postmortems.
- **Independent Non-LLM Policy Engine:** Pure Python safety gate enforcing L1/L2/L3 boundaries, reversibility, and timeouts. The LLM cannot override it.
- **Mandatory Human Approval Gate:** Human approval is strictly enforced inside the backend before any remediation can execute (via LangGraph checkpoint interrupt).
- **Independent Recovery Verification:** Resolution requires before-vs-after metric verification. Recovery verification can FAIL and must escalate.
- **SQLite Knowledge Base:** Persists historical runbooks and incident summaries. Never auto-applies past fixes (suggestions only).
- **Real External Integrations with Mock Fallback:** GitHub API (recent commits) and Slack/Discord webhooks retry with backoff and fall back to transparently logged mocks.

---

## Architecture and Technology Stack

| Area | Technology | Note |
| :--- | :--- | :--- |
| **Orchestration** | LangGraph + Claude | Structured outputs, tool calling, human-in-the-loop interrupt |
| **Backend API** | FastAPI + Uvicorn | Python 3.11, 3.12, or 3.14 (Windows / Linux / macOS) |
| **Causal Graph** | NetworkX | Topological traversal, root cause ranking, counterfactual checks |
| **Safety Engine** | Policy Engine | Non-LLM exact allowlist matching, L2 reversibility clearance |
| **Recovery Engine** | Recovery Verifier | Empirical SLI validation (p95 latency, error rate, synthetic probes) |
| **Persistence** | SQLite | Incidents, alerts, evidence, audit logs, and knowledge base |
| **Frontend UI** | React 18 + Vite | Pure-black & charcoal command centre, Three.js 3D topology, Sora typography |
| **Cloud Deployment**| Render + Vercel | Production-ready FastAPI web service (`render.yaml`) & SPA frontend (`vercel.json`) |

---

## Deployment to Render & Vercel

Complete deployment configurations and step-by-step guides are documented in [DEPLOYMENT.md](DEPLOYMENT.md).

- **Frontend (Vercel — Live):** 🌐 [https://pagerpal.vercel.app](https://pagerpal.vercel.app/) — `frontend/vercel.json` pre-configured with Vite framework build settings and SPA URL rewrites.
- **Backend (Render):** `render.yaml` pre-configured with Python 3, Uvicorn start command, health checks (`/health`), and optional persistent SQLite storage.

---

## Quick Start

### 1. Run Everything (FastAPI Serves Built React Console)

```bash
# Run the application
python run.py
```
Open **http://localhost:8000** in your browser.  
API documentation is available at **http://localhost:8000/docs**.

---

### 2. Run in Development Mode

**Terminal 1 (FastAPI Backend):**
```bash
python -m uvicorn backend.main:app --port 8000 --reload
```

**Terminal 2 (React Vite Frontend):**
```bash
cd frontend
npm run dev
```
Open **http://localhost:5173** in your browser. All API requests are proxied to port 8000.

---

## Running the Test Suite

Run the full pytest suite (53 comprehensive tests across all stages):

```bash
python -m pytest backend/tests/ -v
```

Test suites include:
- `test_stage_a_simulator.py`: 6 fault types, seed reproducibility, ground-truth isolation
- `test_stage_b_correlation_rca.py`: Dynamic alert correlation, causal RCA ranking, hard cases (noisy logs, drift, missing telemetry)
- `test_stage_c_verifier_policy.py`: Evidence verification, confidence scoring rules, exact policy registry, prompt injection quarantine
- `test_stage_d_workflow.py`: End-to-end LangGraph workflow, approve/reject flows, policy denial, recovery failure escalation, emergency stop
- `test_stage_e_kb_postmortem.py`: SQLite knowledge base, suggestion-only search, dynamic postmortems with tailored action items
- `test_backend.py`: API endpoints, SQLite-backed dashboard KPIs, and evaluation harness

---

## Systematic Evaluation Benchmark

Run the automated evaluation benchmark across all 12 scenarios:

```bash
python -m backend.eval.run_eval
```

Results are saved to `eval_results/eval_results.csv` and `eval_results/eval_summary.md`.

---

## Live Demo Walkthrough

🌐 **Live Application:** [https://pagerpal.vercel.app](https://pagerpal.vercel.app/)

See [DEMO.md](DEMO.md) for the complete 5-minute live demonstration script.
