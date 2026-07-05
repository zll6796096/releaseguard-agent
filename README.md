# 🛡️ ReleaseGuard Agent

**Evidence-based AI release gate for Cloud Run.**

> CI tells you whether predefined checks passed.
> ReleaseGuard decides whether the collected evidence is strong enough to ship.

[![Deploy on Cloud Run](https://deploy.cloud.run/button.svg)](#deployment)

---

## What Is This?

ReleaseGuard is an AI agent that acts as a release gate for Cloud Run deployments. When a Pull Request is opened, ReleaseGuard:

1. **Visits** the preview deployment in a headless browser.
2. **Probes** the API endpoints (health, checkout, response times).
3. **Screenshots** the UI and sends it to Gemini for visual analysis.
4. **Judges** the collected evidence using Gemini's structured output.
5. **Applies** a deterministic risk policy to produce an APPROVE or BLOCK verdict.
6. **Posts** a detailed PR comment with evidence, scores, findings, and reasoning.

### The Demo Bug

A PR changes the checkout page CSS so the checkout button has `opacity: 0`. The button is in the DOM — selector tests pass, unit tests pass, CI is green. But no human can see or click it. **ReleaseGuard catches this.**

---

## Architecture

```
GitHub PR Event
    │
    ▼
┌─────────────────────────────────────────────┐
│          ReleaseGuard Agent (Cloud Run)      │
│                                             │
│  Webhook → Evidence Collection → Gemini     │
│             (API + UI probes)    Judgement   │
│                                     │       │
│                              Risk Policy    │
│                                     │       │
│                              PR Comment     │
└─────────────────────────────────────────────┘
    │                 │                │
    ▼                 ▼                ▼
Demo Store        Gemini API      GitHub API
(Preview)         (Analysis)      (Comment)
```

| Component | Technology |
|---|---|
| Runtime | Google Cloud Run |
| AI | Gemini 2.5 Flash (structured output + vision) |
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
git clone https://github.com/your-username/releaseguard-agent.git
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
# Terminal 1: Start Demo Store
cd apps/demo_store
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start ReleaseGuard
cd apps/releaseguard
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Test the Agent Locally

```bash
# Trigger a manual evaluation
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-api-key-change-me" \
  -d '{"preview_url": "http://localhost:8001", "pr_number": 1}'
```

---

## Deployment

### Deploy Demo Store to Cloud Run

```bash
cd apps/demo_store
gcloud run deploy demo-store \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### Deploy ReleaseGuard to Cloud Run

```bash
cd apps/releaseguard
gcloud run deploy releaseguard \
  --source . \
  --region asia-northeast1 \
  --set-env-vars GEMINI_API_KEY=xxx,GITHUB_TOKEN=xxx \
  --memory 1Gi \
  --allow-unauthenticated
```

### Configure GitHub Webhook

1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://releaseguard-xxx.a.run.app/webhook/github`
3. Content type: `application/json`
4. Secret: your `GITHUB_WEBHOOK_SECRET`
5. Events: Select "Pull requests"

---

## MVP Acceptance Criteria

- [ ] Demo Store deploys to Cloud Run and serves a checkout page with a visible button.
- [ ] A PR branch makes the checkout button invisible (`opacity: 0`).
- [ ] ReleaseGuard can be triggered (via webhook or manual API call).
- [ ] ReleaseGuard visits the preview URL and captures a screenshot.
- [ ] ReleaseGuard probes the API endpoints and collects response data.
- [ ] ReleaseGuard sends evidence to Gemini and receives a structured risk assessment.
- [ ] Deterministic risk policy produces a BLOCK verdict for the invisible button.
- [ ] ReleaseGuard posts a formatted PR comment with verdict, evidence, and reasoning.
- [ ] Both services pass health checks on Cloud Run.

---

## Hackathon Requirements Checklist

| Requirement | How We Meet It |
|---|---|
| Google Cloud runtime product | Cloud Run (both services) |
| Google Cloud AI technology | Gemini API (vision + structured output) |
| Agentic behavior | Autonomous evidence collection, judgement, and action (PR comment) |
| Public GitHub repo | ✅ |
| Deployed project URL | Cloud Run URLs |
| ProtoPedia URL | TBD |

---

## Key Documents

- [Service Blueprint](docs/service_blueprint.md) — Architecture and service interactions
- [Risk Policy](docs/risk_policy.md) — Deterministic APPROVE/BLOCK rules
- [Demo Script](docs/demo_script.md) — Hackathon presentation walkthrough
- [Design Decisions](docs/decisions.md) — Assumptions and trade-offs

---

## Built For

**DevOps × AI Agent Hackathon 2026**

Solo builder: [@zhanglonglong](https://github.com/zhanglonglong)

---

## License

MIT
