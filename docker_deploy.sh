#!/bin/bash
# Docker-based deployment to DietPi with blue-green deployment
# This script provides zero-downtime deployment using Docker containers

set -e

# Configuration
DIETPI_USER="${DIETPI_USER:-dietpi}"
DIETPI_HOST="${DIETPI_HOST:-dietpi.local}"
DIETPI_PATH="${DIETPI_PATH:-/home/dietpi/aroma}"
VERSION=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 Aroma Bot Docker Deployment${NC}"
echo "===================================="
echo "Version: $VERSION"
echo ""

# Step 1: Run CI tests locally
echo -e "${YELLOW}📋 Step 1/8: Running CI Tests...${NC}"
if ! ./ci_test.sh; then
    echo -e "${RED}❌ CI tests failed. Deployment aborted.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ CI tests passed${NC}"
echo ""

# Step 2: Build Docker image
echo -e "${YELLOW}📋 Step 2/8: Building Docker image...${NC}"
docker-compose build || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Docker image built${NC}"
echo ""

# Step 3: Tag image with version
echo -e "${YELLOW}📋 Step 3/8: Tagging image...${NC}"
docker tag aroma-bot:latest aroma-bot:$VERSION
echo -e "${GREEN}✅ Image tagged as aroma-bot:$VERSION${NC}"
echo ""

# Step 4: Commit and push changes
echo -e "${YELLOW}📋 Step 4/8: Committing changes...${NC}"
read -p "Enter commit message: " COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Docker deploy: $VERSION"
fi

git add -A
git commit -m "$COMMIT_MSG" || echo "No changes to commit"
git push origin main || {
    echo -e "${RED}❌ Failed to push to git${NC}"
    exit 1
}
echo -e "${GREEN}✅ Changes pushed to git${NC}"
echo ""

# Step 5: Save and transfer Docker image
echo -e "${YELLOW}📋 Step 5/8: Transferring Docker image to DietPi...${NC}"
docker save aroma-bot:$VERSION | gzip > /tmp/aroma-bot-$VERSION.tar.gz
scp /tmp/aroma-bot-$VERSION.tar.gz ${DIETPI_USER}@${DIETPI_HOST}:/tmp/ || {
    echo -e "${RED}❌ Failed to transfer image${NC}"
    exit 1
}
rm /tmp/aroma-bot-$VERSION.tar.gz
echo -e "${GREEN}✅ Image transferred${NC}"
echo ""

# Step 6: Load image and deploy on DietPi
echo -e "${YELLOW}📋 Step 6/8: Deploying on DietPi...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} << EOF
    set -e
    cd ${DIETPI_PATH}
    
    # Pull latest code
    git pull origin main
    
    # Load new Docker image
    gunzip -c /tmp/aroma-bot-$VERSION.tar.gz | docker load
    rm /tmp/aroma-bot-$VERSION.tar.gz
    
    # Tag as latest
    docker tag aroma-bot:$VERSION aroma-bot:latest
    
    # Blue-green deployment
    # Check if bot is running
    if docker ps | grep -q aroma_bot; then
        echo "🔵 Blue container running, deploying green..."
        
        # Start green container
        docker-compose up -d --no-deps --scale aroma_bot=2 aroma_bot
        
        # Wait for health check
        sleep 10
        
        # Check if green is healthy
        if docker ps | grep -q aroma_bot; then
            echo "✅ Green container healthy, stopping blue..."
            # Scale down to 1 (removes old container)
            docker-compose up -d --no-deps --scale aroma_bot=1 aroma_bot
        else
            echo "❌ Green container failed, rolling back..."
            docker-compose up -d --no-deps --scale aroma_bot=1 aroma_bot
            exit 1
        fi
    else
        echo "🟢 No running container, starting fresh..."
        docker-compose up -d
    fi
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Deployed successfully${NC}"
echo ""

# Step 7: Health check
echo -e "${YELLOW}📋 Step 7/8: Performing health check...${NC}"
sleep 5
ssh ${DIETPI_USER}@${DIETPI_HOST} "cd ${DIETPI_PATH} && docker-compose ps | grep aroma_bot | grep -q Up" || {
    echo -e "${RED}❌ Health check failed${NC}"
    echo -e "${YELLOW}🔄 Rolling back...${NC}"
    ssh ${DIETPI_USER}@${DIETPI_HOST} "cd ${DIETPI_PATH} && docker-compose down && docker-compose up -d"
    exit 1
}
echo -e "${GREEN}✅ Health check passed${NC}"
echo ""

# Step 8: Cleanup old images
echo -e "${YELLOW}📋 Step 8/8: Cleaning up old images...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} "docker image prune -f" || true
echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}Version: $VERSION${NC}"
echo ""
echo "View logs: ssh ${DIETPI_USER}@${DIETPI_HOST} 'cd ${DIETPI_PATH} && docker-compose logs -f aroma_bot'"
