# Video Demo Script — ReleaseGuard Agent

**Target Duration**: 2 - 3 Minutes Video

---

## 🎬 Act 1: The Setup (0:00 - 0:30)

### Visuals
- Screen showing the deployed **Demo Store landing page** and **checkout page** in a browser.
- Cursor clicking the checkout button. The payment success confirmation loads fine.
- Screen showing the **GitHub Action workflow config** and **README** showing all checks passed.

### Audio / Narration
> "Welcome to the DevOps × AI Agent Hackathon 2026! Today we are introducing **ReleaseGuard Agent**, an evidence-based AI release gate for Google Cloud Run.
>
> Meet our Demo Store checkout application. Everything is functional. The payment path works, the API returns HTTP 200, and traditional unit tests are 100% green.
>
> But CI checks only validate what we explicitly wrote assertions for. What happens when a regression occurs that passes our test suite but breaks user functionality?"

---

## 🎬 Act 2: The Visual Regression & The Bad PR (0:30 - 1:15)

### Visuals
- Switch to the GitHub pull request interface showing a new PR.
- Zoom in on the file diff for `checkout.html`. Show that a developer accidentally added the class `hidden-button` (which sets `opacity: 0` in CSS) to the checkout button.
- Show that selector-based integration tests (`find_element_by_id`) still pass because the button is present in the DOM, but it is invisible to users.

### Audio / Narration
> "Here, a developer submits an innocent-looking layout change. They accidentally set the CSS opacity of the payment button to zero.
>
> Traditional CI passes! The button is still in the HTML DOM, so unit tests and basic health checks see no issue. 
>
> If this PR is merged, the checkout path will be completely broken for our customers. This is where ReleaseGuard steps in."

---

## 🎬 Act 3: ReleaseGuard Evaluation & PR Report (1:15 - 2:15)

### Visuals
- Show GitHub Actions executing the `ReleaseGuard Agent Release Gate` workflow.
- Show the workflow running `scripts/call_releaseguard.py` which collects metadata, caps the diff text at 50KB, and hits our API.
- Switch back to the PR comments section and show the detailed markdown comment posted by **ReleaseGuard Agent**.
- Highlight:
  - **Verdict**: `🚫 BLOCK`
  - **Overall Risk Score**: `90/100` (driven by the visual Playwright probe check failure)
  - **Triggered Policy Rules**: Rule regarding checkout button invisibility.
  - **Gemini Judgement**: Visual analysis highlighting that the button has 0 opacity and is unusable.
  - **Safe Next Action**: Actionable instructions to fix the checkout CSS rule.

### Audio / Narration
> "When the PR is opened, GitHub Actions invokes the ReleaseGuard Agent deployed on Cloud Run.
>
> In parallel, ReleaseGuard probes the staging deployment. It performs API health checks, triggers a Playwright headless Chromium journey, scans the diff for leaked secrets, and passes all evidence to Gemini 2.5 Flash.
>
> ReleaseGuard has posted a comment directly onto our PR: Verdict `BLOCK`.
>
> Even though standard CI was green, ReleaseGuard's Playwright probe detected that the checkout button's computed CSS opacity was zero. The agent captured a visual screenshot and flagged it.
>
> Crucially, our deterministic risk policy acts as a safety guardrail: a visual or credential leak failure instantly forces a `BLOCK`, which cannot be bypassed or downgraded by the AI."

---

## 🎬 Act 4: Core Safety Policies & Conclusion (2:15 - 2:45)

### Visuals
- Show the ReleaseGuard architecture slide or `docs/architecture.md`.
- Emphasize the core safety policies on screen:
  - **Never Auto-Merges**
  - **Never Modifies Production Traffic Routing**
  - **Graceful Fallbacks if Gemini API is Rate-Limited**

### Audio / Narration
> "ReleaseGuard is built with strict safety guidelines. It acts strictly as an observation and decision layer. It never auto-merges code, and never changes Cloud Run production traffic routing. Humans always make the final merge decision.
>
> In addition, it features graceful fallbacks. If the Gemini API is rate-limited or key configurations are missing, the agent defaults to a deterministic warning without breaking the pipeline.
>
> Stop shipping broken visual layouts. Let ReleaseGuard evaluate the evidence before you merge. Thank you!"
