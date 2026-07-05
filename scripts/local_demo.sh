#!/usr/bin/env bash

# local_demo.sh - Local Demonstration Script for ReleaseGuard Agent MVP

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================================================${NC}"
echo -e "${GREEN}             🛡️  ReleaseGuard Agent - Local MVP Demo 🛡️                 ${NC}"
echo -e "${BLUE}=========================================================================${NC}"

# Check docker daemon and docker-compose
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}Docker is not running. Please start Docker to run compose containers.${NC}"
    echo -e "You can also run both apps manually in separate terminals:"
    echo -e "  - Demo Store:   cd apps/demo_store && python3 -m uvicorn app.main:app --port 8081"
    echo -e "  - ReleaseGuard: cd apps/releaseguard && python3 -m uvicorn app.main:app --port 8080"
    exit 1
fi

echo -e "${YELLOW}Starting ReleaseGuard and Demo Store services via docker-compose...${NC}"
docker-compose up --build -d

echo -e "${YELLOW}Waiting for services to become healthy...${NC}"
for i in {1..10}; do
    HEALTH_RG=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/healthz 2>/dev/null || echo "failed")
    HEALTH_DS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/healthz 2>/dev/null || echo "failed")
    if [ "$HEALTH_RG" = "200" ] && [ "$HEALTH_DS" = "200" ]; then
        echo -e "${GREEN}Services are up and healthy!${NC}"
        break
    fi
    echo -e "Polling health endpoints (attempt $i/10)..."
    sleep 2
done

if [ "$HEALTH_RG" != "200" ] || [ "$HEALTH_DS" != "200" ]; then
    echo -e "${RED}Services failed to start properly. Current status:${NC}"
    echo -e "ReleaseGuard status: $HEALTH_RG"
    echo -e "Demo Store status: $HEALTH_DS"
    docker-compose logs
    exit 1
fi

echo -e "\n${BLUE}-------------------------------------------------------------------------${NC}"
echo -e "${GREEN}Scenario 1: Clean Pull Request (Expected: APPROVE)${NC}"
echo -e "${BLUE}-------------------------------------------------------------------------${NC}"

CLEAN_RESPONSE=$(curl -s -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/releaseguard-agent",
    "pr_number": 42,
    "commit_sha": "f00b4r123",
    "preview_url": "http://demo_store:8081",
    "changed_files": ["app/main.py"],
    "diff_text": "diff --git a/app/main.py b/app/main.py\nindex 123..456 100644\n--- a/app/main.py\n+++ b/app/main.py\n@@ -1,2 +1,2 @@\n-print(\"old\")\n+print(\"new\")"
  }')

echo -e "${GREEN}Response JSON:${NC}"
echo "$CLEAN_RESPONSE" | python3 -m json.tool

echo -e "\n${GREEN}Generated Markdown Report:${NC}"
echo "$CLEAN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['markdown_report'])"

echo -e "\n${BLUE}-------------------------------------------------------------------------${NC}"
echo -e "${RED}Scenario 2: Leaked Credentials / Secrets PR (Expected: BLOCK)${NC}"
echo -e "${BLUE}-------------------------------------------------------------------------${NC}"

SECRET_RESPONSE=$(curl -s -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/releaseguard-agent",
    "pr_number": 43,
    "commit_sha": "abc123secret",
    "preview_url": "http://demo_store:8081",
    "changed_files": ["config.py"],
    "diff_text": "diff --git a/config.py b/config.py\n+++ b/config.py\n+GITHUB_TOKEN = \"ghp_abcdefghijklmnopqrstuvwxyz0123456789\""
  }')

echo -e "${RED}Response JSON:${NC}"
echo "$SECRET_RESPONSE" | python3 -m json.tool

echo -e "\n${RED}Generated Markdown Report:${NC}"
echo "$SECRET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['markdown_report'])"

echo -e "\n${BLUE}-------------------------------------------------------------------------${NC}"
echo -e "${YELLOW}Stopping docker-compose containers...${NC}"
docker-compose down
echo -e "${GREEN}Done!${NC}"
