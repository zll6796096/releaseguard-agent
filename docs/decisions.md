# Design Decisions & Assumptions

> Documenting every non-obvious choice so reviewers (and future-me) understand the trade-offs.

## D1: Monorepo over Polyrepo

**Decision**: Single repository with `apps/demo_store` and `apps/releaseguard`.

**Rationale**: Solo builder, short deadline. A monorepo simplifies CI config, shared tooling, and demo setup. Both services share the same Python version and base dependencies.

---

## D2: FastAPI for Both Services

**Decision**: Use FastAPI (not Flask, not Cloud Functions).

**Rationale**: FastAPI gives us async support, automatic OpenAPI docs, Pydantic validation, and a consistent developer experience across both services. Cloud Run supports any containerized HTTP server, so FastAPI's uvicorn works perfectly.

---

## D3: Gemini Flash over Pro

**Decision**: Default to `gemini-2.5-flash` for release judgements.

**Rationale**: Flash is faster and cheaper. For the MVP demo, the judgement prompt is straightforward (structured evidence → risk assessment). Flash handles this well. Can upgrade to Pro later if judgement quality is insufficient.

---

## D4: PR Comment as the Only UI

**Decision**: No dashboard, no Slack, no email. The GitHub PR comment IS the product surface.

**Rationale**: Hackathon constraint — keep scope narrow. A well-formatted PR comment with evidence summary, risk scores, and a clear APPROVE/BLOCK verdict is sufficient to demonstrate the value proposition.

---

## D5: Webhook-Triggered, Not Polling

**Decision**: ReleaseGuard is triggered by GitHub webhook events (PR opened, synchronized).

**Rationale**: Event-driven is more responsive and cheaper than polling. Cloud Run scales to zero when idle. For the demo, we can also trigger manually via API endpoint.

---

## D6: Playwright Visual Probing + Gemini Evidence Synthesis

**Decision**: Use Playwright to visually probe the DOM and capture a screenshot, then pass the structured visual probe results (metadata) to Gemini for synthesis.

**Rationale**: Traditional CI cannot verify if elements are visually hidden or unusable. By combining Playwright visual/layout probing (e.g. checking visibility, computed styles, opacity) with Gemini's reasoning capabilities, we detect visual regressions (like invisible buttons, broken layouts, missing content) that pass naive DOM/selector checks.

**Assumption**: We use a headless browser (Playwright) running inside the ReleaseGuard container to perform DOM/CSS probing and capture screenshots for manual reference.

---

## D7: Deterministic Risk Policy on Top of LLM Judgement

**Decision**: Gemini provides structured risk assessment; a deterministic policy engine makes the final APPROVE/BLOCK decision.

**Rationale**: LLMs can hallucinate or be inconsistent. The risk policy (`docs/risk_policy.md`) defines clear thresholds. This makes the system auditable and predictable while still leveraging AI for nuanced analysis.

---

## D8: No Real Authentication

**Decision**: Use simple API keys and shared secrets. No OAuth, no multi-tenant auth.

**Rationale**: Hackathon MVP. We need to demonstrate the agent behavior, not build a production auth system. The webhook secret validates GitHub events; an API key protects manual trigger endpoints.

---

## D9: Preview Deploys Use Cloud Run Revisions

**Decision**: Deploy PR previews as Cloud Run revisions with `--no-traffic` and a unique tag.

**Rationale**: Cloud Run natively supports revision tagging, giving each PR a unique preview URL without affecting production traffic. This is simpler than spinning up separate services.

---

## D10: Playwright Bundled in Container

**Decision**: Include Playwright and Chromium in the ReleaseGuard Docker image.

**Rationale**: The agent needs to visit the preview URL and take screenshots. Bundling Playwright avoids external dependencies. The container will be larger (~500MB+) but this is acceptable for Cloud Run.

**Trade-off**: Slower cold starts. Acceptable for demo since the webhook trigger is not latency-sensitive.

---

## D11: Region Selection

**Decision**: Default to `asia-northeast1` (Tokyo).

**Rationale**: Builder is based in Tokyo. Low-latency access during development and demo. Can be changed via environment variable.

---

## D12: Structured Output from Gemini

**Decision**: Use Gemini's structured output (JSON mode) for release judgements.

**Rationale**: We need machine-parseable risk scores and verdicts, not free-form text. Structured output ensures the risk policy engine can reliably extract scores. Pydantic models validate the response.

---

## D13: Evidence Collection Before Judgement

**Decision**: The agent collects ALL evidence first, then sends a single judgement request to Gemini.

**Rationale**: This is a deliberate architectural choice. By separating evidence collection (deterministic) from judgement (LLM-assisted), we can:
1. Retry evidence collection independently.
2. Cache evidence for debugging.
3. Ensure the LLM sees the full picture, not incremental updates.

---

## D14: Demo Bug — Invisible Checkout Button

**Decision**: The demo PR makes the checkout button invisible via `opacity: 0` (not `display: none`).

**Rationale**: `opacity: 0` is more realistic — the button still exists in the DOM, so a naive selector test would pass. Only visual inspection (or Gemini vision analysis) catches it. This perfectly demonstrates ReleaseGuard's value.
