#!/usr/bin/env bash
# =============================================================================
# fix_remaining_2.sh
# Fixes the 2 still-failing models after fix_mesa4_and_push.sh ran.
#
# ROOT CAUSE (both failures):
#   AttributeError: 'NegotiationModel'/'MarketModel' has no attribute 'steps'
#
#   Mesa 4.0 renamed the step counter from  self.steps  →  self.time
#   The previous fix script caught this in misinformation_spread.py but
#   missed the same pattern in:
#     models/llm_evaluation_demo/model.py      line ~133
#     models/financial_market_coalition/model.py  line ~128
#
# Run:
#   cd ~/GSoC-learning-space && bash fix_remaining_2.sh
# =============================================================================
set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'

echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  fix_remaining_2.sh — patch self.steps → self.time           ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Safety check ──────────────────────────────────────────────────────────────
if [ ! -d "models" ]; then
  echo -e "${RED}ERROR: Run from repo root: cd ~/GSoC-learning-space && bash fix_remaining_2.sh${RESET}"
  exit 1
fi

# ── FIX 1: models/llm_evaluation_demo/model.py ───────────────────────────────
echo -e "${CYAN}[1/2] Fixing models/llm_evaluation_demo/model.py ...${RESET}"
python3 << 'PYEOF'
import sys

path = "models/llm_evaluation_demo/model.py"
with open(path) as f:
    src = f.read()

# Count occurrences before patching
hits = src.count("self.steps")
if hits == 0:
    print("  No self.steps found — already fixed or different issue.")
    sys.exit(0)

print(f"  Found {hits} occurrence(s) of self.steps")
src = src.replace("self.steps", "self.time")

with open(path, "w") as f:
    f.write(src)

import ast
ast.parse(src)
print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ models/llm_evaluation_demo/model.py fixed${RESET}"

# ── FIX 2: models/financial_market_coalition/model.py ────────────────────────
echo -e "${CYAN}[2/2] Fixing models/financial_market_coalition/model.py ...${RESET}"
python3 << 'PYEOF'
import sys

path = "models/financial_market_coalition/model.py"
with open(path) as f:
    src = f.read()

hits = src.count("self.steps")
if hits == 0:
    print("  No self.steps found — already fixed or different issue.")
    sys.exit(0)

print(f"  Found {hits} occurrence(s) of self.steps")
src = src.replace("self.steps", "self.time")

with open(path, "w") as f:
    f.write(src)

import ast
ast.parse(src)
print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ models/financial_market_coalition/model.py fixed${RESET}"

# ── Verify syntax on all 5 previously patched files too ──────────────────────
echo ""
echo -e "${BOLD}Verifying syntax on all patched files ...${RESET}"
ALL_OK=true
for f in \
  models/llm_evaluation_demo/model.py \
  models/financial_market_coalition/model.py \
  poc/proposal_core/demo.py \
  models/spatial_coalition/model.py \
  mesa_llm_poc/demo/misinformation_spread.py
do
  if python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null; then
    echo -e "  ${GREEN}✓${RESET} $f"
  else
    echo -e "  ${RED}✗ SYNTAX ERROR${RESET} $f"
    ALL_OK=false
  fi
done

if ! $ALL_OK; then
  echo -e "\n${RED}Syntax errors found — aborting.${RESET}"
  exit 1
fi

# ── Run all 14 models ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  Running all 14 models                                       ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"

PASS=0; FAIL=0
declare -A R
TIMEOUT=120

run_model() {
  local name="$1" script="$2"
  echo -e "\n${CYAN}${BOLD}──── $name ────${RESET}"
  local out ec=0
  out=$(timeout "$TIMEOUT" python "$script" 2>&1) || ec=$?
  if [ $ec -eq 124 ]; then
    echo -e "${RED}  TIMEOUT (>${TIMEOUT}s)${RESET}"
    R["$name"]="FAIL:timeout"; FAIL=$((FAIL+1))
  elif [ $ec -ne 0 ]; then
    echo -e "${RED}  FAILED (exit $ec)${RESET}"
    echo "$out" | tail -25
    R["$name"]="FAIL"; FAIL=$((FAIL+1))
  else
    echo "$out"
    echo -e "${GREEN}  ✓ PASS${RESET}"
    R["$name"]="PASS"; PASS=$((PASS+1))
  fi
}

