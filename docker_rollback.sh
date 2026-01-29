#!/bin/bash
# Docker rollback script
# Rolls back to a previous Docker image version

set -e

# Configuration
DIETPI_USER="${DIETPI_USER:-dietpi}"
DIETPI_HOST="${DIETPI_HOST:-dietpi.local}"
DIETPI_PATH="${DIETPI_PATH:-/home/dietpi/aroma}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 Aroma Bot Docker Rollback${NC}"
echo "===================================="
echo ""

# List available versions
echo -e "${YELLOW}📋 Available versions on DietPi:${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} "docker images aroma-bot --format '{{.Tag}}' | grep -v latest" || {
    echo -e "${RED}❌ No previous versions found${NC}"
    exit 1
}
echo ""

# Get version to rollback to
read -p "Enter version to rollback to (or 'latest' for previous): " VERSION
if [ -z "$VERSION" ]; then
    echo -e "${RED}❌ No version specified${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Rolling back to version: $VERSION${NC}"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

# Perform rollback
echo -e "${YELLOW}📋 Performing rollback...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} << EOF
    set -e
    cd ${DIETPI_PATH}
    
    # Tag the rollback version as latest
    docker tag aroma-bot:$VERSION aroma-bot:latest
    
    # Restart containers with new image
    docker-compose down
    docker-compose up -d
    
    # Wait for startup
    sleep 5
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Rollback failed${NC}"
    exit 1
fi

# Health check
echo -e "${YELLOW}📋 Performing health check...${NC}"
ssh ${DIETPI_USER}@${DIETPI_HOST} "cd ${DIETPI_PATH} && docker-compose ps | grep aroma_bot | grep -q Up" || {
    echo -e "${RED}❌ Health check failed after rollback${NC}"
    exit 1
}

echo -e "${GREEN}✅ Rollback completed successfully!${NC}"
echo -e "${BLUE}Rolled back to version: $VERSION${NC}"
echo ""
echo "View logs: ssh ${DIETPI_USER}@${DIETPI_HOST} 'cd ${DIETPI_PATH} && docker-compose logs -f aroma_bot'"
