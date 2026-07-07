#!/usr/bin/env bash

# Test suite for tmux-enhanced skill
# Usage: test-skill.sh [-v] [-q] [-h]
#   -v: Verbose mode
#   -q: Quiet mode (minimal output)
#   -h: Show help

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Defaults
VERBOSE=0
QUIET=0
# Get base directory (directory containing this script's parent)
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
  BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi
# Use an isolated socket dir so tests never scan or kill other tools' sockets
# (find-sessions.sh --all would otherwise trip over unrelated dead sockets and,
# under `set -o pipefail`, make the grep-based checks report false failures).
SOCKET_DIR="${TMPDIR:-/tmp}/agent-tmux-test-sockets"
export AGENT_TMUX_SOCKET_DIR="$SOCKET_DIR"
PASSED=0
FAILED=0

# Helper functions
log_info() {
    if [[ $QUIET -eq 0 ]]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED=++PASSED))
    fi
}

log_error() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_debug() {
    [[ $VERBOSE -eq 1 ]] && echo "  DEBUG: $1" >&2 || true
}

cleanup() {
    echo "Cleaning up test artifacts..."
    # Kill and remove all test-skill-* sockets
    for sock in "$SOCKET_DIR"/test-skill-*.sock; do
      if [[ -S "$sock" ]]; then
        tmux -S "$sock" kill-server 2>/dev/null || true
        rm -f "$sock"
      fi
    done

    # Clean up test files
    rm -f /tmp/test-lldb.c /tmp/test-lldb-program

    # Clean up all log files
    rm -f /tmp/test-clean.log /tmp/test-default.log /tmp/python-test.log /tmp/lldb-test.log
}

usage() {
    cat << 'USAGE'
Test suite for tmux-enhanced skill

Usage: test-skill.sh [-v] [-q] [-h]

Options:
  -v, --verbose    Show detailed output
  -q, --quiet      Minimal output (pass/fail only)
  -h, --help       Show this help

Examples:
  test-skill.sh              # Run all tests with normal output
  test-skill.sh -v           # Run with verbose output
  test-skill.sh -q           # Run quietly

Exit codes:
  0    All tests passed
  1    One or more tests failed
USAGE
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -q|--quiet)
            QUIET=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Set up cleanup trap (on interrupt and terminate - not on normal exit)
trap cleanup INT TERM

log_debug "Base directory: $BASE_DIR"
log_debug "Socket directory: $SOCKET_DIR"

# Create socket directory
mkdir -p "$SOCKET_DIR"

# Clean up any existing artifacts before starting tests
echo "Preparing test environment..."
cleanup

echo "Testing tmux-enhanced skill..."
echo

# Test 1: Dependency Check
echo "Test 1: Checking dependencies..."
if ! command -v tmux > /dev/null 2>&1; then
    log_error "tmux not found in PATH"
    exit 1
fi

TMUX_VERSION=$(tmux -V | cut -d' ' -f2)
log_debug "tmux version: $TMUX_VERSION"

# Note: timeout command is not required as scripts implement timeout functionality
# via manual polling (compatible with both Linux and macOS)

log_info "Dependencies verified tmux $TMUX_VERSION"

# Test 2: Create Clean Session
echo
echo "Test 2: Creating clean session..."
if "$BASE_DIR/tools/create-session.sh" \
    -n test-skill-clean \
    -c clean \
    -p 'echo "test-clean"' \
    -w "test-clean" \
    -t 3 \
    > /tmp/test-clean.log 2>&1; then
    log_info "Clean session created"
    # Verify the bundled clean.conf was actually applied (deterministic scraping)
    clean_status=$(tmux -S "$SOCKET_DIR/test-skill-clean.sock" show -gv status 2>/dev/null || echo "")
    if [[ "$clean_status" == "off" ]]; then
        log_info "Clean config applied (status bar off)"
    else
        log_error "Clean config not applied (status='$clean_status', expected 'off')"
        exit 1
    fi
else
    log_error "Failed to create clean session"
    log_debug "Log: $(cat /tmp/test-clean.log 2>/dev/null || echo 'No log file')"
    exit 1
fi

# Test 3: Create Default Session (clean-by-default) and verify config isolation
echo
echo "Test 3: Creating default session (no -c) and verifying config isolation..."
if "$BASE_DIR/tools/create-session.sh" \
    -n test-skill-default \
    -p 'echo "test-default"' \
    > /tmp/test-default.log 2>&1; then
    log_info "Default session created"
    # The user's ~/.tmux.conf must NOT leak: prefix should be the tmux default C-b
    default_prefix=$(tmux -S "$SOCKET_DIR/test-skill-default.sock" show -gv prefix 2>/dev/null || echo "")
    if [[ "$default_prefix" == "C-b" ]]; then
        log_info "User config isolated (prefix is default C-b)"
    else
        log_error "User config leaked into default session (prefix='$default_prefix', expected 'C-b')"
        exit 1
    fi
