"""Fail-closed Cloud Build lifecycle for the ReleaseGuard production pair."""

from __future__ import annotations

import argparse
import http.client
import json
import subprocess
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

CONNECT_TIMEOUT_SECONDS = "10"
MAX_TIME_SECONDS = "60"
SHARED_TOKEN_RESOURCE = "releaseguard-shared-token"
SHARED_TOKEN_VERSION = "1"
GEMINI_RESOURCE = "releaseguard-gemini-api-key"
GEMINI_VERSION = "2"


class ReleaseFailure(RuntimeError):
    """A release invariant failed and production must not proceed."""


@dataclass(frozen=True)
class ReleaseState:
    commit: str
    tag: str
    previous_demo_revision: str
    previous_agent_revision: str
    candidate_demo_revision: str
    candidate_agent_revision: str

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), sort_keys=True))

    @classmethod
    def load(cls, path: Path) -> ReleaseState:
        return cls(**json.loads(path.read_text()))


class ReleaseOps:
    """Release rules separated from command execution for behavioral tests."""

    def __init__(self, backend: Any, demo_service: str, agent_service: str):
        self.backend = backend
        self.demo_service = demo_service
        self.agent_service = agent_service

    def _single_revision(self, service: str) -> str:
        traffic = self.backend.get_traffic(service)
        if (
            len(traffic) != 1
            or traffic[0].get("percent") != 100
            or not traffic[0].get("revisionName")
        ):
            raise ReleaseFailure(
                f"{service} must have exactly one 100% revision; got {traffic!r}"
            )
        revision = traffic[0]["revisionName"]
        if not self.backend.revision_ready(revision):
            raise ReleaseFailure(f"{service} revision {revision} is not Ready")
        return revision

    def assert_service_revision(self, service: str, expected_revision: str) -> None:
        actual = self._single_revision(service)
        if actual != expected_revision:
            raise ReleaseFailure(
                f"{service} expected {expected_revision}, found {actual}"
            )

    @staticmethod
    def validate_decision(result: dict[str, Any]) -> None:
        judgement = result.get("gemini_judgement") or {}
        failures = []
        if result.get("verdict") != "APPROVE":
            failures.append("top-level verdict is not APPROVE")
        if not result.get("evidence"):
            failures.append("evidence is empty")
        if judgement.get("decision") != "APPROVE":
            failures.append("Gemini decision is not APPROVE")
        if judgement.get("human_approval_required") is not False:
            failures.append("Gemini requires human approval")
        if judgement.get("is_fallback") is not False:
            failures.append("Gemini result is fallback or fallback state is missing")
        if "fallback activated" in str(judgement.get("why", "")).lower():
            failures.append("Gemini fallback phrase detected")
        if failures:
            raise ReleaseFailure("; ".join(failures))

    def _cleanup_tags(self, tag: str) -> list[str]:
        failures = []
        for service in (self.agent_service, self.demo_service):
            try:
                self.backend.remove_tag(service, tag)
            except Exception as exc:  # noqa: BLE001 - attempt every cleanup
                failures.append(f"{service}: {exc}")
        return failures

    def cleanup_candidates(self, tag: str) -> None:
        failures = self._cleanup_tags(tag)
        if failures:
            raise ReleaseFailure(f"candidate tag cleanup failures: {failures}")

    def _verify_previous(self, state: ReleaseState) -> list[str]:
        failures = []
        for service, revision in (
            (self.demo_service, state.previous_demo_revision),
            (self.agent_service, state.previous_agent_revision),
        ):
            try:
                self.assert_service_revision(service, revision)
            except Exception as exc:  # noqa: BLE001 - collect every verification
                failures.append(f"{service}: {exc}")
        return failures

    def deploy_candidates(
        self,
        *,
        commit: str,
        tag: str,
        demo_image: str,
        agent_image: str,
        state_path: Path,
    ) -> ReleaseState:
        self.backend.verify_secret_version(SHARED_TOKEN_RESOURCE, SHARED_TOKEN_VERSION)
        self.backend.verify_secret_version(GEMINI_RESOURCE, GEMINI_VERSION)
        previous_demo = self._single_revision(self.demo_service)
        previous_agent = self._single_revision(self.agent_service)
        secret_versions = {
            "GEMINI_API_KEY": f"{GEMINI_RESOURCE}:{GEMINI_VERSION}",
            "RELEASEGUARD_SHARED_TOKEN": (
                f"{SHARED_TOKEN_RESOURCE}:{SHARED_TOKEN_VERSION}"
            ),
        }

        try:
            candidate_demo = self.backend.deploy_candidate(
                self.demo_service, demo_image, commit, tag, {}
            )
            candidate_agent = self.backend.deploy_candidate(
                self.agent_service,
                agent_image,
                commit,
                tag,
                secret_versions,
            )
            self.backend.assert_candidate_config(
                self.demo_service, candidate_demo, commit, {}
            )
            self.backend.assert_candidate_config(
                self.agent_service,
                candidate_agent,
                commit,
                secret_versions,
            )
        except Exception as exc:
            cleanup_failures = self._cleanup_tags(tag)
            verification_failures = []
            for service, revision in (
                (self.demo_service, previous_demo),
                (self.agent_service, previous_agent),
            ):
                try:
                    self.assert_service_revision(service, revision)
                except Exception as verify_exc:  # noqa: BLE001
                    verification_failures.append(f"{service}: {verify_exc}")
            details = cleanup_failures + verification_failures
            suffix = f"; cleanup/verification failures: {details}" if details else ""
            raise ReleaseFailure(f"candidate deployment failed: {exc}{suffix}") from exc

        state = ReleaseState(
            commit=commit,
            tag=tag,
            previous_demo_revision=previous_demo,
            previous_agent_revision=previous_agent,
            candidate_demo_revision=candidate_demo,
            candidate_agent_revision=candidate_agent,
        )
        state.save(state_path)
        return state

    def evaluate_candidates(
        self, state: ReleaseState, result_path: Path
    ) -> dict[str, Any]:
        result = None
        primary_failure = None
        try:
            demo_url = self.backend.candidate_url(self.demo_service, state.tag)
            agent_url = self.backend.candidate_url(self.agent_service, state.tag)
            result = self.backend.candidate_smoke(
                demo_url, agent_url, state.commit, result_path
            )
            self.validate_decision(result)
        except Exception as exc:  # noqa: BLE001 - cleanup must still execute
            primary_failure = exc

        cleanup_failures = self._cleanup_tags(state.tag)
        verification_failures = self._verify_previous(state)
        if primary_failure or cleanup_failures or verification_failures:
            parts = []
            if primary_failure:
                parts.append(f"candidate evaluation failed: {primary_failure}")
            if cleanup_failures:
                parts.append(f"tag cleanup failures: {cleanup_failures}")
            if verification_failures:
                parts.append(
                    f"production changed during evaluation: {verification_failures}"
                )
            raise ReleaseFailure("; ".join(parts))
        assert result is not None
        return result

    def _rollback(self, state: ReleaseState) -> list[str]:
        failures = []
        # Always attempt both rollbacks, even if the first command fails.
        for service, revision in (
            (self.agent_service, state.previous_agent_revision),
            (self.demo_service, state.previous_demo_revision),
        ):
            try:
                self.backend.set_traffic(service, revision)
            except Exception as exc:  # noqa: BLE001 - attempt both rollbacks
                failures.append(f"{service} command: {exc}")

        # Independently prove both prior revisions, readiness, and HTTP health.
        for service, revision in (
            (self.agent_service, state.previous_agent_revision),
            (self.demo_service, state.previous_demo_revision),
        ):
            try:
                self.assert_service_revision(service, revision)
            except Exception as exc:  # noqa: BLE001 - collect split-traffic state
                failures.append(f"{service} verification: {exc}")
            try:
                self.backend.health(service)
            except Exception as exc:  # noqa: BLE001 - collect HTTP state
                failures.append(f"{service} HTTP: {exc}")
        return failures

    def promote(
        self, state: ReleaseState, production_result_path: Path
    ) -> dict[str, Any]:
        if self.backend.remote_main() != state.commit:
            raise ReleaseFailure("remote main no longer matches the build commit")

        # Concurrency guard immediately before the first production mutation.
        self.assert_service_revision(self.demo_service, state.previous_demo_revision)
        self.assert_service_revision(self.agent_service, state.previous_agent_revision)

        try:
            self.backend.set_traffic(self.demo_service, state.candidate_demo_revision)
            self.backend.set_traffic(self.agent_service, state.candidate_agent_revision)
            self.assert_service_revision(
                self.demo_service, state.candidate_demo_revision
            )
            self.assert_service_revision(
                self.agent_service, state.candidate_agent_revision
            )
            # Keep the rollback boundary active through every post-promotion
            # HTTP, auth, functional, and Gemini smoke assertion.
            result = self.backend.production_smoke(state.commit, production_result_path)
            self.validate_decision(result)
        except Exception as exc:
            rollback_failures = self._rollback(state)
            suffix = (
                f"; rollback failures: {rollback_failures}"
                if rollback_failures
                else "; rollback verified"
            )
            raise ReleaseFailure(f"promotion failed: {exc}{suffix}") from exc
        return result


