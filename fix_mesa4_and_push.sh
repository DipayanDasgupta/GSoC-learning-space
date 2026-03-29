#!/usr/bin/env bash
# =============================================================================
# fix_mesa4_and_push.sh
# Fixes all 5 failing models for Mesa 4.0.0a0 and pushes to GitHub.
#
# ROOT CAUSE ANALYSIS (from run output):
# ──────────────────────────────────────
# FAIL 1 — TypeError: object.__init__() takes exactly one argument
#   Models: poc/proposal_core/demo.py
#           models/llm_evaluation_demo/model.py
#           models/spatial_coalition/model.py
#           models/financial_market_coalition/model.py
#
#   Root: Mesa 4.0.0a0 mesa_signals/core.py overrides Model.__init__ and
#         calls super().__init__(*args, **kwargs) which reaches object.__init__().
#         object.__init__() rejects any kwargs INCLUDING seed=.
#         Direct mesa.Model(seed=X) works fine — only subclass super() calls fail.
#   Fix:  super().__init__(seed=seed) → super().__init__(rng=seed)
#         Mesa 4.0 accepts rng= and routes it correctly without passing to object.
#
# FAIL 2 — AttributeError: 'MisinformationModel' has no attribute 'steps'
#   Model: mesa_llm_poc/demo/misinformation_spread.py
#
#   Root: In Mesa 4.0 the step counter attribute was renamed.
#         The model's _wrapped_step uses self.time (confirmed in traceback:
#         "self._advance_time(self.time + 1)"). self.model.steps no longer exists.
#   Fix:  self.model.steps → self.model.time
#
# Run:
#   cd ~/GSoC-learning-space && bash fix_mesa4_and_push.sh
# =============================================================================
set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'

echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  fix_mesa4_and_push.sh — Mesa 4.0.0a0 compatibility fixes   ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1a — poc/proposal_core/demo.py
# MarketCoalitionModel.__init__ calls super().__init__(seed=seed)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[1/5] Fixing poc/proposal_core/demo.py ...${RESET}"
python3 << 'PYEOF'
with open("poc/proposal_core/demo.py") as f:
    src = f.read()

# Fix the one subclass super().__init__(seed=seed) call
assert "super().__init__(seed=seed)" in src, \
    "Expected super().__init__(seed=seed) not found — was it already fixed?"

src = src.replace(
    "super().__init__(seed=seed)",
    "super().__init__(rng=seed)"
)

