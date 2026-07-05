# Hackathon Submission Checklist — ReleaseGuard Agent

This document lists all required URLs, assets, configuration parameters, and submission details for the DevOps × AI Agent Hackathon 2026.

---

## 🔗 Project URLs

| Submission Deliverable | Placeholder Link / URL |
|---|---|
| **Public GitHub Repository** | `https://github.com/<your-username>/releaseguard-agent` |
| **ReleaseGuard Service URL** | `https://releaseguard-agent-<hash>-<region>.a.run.app` |
| **Demo Store Service URL** | `https://demo-store-<hash>-<region>.a.run.app` |
| **ProtoPedia Submission Page**| `https://protopedia.net/prototype/<id-placeholder>` |
| **Demonstration Video URL** | `https://www.youtube.com/watch?v=<video-id-placeholder>` |
| **Demo Pull Request URL** | `https://github.com/<your-username>/releaseguard-agent/pull/1` |

---

## 🖼️ Architecture Image Asset

Include this diagram inside your submission pitch slides or submission descriptions:
- **Diagram Path**: [docs/architecture.md](file:///Users/zhanglonglong/Projects/apps/ReleaseGuard%20Agent/docs/architecture.md) (renders Mermaid workflows)
- **Visual Image Link**:
  `https://raw.githubusercontent.com/<your-username>/releaseguard-agent/main/docs/images/architecture_flow.png`

---

## ⚙️ Required Environment Variables

Ensure these are configured at deploy time on Cloud Run or locally in your `.env` file:

### ReleaseGuard Agent (`releaseguard-agent`)
- `GEMINI_API_KEY`: Required. Your Google Gemini API authentication key.
- `RELEASEGUARD_SHARED_TOKEN`: Required. A secure bearer token to authorize trigger calls.
- `LOG_LEVEL`: Optional. Standard log output level (defaults to `INFO`).

### Demo Store (`demo-store`)
- `BUG_HIDE_CHECKOUT_BUTTON`: Optional. Set to `true` on staging revisions to simulate visibility failures (defaults to `false`).

---

## ⚠️ Known Limitations & Disclaimers

Keep these limitations in mind when presenting the MVP:
1. **Cold-Start Overhead**: Playwright's Chromium execution inside Cloud Run can cause 10-15 seconds of initialization latency. For zero-latency production gates, use warm instances or standard VMs.
2. **Capped Diff Scans**: Git change diff text sent to the agent's `/evaluate` endpoint is capped at 50KB to prevent payload overload.
3. **Stateless Scope**: Checks are limited to the PR's current commit diff and preview DOM layout. The agent does not inspect persistent database migrations.