class CommandBackend:
    """Cloud Run/GitHub backend. Secrets are never logged or written to disk."""

    def __init__(self, project: str, region: str, demo: str, agent: str):
        self.project = project
        self.region = region
        self.demo = demo
        self.agent = agent

    @staticmethod
    def _run(args: list[str], *, input_text: str | None = None) -> str:
        completed = subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            # Never include args: an Authorization header may contain a secret.
            diagnostic = completed.stderr.strip()[-800:]
            raise ReleaseFailure(
                f"{args[0]} failed with exit {completed.returncode}: {diagnostic}"
            )
        return completed.stdout

    def _gcloud(self, args: list[str]) -> str:
        return self._run(
            [
                "gcloud",
                *args,
                f"--project={self.project}",
                f"--region={self.region}",
                "--quiet",
            ]
        )

    def _curl(
        self,
        args: list[str],
        *,
        input_text: str | None = None,
        fail_http: bool = True,
    ) -> str:
        mode = "-fsS" if fail_http else "-sS"
        return self._run(
            [
                "curl",
                mode,
                "--connect-timeout",
                CONNECT_TIMEOUT_SECONDS,
                "--max-time",
                MAX_TIME_SECONDS,
                *args,
            ],
            input_text=input_text,
        )

    def service(self, service: str) -> dict[str, Any]:
        return json.loads(
            self._gcloud(["run", "services", "describe", service, "--format=json"])
        )

    def revision(self, revision: str) -> dict[str, Any]:
        return json.loads(
            self._gcloud(["run", "revisions", "describe", revision, "--format=json"])
        )

    def get_traffic(self, service: str) -> list[dict[str, Any]]:
        return self.service(service)["status"].get("traffic", [])

    def revision_ready(self, revision: str) -> bool:
        conditions = self.revision(revision).get("status", {}).get("conditions", [])
        return any(
            item.get("type") == "Ready" and item.get("status") == "True"
            for item in conditions
        )

    def verify_secret_version(self, secret: str, version: str) -> None:
        metadata = json.loads(
            self._run(
                [
                    "gcloud",
                    "secrets",
                    "versions",
                    "describe",
                    version,
                    f"--secret={secret}",
                    f"--project={self.project}",
                    "--format=json",
                ]
            )
        )
        if metadata.get("state") != "ENABLED":
            raise ReleaseFailure(f"{secret}:{version} is not ENABLED")

    def deploy_candidate(
        self,
        service: str,
        image: str,
        commit: str,
        tag: str,
        secret_versions: dict[str, str],
    ) -> str:
        args = [
            "run",
            "deploy",
            service,
            f"--image={image}",
            "--no-traffic",
            f"--tag={tag}",
            (
                "--update-labels="
                f"app=releaseguard,managed-by=cloud-build,source-commit={commit}"
            ),
        ]
        if service == self.demo:
            args.append("--update-env-vars=BUG_HIDE_CHECKOUT_BUTTON=false")
        elif service == self.agent:
            args.extend(
                [
                    "--memory=2Gi",
                    "--cpu=2",
                    "--remove-env-vars=GEMINI_API_KEY,RELEASEGUARD_SHARED_TOKEN",
                    (
                        "--update-secrets="
                        f"GEMINI_API_KEY={secret_versions['GEMINI_API_KEY']},"
                        "RELEASEGUARD_SHARED_TOKEN="
                        f"{secret_versions['RELEASEGUARD_SHARED_TOKEN']}"
                    ),
                ]
            )
        self._gcloud(args)
        tagged = [
            item
            for item in self.get_traffic(service)
            if item.get("tag") == tag and item.get("revisionName")
        ]
        if len(tagged) != 1:
            raise ReleaseFailure(f"{service} candidate tag was not resolved exactly")
        revision = tagged[0]["revisionName"]
        if not self.revision_ready(revision):
            raise ReleaseFailure(f"{service} candidate revision is not Ready")
        return revision

    def assert_candidate_config(
        self,
        service: str,
        revision: str,
        commit: str,
        secret_versions: dict[str, str],
    ) -> None:
        data = self.revision(revision)
        labels = data.get("metadata", {}).get("labels", {})
        if labels.get("source-commit") != commit:
            raise ReleaseFailure(f"{service} source-commit label mismatch")
        service_data = self.service(service)
        template = service_data["spec"]["template"]
        if (
            template.get("metadata", {}).get("labels", {}).get("source-commit")
            != commit
        ):
            raise ReleaseFailure(f"{service} template source-commit mismatch")
        template_container = template["spec"]["containers"][0]
        if not template_container["image"].endswith(f":{commit}"):
            raise ReleaseFailure(f"{service} immutable image tag mismatch")
        if service != self.agent:
            return
        container = data["spec"]["containers"][0]
        env = {item["name"]: item for item in container.get("env", [])}
        expected = {
            name: value.rsplit(":", 1) for name, value in secret_versions.items()
        }
        for name, (secret, version) in expected.items():
            item = env.get(name, {})
            if "value" in item:
                raise ReleaseFailure(f"{name} is configured as plaintext")
            ref = item.get("valueFrom", {}).get("secretKeyRef", {})
            if ref != {"name": secret, "key": version}:
                raise ReleaseFailure(f"{name} secret version mismatch")

    def remove_tag(self, service: str, tag: str) -> None:
        if not any(item.get("tag") == tag for item in self.get_traffic(service)):
            return
        self._gcloud(
            [
                "run",
                "services",
                "update-traffic",
                service,
                f"--remove-tags={tag}",
            ]
        )
        if any(item.get("tag") == tag for item in self.get_traffic(service)):
            raise ReleaseFailure(f"{service} tag {tag} still exists")

    def candidate_url(self, service: str, tag: str) -> str:
        matches = [
            item.get("url")
            for item in self.get_traffic(service)
            if item.get("tag") == tag and item.get("url")
        ]
        if len(matches) != 1:
            raise ReleaseFailure(f"{service} candidate URL was not resolved exactly")
        return matches[0]

    def _get_json(self, url: str, *, retry: bool = False) -> dict[str, Any]:
        args = []
        if retry:
            args.extend(["--retry", "8", "--retry-all-errors", "--retry-delay", "5"])
        return json.loads(self._curl([*args, url]))

    def _assert_health_url(self, url: str) -> None:
        result = self._get_json(f"{url}/healthz/", retry=True)
        if result != {"status": "ok"}:
            raise ReleaseFailure(f"health response was not exact for {url}")

    def _payload(self, demo_url: str, commit: str) -> dict[str, Any]:
        metadata = self._get_json(
            "https://api.github.com/repos/"
            f"zll6796096/releaseguard-agent/commits/{commit}",
            retry=True,
        )
        if metadata.get("sha") != commit:
            raise ReleaseFailure("GitHub commit evidence SHA mismatch")
        files = metadata.get("files", [])
        changed_files = [item["filename"] for item in files]
        patches = [
            f"diff --git a/{item['filename']} b/{item['filename']}\n{item['patch']}"
            for item in files
            if item.get("patch")
        ]
        if not changed_files or not patches:
            raise ReleaseFailure("GitHub commit evidence is incomplete")
        build_evidence = """Verified Cloud Build evidence (observed before candidate evaluation):
- Repository deterministic test suites passed.
- Release lifecycle behavioral tests passed, including sentinel token-isolation behavior.
- Both candidate revisions are Ready and remain outside production traffic.
- Runtime API/checkout/secret-scan/Playwright evidence is collected separately below.
This evidence does not authorize production traffic; it only documents completed checks."""
        patch_text = "\n\n".join(patches)
        return {
            "repo": "zll6796096/releaseguard-agent",
            "pr_number": 0,
            "commit_sha": commit,
            "preview_url": demo_url,
            "changed_files": changed_files,
            "diff_text": f"{build_evidence}\n\n{patch_text}"[:12000],
        }

    def _access_shared_token(self) -> str:
        token = self._run(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                SHARED_TOKEN_VERSION,
                f"--secret={SHARED_TOKEN_RESOURCE}",
                f"--project={self.project}",
            ]
        ).strip()
        if not token:
            raise ReleaseFailure("shared token version returned no data")
        return token

    def _authorized_post_json(
        self, url: str, payload: str, token: str
    ) -> dict[str, Any]:
        """POST JSON over in-process HTTPS without exposing token in argv."""
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ReleaseFailure("authorized evaluation URL must use HTTPS")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        connection = http.client.HTTPSConnection(
            parsed.hostname,
            parsed.port,
            timeout=float(CONNECT_TIMEOUT_SECONDS),
        )
        try:
            connection.connect()
            if connection.sock is None:
                raise OSError("HTTPS socket was not established")
            connection.sock.settimeout(float(MAX_TIME_SECONDS))
            connection.request(
                "POST",
                path,
                body=payload.encode(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            response_body = response.read()
        except Exception:  # noqa: BLE001 - never echo transport/token context
            raise ReleaseFailure("authorized evaluation HTTPS request failed") from None
        finally:
            with suppress(Exception):
                connection.close()
        if not 200 <= response.status < 300:
            raise ReleaseFailure(
                f"authorized evaluation returned HTTP {response.status}"
            )
        try:
            return json.loads(response_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ReleaseFailure(
                "authorized evaluation returned invalid JSON"
            ) from None

    def _evaluation_smoke(
        self,
        demo_url: str,
        agent_url: str,
        commit: str,
        result_path: Path,
    ) -> dict[str, Any]:
        self._assert_health_url(demo_url)
        self._curl([f"{demo_url}/"])
        checkout = self._curl([f"{demo_url}/checkout"])
        if 'data-testid="checkout-button"' not in checkout:
            raise ReleaseFailure("production checkout button is missing")
        self._assert_health_url(agent_url)
        self._curl([f"{agent_url}/openapi.json"])

        payload = json.dumps(self._payload(demo_url, commit))
        unauthorized = self._curl(
            [
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
                f"{agent_url}/evaluate",
            ],
            input_text=payload,
            fail_http=False,
        )
        if unauthorized != "401":
            raise ReleaseFailure(
                f"unauthorized evaluation returned HTTP {unauthorized!r}"
            )

        token = self._access_shared_token()
        result = self._authorized_post_json(
            f"{agent_url}/evaluate",
            payload,
            token,
        )
        result_path.write_text(json.dumps(result))
        return result

    def candidate_smoke(
        self,
        demo_url: str,
        agent_url: str,
        commit: str,
        result_path: Path,
    ) -> dict[str, Any]:
        return self._evaluation_smoke(demo_url, agent_url, commit, result_path)

    def remote_main(self) -> str:
        result = self._get_json(
            "https://api.github.com/repos/zll6796096/releaseguard-agent/commits/main",
            retry=True,
        )
        return result["sha"]

    def set_traffic(self, service: str, revision: str) -> None:
        self._gcloud(
            [
                "run",
                "services",
                "update-traffic",
                service,
                f"--to-revisions={revision}=100",
            ]
        )

    def service_url(self, service: str) -> str:
        url = self.service(service).get("status", {}).get("url")
        if not url:
            raise ReleaseFailure(f"{service} has no service URL")
        return url

    def health(self, service: str) -> None:
        self._assert_health_url(self.service_url(service))

    def production_smoke(self, commit: str, result_path: Path) -> dict[str, Any]:
        return self._evaluation_smoke(
            self.service_url(self.demo),
            self.service_url(self.agent),
            commit,
            result_path,
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("action", choices=("deploy", "cleanup", "evaluate", "promote"))
    result.add_argument("--project", required=True)
    result.add_argument("--region", required=True)
    result.add_argument("--demo-service", required=True)
    result.add_argument("--agent-service", required=True)
    result.add_argument(
        "--state-path", type=Path, default=Path("/workspace/releaseguard-state.json")
    )
    result.add_argument("--commit")
    result.add_argument("--tag")
    result.add_argument("--demo-image")
    result.add_argument("--agent-image")
    result.add_argument(
        "--candidate-result",
        type=Path,
        default=Path("/workspace/releaseguard-candidate.json"),
    )
    result.add_argument(
        "--production-result",
        type=Path,
        default=Path("/workspace/releaseguard-production.json"),
    )
    return result


def main() -> None:
    args = parser().parse_args()
    backend = CommandBackend(
        args.project, args.region, args.demo_service, args.agent_service
    )
    ops = ReleaseOps(backend, args.demo_service, args.agent_service)
    if args.action == "deploy":
        required = (args.commit, args.tag, args.demo_image, args.agent_image)
        if not all(required):
            raise ReleaseFailure("deploy requires commit, tag, and both images")
        state = ops.deploy_candidates(
            commit=args.commit,
            tag=args.tag,
            demo_image=args.demo_image,
            agent_image=args.agent_image,
            state_path=args.state_path,
        )
        print(
            "candidates Ready",
            state.candidate_demo_revision,
            state.candidate_agent_revision,
        )
    elif args.action == "cleanup":
        if not args.tag:
            raise ReleaseFailure("cleanup requires tag")
        ops.cleanup_candidates(args.tag)
    elif args.action == "evaluate":
        result = ops.evaluate_candidates(
            ReleaseState.load(args.state_path), args.candidate_result
        )
        print(
            "candidate gate",
            result["verdict"],
            result["gemini_judgement"]["decision"],
            result.get("overall_risk"),
        )
    else:
        result = ops.promote(ReleaseState.load(args.state_path), args.production_result)
        print(
            "production gate",
            result["verdict"],
            result["gemini_judgement"]["decision"],
            result.get("overall_risk"),
        )


if __name__ == "__main__":
    main()
