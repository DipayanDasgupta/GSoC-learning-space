#!/usr/bin/env bash
# =============================================================================
# run_proposal_poc.sh
# Runs the Pillar 1/2/3 PoC and the full pytest suite.
# cd ~/GSoC-learning-space && bash run_proposal_poc.sh
# =============================================================================
set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     GSoC 2026 — Meta Agents Proposal PoC Runner             ║"
echo "║     Dipayan Dasgupta · IIT Madras · Mesa Meta Agents         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

PASS=0; FAIL=0
POC_DIR="models/meta_agents_proposal"

run_py() {
  local label="$1" script="$2"
  echo -e "${CYAN}${BOLD}─── $label ────────────────────────────────────────────${RESET}"
  local out ec=0
  out=$(cd "$POC_DIR" && timeout 60 python "$(basename "$script")" 2>&1) || ec=$?
  if [ $ec -ne 0 ]; then
    echo -e "${RED}FAILED (exit $ec)${RESET}"
    echo "$out"
    FAIL=$((FAIL+1))
  else
    echo "$out"
    echo -e "${GREEN}  ✓ PASS${RESET}"
    PASS=$((PASS+1))
  fi
  echo ""
}

# ── Individual pillar demos ───────────────────────────────────────────────────
run_py "Pillar 1: MetaAgentV2 Lifecycle + Bug Fixes" "$POC_DIR/meta_agent_v2.py"
run_py "Pillar 2: LLMEvaluationAgent Protocol"       "$POC_DIR/llm_evaluation.py"
run_py "Pillar 3: spatial_find_combinations()"       "$POC_DIR/spatial.py"
run_py "All Pillars: Financial Market Coalition"     "$POC_DIR/demo.py"

# ── Pytest suite ──────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}─── Pytest Suite (28 tests across 3 pillars) ──────────────────${RESET}"
TEST_OUT=0
if python -m pytest "$POC_DIR/tests/" -v \
    --tb=short \
    --no-header \
    -q \
    2>&1; then
  echo -e "${GREEN}  ✓ All tests passed${RESET}"
  PASS=$((PASS+1))
else
  TEST_OUT=1
  echo -e "${RED}  ✗ Some tests failed${RESET}"
  FAIL=$((FAIL+1))
fi
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS+FAIL))
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  RESULTS: $PASS/$TOTAL passed                                     ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}${BOLD}  ✓ ALL PASSING — proposal PoC fully verified${RESET}"
  echo ""
  echo "  Three independently-runnable pillars + 28 pytest tests."
  echo "  Paste output into proposal Appendix as 'Verified Terminal Output'."
else
  echo -e "\n${RED}  ✗ $FAIL failures${RESET}"
  exit 1
fi
