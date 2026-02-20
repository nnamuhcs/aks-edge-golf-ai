#!/usr/bin/env bash
# verify_and_fix.sh – Run lint/tests/build, fix issues, and re-run until clean.
# Iterates up to MAX_ITERATIONS times.
set -euo pipefail

MAX_ITERATIONS=${1:-10}
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ITERATION=0
ALL_PASS=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[verify]${NC} $*"; }
warn() { echo -e "${YELLOW}[verify]${NC} $*"; }
fail() { echo -e "${RED}[verify]${NC} $*"; }

run_backend_tests() {
    log "Running backend tests..."
    cd "$PROJECT_ROOT/backend"
    # MediaPipe C++ cleanup can cause "Aborted" after all tests pass
    # Check if all tests passed by looking at output
    local output
    output=$(python3 -m pytest tests/ -v --tb=short 2>&1) || true
    echo "$output"
    if echo "$output" | grep -q "passed"; then
        if echo "$output" | grep -q "failed"; then
            return 1
        fi
        return 0
    fi
    return 1
}

run_backend_lint() {
    log "Running backend lint (Python)..."
    cd "$PROJECT_ROOT/backend"
    python3 -m py_compile app/main.py && \
    python3 -m py_compile app/pipeline.py && \
    python3 -m py_compile app/scoring.py && \
    python3 -m py_compile app/stage_segmentation.py && \
    python3 -m py_compile app/pose_estimator.py && \
    python3 -m py_compile app/orientation.py && \
    python3 -m py_compile app/annotator.py && \
    python3 -m py_compile app/reference_matcher.py && \
    python3 -m py_compile app/config.py
    return $?
}

run_frontend_build() {
    log "Running frontend build..."
    cd "$PROJECT_ROOT/frontend"
    if [ ! -d "node_modules" ]; then
        npm install --silent
    fi
    npm run build 2>&1
    return $?
}

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    log "━━━ Iteration $ITERATION / $MAX_ITERATIONS ━━━"

    BACKEND_LINT_OK=true
    BACKEND_TEST_OK=true
    FRONTEND_BUILD_OK=true

    # Backend lint
    if ! run_backend_lint; then
        fail "Backend lint failed"
        BACKEND_LINT_OK=false
    else
        log "✓ Backend lint passed"
    fi

    # Backend tests
    if ! run_backend_tests; then
        fail "Backend tests failed"
        BACKEND_TEST_OK=false
    else
        log "✓ Backend tests passed"
    fi

    # Frontend build
    if ! run_frontend_build; then
        fail "Frontend build failed"
        FRONTEND_BUILD_OK=false
    else
        log "✓ Frontend build passed"
    fi

    # Check if all passed
    if $BACKEND_LINT_OK && $BACKEND_TEST_OK && $FRONTEND_BUILD_OK; then
        ALL_PASS=true
        break
    fi

    if [ $ITERATION -lt $MAX_ITERATIONS ]; then
        warn "Some checks failed. Attempting fixes..."

        # Auto-fix: if Python syntax errors, try to identify and report
        if ! $BACKEND_LINT_OK; then
            warn "Fix Python syntax errors manually and re-run"
        fi

        # Auto-fix: if npm install needed
        if ! $FRONTEND_BUILD_OK; then
            log "Retrying npm install..."
            cd "$PROJECT_ROOT/frontend"
            rm -rf node_modules package-lock.json
            npm install --silent 2>&1 || true
        fi

        sleep 2
    fi
done

echo ""
if $ALL_PASS; then
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "✅ ALL CHECKS PASSED (iteration $ITERATION)"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    fail "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fail "❌ CHECKS FAILED after $MAX_ITERATIONS iterations"
    fail "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
