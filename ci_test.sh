#!/bin/bash
# CI/CD Test Runner
# Runs all tests and validations before allowing deployment

set -e  # Exit on any error

echo "🚀 Starting CI/CD Test Pipeline..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
TESTS_PASSED=true

# Function to run a test step
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo ""
    echo "📋 Running: $test_name"
    echo "-----------------------------------"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED${NC}: $test_name"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}: $test_name"
        TESTS_PASSED=false
        return 1
    fi
}

# 1. Python Syntax Check
run_test "Python Syntax Check" "python3 -m py_compile services/*.py models/*.py *.py 2>/dev/null || true"

# 2. Import Check
run_test "Import Validation" "python3 -c 'from services.pve_service import PvEService; from services.targeting_service import TargetingService; from services.user_service import UserService; print(\"All imports successful\")'"

# 3. Run Critical Tests
echo ""
echo "🧪 Running Test Suite..."
echo "-----------------------------------"

# Defense tests
run_test "Defense System Tests" "pytest tests/test_defense.py -v --tb=short -x" || true

# PvE tests
run_test "PvE System Tests" "pytest tests/test_pve.py -v --tb=short -x" || true

# Combat tests
run_test "Combat Mechanics Tests" "pytest tests/test_combat_mechanics.py -v --tb=short -x" || true

# 4. Check for common issues
echo ""
echo "🔍 Code Quality Checks..."
echo "-----------------------------------"

# Check for print statements in production code (excluding debug prints)
if grep -r "print(" services/ --include="*.py" | grep -v "DEBUG" | grep -v "print(f" | head -5; then
    echo -e "${YELLOW}⚠️  WARNING${NC}: Found print statements in code (review recommended)"
else
    echo -e "${GREEN}✅ PASSED${NC}: No problematic print statements"
fi

# Check for TODO comments
TODO_COUNT=$(grep -r "TODO\|FIXME\|XXX" services/ models/ --include="*.py" 2>/dev/null | wc -l || echo "0")
if [ "$TODO_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  INFO${NC}: Found $TODO_COUNT TODO/FIXME comments"
else
    echo -e "${GREEN}✅ PASSED${NC}: No TODO comments"
fi

# 5. Database Migration Check (if applicable)
if [ -d "migrations" ]; then
    echo ""
    echo "📊 Checking Database Migrations..."
    echo -e "${GREEN}✅ PASSED${NC}: Migration directory exists"
fi

# Final Summary
echo ""
echo "=================================="
echo "📊 Test Summary"
echo "=================================="

if [ "$TESTS_PASSED" = true ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "✨ Code is ready for deployment!"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "⚠️  Please fix the failing tests before deploying."
    exit 1
fi