with open("poc/proposal_core/demo.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ poc/proposal_core/demo.py fixed${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1b — models/llm_evaluation_demo/model.py
# NegotiationModel.__init__ calls super().__init__(seed=seed)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[2/5] Fixing models/llm_evaluation_demo/model.py ...${RESET}"
python3 << 'PYEOF'
with open("models/llm_evaluation_demo/model.py") as f:
    src = f.read()

assert "super().__init__(seed=seed)" in src, \
    "Expected super().__init__(seed=seed) not found"

src = src.replace(
    "super().__init__(seed=seed)",
    "super().__init__(rng=seed)"
)

with open("models/llm_evaluation_demo/model.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ models/llm_evaluation_demo/model.py fixed${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1c — models/spatial_coalition/model.py
# SpatialCoalitionModel.__init__ calls super().__init__(seed=seed)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[3/5] Fixing models/spatial_coalition/model.py ...${RESET}"
python3 << 'PYEOF'
with open("models/spatial_coalition/model.py") as f:
    src = f.read()

assert "super().__init__(seed=seed)" in src, \
    "Expected super().__init__(seed=seed) not found"

src = src.replace(
    "super().__init__(seed=seed)",
    "super().__init__(rng=seed)"
)

with open("models/spatial_coalition/model.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ models/spatial_coalition/model.py fixed${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1d — models/financial_market_coalition/model.py
# MarketModel.__init__ calls super().__init__(seed=seed)
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[4/5] Fixing models/financial_market_coalition/model.py ...${RESET}"
python3 << 'PYEOF'
with open("models/financial_market_coalition/model.py") as f:
    src = f.read()

assert "super().__init__(seed=seed)" in src, \
    "Expected super().__init__(seed=seed) not found"

src = src.replace(
    "super().__init__(seed=seed)",
    "super().__init__(rng=seed)"
)

with open("models/financial_market_coalition/model.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ models/financial_market_coalition/model.py fixed${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2 — mesa_llm_poc/demo/misinformation_spread.py
# self.model.steps renamed to self.model.time in Mesa 4.0.
# Confirmed by traceback: model.py calls self._advance_time(self.time + 1)
# Also fix the model.__init__ which uses rng=rng but also the agent methods
# that reference self.model.steps in two places.
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[5/5] Fixing mesa_llm_poc/demo/misinformation_spread.py ...${RESET}"
python3 << 'PYEOF'
with open("mesa_llm_poc/demo/misinformation_spread.py") as f:
    src = f.read()

occurrences = src.count("self.model.steps")
print(f"  Found {occurrences} occurrence(s) of self.model.steps")
assert occurrences > 0, "Expected self.model.steps — was it already fixed?"

# Replace all occurrences
src = src.replace("self.model.steps", "self.model.time")

# Also fix the __main__ block's print if it uses model.steps
# (the model itself doesn't use self.steps but just in case)
src = src.replace(
    'f"  Step {step:3d}:',
    f'f"  Step {{step:3d}}:'
).replace(
    "f'  Step {step:3d}:",
    "f'  Step {step:3d}:"
)

with open("mesa_llm_poc/demo/misinformation_spread.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ mesa_llm_poc/demo/misinformation_spread.py fixed${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# Verify all 5 fixed files parse correctly
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Verifying all patched files...${RESET}"
SYNTAX_OK=true
for f in \
  poc/proposal_core/demo.py \
  models/llm_evaluation_demo/model.py \
  models/spatial_coalition/model.py \
  models/financial_market_coalition/model.py \
  mesa_llm_poc/demo/misinformation_spread.py
do
  if python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null; then
    echo -e "  ${GREEN}✓${RESET} $f"
  else
    echo -e "  ${RED}✗ SYNTAX ERROR${RESET} $f"
    SYNTAX_OK=false
  fi
done

if ! $SYNTAX_OK; then
  echo -e "${RED}Syntax errors found — aborting.${RESET}"
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Run all 14 models and capture results
# ─────────────────────────────────────────────────────────────────────────────
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
    echo "$out" | tail -20
    R["$name"]="FAIL"; FAIL=$((FAIL+1))
  else
    echo "$out"
    echo -e "${GREEN}  ✓ PASS${RESET}"
    R["$name"]="PASS"; PASS=$((PASS+1))
  fi
}

# ── Proposal Core Models ──────────────────────────────────────────────────────
run_model "MetaAgentV2 Core (Proposal)"          "poc/proposal_core/demo.py"
run_model "Pillar 2: LLM Evaluation (Proposal)"  "poc/proposal_core/tests/test_llm_eval.py"
run_model "Pillar 3: Spatial Coalition (Proposal)" "poc/proposal_core/tests/test_spatial.py"

# ── Main Demo Models ──────────────────────────────────────────────────────────
run_model "Pillar 1: Meta Agents POC"            "models/meta_agents_poc/model.py"
run_model "Pillar 2: LLM Evaluation Demo"        "models/llm_evaluation_demo/model.py"
run_model "Pillar 3: Spatial Coalition"          "models/spatial_coalition/model.py"
run_model "All Pillars: Financial Market"        "models/financial_market_coalition/model.py"

# ── PR Evidence Models ────────────────────────────────────────────────────────
run_model "Alliance Formation"                   "models/alliance_formation/model.py"
run_model "Boltzmann Wealth"                     "models/boltzmann_wealth/model.py"
run_model "Capacity-Aware Placement"             "models/capacity_aware_placement/model.py"
run_model "VoronoiGrid Capacity Fix"             "models/voronoi_capacity/model.py"
run_model "SpaceRenderer Migration"              "models/spacerenderer_migration/model.py"
run_model "Wolf-Sheep grass=False Fix"           "models/wolf_sheep_investigation/reproduce_3597.py"

# ── Mesa-LLM PoC ──────────────────────────────────────────────────────────────
run_model "Misinformation Spread Demo"           "mesa_llm_poc/demo/misinformation_spread.py"

# ─────────────────────────────────────────────────────────────────────────────
# Results summary
# ─────────────────────────────────────────────────────────────────────────────
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
  echo -e "\n${RED}${BOLD}  ✗ $FAIL still failing — check errors above before pushing.${RESET}"
  echo ""
  echo "  Diagnostic tip — check which Mesa attribute is the step counter:"
  echo "  python3 -c \"import mesa; m=mesa.Model(); m.step(); print(dir(m))\" | tr ',' '\n' | grep -i 'step\|time'"
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# All green — commit and push
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}  ✓ ALL $TOTAL MODELS PASSING — committing and pushing${RESET}"

git add \
  poc/proposal_core/demo.py \
  models/llm_evaluation_demo/model.py \
  models/spatial_coalition/model.py \
  models/financial_market_coalition/model.py \
  mesa_llm_poc/demo/misinformation_spread.py

git commit -m "fix: Mesa 4.0.0a0 compatibility — seed= → rng=, steps → time

Two root causes fixed across 5 failing models:

Fix 1 — seed= kwarg rejected by object.__init__() (4 models)
  Mesa 4.0.0a0 mesa_signals/core.py overrides Model.__init__ and passes
  **kwargs up the MRO. object.__init__() rejects any kwargs, including seed=.
  Direct mesa.Model(seed=X) calls work fine; only subclass super().__init__()
  calls fail. Changed seed= → rng= in all 4 affected subclasses:
    poc/proposal_core/demo.py          (MarketCoalitionModel)
    models/llm_evaluation_demo/model.py (NegotiationModel)
    models/spatial_coalition/model.py  (SpatialCoalitionModel)
    models/financial_market_coalition/model.py (MarketModel)

Fix 2 — model.steps renamed to model.time in Mesa 4.0 (1 model)
  Confirmed by traceback: model.py calls self._advance_time(self.time + 1).
  The 'steps' attribute no longer exists; replaced with 'time'.
    mesa_llm_poc/demo/misinformation_spread.py (CitizenAgent.observe + build_prompt)

All 14 models now passing on Mesa 4.0.0a0 dev fork."

git push origin main
echo ""
echo -e "${GREEN}${BOLD}  DONE — 14/14 pushed to origin/main.${RESET}"
echo ""
echo "  Capture full output for proposal:"
echo "  bash fix_mesa4_and_push.sh 2>&1 | tee run_results_final.txt"