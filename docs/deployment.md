# Cloud Run Deployment Guide — ReleaseGuard Agent

This guide provides instructions to deploy the checkout demo store and the ReleaseGuard Agent to Google Cloud Run, verify URLs, and monitor execution logs.

---

## Prerequisites

1. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
2. Authenticate the CLI with your Google account:
   ```bash
   gcloud auth login
   ```
3. Set up or obtain a Google Cloud project ID (configured as `GOOGLE_CLOUD_PROJECT` env var).
4. Enable the necessary GCP APIs:
   ```bash
   gcloud services enable run.googleapis.com \
                          cloudbuild.googleapis.com \
                          artifactregistry.googleapis.com
   ```

---

## Deploying Applications

We use Cloud Run's source-based deployment feature (`gcloud run deploy --source`), which packages local source files, uploads them to Cloud Build, builds a secure container, and deploys it automatically.

### 1. Deploy Demo Store

The demo store simulates a web checkout application:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"

# Run the deployment script (defaults to asia-northeast1 region)
./scripts/deploy_demo_store.sh
```

**Override region example**:
```bash
./scripts/deploy_demo_store.sh us-central1
```

### 2. Deploy ReleaseGuard Agent

The agent requires configuring access credentials to hit the Gemini API and secure the manual validation webhook.

Set your deployment env variables first:
```bash
export GEMINI_API_KEY="AIzaSyYourGeminiApiKeyHere"
export RELEASEGUARD_SHARED_TOKEN="your-shared-security-bearer-token"
export LOG_LEVEL="INFO"
```

Then run the deployment script:
```bash
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
