#!/usr/bin/env bash
# =============================================================================
# run_all_models.sh
# Run from the root of your GSoC-learning-space repo:
#   bash run_all_models.sh
#   bash run_all_models.sh 2>&1 | tee run_results.txt
#
# Updated for current directory structure (March 2026)
# =============================================================================

set -euo pipefail

# ── Colour codes ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

TIMEOUT=60   # seconds per model

PASS_COUNT=0
FAIL_COUNT=0
declare -A RESULTS
declare -A OUTPUTS

# ── Helper: run one model ─────────────────────────────────────────────────────
run_model() {
  local name="$1"
  local script="$2"
  local description="$3"

  echo ""
  echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${CYAN}${BOLD}  MODEL: $name${RESET}"
  echo -e "${CYAN}  $description${RESET}"
  echo -e "${CYAN}  Script: $script${RESET}"
  echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

  if [ ! -f "$script" ]; then
    echo -e "${RED}  ERROR: $script not found — skipping${RESET}"
    RESULTS["$name"]="FAIL (file missing)"
    OUTPUTS["$name"]="File not found: $script"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi

  local output
  local exit_code=0

  output=$(timeout "$TIMEOUT" python "$script" 2>&1) || exit_code=$?

  if [ $exit_code -eq 124 ]; then
    echo -e "${RED}  TIMEOUT after ${TIMEOUT}s${RESET}"
    RESULTS["$name"]="FAIL (timeout)"
    OUTPUTS["$name"]="TIMEOUT after ${TIMEOUT}s"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi

  if [ $exit_code -ne 0 ]; then
    echo -e "${RED}  FAILED (exit code $exit_code)${RESET}"
    echo "$output"
    RESULTS["$name"]="FAIL (exit $exit_code)"
    OUTPUTS["$name"]="$output"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return
  fi

  echo "$output"
  RESULTS["$name"]="PASS"
  OUTPUTS["$name"]="$output"
  PASS_COUNT=$((PASS_COUNT + 1))
  echo -e "${GREEN}  ✓ PASSED${RESET}"
}

# ── Safety check ──────────────────────────────────────────────────────────────
if [ ! -d "models" ]; then
  echo -e "${RED}ERROR: Run this script from the root of GSoC-learning-space${RESET}"
  echo "  cd ~/GSoC-learning-space && bash run_all_models.sh"
  exit 1
fi

echo -e "${BOLD}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  GSoC 2026 Learning Space — Model Test Runner"
echo "  Dipayan Dasgupta | Mesa Meta Agents"
echo "  $(date)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${RESET}"

# Check Mesa version
echo -e "${YELLOW}Checking environment...${RESET}"
python --version
if python -c "import mesa; print(f'Mesa version: {mesa.__version__}')" 2>/dev/null; then
  echo -e "${GREEN}Mesa installed correctly${RESET}"
else
  echo -e "${RED}WARNING: mesa not importable${RESET}"
fi

# ── 1. Proposal Core Models ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══ PROPOSAL CORE MODELS ══════════════════════════════════════════${RESET}"

run_model \
  "MetaAgentV2 Core (Proposal)" \
  "poc/proposal_core/demo.py" \
  "Core lifecycle: join/leave/merge/split with MetaAgentV2"

run_model \
  "Pillar 2: LLM Evaluation (Proposal)" \
  "poc/proposal_core/tests/test_llm_eval.py" \
  "LLM evaluation tests with Pydantic validation"

run_model \
  "Pillar 3: Spatial Coalition (Proposal)" \
  "poc/proposal_core/tests/test_spatial.py" \
  "Spatial find_combinations with capacity-aware cells"

# ── 2. Main Demo Models ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══ MAIN DEMO MODELS ══════════════════════════════════════════════${RESET}"

run_model \
  "Pillar 1: Meta Agents POC" \
  "models/meta_agents_poc/model.py" \
  "Basic MetaAgent lifecycle demonstration"

run_model \
  "Pillar 2: LLM Evaluation Demo" \
  "models/llm_evaluation_demo/model.py" \
  "LLMEvaluationAgent with MockLLM (currently failing — needs fix)"

run_model \
  "Pillar 3: Spatial Coalition" \
  "models/spatial_coalition/model.py" \
  "spatial_find_combinations() benchmark"

run_model \
  "All Pillars: Financial Market Coalition" \
  "models/financial_market_coalition/model.py" \
  "Full integration: spatial + LLM scoring + agent lifecycle"

# ── 3. DiscreteSpace / PR Evidence Models ─────────────────────────────────────
echo ""
echo -e "${BOLD}═══ DISCRETE SPACE & BUG-FIX MODELS (PR EVIDENCE) ════════════════${RESET}"

run_model \
  "Alliance Formation" \
  "models/alliance_formation/model.py" \
  "Motivated PR #3572 (evaluate_combination type validation)"

run_model \
  "Boltzmann Wealth (Capacity Aware)" \
  "models/boltzmann_wealth/model.py" \
  "Motivated PR #3542 (not_full_cells)"

run_model \
  "Capacity-Aware Placement" \
  "models/capacity_aware_placement/model.py" \
  "Tests not_full_cells and select_random_not_full_cell()"

run_model \
  "VoronoiGrid Capacity Fix" \
  "models/voronoi_capacity/model.py" \
  "Verifies PR #3544 (capacity not being overwritten)"

run_model \
  "SpaceRenderer Migration" \
  "models/spacerenderer_migration/model.py" \
  "Tests updated SpaceRenderer API"

run_model \
  "Wolf-Sheep grass=False Fix" \
  "models/wolf_sheep_investigation/reproduce_3597.py" \
  "Reproduces and validates grass=False fix"

# ── 4. Mesa-LLM PoC ───────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══ MESA-LLM PoC ══════════════════════════════════════════════════${RESET}"

run_model \
  "Misinformation Spread Demo" \
  "mesa_llm_poc/demo/misinformation_spread.py" \
  "AsyncEngine + VectorMemory + LangGraphAgent"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════════"
echo "  RESULTS SUMMARY"
echo "═══════════════════════════════════════════════════════════════════${RESET}"
echo ""

TOTAL=$((PASS_COUNT + FAIL_COUNT))
for name in "${!RESULTS[@]}"; do
  status="${RESULTS[$name]}"
  if [[ "$status" == "PASS" ]]; then
    echo -e "  ${GREEN}✓ PASS${RESET}  $name"
  else
    echo -e "  ${RED}✗ $status${RESET}  $name"
  fi
done | sort

echo ""
echo -e "  ${BOLD}Total: $TOTAL models | ${GREEN}$PASS_COUNT passed${RESET} | ${RED}$FAIL_COUNT failed${RESET}${BOLD}"

if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}  ✓ ALL MODELS PASSING — Ready for proposal!${RESET}"
else
  echo -e "${RED}${BOLD}  ✗ Some models are failing — please fix before final submission${RESET}"
fi

echo ""
echo -e "${BOLD}Next steps:${RESET}"
echo "  • Fix the failing LLM Evaluation Demo (TypeError in mesa_signals)"
echo "  • Run: bash run_all_models.sh 2>&1 | tee run_results.txt"
echo ""

exit $((FAIL_COUNT > 0 ? 1 : 0))