#!/bin/bash
# Quick test script for security gate validation
set -e

# Configuration
TEST_REPO="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Usage
if [ -z "$TEST_REPO" ]; then
    echo "Usage: $0 /path/to/test/repository"
    echo ""
    echo "Examples:"
    echo "  $0 /tmp/test-workspace"
    echo "  $0 ~/Repos/h2o-test-app"
    echo ""
    exit 1
fi

# Validate test repo exists
if [ ! -d "$TEST_REPO" ]; then
    echo -e "${RED}Error: Directory not found: $TEST_REPO${NC}"
    exit 1
fi

echo "=============================================="
echo "🧪 Security Gate Quick Test"
echo "=============================================="
echo "Test repository: $TEST_REPO"
echo "Script location: $SCRIPT_DIR"
echo ""

# Check for lockfiles
echo "📋 Checking for lockfiles..."
HAS_LOCKFILE=false

if [ -f "$TEST_REPO/package-lock.json" ]; then
    echo "  ✅ Found: package-lock.json"
    HAS_LOCKFILE=true
fi

if [ -f "$TEST_REPO/poetry.lock" ]; then
    echo "  ✅ Found: poetry.lock"
    HAS_LOCKFILE=true
fi

if [ -f "$TEST_REPO/uv.lock" ]; then
    echo "  ✅ Found: uv.lock"
    HAS_LOCKFILE=true
fi

if [ -f "$TEST_REPO/go.sum" ]; then
    echo "  ✅ Found: go.sum"
    HAS_LOCKFILE=true
fi

if [ "$HAS_LOCKFILE" = false ]; then
    echo -e "  ${YELLOW}⚠️  No lockfiles found${NC}"
    echo ""
    echo "Generate lockfiles first:"
    echo "  npm install --package-lock-only  # Node.js"
    echo "  uv lock                          # Python"
    echo "  go mod tidy                      # Go"
    echo ""
    exit 1
fi

echo ""

# Run the security gate
echo "🔍 Running dependency age validation..."
echo ""

cd "$TEST_REPO"
export WORKSPACE_PATH="$TEST_REPO"

if python3 "$SCRIPT_DIR/scripts/dependency_age_gate.py"; then
    echo ""
    echo "=============================================="
    echo -e "${GREEN}✅ TEST PASSED: Security gate validation successful${NC}"
    echo "=============================================="
    exit 0
else
    EXIT_CODE=$?
    echo ""
    echo "=============================================="
    echo -e "${RED}❌ TEST FAILED: Security violations detected${NC}"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Review violations above"
    echo "  2. Wait for packages to mature (recommended)"
    echo "  3. Request break-glass exemption if urgent"
    echo ""
    exit $EXIT_CODE
fi