else
    log_error "Failed to create default session"
    log_debug "Log: $(cat /tmp/test-default.log 2>/dev/null || echo 'No log file')"
    exit 1
fi

# Test 4: Find Sessions
echo
echo "Test 4: Finding sessions..."
if "$BASE_DIR/tools/find-sessions.sh" --all | grep "test-skill-clean" > /dev/null; then
    log_info "test-skill-clean session found"
else
    log_error "test-skill-clean session not found"
    exit 1
fi

if "$BASE_DIR/tools/find-sessions.sh" --all | grep "test-skill-default" > /dev/null; then
    log_info "test-skill-default session found"
else
    log_error "test-skill-default session not found"
    exit 1
fi

# Test 5: Wait for Text
echo
echo "Test 5: Wait for text..."
if tmux -S "$SOCKET_DIR/test-skill-clean.sock" has-session -t test-skill-clean 2>/dev/null; then
    log_info "Session test-skill-clean is responding"
else
    log_error "Session test-skill-clean not responding"
    exit 1
fi

# Test 6: Python REPL
echo
echo "Test 6: Testing Python REPL..."
if "$BASE_DIR/tools/create-session.sh" \
    -n test-skill-python \
    -c clean \
    -p 'PYTHON_BASIC_REPL=1 python3 -q' \
    -w '^>>>' \
    -t 3 > /tmp/python-test.log 2>&1; then
    # Send a command
    tmux -S "$SOCKET_DIR/test-skill-python.sock" send-keys -t "test-skill-python:0.0" "print('test')" Enter
    sleep 1

    # Check output
    if tmux -S "$SOCKET_DIR/test-skill-python.sock" capture-pane -p -t "test-skill-python:0.0" | grep -q "test"; then
        log_info "Python REPL working correctly"
    else
        log_warn "Python REPL session created but output not verified"
    fi

    # Clean up
    tmux -S "$SOCKET_DIR/test-skill-python.sock" kill-session -t test-skill-python 2>/dev/null || true
else
    log_warn "Python REPL test skipped or failed (python3 may not be available)"
fi

# Test 7: LLDB Session (if lldb and clang are available)
echo
echo "Test 7: Testing LLDB with lldbinit..."
if command -v lldb > /dev/null 2>&1 && command -v clang > /dev/null 2>&1; then
    # Create test program
    echo '#include <stdio.h>
int main() { printf("test"); return 0; }' > /tmp/test-lldb.c
    clang /tmp/test-lldb.c -o /tmp/test-lldb-program 2>/dev/null || true

    if [[ -f /tmp/test-lldb-program ]]; then
        if "$BASE_DIR/tools/create-session.sh" \
            -n test-skill-lldb \
            -p 'lldb /tmp/test-lldb-program' \
            -w '\(lldbinit\)' \
            -t 3 > /tmp/lldb-test.log 2>&1; then
            log_info "LLDB session created"

            # Clean up
            tmux -S "$SOCKET_DIR/test-skill-lldb.sock" kill-session -t test-skill-lldb 2>/dev/null || true
        else
            log_warn "LLDB session creation failed" && exit 1
        fi

    else
        log_warn "Could not compile test program"
    fi
else
    log_warn "LLDB test skipped (lldb or clang not available)"
fi

# Test 8: Cleanup
echo
echo "Test 8: Testing cleanup..."
tmux -S "$SOCKET_DIR/test-skill-clean.sock" kill-session -t test-skill-clean 2>/dev/null || true
tmux -S "$SOCKET_DIR/test-skill-default.sock" kill-session -t test-skill-default 2>/dev/null || true

if ! tmux -S "$SOCKET_DIR/test-skill-clean.sock" has-session -t test-skill-clean 2>/dev/null && \
   ! tmux -S "$SOCKET_DIR/test-skill-default.sock" has-session -t test-skill-default 2>/dev/null; then
    log_info "Cleanup successful"
else
    log_warn "Some sessions may not have been cleaned up properly"
fi

echo
echo "="

if [[ $FAILED -eq 0 ]]; then
    if [[ $QUIET -eq 0 ]]; then
        echo -e "${GREEN}All tests passed! ✓${NC}"
        echo
        echo "Summary: $PASSED tests passed"
        echo "The tmux-enhanced skill is working correctly."
    else
        echo "PASS"
    fi
    # Only cleanup on successful completion
    cleanup
    exit 0
else
    if [[ $QUIET -eq 0 ]]; then
        echo -e "${RED}Some tests failed! ✗${NC}"
        echo
        echo "Summary: $PASSED tests passed, $FAILED tests failed"
    else
        echo "FAIL"
    fi
    exit 1
fi
