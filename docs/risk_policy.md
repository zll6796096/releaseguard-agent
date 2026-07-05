# Risk Policy — ReleaseGuard Agent

> This document defines the deterministic rules that convert Gemini's structured risk assessment into a final APPROVE or BLOCK verdict.

## Philosophy

The LLM provides nuanced analysis. The policy provides predictable, auditable decisions.

```
Evidence → Gemini Judgement → Risk Policy → Verdict
(deterministic)   (AI-assisted)    (deterministic)   (APPROVE | BLOCK)
```

---

## Evidence Categories

Each evidence probe produces a score from 0 (no risk) to 100 (critical risk).

| Category | Probe Type | Description |
|---|---|---|
| `api_health` | API probe | HTTP health check returns 200 (failure: 80) |
| `api_checkout` | API probe | Checkout endpoint returns valid response (unavailable: 85, button missing/invisible: 90) |
| `playwright_probe` | UI journey probe | Playwright runs headless Chromium check on checkout button visibility and layout (fail: 90, warning: 50) |
| `secret_scan` | Security probe | Scans PR diff text for exposed credentials or private keys (failure: 95) |

---

## Risk Scores (from Gemini Structured Output)

Gemini returns a JSON object with:

```json
{
  "overall_risk": 0-100,
  "category_risks": {
    "api_health": 0-100,
    "api_checkout": 0-100,
    "playwright_probe": 0-100,
    "secret_scan": 0-100
  },
  "findings": [
    {
      "severity": "critical | high | medium | low | info",
      "category": "string",
      "description": "string",
      "evidence": "string"
    }
  ],
  "summary": "string"
}
```

---

## Policy Rules

### Rule 1: Risk Level Thresholds

The release gate uses the following risk score thresholds:
- **`overall_risk >= 80`**: **BLOCK** the release.
- **`50 <= overall_risk <= 79`**: **WARN** (proceed with manual validation) unless a hard policy requires **BLOCK** (e.g. if any individual critical check dictates a block).
- **`overall_risk < 50`**: **APPROVE** the release.

---

## Verdict Format

The final verdict posted to the GitHub PR comment:

```
## 🛡️ ReleaseGuard Verdict: {APPROVE ✅ | WARN 🟡 | BLOCK 🚫}

**Overall Risk Score**: {overall_risk}/100
**Policy Rules Triggered**: {list of triggered rules or "None"}

### Evidence Summary
{table of category scores}

### Findings
{list of findings with severity, description, evidence}

### AI Analysis
{Gemini's summary}

---
*ReleaseGuard Agent v0.1.0 • Policy: deterministic + Gemini Synthesis*
```

---

## Policy Versioning

- The policy version is embedded in every PR comment.
- Changes to this document require a new version tag.
- MVP version: `v0.1.0`.

---

## Override Mechanism (Post-MVP)

Not implemented in MVP. Future: allow repo maintainers to add `releaseguard:override` label to bypass the block. The agent would acknowledge the override in a follow-up comment.
