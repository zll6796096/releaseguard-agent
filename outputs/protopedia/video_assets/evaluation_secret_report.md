## 🛡️ ReleaseGuard Verdict: 🚫 BLOCK

**Overall Risk Score**: `95/100`

### ⚠️ Triggered Policy Rules
- Rule: Secret scan detected exposed credentials or tokens in diff.

### 🧠 Gemini AI Judgement Synthesis
- **Verdict Recommendation**: `WARN`
- **AI Risk Score**: `50/100`
- **Confidence**: `50.0%`
- **Analysis**: Gemini API fallback activated: GEMINI_API_KEY environment variable is not configured.

- **Recommended Next Action**: Perform manual visual validation of checkout journey and code diff.
- **Unsafe Actions Detected**:
  - ⚠️ Relying on automatic AI validation without checking key configuration.

### 🛣️ Affected Journeys
- **Journey**: `unknown`

### 📊 Evidence Summary

| Category | Status | Risk Score | Message |
| --- | --- | --- | --- |
| `api_health` | 🟢 Passed | `0/100` | Service health check passed successfully. |
| `api_checkout` | 🟢 Passed | `0/100` | Checkout button is present and visible to users. |
| `secret_scan` | 🔴 Failed | `95/100` | Detected 1 potential secret(s) in PR diff. |
| `playwright_probe` | 🟢 Passed | `0/100` | Checkout button with data-testid='checkout-button' is present and visible. |

### 📸 Playwright Screenshot Artifact
**Path**: `/tmp/releaseguard-artifacts/checkout.png`

<!-- TODO: Cloud Storage or artifact upload is needed to generate public URLs for screenshots in GitHub PR comments -->

### 🔍 Detailed Findings

#### 🔴 Failed `secret_scan` (Risk: `95/100`)
**Details**: Detected 1 potential secret(s) in PR diff.
```json
{
  "secrets_found": [
    {
      "type": "github_token",
      "count": 1,
      "examples": [
        "github_token_example_redacted"
      ]
    }
  ]
}
```

---
*ReleaseGuard Agent v0.1.0 • Policy: Local Rule-Based + Playwright Probing + Gemini Synthesis*
