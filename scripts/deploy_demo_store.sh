#!/usr/bin/env bash

# deploy_demo_store.sh - Deploys the checkout demo store to Google Cloud Run

set -euo pipefail

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================================================${NC}"
echo -e "${GREEN}          🚀 Deploying Demo Store to Google Cloud Run                   ${NC}"
echo -e "${GREEN}=========================================================================${NC}"

# Check for required Google Cloud Project environment variable
if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ]; then
    echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT environment variable is not set.${NC}"
    echo -e "Please configure it using: export GOOGLE_CLOUD_PROJECT=\"your-project-id\""
    exit 1
fi

# Region setup (Accept region argument or fallback to asia-northeast1)
REGION="${1:-${CLOUD_RUN_REGION:-asia-northeast1}}"
SERVICE_NAME="demo-store"

echo -e "GCP Project:   ${YELLOW}${GOOGLE_CLOUD_PROJECT}${NC}"
echo -e "Region:        ${YELLOW}${REGION}${NC}"
echo -e "Service Name:  ${YELLOW}${SERVICE_NAME}${NC}"
echo -e "Deployment:    ${YELLOW}Source-based Build & Deploy${NC}\n"

# Verify gcloud authentication state
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo -e "${RED}Error: No active gcloud credentials found. Please run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Set the active project in gcloud configuration
gcloud config set project "${GOOGLE_CLOUD_PROJECT}"

# Navigate to the service folder
cd "$(dirname "$0")/../apps/demo_store"

# Deploy to Cloud Run from source
echo -e "${GREEN}Building and deploying demo-store service...${NC}"
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars="BUG_HIDE_CHECKOUT_BUTTON=false"

echo -e "\n${GREEN}Deployment finished successfully!${NC}"
echo -e "Verify the service URL by running:"
echo -e "  ${YELLOW}gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'${NC}"
