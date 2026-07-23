#!/usr/bin/env bash

# deploy_releaseguard.sh - Runs the guarded ReleaseGuard Cloud Build trigger.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "ERROR: Cloud Run delivery is allowed only from main" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain=v1)" ]]; then
  echo "ERROR: classify and commit local changes before delivery" >&2
  git status --short
  exit 1
fi

git fetch --prune origin
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
gcloud builds triggers run releaseguard-main-cloud-run \
  --project=zhang23-23 \
  --region=global \
  --branch=main
