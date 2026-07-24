import json

import pytest
from releaseguard_cloudbuild import (
    CommandBackend,
    ReleaseFailure,
    ReleaseOps,
    ReleaseState,
)

DEMO = "demo-store"
AGENT = "releaseguard-agent"
PRIOR_DEMO = "demo-store-00006-key"
PRIOR_AGENT = "releaseguard-agent-00005-naw"
CANDIDATE_DEMO = "demo-store-00007-new"
CANDIDATE_AGENT = "releaseguard-agent-00006-new"
COMMIT = "a" * 40
TAG = "candidate-aaaaaaa"


class FakeBackend:
    def __init__(self):
        self.traffic = {
            DEMO: [{"revisionName": PRIOR_DEMO, "percent": 100}],
            AGENT: [{"revisionName": PRIOR_AGENT, "percent": 100}],
        }
        self.ready = {
            PRIOR_DEMO,
            PRIOR_AGENT,
            CANDIDATE_DEMO,
            CANDIDATE_AGENT,
        }
        self.tags = {DEMO: set(), AGENT: set()}
        self.calls = []
        self.fail_candidate_deploy_for = None
        self.fail_candidate_promotion_for = None
        self.fail_rollback_for = None
        self.fail_candidate_smoke = False
        self.fail_production_smoke = False

    def verify_secret_version(self, secret, version):
        self.calls.append(("verify_secret_version", secret, version))

    def get_traffic(self, service):
        return self.traffic[service]

    def revision_ready(self, revision):
        self.calls.append(("ready", revision))
        return revision in self.ready

    def deploy_candidate(self, service, image, commit, tag, secret_versions):
        self.calls.append(("deploy", service, secret_versions))
        self.tags[service].add(tag)
        if self.fail_candidate_deploy_for == service:
            raise ReleaseFailure(f"deploy failed for {service}")
        return CANDIDATE_DEMO if service == DEMO else CANDIDATE_AGENT

    def assert_candidate_config(self, service, revision, commit, secret_versions):
        self.calls.append(
            ("assert_candidate_config", service, revision, secret_versions)
        )

    def remove_tag(self, service, tag):
        self.calls.append(("remove_tag", service, tag))
        self.tags[service].discard(tag)

    def candidate_url(self, service, tag):
        assert tag in self.tags[service]
        return f"https://{tag}---{service}.example.test"

    def candidate_smoke(self, demo_url, agent_url, commit, result_path):
        self.calls.append(("candidate_smoke", demo_url, agent_url))
        if self.fail_candidate_smoke:
            raise ReleaseFailure("candidate smoke failed")
        result_path.write_text(json.dumps(approved_result()))
        return approved_result()

    def remote_main(self):
        return COMMIT

    def set_traffic(self, service, revision):
        self.calls.append(("set_traffic", service, revision))
        candidate = revision in {CANDIDATE_DEMO, CANDIDATE_AGENT}
        if candidate and self.fail_candidate_promotion_for == service:
            raise ReleaseFailure(f"promotion failed for {service}")
        if not candidate and self.fail_rollback_for == service:
            raise ReleaseFailure(f"rollback failed for {service}")
        self.traffic[service] = [{"revisionName": revision, "percent": 100}]

    def health(self, service):
        self.calls.append(("health", service))

    def production_smoke(self, commit, result_path):
        self.calls.append(("production_smoke", commit))
        if self.fail_production_smoke:
            raise ReleaseFailure("post-promotion smoke failed")
        result_path.write_text(json.dumps(approved_result()))
        return approved_result()


def approved_result():
    return {
        "verdict": "APPROVE",
        "evidence": [{"category": "api_health", "status": "success"}],
        "gemini_judgement": {
            "decision": "APPROVE",
            "human_approval_required": False,
            "is_fallback": False,
            "why": "All evidence passed",
        },
    }


def state():
    return ReleaseState(
        commit=COMMIT,
        tag=TAG,
        previous_demo_revision=PRIOR_DEMO,
        previous_agent_revision=PRIOR_AGENT,
        candidate_demo_revision=CANDIDATE_DEMO,
        candidate_agent_revision=CANDIDATE_AGENT,
    )


def test_decision_requires_nested_explicit_approval():
    backend = FakeBackend()
    ops = ReleaseOps(backend, DEMO, AGENT)

    for field, value in (
        ("decision", "WARN"),
        ("human_approval_required", True),
        ("is_fallback", True),
    ):
        result = approved_result()
        result["gemini_judgement"][field] = value
        with pytest.raises(ReleaseFailure):
            ops.validate_decision(result)

    missing_fallback_state = approved_result()
    del missing_fallback_state["gemini_judgement"]["is_fallback"]
    with pytest.raises(ReleaseFailure):
        ops.validate_decision(missing_fallback_state)

    ops.validate_decision(approved_result())


