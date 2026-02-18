#!/bin/bash
# Deploy to DietPi
# This script safely deploys code to the DietPi server with automatic rollback on failure

set -e

# Configuration
DIETPI_USER="${DIETPI_USER:-dietpi}"
DIETPI_HOST="${DIETPI_HOST:-dietpi.local}"
DIETPI_PATH="${DIETPI_PATH:-/home/dietpi/aroma}"
BACKUP_DIR="/tmp/aroma_backup_$(date +%Y%m%d_%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Aroma Bot Deployment to DietPi${NC}"
echo "===================================="
echo ""

# Step 1: Run CI tests locally
echo -e "${YELLOW}📋 Step 1/6: Running CI Tests...${NC}"
if ! ./ci_test.sh; then
    echo -e "${RED}❌ CI tests failed. Deployment aborted.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ CI tests passed${NC}"
echo ""

# Step 2: Commit changes
echo -e "${YELLOW}📋 Step 2/6: Committing changes...${NC}"
read -p "Enter commit message: " COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Deploy: $(date +%Y-%m-%d\ %H:%M:%S)"
fi

git add -A
git commit -m "$COMMIT_MSG" || echo "No changes to commit"
echo -e "${GREEN}✅ Changes committed${NC}"
echo ""

# Step 3: Create backup on DietPi
echo -e "${YELLOW}📋 Step 3/6: Creating backup on DietPi...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} "mkdir -p ${BACKUP_DIR} && cp -r ${DIETPI_PATH}/* ${BACKUP_DIR}/" || {
    echo -e "${RED}❌ Failed to create backup${NC}"
    exit 1
}
echo -e "${GREEN}✅ Backup created at ${BACKUP_DIR}${NC}"
echo ""

# Step 4: Push to git
echo -e "${YELLOW}📋 Step 4/6: Pushing to git repository...${NC}"
git push origin main || {
    echo -e "${RED}❌ Failed to push to git${NC}"
    exit 1
}
echo -e "${GREEN}✅ Pushed to git${NC}"
echo ""

# Step 5: Pull on DietPi
echo -e "${YELLOW}📋 Step 5/6: Pulling changes on DietPi...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} "cd ${DIETPI_PATH} && git pull origin main" || {
    echo -e "${RED}❌ Failed to pull changes${NC}"
    echo -e "${YELLOW}🔄 Rolling back...${NC}"
    ssh ${DIETPI_USER}@${DIETPI_HOST} "rm -rf ${DIETPI_PATH}/* && cp -r ${BACKUP_DIR}/* ${DIETPI_PATH}/"
    exit 1
}
echo -e "${GREEN}✅ Changes pulled${NC}"
echo ""

# Step 6: Restart bot service
echo -e "${YELLOW}📋 Step 6/6: Restarting bot service...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} "cd ${DIETPI_PATH} && docker compose build && sudo systemctl restart aroma-bot" || {
    echo -e "${RED}❌ Failed to restart service${NC}"
    echo -e "${YELLOW}🔄 Rolling back...${NC}"
    ssh ${DIETPI_USER}@${DIETPI_HOST} "rm -rf ${DIETPI_PATH}/* && cp -r ${BACKUP_DIR}/* ${DIETPI_PATH}/ && sudo systemctl restart aroma-bot"
    exit 1
}
echo -e "${GREEN}✅ Service restarted${NC}"
echo ""

# Step 7: Health check
echo -e "${YELLOW}📋 Performing health check...${NC}"
sleep 5
if ssh ${DIETPI_USER}@${DIETPI_HOST} "sudo systemctl is-active --quiet aroma-bot"; then
    echo -e "${GREEN}✅ Bot is running successfully${NC}"
    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${BLUE}Backup location: ${BACKUP_DIR}${NC}"
else
    echo -e "${RED}❌ Bot failed to start${NC}"
    echo -e "${YELLOW}🔄 Rolling back...${NC}"
    ssh ${DIETPI_USER}@${DIETPI_HOST} "rm -rf ${DIETPI_PATH}/* && cp -r ${BACKUP_DIR}/* ${DIETPI_PATH}/ && sudo systemctl restart aroma-bot"
    exit 1
fi
