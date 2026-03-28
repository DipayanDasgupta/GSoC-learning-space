#!/usr/bin/env bash
# =============================================================================
# run_all_models.sh
# Run from the root of your GSoC-learning-space repo:
#   bash run_all_models.sh
#   bash run_all_models.sh 2>&1 | tee run_results.txt
#
# What it does:
#   - Runs all 7 non-Solara Python models with a per-model timeout
#   - Prints their full stdout output (for proposal PoC sections)
#   - Prints a PASS/FAIL summary at the end
#   - Exits 0 if all pass, 1 if any fail
#
# No API key required. No Solara UI is launched.
# Expected total runtime: < 90 seconds
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
declare -A RESULTS   # model_name -> PASS|FAIL
declare -A OUTPUTS   # model_name -> captured stdout

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
    RESULTS["$name"]="FAIL"
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
  echo "ERROR: Run this script from the root of GSoC-learning-space"
  echo "  cd ~/GSoC-learning-space && bash run_all_models.sh"
  exit 1
fi

echo -e "${BOLD}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  GSoC Learning Space — Model Test Runner"
echo "  Dipayan Dasgupta | IIT Madras | Mesa Meta Agents Proposal"
echo "  $(date)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${RESET}"

# ── Check Python environment ──────────────────────────────────────────────────
echo -e "${YELLOW}Checking environment...${RESET}"
python --version
echo "Working directory: $(pwd)"

# Check mesa is importable
if python -c "import mesa; print(f'Mesa version: {mesa.__version__}')" 2>/dev/null; then
  echo -e "${GREEN}Mesa installed correctly${RESET}"
else
  echo -e "${RED}WARNING: mesa not importable. Run: pip install mesa${RESET}"
fi

# ── Run proposal PoC models ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══ PROPOSAL PoC MODELS ═══════════════════════════════════════════${RESET}"

run_model \
  "Pillar 1: Meta Agents Lifecycle" \
  "models/meta_agents_poc/model.py" \
  "Tests join/leave/dissolve lifecycle API. Shows Pillar 1 design."

run_model \
  "Pillar 2: LLM Evaluation Demo" \
  "models/llm_evaluation_demo/model.py" \
  "LLMEvaluationAgent with MockLLM. No API key needed. Shows Pillar 2."

run_model \
  "Pillar 3: Spatial Coalition" \
  "models/spatial_coalition/model.py" \
  "spatial_find_combinations() candidate count benchmark. Shows Pillar 3."

run_model \
  "All Pillars: Financial Market" \
  "models/financial_market_coalition/model.py" \
  "All 3 pillars in one model: spatial syndicates + LLM scoring + lifecycle."

# ── Run DiscreteSpace / bug-fix models ───────────────────────────────────────
echo ""
echo -e "${BOLD}═══ DISCRETE SPACE MODELS (PR EVIDENCE) ══════════════════════════${RESET}"

run_model \
  "Alliance Formation (PR #3567)" \
  "models/alliance_formation/model.py" \
  "find_combinations with ideology scoring. Motivated PR #3567."

run_model \
  "Boltzmann Wealth (PR #3542)" \
  "models/boltzmann_wealth/model.py" \
  "Capacity-aware placement. Motivated PR #3542 (not_full_cells)."

run_model \
  "Capacity-Aware Placement (PR #3542)" \
  "models/capacity_aware_placement/model.py" \
  "select_random_not_full_cell() lifecycle over 50 steps."

run_model \
  "Voronoi Capacity (PR #3544)" \
  "models/voronoi_capacity/model.py" \
  "VoronoiGrid capacity=1 enforcement. Verifies PR #3544 fix."

run_model \
  "SpaceRenderer Migration (PR #3283)" \
  "models/spacerenderer_migration/model.py" \
  "SpaceRenderer.render() API. Zero FutureWarning."

run_model \
  "WolfSheep grass=False (PR #3627)" \
  "models/wolf_sheep_investigation/reproduce_3597.py" \
  "Reproduces and confirms fix for grass=False StopIteration crash."

# ── Mesa-LLM PoC (no API key) ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══ MESA-LLM PoC ═══════════════════════════════════════════════════${RESET}"

run_model \
  "Misinformation Spread (All LLM Pillars)" \
  "mesa_llm_poc/demo/misinformation_spread.py" \
  "VectorMemory + AsyncEngine + LangGraphAgent composing. No API key."

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
echo -e "  ${BOLD}Total: $TOTAL models | ${GREEN}$PASS_COUNT passed${RESET}${BOLD} | ${RED}$FAIL_COUNT failed${RESET}"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}  ✓ ALL MODELS PASSING — learning space verified clean${RESET}"
  echo ""
  echo "  Paste the outputs above into your GSoC proposal"
  echo "  PoC sections as 'Verified Terminal Output' blocks."
else
  echo -e "${RED}${BOLD}  ✗ $FAIL_COUNT FAILURES — fix before submitting proposal${RESET}"
fi

echo ""
echo -e "${BOLD}  To capture full output for your proposal:${RESET}"
echo "  bash run_all_models.sh 2>&1 | tee run_results.txt"
echo ""
echo -e "${BOLD}  To run a single model:${RESET}"
echo "  python models/meta_agents_poc/model.py"
echo "  python models/llm_evaluation_demo/model.py"
echo "  python models/spatial_coalition/model.py"
echo "  python models/financial_market_coalition/model.py"
echo ""

# ── Quick install check if anything failed ────────────────────────────────────
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}Troubleshooting: if you get ImportError, run:${RESET}"
  echo "  pip install mesa"
  echo "  pip install mesa[all]   # includes solara, altair"
  echo ""
  exit 1
fi

exit 0