def test_partial_candidate_deploy_cleans_both_tags(tmp_path):
    backend = FakeBackend()
    backend.fail_candidate_deploy_for = AGENT
    ops = ReleaseOps(backend, DEMO, AGENT)

    with pytest.raises(ReleaseFailure):
        ops.deploy_candidates(
            commit=COMMIT,
            tag=TAG,
            demo_image="demo-image",
            agent_image="agent-image",
            state_path=tmp_path / "state.json",
        )

    assert backend.tags == {DEMO: set(), AGENT: set()}
    assert backend.traffic[DEMO] == [{"revisionName": PRIOR_DEMO, "percent": 100}]
    assert backend.traffic[AGENT] == [{"revisionName": PRIOR_AGENT, "percent": 100}]
    assert (
        "verify_secret_version",
        "releaseguard-shared-token",
        "1",
    ) in backend.calls
    assert (
        "verify_secret_version",
        "releaseguard-gemini-api-key",
        "2",
    ) in backend.calls


def test_candidate_evaluation_failure_always_cleans_tags_and_preserves_production(
    tmp_path,
):
    backend = FakeBackend()
    backend.tags = {DEMO: {TAG}, AGENT: {TAG}}
    backend.fail_candidate_smoke = True
    ops = ReleaseOps(backend, DEMO, AGENT)

    with pytest.raises(ReleaseFailure):
        ops.evaluate_candidates(state(), tmp_path / "candidate.json")

    assert backend.tags == {DEMO: set(), AGENT: set()}
    assert backend.traffic[DEMO] == [{"revisionName": PRIOR_DEMO, "percent": 100}]
    assert backend.traffic[AGENT] == [{"revisionName": PRIOR_AGENT, "percent": 100}]


def test_candidate_evaluation_success_always_cleans_tags(tmp_path):
    backend = FakeBackend()
    backend.tags = {DEMO: {TAG}, AGENT: {TAG}}
    ops = ReleaseOps(backend, DEMO, AGENT)

    result = ops.evaluate_candidates(state(), tmp_path / "candidate.json")

    assert result["verdict"] == "APPROVE"
    assert backend.tags == {DEMO: set(), AGENT: set()}
    assert backend.traffic[DEMO] == [{"revisionName": PRIOR_DEMO, "percent": 100}]
    assert backend.traffic[AGENT] == [{"revisionName": PRIOR_AGENT, "percent": 100}]


def test_second_promotion_failure_rolls_back_both_services(tmp_path):
    backend = FakeBackend()
    backend.fail_candidate_promotion_for = AGENT
    ops = ReleaseOps(backend, DEMO, AGENT)

    with pytest.raises(ReleaseFailure, match="promotion failed"):
        ops.promote(state(), tmp_path / "production.json")

    assert backend.traffic[DEMO] == [{"revisionName": PRIOR_DEMO, "percent": 100}]
    assert backend.traffic[AGENT] == [{"revisionName": PRIOR_AGENT, "percent": 100}]
    assert ("set_traffic", AGENT, PRIOR_AGENT) in backend.calls
    assert ("set_traffic", DEMO, PRIOR_DEMO) in backend.calls
    assert ("health", DEMO) in backend.calls
    assert ("health", AGENT) in backend.calls


def test_rollback_failure_is_reported_after_attempting_both_rollbacks(tmp_path):
    backend = FakeBackend()
    backend.fail_candidate_promotion_for = AGENT
    backend.fail_rollback_for = DEMO
    ops = ReleaseOps(backend, DEMO, AGENT)

    with pytest.raises(ReleaseFailure, match="rollback failures"):
        ops.promote(state(), tmp_path / "production.json")

    assert ("set_traffic", AGENT, PRIOR_AGENT) in backend.calls
    assert ("set_traffic", DEMO, PRIOR_DEMO) in backend.calls
    assert backend.traffic[AGENT] == [{"revisionName": PRIOR_AGENT, "percent": 100}]
    assert backend.traffic[DEMO] == [{"revisionName": CANDIDATE_DEMO, "percent": 100}]


def test_post_promotion_smoke_failure_rolls_back_both_services(tmp_path):
    backend = FakeBackend()
    backend.fail_production_smoke = True
    ops = ReleaseOps(backend, DEMO, AGENT)

    with pytest.raises(ReleaseFailure, match="post-promotion smoke failed"):
        ops.promote(state(), tmp_path / "production.json")

    assert backend.traffic[DEMO] == [{"revisionName": PRIOR_DEMO, "percent": 100}]
    assert backend.traffic[AGENT] == [{"revisionName": PRIOR_AGENT, "percent": 100}]


