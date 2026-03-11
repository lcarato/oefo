#!/bin/bash
#
# OEFO OpenClaw Integration Wrapper Script
#
# Provides a unified interface for OpenClaw to run common OEFO operations:
#   - Environment validation (audit)
#   - Smoke testing (smoke)
#   - Test suite execution (test)
#   - Package building (build)
#   - Release dry-run (release-dry-run)
#
# Usage:
#   ./scripts/oefo_claw_run.sh audit
#   ./scripts/oefo_claw_run.sh smoke
#   ./scripts/oefo_claw_run.sh test
#   ./scripts/oefo_claw_run.sh build
#   ./scripts/oefo_claw_run.sh release-dry-run
#
# Exit codes:
#   0 - Operation succeeded
#   1 - Operation failed or invalid subcommand

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_DIR}/logs"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/oefo_claw_run_${TIMESTAMP}.log"

# ============================================================================
# Functions
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_section() {
    echo "" | tee -a "$LOG_FILE"
    echo "================================================================================" | tee -a "$LOG_FILE"
    echo "$1" | tee -a "$LOG_FILE"
    echo "================================================================================" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

error() {
    echo "ERROR: $*" | tee -a "$LOG_FILE" >&2
    exit 1
}

success() {
    echo "" | tee -a "$LOG_FILE"
    echo "✓ $*" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

# ============================================================================
# Subcommand Handlers
# ============================================================================

cmd_audit() {
    log_section "OEFO Environment Audit"
    log "Running: python scripts/oefo_env_check.py"

    if python "$SCRIPT_DIR/oefo_env_check.py"; then
        success "Environment audit passed"
        return 0
    else
        error "Environment audit failed"
        return 1
    fi
}

cmd_smoke() {
    log_section "OEFO Smoke Test"
    log "Running: python scripts/oefo_smoke_test.py"

    if python "$SCRIPT_DIR/oefo_smoke_test.py"; then
        success "Smoke test passed"
        return 0
    else
        error "Smoke test failed"
        return 1
    fi
}

cmd_test() {
    log_section "OEFO Test Suite"
    log "Running: python -m pytest -q"

    if python -m pytest -q; then
        success "Test suite passed"
        return 0
    else
        error "Test suite failed"
        return 1
    fi
}

cmd_build() {
    log_section "OEFO Package Build"
    log "Running: python -m build"

    if python -m build; then
        success "Package build succeeded"
        return 0
    else
        error "Package build failed"
        return 1
    fi
}

cmd_release_dry_run() {
    log_section "OEFO Release Dry-Run"

    log "Step 1: Building package"
    if ! python -m build; then
        error "Build failed during release dry-run"
        return 1
    fi

    log "Step 2: Checking distribution"
    if ! python -m twine check dist/*; then
        error "Distribution check failed during release dry-run"
        return 1
    fi

    success "Release dry-run passed (dist/ ready for upload)"
    return 0
}

# ============================================================================
# Main
# ============================================================================

main() {
    local subcommand="${1:-}"

    # Validate subcommand
    case "$subcommand" in
        audit|refactor|smoke|test|build|release-dry-run)
            ;;
        "")
            error "Usage: $0 {audit|refactor|smoke|test|build|release-dry-run}"
            ;;
        *)
            error "Unknown subcommand: $subcommand"
            ;;
    esac

    log_section "OEFO OpenClaw Run - Subcommand: $subcommand"
    log "Project directory: $PROJECT_DIR"
    log "Log file: $LOG_FILE"
    log "Start time: $(date '+%Y-%m-%d %H:%M:%S')"

    # Execute subcommand
    case "$subcommand" in
        audit|refactor)
            cmd_audit
            ;;
        smoke)
            cmd_smoke
            ;;
        test)
            cmd_test
            ;;
        build)
            cmd_build
            ;;
        release-dry-run)
            cmd_release_dry_run
            ;;
    esac

    local exit_code=$?

    log "End time: $(date '+%Y-%m-%d %H:%M:%S')"
    log "Exit code: $exit_code"

    return $exit_code
}

# ============================================================================
# Entry Point
# ============================================================================

main "$@"
exit $?
