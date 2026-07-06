# 🛡️ ReleaseGuard Agent

**Evidence-based AI release gate for Cloud Run.**

> CI tells you whether predefined checks passed.
> ReleaseGuard decides whether the collected evidence is strong enough to ship.

[![Deploy on Cloud Run](https://deploy.cloud.run/button.svg)](#deployment)

---

## ⚡ Quickstart

Get ReleaseGuard running locally in 3 steps:

1. **Clone & Set Up Env**:
   ```bash
   git clone https://github.com/zll6796096/releaseguard-agent.git
   cd releaseguard-agent
   cp .env.example .env
   # Fill in GEMINI_API_KEY inside .env
   ```
2. **Start Applications**:
   ```bash
   # Run both services via docker-compose (requires Docker)
   docker-compose up --build
   ```
3. **Trigger Evaluation Check**:
   ```bash
   # You can run the interactive local demo script which starts docker-compose,
   # runs standard evaluation scenarios (clean PR, hidden button, and leaked secrets), and outputs the results:
   ./scripts/local_demo.sh

   # Alternatively, you can curl the ReleaseGuard agent directly at its mapped port 8085:
   curl -X POST http://localhost:8085/evaluate \
     -H "Content-Type: application/json" \
     -d '{
       "repo": "owner/releaseguard-agent",
       "pr_number": 1,
       "commit_sha": "abc123sha",
       "preview_url": "http://demo_store:8080",
       "changed_files": ["app/main.py"],
       "diff_text": "diff --git a/app/main.py b/app/main.py"
     }'
   ```

---

## 🚀 Cloud Run Live Demo

- **Clean Demo Store URL**: [https://demo-store-788259830737.asia-northeast1.run.app](https://demo-store-788259830737.asia-northeast1.run.app)
- **ReleaseGuard Agent URL**: [https://releaseguard-agent-788259830737.asia-northeast1.run.app](https://releaseguard-agent-788259830737.asia-northeast1.run.app)
- **Final BLOCK Demo PR**: [https://github.com/zll6796096/releaseguard-agent/pull/2](https://github.com/zll6796096/releaseguard-agent/pull/2)
- **PR Preview URL**: [https://demo-store-pr-hidden-788259830737.asia-northeast1.run.app](https://demo-store-pr-hidden-788259830737.asia-northeast1.run.app)
- **Legacy simulated demo PR**: [https://github.com/zll6796096/releaseguard-agent/pull/1](https://github.com/zll6796096/releaseguard-agent/pull/1)

---

## What Is This?

ReleaseGuard is an AI agent that acts as a release gate for Cloud Run deployments. When a Pull Request is opened, ReleaseGuard:

1. **Visits** the preview deployment in a headless browser (Playwright) to probe UI visibility.
2. **Probes** the API endpoints (health, checkout).
3. **Captures** a screenshot for manual audit / reference.
4. **Synthesizes** the collected text evidence (API health, Playwright DOM visibility findings, secret scans, and code diffs) using Gemini's structured output.
5. **Applies** a deterministic risk policy to produce an APPROVE, WARN, or BLOCK verdict.
6. **Posts** a detailed PR comment with evidence, scores, findings, and reasoning.

### The Demo Bug

A PR changes the checkout page CSS so the checkout button has `opacity: 0`. The button is in the DOM — selector tests pass, unit tests pass, CI is green. But no human can see or click it. **ReleaseGuard catches this.**

---

## Architecture

```
GitHub PR Event
    │
    ▼
GitHub Actions
    │
    ▼
POST /evaluate
    │
    ▼
ReleaseGuard Agent (Cloud Run)
    ├─ API probe
    ├─ Playwright UI probe
    ├─ Secret scan
    ├─ Gemini evidence synthesis
    └─ Deterministic risk policy
    │
    ▼
GitHub PR Comment + Failed Check on BLOCK
```

| Component | Technology |
|---|---|
| Runtime | Google Cloud Run |
| AI | Gemini 2.5 Flash (structured output + evidence synthesis) |
| Language | Python 3.12, FastAPI |
| Browser | Playwright (headless Chromium) |
| Policy | Deterministic rules engine |

---

## Repository Structure

```
.
├── .agents/
│   └── AGENTS.md              # Engineering rules for AI agents
├── apps/
│   ├── demo_store/            # Checkout demo app (Cloud Run)
│   │   ├── main.py
│   │   ├── templates/
│   │   ├── static/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── releaseguard/          # AI release gate agent (Cloud Run)
│       ├── main.py
│       ├── services/
│       │   ├── evidence.py    # Evidence collection (API + UI probes)
│       │   ├── gemini.py      # Gemini judgement service
│       │   ├── policy.py      # Deterministic risk policy
│       │   └── github.py      # GitHub API (comments)
│       ├── models/
│       │   ├── evidence.py    # Pydantic evidence models
│       │   └── judgement.py   # Pydantic risk models
│       ├── Dockerfile
│       └── requirements.txt
├── docs/
│   ├── service_blueprint.md   # Architecture & service map
│   ├── risk_policy.md         # Deterministic risk rules
│   ├── demo_script.md         # Hackathon demo walkthrough
│   └── decisions.md           # Design decisions & assumptions
├── .env.example               # Environment variable template
└── README.md                  # This file
```

---

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Gemini API key ([Get one here](https://aistudio.google.com/apikey))
- A GitHub personal access token (for posting PR comments)

### Setup

```bash
# Clone the repo
git clone https://github.com/zll6796096/releaseguard-agent.git
cd releaseguard-agent

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Install dependencies (Demo Store)
cd apps/demo_store
pip install -r requirements.txt

# Install dependencies (ReleaseGuard)
cd ../releaseguard
pip install -r requirements.txt
playwright install chromium
```

### Run Locally

```bash
# Terminal 1: Start Demo Store (binds to 8081)
cd apps/demo_store
uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload

# Terminal 2: Start ReleaseGuard (binds to 8080)
cd apps/releaseguard
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Test the Agent Locally

```bash
# Trigger a manual evaluation pointing to your local demo store
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/releaseguard-agent",
    "pr_number": 1,
    "commit_sha": "localsample123",
    "preview_url": "http://localhost:8081",
    "changed_files": ["app/main.py"],
    "diff_text": "diff --git a/app/main.py b/app/main.py"
  }'
```

---

## Deployment

We provide helper scripts under the `scripts/` directory to simplify deployment using `gcloud run deploy --source`.

### Prerequisites

Configure your environment variables:
```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GEMINI_API_KEY="your-gemini-api-key"
export RELEASEGUARD_SHARED_TOKEN="your-shared-security-bearer-token"
export LOG_LEVEL="INFO"
```

### Deploy Services

```bash
# Deploy checkout Demo Store (defaults to asia-northeast1)
./scripts/deploy_demo_store.sh

# Deploy ReleaseGuard Agent
./scripts/deploy_releaseguard.sh
```

For more details on region override, log streaming, and URL verification, refer to the [Cloud Run Deployment Guide](docs/deployment.md).

### GitHub Webhook (Future Work)

Direct webhook endpoints (like `POST /webhook/github` handled by the agent) are planned for a future release. The current MVP integration runs natively via GitHub Actions workflow triggers using python scripts to execute the checks.

---

## GitHub Actions Integration

ReleaseGuard can run directly inside your GitHub repository using GitHub Actions on pull request events.

### Required Repository Secrets & Variables

Configure these settings in your repository under **Settings > Secrets and variables**:

#### Secrets (Settings > Secrets and variables > Actions > Secrets)
- `RELEASEGUARD_AGENT_URL`: The URL of your deployed ReleaseGuard service (e.g., `https://releaseguard-xxx.a.run.app`).
- `RELEASEGUARD_SHARED_TOKEN`: (Optional) The bearer token configured for manual evaluation security.

#### Variables (Settings > Secrets and variables > Actions > Variables)
- `RELEASEGUARD_PREVIEW_URL`: The URL of the PR preview environment to validate (e.g., `https://demo-store-pr-xxx.run.app` or for local testing, the current demo_store IP).

### How to Run the Workflow
1. Create a pull request to the `main` branch.
2. The `ReleaseGuard Agent Release Gate` action will automatically trigger.
3. It collects change diffs, checks visual layouts, scans for leaked keys, applies policy checks, and comments or updates a comment with the detailed markdown report directly on your PR.

### How to Simulate a Visual Regression (Bad PR)
To test if ReleaseGuard detects visual issues:
1. Create a branch and modify the checkout page templates.
2. Add the CSS class `hidden-button` (which sets `opacity: 0`) to the checkout button in `apps/demo_store/app/templates/checkout.html`.
3. Push changes and open a PR. ReleaseGuard will catch this and post a `BLOCK` verdict with a 90/100 risk score on the PR!

---

## MVP Verification Checklist

- [x] Demo Store deploys to Cloud Run and serves a checkout page with a visible button.
- [x] A PR branch makes the checkout button invisible (`opacity: 0`).
- [x] ReleaseGuard can be triggered (via manual API call / GitHub Actions workflow).
- [x] ReleaseGuard visits the preview URL and captures a screenshot.
- [x] ReleaseGuard probes the API endpoints and collects response data.
- [x] ReleaseGuard sends evidence to Gemini and receives a structured risk assessment.
- [x] Deterministic risk policy produces a BLOCK verdict for the invisible button.
- [x] ReleaseGuard posts a formatted PR comment with verdict, evidence, and reasoning.
- [x] Both services pass health checks on Cloud Run.

---

## 🛠️ How to use this on your own project

1. **Deploy ReleaseGuard Agent**: Deploy the agent service to Google Cloud Run (providing your `GEMINI_API_KEY` and setting a secure `RELEASEGUARD_SHARED_TOKEN`).
2. **Create Preview/Staging Env**: Ensure your target web application spins up a preview URL on pull request events.
3. **Add `/healthz/`**: Implement a `/healthz/` endpoint in your web application that returns `200 OK` when healthy.
4. **Mark Critical Elements**: Add unique `data-testid` attributes to critical elements in your UI (e.g. `data-testid="checkout-button"`).
5. **Copy Workflow Action**: Copy the `.github/workflows/releaseguard.yml` and `scripts/call_releaseguard.py` script into your repository.
6. **Configure Secrets & Variables**: Configure `RELEASEGUARD_AGENT_URL`, `RELEASEGUARD_SHARED_TOKEN`, and `RELEASEGUARD_PREVIEW_URL` in your GitHub repo settings.
7. **Protect Branches**: Set the ReleaseGuard status check as a required branch protection rule to block pull request merges on BLOCK verdicts.

---

## ⚠️ Known Limitations

- **Cold Start Latency**: Headless Chromium execution inside Cloud Run has cold-start overheads (up to 10-15s). Real production setups should use warm instances or configure CPU-allocation set to 'always allocated'.
- **Diff Size Cap**: Git diff metadata payload sent to the agent is capped at 50KB to respect Gemini payload boundaries.
- **Stateless Analysis**: The agent does not track database schema migrations or state alterations over time; checks are scoped to current commit snapshots.

---

## Hackathon Requirements Checklist

| Requirement | How We Meet It |
|---|---|
| Google Cloud runtime product | Cloud Run (both services) |
| Google Cloud AI technology | Gemini API (structured output + evidence synthesis) |
| Agentic behavior | Autonomous evidence collection, judgement, and action (PR comment) |
| Public GitHub repo | ✅ |
| Deployed project URL | Cloud Run URLs |
| ProtoPedia URL | TBD |

---

## Key Documents

- [Service Blueprint](docs/service_blueprint.md) — Architecture and service interactions
- [Technical Architecture](docs/architecture.md) — Mermaid diagrams and evidence flow
- [Risk Policy](docs/risk_policy.md) — Deterministic APPROVE/BLOCK rules
- [Demo Script](docs/demo_script.md) — Hackathon presentation walkthrough
- [Design Decisions](docs/decisions.md) — Assumptions and trade-offs
- [ProtoPedia Draft](docs/protopedia_draft.md) — Submission templates
- [Validation Report](docs/cloudrun_validation.md) — Real Cloud Run Validation Results

---

## Built For

**DevOps × AI Agent Hackathon 2026**

Solo builder: [@zll6796096](https://github.com/zll6796096)

---

## License

MIT