def test_split_traffic_fails_closed():
    backend = FakeBackend()
    backend.traffic[DEMO] = [
        {"revisionName": PRIOR_DEMO, "percent": 50},
        {"revisionName": CANDIDATE_DEMO, "percent": 50},
    ]
    ops = ReleaseOps(backend, DEMO, AGENT)

    with pytest.raises(ReleaseFailure, match="exactly one 100% revision"):
        ops.assert_service_revision(DEMO, PRIOR_DEMO)


def test_authorized_request_never_exposes_token_to_subprocess_or_error(
    monkeypatch, caplog, tmp_path
):
    sentinel = "sentinel-token-that-must-never-escape"
    observed = {}
    subprocess_argv = []

    class FakeSocket:
        def settimeout(self, value):
            observed["read_timeout"] = value

    class FakeResponse:
        status = 200

        @staticmethod
        def read():
            return json.dumps(approved_result()).encode()

    class SuccessfulConnection:
        def __init__(self, host, port=None, timeout=None):
            observed["host"] = host
            observed["port"] = port
            observed["connect_timeout"] = timeout
            self.sock = FakeSocket()

        def connect(self):
            observed["connected"] = True

        def request(self, method, path, body, headers):
            observed["method"] = method
            observed["path"] = path
            observed["authorization"] = headers["Authorization"]

        @staticmethod
        def getresponse():
            return FakeResponse()

        @staticmethod
        def close():
            return None

    backend = CommandBackend("project", "region", DEMO, AGENT)
    monkeypatch.setattr(
        "releaseguard_cloudbuild.http.client.HTTPSConnection",
        SuccessfulConnection,
    )
    monkeypatch.setattr(
        backend,
        "_run",
        lambda args, **kwargs: subprocess_argv.append(args) or "",
    )

    result = backend._authorized_post_json(
        "https://agent.example.test/evaluate", "{}", sentinel
    )

    assert result["verdict"] == "APPROVE"
    assert observed["authorization"] == f"Bearer {sentinel}"
    assert observed["connect_timeout"] == 10.0
    assert observed["read_timeout"] == 60.0
    assert sentinel not in observed["path"]
    assert not any(
        sentinel in str(argument) for argv in subprocess_argv for argument in argv
    )
    assert sentinel not in caplog.text

    curl_argv = []

    def fake_curl(args, **kwargs):
        curl_argv.append(args)
        if any(str(argument).endswith("/checkout") for argument in args):
            return 'data-testid="checkout-button"'
        if "%{http_code}" in args:
            return "401"
        return ""

    monkeypatch.setattr(backend, "_curl", fake_curl)
    monkeypatch.setattr(backend, "_assert_health_url", lambda url: None)
    monkeypatch.setattr(
        backend,
        "_payload",
        lambda demo_url, commit: {
            "repo": "owner/repo",
            "commit_sha": commit,
        },
    )
    monkeypatch.setattr(backend, "_access_shared_token", lambda: sentinel)
    result_path = tmp_path / "result.json"
    backend._evaluation_smoke(
        "https://demo.example.test",
        "https://agent.example.test",
        COMMIT,
        result_path,
    )
    assert not any(sentinel in str(argument) for argv in curl_argv for argument in argv)
    assert sentinel not in str(result_path)
    assert sentinel not in result_path.read_text()

    class FailingConnection(SuccessfulConnection):
        def connect(self):
            raise RuntimeError(sentinel)

    monkeypatch.setattr(
        "releaseguard_cloudbuild.http.client.HTTPSConnection",
        FailingConnection,
    )
    with pytest.raises(ReleaseFailure) as captured:
        backend._authorized_post_json(
            "https://agent.example.test/evaluate", "{}", sentinel
        )

    assert sentinel not in str(captured.value)
    assert sentinel not in caplog.text


def test_payload_includes_verified_build_evidence_before_patch(monkeypatch):
    backend = CommandBackend("project", "region", DEMO, AGENT)
    monkeypatch.setattr(
        backend,
        "_get_json",
        lambda url, retry=False: {
            "sha": COMMIT,
            "files": [
                {
                    "filename": "safe.py",
                    "patch": "+print('safe')",
                }
            ],
        },
    )

    payload = backend._payload("https://demo.example.test", COMMIT)

    assert payload["diff_text"].startswith("Verified Cloud Build evidence")
    assert "sentinel token-isolation behavior" in payload["diff_text"]
    assert "does not authorize production traffic" in payload["diff_text"]
    assert "diff --git a/safe.py b/safe.py" in payload["diff_text"]
