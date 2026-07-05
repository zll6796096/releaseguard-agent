# Service Blueprint — ReleaseGuard Agent

This document details the service topology, endpoints, pipeline workflow, and container structures implemented for the ReleaseGuard Agent MVP.

---

## System Architecture Overview

```
 ┌──────────────┐     PR Event      ┌─────────────────────────┐
 │   GitHub     │ ────────────────▶ │     GitHub Actions      │
 │  (PR Event)  │                   │                         │
 └──────────────┘                   │ 1. Checkout codebase    │
                                    │ 2. Run call_releaseguard│
                                    └────────────┬────────────┘
                                                 │
                                                 │ POST /evaluate
                                                 ▼
                                    ┌─────────────────────────┐
                                    │   ReleaseGuard Agent    │
                                    │      (Cloud Run)        │
                                    │                         │
                                    │ 1. api_probe            │
                                    │ 2. secret_scan          │
                                    │ 3. playwright_probe     │
                                    │ 4. gemini_judge         │
                                    │ 5. Merge risk verdicts  │
                                    └────────────┬────────────┘
                                                 │
                                 ┌───────────────┼───────────────┐
                                 │               │               │
                                 ▼               ▼               ▼
                          ┌────────────┐  ┌────────────┐  ┌────────────┐
                          │ Demo Store │  │ Gemini API │  │ GitHub API │
                          │ (Preview)  │  │ (Judgement)│  │ (Comment)  │
                          │ Cloud Run  │  └────────────┘  └────────────┘
                          └────────────┘
```

---

## Services Specification

### 1. Demo Store Application (`apps/demo_store`)
Simulates the core checkout flow of the business application.

- **Runtime**: Python 3.12-slim (FastAPI)
- **Local Port**: `8081` (Dynamic `PORT` variable assigned on Cloud Run, defaulting to `8080`)
- **Container Security**: Hardened to execute under a non-root group and user (`appuser:appgroup`).
- **Triggerable Regression**: Set env variable `BUG_HIDE_CHECKOUT_BUTTON=true` to toggle CSS-based payment button opacity invisibility (`opacity: 0`).

**Endpoints:**
- `GET /` — Landing page.
- `GET /checkout` — Checkout UI.
- `GET /healthz` — Service health validator.

---

### 2. ReleaseGuard Agent (`apps/releaseguard`)
Evaluates the release request using automated visual rendering probes and AI.

- **Runtime**: Python 3.12-slim (FastAPI + Playwright headless Chromium)
- **Local Port**: `8080` (Dynamic `PORT` variable assigned on Cloud Run, defaulting to `8080`)
- **Container Security**: Hardened to run Playwright Chromium under a non-root user (`appuser:appgroup`), mapping browsers locally inside `/app/ms-playwright`.
- **Resources**: Configured with 2 vCPUs and 2Gi Memory for browser workloads.

**Endpoints:**
- `POST /evaluate` — Processes `EvaluationRequest` payload, runs parallel scanners, executes policy merging, and returns `ReleaseDecision` JSON.
- `GET /healthz` — Service health validator.

---

## Evaluation Pipeline Workflow

When a pull request triggers the CI pipeline:

### Step 1: CI Context Extraction
The GitHub Actions runner executes `scripts/call_releaseguard.py` to:
- Read repository context, PR ID, and HEAD commit SHA.
- Extract modified files list.
- Extract change diff text using git commands (capped at a safe size of 50KB to respect payload limits).
- POST the structured JSON payload to ReleaseGuard `/evaluate`.

### Step 2: Parallel Probing (Evidence Collection)
Upon receiving the payload, the ReleaseGuard orchestrator invokes parallelized validation checks:
- **`api_health`**: Probes target preview `/healthz`.
- **`api_checkout`**: Checks target preview `/checkout` element selectors.
- **`playwright_probe`**: Opens the target preview `/checkout` page inside headless Chromium, checks button computed opacity, and captures full-page visual artifacts.
- **`secret_scan`**: Scans the incoming diff text for leaked tokens or API keys.

### Step 3: Safety Override Validation
The local rule-based engine evaluates results:
- If a security secret leak is found, or the checkout button is missing or invisible, it enforces a **BLOCK** verdict.
- Bypassing deterministic rules is forbidden. If a deterministic block occurs, the final verdict remains `BLOCK` even if Gemini analysis recommends approvals.

### Step 4: Gemini AI Judgement Synthesis
- The prompt builder constructs a structured instruction containing the collected evidence list, code changes, and preliminary verdicts.
- Calls Gemini 2.5 Flash using structured JSON mode to populate a Pydantic `GeminiJudgement` record (risk description, next steps, confidence).
- Fallback warning outputs are generated automatically if the API key is not configured.

### Step 5: Report Rendering
The outputs are compiled into a comprehensive markdown report. GitHub Actions receives the response JSON, parses the markdown, and updates a stable comment on the PR using `actions/github-script` with the marker `<!-- releaseguard-agent-report -->`.
