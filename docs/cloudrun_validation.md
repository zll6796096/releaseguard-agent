# ReleaseGuard Agent MVP — Cloud Run Validation Report

This report documents the deployment, configuration, and verification details of the ReleaseGuard Agent MVP and the Demo Store in the live Google Cloud Run environment.

---

## 📅 Deployment Details
- **Date/Time**: 2026-07-06T00:30:00+09:00 (Local Time)
- **GCP Project**: [Redacted/Omitted]
- **Region**: `asia-northeast1`

---

## 🔗 Deployed Service URLs
- **Demo Store URL**: `https://demo-store-788259830737.asia-northeast1.run.app`
- **ReleaseGuard Agent URL**: `https://releaseguard-agent-788259830737.asia-northeast1.run.app`
- **GitHub Repository**: `https://github.com/zll6796096/releaseguard-agent`
- **Demo Pull Request**: `https://github.com/zll6796096/releaseguard-agent/pull/1`

---

## 🏥 Health Check Results
- **Demo Store `/healthz/`**: `200 OK` (Bypasses Google Frontend `/healthz` interception via trailing slash redirect handling).
  ```bash
  curl -i -fsS "https://demo-store-788259830737.asia-northeast1.run.app/healthz/"
  # Returns: {"status":"ok"}
  ```
- **ReleaseGuard Agent `/healthz/`**: `200 OK`
  ```bash
  curl -i -fsS "https://releaseguard-agent-788259830737.asia-northeast1.run.app/healthz/"
  # Returns: {"status":"ok"}
  ```

---

## 🛡️ API Endpoint Verification (`POST /evaluate`)

### 1. Unauthorized Request Validation
- **Command**:
  ```bash
  curl -i -X POST "https://releaseguard-agent-788259830737.asia-northeast1.run.app/evaluate" \
    -H "Content-Type: application/json" \
    -d '{"repo":"zll6796096/releaseguard-agent","pr_number":0,"commit_sha":"manual","preview_url":"https://demo-store-788259830737.asia-northeast1.run.app","changed_files":[],"diff_text":""}'
  ```
- **Result**: `401 Unauthorized`
  ```json
  {"detail":"Unauthorized: Invalid or missing token"}
  ```

### 2. Clean Scenario
- **Verdict**: `APPROVE`
- **Overall Risk Score**: `10/100` (Gemini synthesis is fully operational).
- **Result**:
  ```json
  {
    "verdict": "APPROVE",
    "overall_risk": 10,
    "gemini_judgement": {
      "decision": "APPROVE",
      "risk_score": 10,
      "confidence": 0.95,
      ...
    }
  }
  ```

### 3. Hidden Checkout Visual Regression Scenario (`?bug=true`)
- **Verdict**: `BLOCK`
- **Overall Risk Score**: `90/100`
- **Key Evidence**:
  - `api_checkout` failed with risk score `90` (Checkout button invisible in DOM due to CSS classes).
  - `playwright_probe` failed with risk score `90` (Checkout button not visible due to `opacity: 0`).
  - Correctly reports the regression without committing local `file://` screenshot paths to GHA comments.

### 4. Secret Leak Scenario
- **Verdict**: `BLOCK`
- **Overall Risk Score**: `95/100`
- **Key Evidence**:
  - `secret_scan` failed with risk score `95` (Detected committed GitHub Token in the diff text).

---

## 🐙 GitHub Action PR Integration Result
- **Demo PR**: [https://github.com/zll6796096/releaseguard-agent/pull/1](https://github.com/zll6796096/releaseguard-agent/pull/1)
- **Workflow Result**: 
  - **Verdict BLOCK Check**: When `RELEASEGUARD_PREVIEW_URL` was configured to `https://demo-store-788259830737.asia-northeast1.run.app?bug=true`, the GitHub Action workflow successfully posted the `BLOCK` report comment, and subsequently failed the workflow as intended.
  - **Verdict APPROVE Check**: After resetting `RELEASEGUARD_PREVIEW_URL` to `https://demo-store-788259830737.asia-northeast1.run.app`, the re-run of the action successfully updated the existing PR comment to `APPROVE` and passed the build.

---

## 🛡️ Final Code-Driven Demo PR Validation
- **PR URL**: `https://github.com/zll6796096/releaseguard-agent/pull/2`
- **Preview Service URL**: `https://demo-store-pr-hidden-788259830737.asia-northeast1.run.app`
- **GitHub Action Run URL**: `https://github.com/zll6796096/releaseguard-agent/actions/runs/28746644766`
- **Verdict**: `BLOCK`
- **Risk Score**: `90`
- **Evidence Summary**:
  - Checkout button was hidden unconditionally in the HTML template by the branch code.
  - ReleaseGuard detected that the checkout button was invisible (opacity 0) on the dedicated preview service and returned a BLOCK verdict.
  - GitHub Actions successfully posted the BLOCK report to the PR and subsequently terminated with a failure.

---

## ⚠️ Known Limitations & Disclaimers
1. **Cold Start Latency**: Headless Chromium inside Cloud Run has cold-start overheads (up to 10-15s). Configure warm instances in production.
2. **Diff Size Cap**: Git diff payload sent to the agent is capped at 50KB to respect Gemini payload boundaries.
3. **Stateless Analysis**: The agent does not track database schema migrations or state alterations over time; checks are scoped to current commit snapshots.
