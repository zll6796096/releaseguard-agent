import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "cloudbuild.yaml").read_text(encoding="utf-8")
lifecycle_text = (root / "scripts" / "releaseguard_cloudbuild.py").read_text(
    encoding="utf-8"
)
behavior_test_text = (root / "scripts" / "test_releaseguard_cloudbuild.py").read_text(
    encoding="utf-8"
)

required = (
    "${COMMIT_SHA}",
    "candidate-${SHORT_SHA}",
    "scripts/releaseguard_cloudbuild.py deploy",
    "scripts/releaseguard_cloudbuild.py cleanup",
    "scripts/releaseguard_cloudbuild.py evaluate",
    "scripts/releaseguard_cloudbuild.py promote",
    "pytest scripts/test_releaseguard_cloudbuild.py",
    "timeout: 1800s",
    "trap cleanup_on_error ERR",
    "trap cleanup_candidates EXIT",
)
for value in required:
    assert value in text, value

assert "python scripts/releaseguard_cloudbuild.py" not in text
assert text.count("python3 scripts/releaseguard_cloudbuild.py") >= 5

for forbidden in (
    "demo-store-pr-hidden",
    "--allow-unauthenticated",
    "git ls-remote",
    "|| true",
    ":latest",
):
    assert forbidden not in text
    assert forbidden not in lifecycle_text

script_required = (
    'SHARED_TOKEN_VERSION = "1"',
    'GEMINI_VERSION = "2"',
    "verify_secret_version",
    "--no-traffic",
    "--remove-env-vars=GEMINI_API_KEY,RELEASEGUARD_SHARED_TOKEN",
    "--update-secrets=",
    "human_approval_required",
    "is_fallback",
    '"decision") != "APPROVE"',
    "fallback activated",
    "remove_tag",
    "Always attempt both rollbacks",
    "rollback failures",
    "exactly one 100% revision",
    "post-promotion",
    "--connect-timeout",
    "--max-time",
    "api.github.com/repos/",
    "/evaluate",
)
for value in script_required:
    assert value in lifecycle_text, value

assert lifecycle_text.count('"curl"') == 1
assert "urllib" not in lifecycle_text
assert "requests." not in lifecycle_text
assert not re.search(r"--(?:set|update)-env-vars[^\n]*GEMINI_API_KEY", lifecycle_text)
assert not re.search(
    r"--(?:set|update)-env-vars[^\n]*RELEASEGUARD_SHARED_TOKEN",
    lifecycle_text,
)

for test_name in (
    "test_second_promotion_failure_rolls_back_both_services",
    "test_rollback_failure_is_reported_after_attempting_both_rollbacks",
    "test_post_promotion_smoke_failure_rolls_back_both_services",
    "test_candidate_evaluation_failure_always_cleans_tags_and_preserves_production",
):
    assert test_name in behavior_test_text

for script_name in ("deploy_releaseguard.sh", "deploy_demo_store.sh"):
    script = (root / "scripts" / script_name).read_text(encoding="utf-8")
    assert "gcloud run deploy" not in script