# Proposal Core
run_model "MetaAgentV2 Core (Proposal)"            "poc/proposal_core/demo.py"
run_model "Pillar 2: LLM Evaluation (Proposal)"    "poc/proposal_core/tests/test_llm_eval.py"
run_model "Pillar 3: Spatial Coalition (Proposal)" "poc/proposal_core/tests/test_spatial.py"

# Main Demo Models
run_model "Pillar 1: Meta Agents POC"              "models/meta_agents_poc/model.py"
run_model "Pillar 2: LLM Evaluation Demo"          "models/llm_evaluation_demo/model.py"
run_model "Pillar 3: Spatial Coalition"            "models/spatial_coalition/model.py"
run_model "All Pillars: Financial Market"          "models/financial_market_coalition/model.py"

# PR Evidence
run_model "Alliance Formation"                     "models/alliance_formation/model.py"
run_model "Boltzmann Wealth"                       "models/boltzmann_wealth/model.py"
run_model "Capacity-Aware Placement"               "models/capacity_aware_placement/model.py"
run_model "VoronoiGrid Capacity Fix"               "models/voronoi_capacity/model.py"
run_model "SpaceRenderer Migration"                "models/spacerenderer_migration/model.py"
run_model "Wolf-Sheep grass=False Fix"             "models/wolf_sheep_investigation/reproduce_3597.py"

# Mesa-LLM PoC
run_model "Misinformation Spread Demo"             "mesa_llm_poc/demo/misinformation_spread.py"

# ── Results summary ───────────────────────────────────────────────────────────
TOTAL=$((PASS+FAIL))
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════════════"
echo -e "  RESULTS SUMMARY"
echo -e "═══════════════════════════════════════════════════════════════════${RESET}"
echo ""
for name in "${!R[@]}"; do
  if [[ "${R[$name]}" == "PASS" ]]; then
    echo -e "  ${GREEN}✓ PASS${RESET}  $name"
  else
    echo -e "  ${RED}✗ ${R[$name]}${RESET}  $name"
  fi
done | sort
echo ""
echo -e "  ${BOLD}$TOTAL total  |  ${GREEN}$PASS passed${RESET}${BOLD}  |  ${RED}$FAIL failed${RESET}"

if [ "$FAIL" -gt 0 ]; then
  echo -e "\n${RED}${BOLD}  ✗ $FAIL still failing — check errors above.${RESET}"
  echo ""
  echo "  Quick diagnostic — list all self.steps in your models:"
  echo "  grep -rn 'self\.steps' models/ mesa_llm_poc/ poc/"
  exit 1
fi

# ── All green — commit and push ───────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}  ✓ ALL $TOTAL MODELS PASSING — committing and pushing${RESET}"

git add \
  models/llm_evaluation_demo/model.py \
  models/financial_market_coalition/model.py

git commit -m "fix: replace self.steps with self.time in 2 remaining failing models

Mesa 4.0 renamed the step counter attribute from 'steps' to 'time'.
The previous fix caught this in misinformation_spread.py but missed
the same pattern in two other models:

  models/llm_evaluation_demo/model.py
    NegotiationModel.step() printed self.steps on line ~133

  models/financial_market_coalition/model.py
    MarketModel.step() printed self.steps on line ~128

Both replaced with self.time. All 14 models now passing on Mesa 4.0.0a0."

git push origin main

echo ""
echo -e "${GREEN}${BOLD}  DONE — 14/14 pushed to origin/main.${RESET}"
echo ""
echo "  Capture full output:"
echo "  bash fix_remaining_2.sh 2>&1 | tee run_results_14_14.txt"