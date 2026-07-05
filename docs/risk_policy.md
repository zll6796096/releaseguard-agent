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

Each evidence probe produces a score from 0 (no risk) to 10 (critical risk).

| Category | Probe Type | Description |
|---|---|---|
| `api_health` | API probe | HTTP health check returns 200 |
| `api_checkout` | API probe | Checkout endpoint returns valid response |
| `ui_screenshot` | Vision probe | Gemini analyzes page screenshot for visual issues |
| `ui_critical_elements` | Vision probe | Key UI elements (buttons, forms) are visible and usable |
| `response_time` | API probe | Response time within acceptable range |

---

## Risk Scores (from Gemini Structured Output)

Gemini returns a JSON object with:

```json
{
  "overall_risk": 0-10,
  "category_risks": {
    "api_health": 0-10,
    "api_checkout": 0-10,
    "ui_screenshot": 0-10,
    "ui_critical_elements": 0-10,
    "response_time": 0-10
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

### Rule 1: Critical Finding → BLOCK

If any finding has `severity == "critical"`, the verdict is **BLOCK**.

> Rationale: A single critical finding (e.g., checkout button not visible) is enough to block a release.

### Rule 2: Overall Risk Threshold → BLOCK

If `overall_risk >= 7`, the verdict is **BLOCK**.

> Rationale: High aggregate risk means too many things are wrong.

### Rule 3: Any Category Risk ≥ 8 → BLOCK

If any `category_risks[*] >= 8`, the verdict is **BLOCK**.

> Rationale: A single category being severely broken is a release blocker.

### Rule 4: Multiple High Findings → BLOCK

If there are 2 or more findings with `severity == "high"`, the verdict is **BLOCK**.

> Rationale: Multiple high-severity issues compound risk.

### Rule 5: Otherwise → APPROVE

If none of the above rules trigger, the verdict is **APPROVE**.

---

## Verdict Format

The final verdict posted to the GitHub PR comment:

```
## 🛡️ ReleaseGuard Verdict: {APPROVE ✅ | BLOCK 🚫}

**Overall Risk Score**: {overall_risk}/10
**Policy Rules Triggered**: {list of triggered rules or "None"}

### Evidence Summary
{table of category scores}

### Findings
{list of findings with severity, description, evidence}

### AI Analysis
{Gemini's summary}

---
*ReleaseGuard Agent v0.1.0 • Policy: deterministic • Judgement: Gemini Flash*
```

---

## Policy Versioning

- The policy version is embedded in every PR comment.
- Changes to this document require a new version tag.
- MVP version: `v0.1.0`.

---

## Override Mechanism (Post-MVP)

Not implemented in MVP. Future: allow repo maintainers to add `releaseguard:override` label to bypass the block. The agent would acknowledge the override in a follow-up comment.
