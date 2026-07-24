import json

import pytest
from releaseguard_cloudbuild import ReleaseFailure, ReleaseOps, ReleaseState

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
