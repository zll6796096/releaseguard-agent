# Demo Script — ReleaseGuard Agent

> Step-by-step walkthrough for the hackathon demo (3-5 minutes).

## Pre-Demo Checklist

- [ ] Demo Store deployed to Cloud Run (production version, button visible)
- [ ] ReleaseGuard deployed to Cloud Run
- [ ] GitHub webhook configured and verified
- [ ] PR with "invisible button" bug prepared (draft, not yet opened)
- [ ] Browser tabs open:
  - Production Demo Store checkout page
  - GitHub repo PR page
  - Cloud Run console (optional, for showing logs)

---

## Act 1: The Setup (30 seconds)

### Narration

> "Meet Demo Store — a simple checkout app running on Cloud Run. Everything works. The checkout button is visible, the API responds, CI passes. Life is good."

### Actions

1. Show the **production checkout page** in the browser.
2. Click the checkout button — it works.
3. Point out: "All CI checks pass. Unit tests pass. Integration tests pass."

---

## Act 2: The Dangerous PR (30 seconds)

### Narration

> "Now a developer submits a PR. It looks innocent — just a CSS tweak. But buried in the diff is `opacity: 0` on the checkout button. The button still exists in the DOM. Selector tests still find it. Every automated check passes. But no human can click it."

### Actions

1. Open the **PR diff** on GitHub.
2. Highlight the `opacity: 0` line.
3. Show that CI checks are green (or simulate this).
4. Say: "Traditional CI sees no problem. Would you ship this?"

---

## Act 3: ReleaseGuard Takes Over (2-3 minutes)

### Narration

> "This is where ReleaseGuard steps in. It's not another CI check. It's an AI agent that collects evidence and makes a release judgement."

### Actions

1. **Trigger the evaluation** (either by opening the PR or calling the manual API):
   ```bash
   curl -X POST https://releaseguard-xxx.a.run.app/api/evaluate \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer demo-api-key" \
     -d '{"preview_url": "https://demo-store-pr-1-xxx.a.run.app", "pr_number": 1}'
   ```

2. **Narrate while waiting** (10-20 seconds):
   > "ReleaseGuard is now visiting the preview deployment. It's checking the health endpoint. Running the checkout API. But here's the key part — it's also taking a screenshot and asking Gemini to look at it with human eyes."

3. **Show the PR comment** when it appears. Walk through each section:

   - **Verdict: BLOCK 🚫** — "The agent decided this PR should not ship."
   - **Evidence Summary** — "It collected five types of evidence."
   - **Risk Scores** — "API health is fine. Response time is fine. But look at `ui_critical_elements`: 9/10 risk."
   - **Findings** — "Critical finding: Checkout button has opacity 0, effectively invisible to users."
   - **AI Analysis** — "Gemini explains WHY this is a problem in natural language."
   - **Policy Rules Triggered** — "Rule 1: Critical finding → BLOCK."

---

## Act 4: The Punchline (30 seconds)

### Narration

> "Traditional CI tells you whether your predefined checks passed. ReleaseGuard decides whether the evidence is strong enough to ship. It sees what CI cannot. It thinks about what tests don't cover. And it gives you a clear, auditable verdict."

### Key Messages

1. **Evidence-based**: Not just running tests — collecting multi-modal evidence.
2. **AI-assisted, policy-governed**: Gemini provides nuance; deterministic policy provides predictability.
3. **Catches what CI misses**: Visual regressions, usability issues, the invisible checkout button.
4. **Runs on Cloud Run + Gemini**: Fully Google Cloud native.

---

## Backup: Manual Trigger

If the webhook doesn't fire, use the manual evaluation endpoint:

```bash
# Trigger evaluation
curl -X POST https://releaseguard-xxx.a.run.app/api/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RELEASEGUARD_API_KEY}" \
  -d '{
    "preview_url": "https://demo-store-pr-1-xxx.a.run.app",
    "pr_number": 1,
    "repo_owner": "your-username",
    "repo_name": "releaseguard-agent"
  }'

# Check result
curl https://releaseguard-xxx.a.run.app/api/evaluations/latest \
  -H "Authorization: Bearer ${RELEASEGUARD_API_KEY}"
```

---

## Common Questions & Answers

**Q: Is this just a CI check?**
A: No. CI runs predefined checks (lint, test, build). ReleaseGuard collects evidence and uses AI to make a judgement. It catches things that no one wrote a test for.

**Q: Can the LLM be wrong?**
A: Yes, which is why the final decision uses a deterministic risk policy. The LLM provides analysis; the policy provides guardrails.

**Q: Does it auto-merge?**
A: No. It only comments. A human makes the final merge decision.

**Q: What if the agent is down?**
A: The PR simply doesn't get a ReleaseGuard comment. It's additive, not blocking infrastructure.
