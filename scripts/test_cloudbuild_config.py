import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "cloudbuild.yaml").read_text(encoding="utf-8")

required = (
    "${COMMIT_SHA}",
    "--no-traffic",
    "candidate-${SHORT_SHA}",
    "releaseguard-shared-token",
    "releaseguard-gemini-api-key",
    "--update-secrets",
    "/evaluate",
    '"APPROVE"',
    "update-traffic",
    "source-commit=${COMMIT_SHA}",
    "api.github.com/repos/zll6796096/releaseguard-agent/commits/main",
    "previous_demo_revision",
    "previous_agent_revision",
    "trap rollback ERR",
    "unauthorized_status",
    'test "$$unauthorized_status" = "401"',
    '"fallback activated" not in',
)
for value in required:
    assert value in text, value

assert "demo-store-pr-hidden" not in text
assert "--allow-unauthenticated" not in text
assert "git ls-remote" not in text
assert not re.search(r"--(?:set|update)-env-vars[^\n]*GEMINI_API_KEY", text)
assert not re.search(r"--(?:set|update)-env-vars[^\n]*RELEASEGUARD_SHARED_TOKEN", text)

for script_name in ("deploy_releaseguard.sh", "deploy_demo_store.sh"):
    script = (root / "scripts" / script_name).read_text(encoding="utf-8")
    assert "gcloud run deploy" not in script
