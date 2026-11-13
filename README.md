⚡ PAGERPAL

Autonomous Multi-Agent Incident Response Console

From incident detection to evidence-backed resolution — intelligently, safely, and autonomously.

<p align="center">Built for AgentX | SYNERGY | Syedric College

</p><p align="center">
  <img src="https://img.shields.io/badge/AI-Multi--Agent%20System-8B5CF6?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Orchestration-LangGraph-2563EB?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge" />
</p><p align="center">
  <a href="https://pagerpal.vercel.app/">🌐 Live Demo</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-team">Team</a>
</p>---

🚨 The Problem

Modern software systems operate through interconnected services, databases, APIs, and infrastructure components.

When something breaks, engineers often need to:

- Investigate multiple monitoring dashboards.
- Correlate alerts, logs, metrics, and traces.
- Identify the actual root cause.
- Understand the impact on downstream services.
- Decide which remediation action is safe.
- Verify whether the system has recovered.

This process can consume valuable time, especially during critical incidents.

💡 Our Solution — PagerPal

PagerPal is an evidence-driven, safety-controlled autonomous incident response platform powered by a multi-agent AI architecture.

It transforms traditional incident management into an intelligent workflow where specialized AI agents collaborate to investigate incidents, identify root causes, evaluate risks, and recommend safe remediation actions.

Unlike conventional AI automation tools, PagerPal separates AI decision-making from execution permissions through an independent Python-based policy engine.

Our vision:

«Turn a 30-minute, 3 AM incident-response scramble into a 2-minute, evidence-backed approve-and-resolve workflow.»

🌐 Live Application: https://pagerpal.vercel.app/

---

✨ Key Features

1. Multi-Agent AI Investigation

PagerPal uses LangGraph to coordinate specialized agents through a structured incident-response workflow.

Agent| Responsibility
Supervisor Agent| Controls workflow execution and agent coordination
Triage Agent| Evaluates incident severity and blast radius
Investigator Agent| Examines logs, metrics, traces, and deployments
Causal RCA Engine| Identifies probable root causes through dependency graphs
Evidence Verifier| Validates investigation claims against telemetry
Confidence Scorer| Calculates deterministic confidence scores
Remediation Agent| Recommends approved recovery actions
Communications Agent| Generates notifications and incident postmortems

2. Causal Root Cause Analysis

Powered by NetworkX, PagerPal models service dependencies as a directed graph.

It helps identify:

- Probable root causes.
- Upstream and downstream dependencies.
- Causal paths between affected services.
- Counterfactual checks.
- Potential blast radius.

3. Evidence-Based Verification

PagerPal does not blindly trust AI-generated conclusions.

Investigation claims are checked against empirical telemetry. Unsupported claims are rejected through bounded verification and retry mechanisms.

4. Independent Safety Policy Engine

A dedicated Python policy engine controls what the system is allowed to execute.

- L1: Safe diagnostic operations.
- L2: Approved, reversible remediation actions.
- L3: High-risk actions requiring escalation.

The LLM cannot override the policy engine.

5. Human-in-the-Loop Approval

Remediation is not automatically executed just because an AI agent recommends it.

A mandatory human approval checkpoint is enforced through LangGraph interrupts.

The operator can review, approve, or reject the proposed action.

6. Independent Recovery Verification

After an approved remediation, PagerPal compares before-and-after system metrics.

Recovery checks include:

- P95 latency.
- Error rates.
- Synthetic health probes.

If recovery verification fails, the incident is escalated instead of being incorrectly marked as resolved.

7. Incident Knowledge Base

An SQLite-powered knowledge base stores historical incidents, summaries, and runbooks.

Previous incidents can provide suggestions, but historical fixes are never automatically executed.

8. External Integrations

- GitHub API integration for recent commit investigation.
- Slack and Discord webhook notifications.
- Retry mechanisms with backoff.
- Transparent mock fallbacks when external integrations are unavailable.

---

🧠 What Makes PagerPal Different?

PagerPal combines several engineering approaches into one incident-response architecture.

Traditional Monitoring| PagerPal
Displays alerts| Investigates incidents
Requires manual correlation| Correlates telemetry
Relies on manual RCA| Uses causal dependency analysis
Human manually researches fixes| AI proposes evidence-backed remediation
Automation may execute predefined actions| Independent policy engine controls execution
Assumes action success| Independently verifies recovery

The key innovation is not simply using AI to fix incidents. It is combining agentic intelligence with deterministic safety enforcement and human accountability.

---

🏗️ Architecture

PagerPal follows a multi-layer architecture designed to separate investigation, decision-making, safety validation, execution, and recovery verification.

flowchart TD
    A["Simulated Monitoring Telemetry"] --> B["Supervisor Agent"]
    B --> C["Triage Agent"]
    C --> D["Investigator Agent"]
    D --> E["Causal RCA Engine"]
    E --> F["Evidence Verifier"]
    F --> G["Confidence Scorer"]
    G --> H["Remediation Agent"]
    H --> I["Independent Python Policy Engine"]
    I --> J{"Human Approval"}
    J -->|Approved| K["Execute Remediation"]
    J -->|Rejected| L["Stop / Escalate"]
    K --> M["Recovery Verification"]
    M --> N{"Recovery Successful?"}
    N -->|Yes| O["Resolve Incident"]
    N -->|No| L
    O --> P["Knowledge Base & Postmortem"]

Architecture Principles

