# AGENTS.md — Engineering Rules for ReleaseGuard Agent

## Project Identity

- **Name**: ReleaseGuard Agent
- **Type**: Monorepo with two Python FastAPI services
- **Runtime**: Python 3.12+, FastAPI, uvicorn
- **Cloud**: Google Cloud Run, Gemini API

## Repository Layout

```
apps/
  demo_store/       # Checkout demo app (Cloud Run)
  releaseguard/     # AI release gate agent (Cloud Run)
docs/               # Architecture, policy, and demo docs
```

## Hard Rules

1. **No destructive operations.** Never execute DROP, TRUNCATE, DELETE on production databases. Never modify production traffic routing.
2. **No auto-merge.** ReleaseGuard may APPROVE or BLOCK a PR via comment. It must never merge.
3. **No Slack integration.** Out of scope for MVP.
4. **No complex dashboards.** The PR comment IS the UI.
5. **No real auth.** Use shared secrets or API keys for demo purposes only.
6. **Keep scope narrow.** If a feature is not in `docs/service_blueprint.md`, do not build it.

## Code Style

- Use `ruff` for linting and formatting (line length 99).
- Type hints on all function signatures.
- Docstrings on all public functions (Google style).
- Use `pydantic` for all request/response models.
- Use `httpx` for HTTP calls (async preferred).
- Use `structlog` for structured logging.

## FastAPI Conventions

- Every service exposes `GET /healthz` returning `{"status": "ok"}`.
- Use dependency injection for shared resources (Gemini client, HTTP client).
- Keep route handlers thin — delegate logic to service modules.
- Use `lifespan` context manager for startup/shutdown.

## Environment & Config

- All config via environment variables, loaded through `pydantic-settings`.
- Never commit secrets. Use `.env.example` as the template.
- Cloud Run services read secrets from environment variables set at deploy time.

## Testing

- Use `pytest` with `pytest-asyncio` for async tests.
- Place tests in `tests/` within each app directory.
- Mock external APIs (Gemini, GitHub) in unit tests.

## Git & PR Workflow

- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`.
- One logical change per commit.
- PR descriptions must reference the relevant `docs/` page.

## Deployment

- Each app has its own `Dockerfile` in its directory.
- Deploy via `gcloud run deploy` or Cloud Build.
- Use `--no-traffic` for preview deployments.
- Tag images with the git SHA.

## AI Agent Behavior (ReleaseGuard-specific)

- The agent must collect evidence BEFORE making a judgement.
- Evidence collection is deterministic (API probes, UI screenshot analysis).
- Judgement is LLM-assisted but final decision uses deterministic risk policy.
- All evidence and reasoning must be logged and included in the PR comment.
- The agent must never take destructive action — it only observes and reports.
