# Cloud Run Deployment Guide — ReleaseGuard Agent

This guide describes the guarded Git-to-Cloud-Run delivery path for the checkout demo
store and ReleaseGuard Agent.

---

## Prerequisites

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
2. Authenticate the CLI with your Google account:
   ```bash
   gcloud auth login
   ```
3. Use the `zhang23-23` project and the shared least-privilege Cloud Build service account.
4. Ensure the required GCP APIs are enabled:
   ```bash
   gcloud services enable run.googleapis.com \
                          cloudbuild.googleapis.com \
                          artifactregistry.googleapis.com
   ```

---

## Production delivery

`releaseguard-main-cloud-run` builds both production services from `main`. The
agent pins `releaseguard-gemini-api-key:2` and
`releaseguard-shared-token:1` from Secret Manager after checking that both
versions are enabled using metadata only. The shared token is synchronized to
the GitHub Actions secret of the same purpose without printing it. Neither
credential is passed as a plaintext Cloud Run value. The existing default
Compute runtime service account and its roles are intentionally inherited and
are not changed by this delivery pipeline.

The Cloud Build identity has the one-permission custom role
`appsSecretVersionMetadataReader`
(`secretmanager.versions.get`) only on those two ReleaseGuard secret resources.
Its shared-token value access is likewise secret-resource scoped; it has no
project-level Secret Manager role and cannot access the Gemini key value.
Authenticated smoke requests are sent by the lifecycle process directly over
verified HTTPS; the shared token is never placed in a subprocess argument,
command string, file path, log message, or propagated exception.

The build tests both apps, builds immutable images from the same Git commit,
deploys no-traffic candidates, and makes the candidate agent evaluate the
candidate clean demo. It requires `verdict=APPROVE` before either production
traffic route changes. The promotion step verifies that the build still
represents the tip of `main` and that neither prior production revision changed
while the candidates were being tested. A partial traffic change is rolled back
to both recorded previous revisions. Candidate tags are removed after every
evaluation outcome. The rollback boundary remains active through post-promotion
traffic, readiness, HTTP, bearer-auth, functional checkout, and non-fallback
Gemini checks; rollback command or verification errors fail the build and are
reported rather than ignored.

`demo-store-pr-hidden` remains the intentionally broken PR demonstration and is
never updated or granted to the production trigger.

The former externally issued plaintext Gemini key must be revoked at its
original issuer because this GCP project cannot prove authority over that
external credential.

Push a clean, synchronized `main` branch to run automatically. The two recovery
helpers perform the same guarded trigger action:

```bash
./scripts/deploy_demo_store.sh
./scripts/deploy_releaseguard.sh
```

---

## Verifying Deployed URLs

Once deployment completes, the scripts print commands to fetch the service endpoints. You can also fetch the URLs directly using the following commands:

```bash
# Verify Demo Store URL
gcloud run services describe demo-store \
  --region asia-northeast1 \
  --format="value(status.url)"

# Verify ReleaseGuard URL
gcloud run services describe releaseguard-agent \
  --region asia-northeast1 \
  --format="value(status.url)"
```

Test the deployed services:
1. Open the Demo Store URL in your web browser. You should see the landing page. Click **Go to Checkout** and confirm the pay button is visible.
2. Hit the ReleaseGuard `/healthz` endpoint:
   ```bash
   curl https://<YOUR-RELEASEGUARD-URL>/healthz
   # Should return: {"status": "ok"}
   ```

---

## Monitoring and Logs

You can view execution traces, logs, and container metrics directly using `gcloud` or through the Google Cloud Console.

### Stream Revision Logs

To watch execution logs in real-time (useful when debugging incoming PR webhooks or evaluation checks):

```bash
# Stream ReleaseGuard Agent logs
gcloud beta run services logs tail releaseguard-agent --region asia-northeast1
```

### Trace Checks
Check the log outputs for key events during an evaluation run:
- `evaluation_started`: Triggered when `/evaluate` is hit. Includes repository and PR commit metadata.
- `evaluation_completed`: Summarizes decision results and overall risk scores.
- `playwright_probe` metrics: Traces Chromium page loading times and selector matching status.