1. Separation of Intelligence and Authority: AI agents investigate and recommend; the policy engine controls execution permissions.
2. Evidence Before Action: Remediation recommendations must be supported by verified evidence.
3. Human Accountability: Mandatory approval before remediation execution.
4. Verified Recovery: An incident is resolved only after independent recovery checks.
5. Auditable Execution: Incident decisions and actions are recorded.

---

🛠️ Technology Stack

PagerPal combines agentic AI, graph-based causal analysis, deterministic policy enforcement, and immersive infrastructure visualization.

AI & Intelligence Layer

Technology| Purpose
LangGraph| Multi-agent orchestration and workflow state management
Claude| Structured AI reasoning and tool calling
NetworkX| Service dependency graphs and causal RCA
Python Policy Engine| Independent safety validation
Deterministic Confidence Scorer| Rule-based confidence calculation

Backend & Data Layer

Technology| Purpose
Python 3.11+| Core backend development
FastAPI| REST API and backend services
Uvicorn| ASGI server
SQLite| Incident and knowledge persistence
Pytest| Automated testing

Frontend & Visualization Layer

Technology| Purpose
React 18| Interactive frontend
Vite| Development and build tooling
Three.js| 3D infrastructure topology visualization
Sora Typography| Visual identity and interface typography

Deployment & Integrations

Technology| Purpose
Vercel| Frontend deployment
Render| Backend deployment
GitHub API| Repository and commit investigation
Slack / Discord Webhooks| Incident notifications

---

🔐 Safety & Security

PagerPal is designed around controlled autonomy.

- All monitoring telemetry is simulated and labelled "SIMULATION".
- No real customer or financial data is processed by the simulator.
- Diagnostic tools operate through allowlisted, read-only interfaces.
- Untrusted telemetry is sanitized and isolated.
- Remediation actions must match an exact policy allowlist.
- High-risk actions are restricted and escalated.
- Human approval is mandatory before remediation execution.
- Recovery must be independently verified.
- Historical knowledge-base fixes remain suggestions only.

AI proposes. Policy validates. Humans authorize. Recovery verification confirms.

---

📊 Testing & Evaluation

PagerPal includes a comprehensive automated testing and evaluation framework.

Automated Test Suite

Run:

python -m pytest backend/tests/ -v

53 automated tests across five development stages and backend validation.

Test Suite| Coverage
Stage A — Simulator| Fault simulation, reproducibility, ground-truth isolation
Stage B — Correlation & RCA| Alert correlation, causal ranking, missing telemetry
Stage C — Verification & Policy| Evidence validation, confidence scoring, policy enforcement, prompt injection
Stage D — Workflow| End-to-end orchestration, approval/rejection, recovery failure, emergency stop
Stage E — Knowledge Base| SQLite persistence, suggestions, postmortems
Backend Tests| API endpoints, dashboard KPIs, evaluation harness

Evaluation Benchmark

PagerPal supports an automated benchmark across 12 incident scenarios.

Run:

python -m backend.eval.run_eval

Results are generated in:

eval_results/
├── eval_results.csv
└── eval_summary.md

---

🚀 Getting Started

Prerequisites

- Python 3.11 or later.
- Node.js and npm.
- Git.
- Claude API key for AI-powered functionality.

1. Clone the Repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd PagerPal

2. Configure Environment Variables

Create the required environment configuration using the project's supported settings.

Example:

ANTHROPIC_API_KEY=your_api_key

Configure optional GitHub and notification webhook credentials when required.

Never commit API keys or secrets to GitHub.

3. Install Backend Dependencies

Install the dependencies listed in the project's backend requirements file.

pip install -r requirements.txt

4. Install Frontend Dependencies

cd frontend
npm install
cd ..

5. Run the Application

python run.py

Open:

http://localhost:8000

API documentation:

http://localhost:8000/docs

Development Mode

Terminal 1 — Backend

python -m uvicorn backend.main:app --port 8000 --reload

Terminal 2 — Frontend

cd frontend
npm run dev

Open:

http://localhost:5173

---

☁️ Deployment

PagerPal uses a separated frontend and backend deployment architecture.

Component| Platform
Frontend| Vercel
Backend| Render
Database| SQLite

Deployment configuration files:

vercel.json
render.yaml
DEPLOYMENT.md

For complete deployment instructions, refer to "DEPLOYMENT.md".

Live Deployment

🌐 Frontend: https://pagerpal.vercel.app/

---

🎬 Live Demonstration

Explore PagerPal through the deployed application.

Demo: https://pagerpal.vercel.app/

The demonstration showcases:

1. Incident detection and triage.
2. Multi-agent investigation.
3. Causal root cause analysis.
4. Evidence verification and confidence scoring.
5. Remediation recommendation.
6. Human approval and policy enforcement.
7. Recovery verification.
8. Incident reporting and postmortem generation.

For the complete demonstration flow, refer to "DEMO.md".

---

👥 Team

Built by Team PagerPal

Developed for AgentX at SYNERGY, Syedric College.

Team Member
Ajiras Abhishek
Ajay Raj A M
Rishitha R
Rithu

---

🎯 Our Vision

We believe the future of incident management is not just automated monitoring.

It is intelligent systems that can understand failures, investigate evidence, reason about dependencies, recommend safe actions, and verify outcomes — without compromising human control.

PagerPal brings autonomous intelligence and responsible automation together.

<p align="center">⚡ PAGERPAL

Investigate Smarter. Respond Faster. Recover Safely.

Built for AgentX | SYNERGY | Syedric College

</p>
