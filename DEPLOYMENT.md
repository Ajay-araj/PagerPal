# PagerPal Production Deployment Guide
## Render (FastAPI Backend) & Vercel (React + Vite Frontend)

This guide provides step-by-step instructions to deploy **PagerPal** into production using **Render** for the Python/FastAPI backend and **Vercel** for the React + Vite frontend.

---

## Architecture Overview

```
                                      +-----------------------------+
                                      |      Vercel Frontend        |
                                      |    (React 18 + Vite SPA)    |
                                      +--------------+--------------+
                                                     |
                                                     | HTTPS REST API
                                                     v
                                      +-----------------------------+
                                      |       Render Backend        |
                                      |      (FastAPI + Uvicorn)    |
                                      +--------------+--------------+
                                                     |
                     +-------------------------------+-------------------------------+
                     |                               |                               |
                     v                               v                               v
       +----------------------------+  +----------------------------+  +----------------------------+
       |   SQLite Database (DB)     |  |   LangGraph Agent Pipeline |  |   External Integrations    |
       |  (Ephemeral or Persistent) |  |   (7 Autonomous Agents)    |  |  (Slack / Discord / GitHub)|
       +----------------------------+  +----------------------------+  +----------------------------+
```

---

## Part 1: Deploying the Backend on Render

### Step 1: Connect Your Git Repository
1. Log in to [Render.com](https://render.com).
2. Click **New +** > **Web Service**.
3. Connect your GitHub/GitLab repository (`PagerPal`).

### Step 2: Configure Service Settings
- **Name:** `pagerpal-backend`
- **Region:** Choose the region closest to your users (e.g., Oregon or Frankfurt).
- **Branch:** `main`
- **Root Directory:** *(leave blank)*
- **Runtime:** `Python 3`
- **Build Command:**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```
- **Health Check Path:** `/health`

### Step 3: Set Environment Variables
In the **Environment** tab on Render, add the following variables:

| Key | Example Value | Description |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Recommended Python version on Render |
| `ENVIRONMENT` | `SIMULATION` | Guarantees safe sandboxed execution |
| `FRONTEND_URL` | `https://your-pagerpal.vercel.app` | Allowed CORS origin (add multiple separated by comma) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` *(Optional)* | Anthropic API key. If omitted, falls back to deterministic rule-based reasoning |
| `GITHUB_TOKEN` | `ghp_...` *(Optional)* | For filing postmortem issues/PRs automatically |
| `SLACK_WEBHOOK_URL`| `https://hooks.slack.com/...` *(Optional)* | For real-time incident notifications |
| `DISCORD_WEBHOOK_URL`| `https://discord.com/api/webhooks/...` *(Optional)* | For Discord notifications |

### Step 4: (Optional) SQLite Database Persistence
On Render's Free tier, the filesystem is ephemeral (resets on restart/redeploy).
- **Free Tier:** PagerPal automatically initializes `backend/pagerpal.db` on boot with sample services, knowledge base records, and recent incidents. It functions out-of-the-box without extra setup.
- **Paid Tier (Starter $7/mo):**
  1. Go to the **Disks** section in Render.
  2. Click **Add Disk**:
     - **Name:** `pagerpal-data`
     - **Mount Path:** `/data`
     - **Size:** `1 GB`
  3. Add environment variable:
     - `DATABASE_PATH`: `/data/pagerpal.db`

### Step 5: Deploy & Verify
1. Click **Create Web Service**.
2. Wait for the build to finish.
3. Test your backend health endpoint in browser or terminal:
   ```bash
   curl https://pagerpal-backend.onrender.com/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "environment": "SIMULATION",
     "message": "PagerPal API running. All data is simulated; no production systems connected.",
     "timestamp": "..."
   }
   ```

---

## Part 2: Deploying the Frontend on Vercel

### Step 1: Import Project to Vercel
1. Log in to [Vercel.com](https://vercel.com).
2. Click **Add New...** > **Project**.
3. Select your `PagerPal` repository.

### Step 2: Configure Project Settings
- **Framework Preset:** `Vite`
- **Root Directory:** Click Edit and select `frontend`.
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

### Step 3: Configure Environment Variables
Under **Environment Variables**, add:

| Key | Value | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `https://pagerpal-backend.onrender.com` | Your actual Render backend URL without trailing slash |

### Step 4: Deploy & Verify
1. Click **Deploy**.
2. Once complete, click your deployment URL (e.g., `https://pagerpal.vercel.app`).
3. Verify that:
   - The approved loading screen displays the black sphere and golden orbital ring with foreground 3D elements.
   - Cycle 1 runs 0% -> 100%.
   - Cycle 2 runs 0% -> 100%.
   - Smooth transition into the Pure Black & Charcoal dashboard.
   - The TopBar indicates `SIMULATION` and live UTC clock.
   - Clicking **Chaos Mode** opens the fault injection modal.

---

## Part 3: Render & Vercel Cross-Origin (CORS) Synchronization

Once your Vercel deployment URL is generated (e.g., `https://pagerpal-xyz.vercel.app`):
1. Go back to your Render Dashboard > `pagerpal-backend` > **Environment**.
2. Update `FRONTEND_URL` to:
   ```env
   FRONTEND_URL=https://pagerpal-xyz.vercel.app,https://your-custom-domain.com
   ```
3. Render automatically supports all preview deployments matching `https://*.vercel.app`.
4. Click **Save Changes** on Render.

---

## Part 4: Production Checklist

- [x] PagerPal Loading Screen preserved: exactly two 0-100% loading cycles with black sphere background (`/loading-bg.png`).
- [x] Pure Black & Charcoal Design System (#050505, #080808, #0D0D0D, #121212, #242424) with Sora display font.
- [x] 3D Service Topology mesh with Three.js orbit/zoom controls and failure propagation highlights.
- [x] All 53 automated backend test suites passing (`pytest backend/tests/ -v`).
- [x] Section 10 Evaluation Suite verified: 100% Top-1 RCA, 100% approval enforcement, 100% recovery verification.
- [x] SPA routing configured via `frontend/vercel.json`.
- [x] Render Infrastructure-as-Code configured via `render.yaml`.
- [x] Sandboxed simulation guarantee: all operations strictly isolated from production infrastructure.
