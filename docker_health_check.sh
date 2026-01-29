#!/bin/bash
# Quick Docker health check script

echo "🔍 Docker Health Check"
echo "======================"
echo ""

# Check if containers are running
echo "1. Container Status:"
sudo docker-compose ps
echo ""

# Check database connection from bot
echo "2. Bot Database Configuration:"
sudo docker-compose logs aroma_bot 2>&1 | grep "\[DATABASE\]" | tail -2
echo ""

# Check if tables exist in aroma_bot
echo "3. Tables in aroma_bot database:"
sudo docker-compose exec postgres psql -U alan -d aroma_bot -c "\dt" | head -10
echo ""

# Check for errors
echo "4. Recent Errors:"
ERROR_COUNT=$(sudo docker-compose logs aroma_bot 2>&1 | grep -i "error\|exception" | tail -5 | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Found $ERROR_COUNT recent errors:"
    sudo docker-compose logs aroma_bot 2>&1 | grep -i "error\|exception" | tail -5
else
    echo "✅ No recent errors"
fi
echo ""

echo "5. Bot Status:"
if sudo docker-compose logs aroma_bot 2>&1 | tail -20 | grep -q "relation.*does not exist"; then
    echo "❌ Bot has database connection issues"
else
    echo "✅ Bot appears to be running normally"
fi
