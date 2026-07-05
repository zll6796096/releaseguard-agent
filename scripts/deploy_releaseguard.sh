#!/usr/bin/env bash

# deploy_releaseguard.sh - Deploys the ReleaseGuard Agent to Google Cloud Run

set -euo pipefail

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================================================${NC}"
echo -e "${GREEN}          🚀 Deploying ReleaseGuard Agent to Google Cloud Run            ${NC}"
echo -e "${GREEN}=========================================================================${NC}"

# Check for required Project variable
if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ]; then
    echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT environment variable is not set.${NC}"
    echo -e "Please configure it using: export GOOGLE_CLOUD_PROJECT=\"your-project-id\""
    exit 1
fi

# Check for required Gemini API key
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo -e "${RED}Error: GEMINI_API_KEY environment variable is not set.${NC}"
    echo -e "Required to generate release gate AI synthesis judgements."
    exit 1
fi

# Check for required shared token
if [ -z "${RELEASEGUARD_SHARED_TOKEN:-}" ]; then
    echo -e "${RED}Error: RELEASEGUARD_SHARED_TOKEN environment variable is not set.${NC}"
    echo -e "Required to secure the manual evaluation API."
    exit 1
fi

# Set default Log level if empty
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Region setup (Accept region argument or fallback to asia-northeast1)
REGION="${1:-${CLOUD_RUN_REGION:-asia-northeast1}}"
SERVICE_NAME="releaseguard-agent"

echo -e "GCP Project:   ${YELLOW}${GOOGLE_CLOUD_PROJECT}${NC}"
echo -e "Region:        ${YELLOW}${REGION}${NC}"
echo -e "Service Name:  ${YELLOW}${SERVICE_NAME}${NC}"
echo -e "Log Level:     ${YELLOW}${LOG_LEVEL}${NC}"
echo -e "Deployment:    ${YELLOW}Source-based Build & Deploy${NC}\n"

# Verify gcloud authentication state
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo -e "${RED}Error: No active gcloud credentials found. Please run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Set the active project in gcloud configuration
gcloud config set project "${GOOGLE_CLOUD_PROJECT}"

# Navigate to the service folder
cd "$(dirname "$0")/../apps/releaseguard"

# Deploy to Cloud Run from source
# Playwright and Chromium require more CPU/memory resources for reliable execution
echo -e "${GREEN}Building and deploying releaseguard-agent service...${NC}"
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --memory 2Gi \
  --cpu 2 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY},RELEASEGUARD_SHARED_TOKEN=${RELEASEGUARD_SHARED_TOKEN},LOG_LEVEL=${LOG_LEVEL},RELEASEGUARD_PORT=8080"

echo -e "\n${GREEN}Deployment finished successfully!${NC}"
echo -e "Verify the service URL by running:"
echo -e "  ${YELLOW}gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'${NC}"
