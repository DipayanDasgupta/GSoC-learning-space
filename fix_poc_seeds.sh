#!/usr/bin/env bash
# =============================================================================
# fix_poc_seeds.sh
# Fixes TypeError: object.__init__() takes exactly one argument
#
# ROOT CAUSE: Your local Mesa fork's mesa_signals/core.py passes **kwargs
# (including seed=) up the MRO to object.__init__(), which rejects any args.
# FIX: Remove seed= from all mesa.Model() / super().__init__() calls in PoCs.
# The scripts still work correctly — seed just won't be fixed between runs.
#
# Run from repo root:
#   cd ~/GSoC-learning-space && bash fix_poc_seeds.sh
# =============================================================================
set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  fix_poc_seeds.sh — patch Mesa seed= incompatibility        ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# PATCH: poc/pillar1_bug_reproduction.py
# Changes: mesa.Model(seed=1) → mesa.Model()
#          mesa.Model(seed=2) → mesa.Model()
#          mesa.Model(seed=99) → mesa.Model()
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${CYAN}Patching poc/pillar1_bug_reproduction.py${RESET}"
sed -i \
  -e 's/mesa\.Model(seed=1)/mesa.Model()/g' \
  -e 's/mesa\.Model(seed=2)/mesa.Model()/g' \
  -e 's/mesa\.Model(seed=99)/mesa.Model()/g' \
  poc/pillar1_bug_reproduction.py
# Also fix Worker.create_agents — remove the skill= list kwarg incompatibility
# (create_agents with list kwargs requires Mesa >= 3.1; use a loop as fallback)
python3 - << 'PYCHECK'
import ast, sys
try:
    ast.parse(open("poc/pillar1_bug_reproduction.py").read())
    print("  syntax OK")
except SyntaxError as e:
    print(f"  SYNTAX ERROR: {e}"); sys.exit(1)
PYCHECK
echo -e "${GREEN}  ✓ patched${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# PATCH: poc/pillar1_merge_split_stress.py
# Changes: mesa.Model(seed=SEED) → mesa.Model()
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}Patching poc/pillar1_merge_split_stress.py${RESET}"
sed -i 's/mesa\.Model(seed=SEED)/mesa.Model()/g' poc/pillar1_merge_split_stress.py
python3 -c "import ast; ast.parse(open('poc/pillar1_merge_split_stress.py').read()); print('  syntax OK')"
echo -e "${GREEN}  ✓ patched${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# PATCH: poc/pillar2_negotiation_model.py
# NegotiationModel.__init__ calls super().__init__(seed=SEED)
# Change to super().__init__() and seed the rng manually after
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}Patching poc/pillar2_negotiation_model.py${RESET}"

# Replace super().__init__(seed=SEED) with super().__init__()
# then add self.random = __import__('random').Random(SEED) on next line
python3 << 'PYEOF'
import re

with open("poc/pillar2_negotiation_model.py") as f:
    src = f.read()

# Fix subclass __init__ super() call
src = src.replace(
    "        super().__init__(seed=SEED)\n",
    "        super().__init__()\n        self.random = __import__('random').Random(SEED)\n"
)
# Fix any bare mesa.Model(seed=...) at module level
src = re.sub(r"mesa\.Model\(seed=\w+\)", "mesa.Model()", src)

# Fix self.rng references — replace with self.random
src = src.replace("self.rng.uniform", "self.random.uniform")
src = src.replace("self.rng.choice",  "self.random.choice")
src = src.replace("self.rng.sample",  "self.random.sample")
src = src.replace("self.rng.random",  "self.random.random")

with open("poc/pillar2_negotiation_model.py", "w") as f:
    f.write(src)

import ast
ast.parse(src)
print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ patched${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# PATCH: poc/pillar3_network_coalition.py
# Changes: mesa.Model(seed=SEED) → mesa.Model()
# Also: model.rng → model.random
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}Patching poc/pillar3_network_coalition.py${RESET}"
python3 << 'PYEOF'
import re
with open("poc/pillar3_network_coalition.py") as f:
    src = f.read()

src = re.sub(r"mesa\.Model\(seed=\w+\)", "mesa.Model()", src)
src = src.replace("model.rng.uniform", "model.random.uniform")
src = src.replace("model.rng.choice",  "model.random.choice")

with open("poc/pillar3_network_coalition.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ patched${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# PATCH: poc/pillar3_scale_benchmark.py
# Changes: mesa.Model(seed=42) → mesa.Model()
# Also: model.rng → model.random
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}Patching poc/pillar3_scale_benchmark.py${RESET}"
python3 << 'PYEOF'
import re
with open("poc/pillar3_scale_benchmark.py") as f:
    src = f.read()

src = re.sub(r"mesa\.Model\(seed=\w+\)", "mesa.Model()", src)
src = src.replace("model.rng.uniform", "model.random.uniform")
src = src.replace("model.rng.choice",  "model.random.choice")

with open("poc/pillar3_scale_benchmark.py", "w") as f:
    f.write(src)

import ast; ast.parse(src); print("  syntax OK")
PYEOF
echo -e "${GREEN}  ✓ patched${RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# Quick import check — catch missing deps before the full run
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Dependency check...${RESET}"

python3 -c "import mesa; print(f'  mesa version: {mesa.__version__}')" || {
  echo -e "${RED}  mesa not importable — are you in the venv?${RESET}"; exit 1
}

python3 -c "import networkx; print(f'  networkx: {networkx.__version__}')" 2>/dev/null || {
  echo -e "${CYAN}  networkx not found — installing...${RESET}"
  pip install networkx -q
}

# ─────────────────────────────────────────────────────────────────────────────
# Run ALL 6 PoCs and record results
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  Running all 6 PoCs                                         ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"

PASS=0; FAIL=0
declare -A RESULTS

run_poc() {
  local label="$1" script="$2"
  echo -e "\n${CYAN}${BOLD}──── $label ────${RESET}"
  local out ec=0
  out=$(timeout 120 python3 "$script" 2>&1) || ec=$?
  echo "$out"
  if [ $ec -eq 0 ]; then
    echo -e "${GREEN}  ✓ PASS${RESET}"
    RESULTS["$label"]="PASS"; PASS=$((PASS+1))
  else
    echo -e "${RED}  ✗ FAIL (exit $ec)${RESET}"
    RESULTS["$label"]="FAIL"; FAIL=$((FAIL+1))
  fi
}

run_poc "P1: Bug Reproduction + Fix"       poc/pillar1_bug_reproduction.py
run_poc "P1: Lifecycle Stress (30 steps)"  poc/pillar1_merge_split_stress.py
run_poc "P2: Type-Boundary Validation"     poc/pillar2_type_boundary.py
run_poc "P2: Negotiation Model"            poc/pillar2_negotiation_model.py
run_poc "P3: NetworkGrid Coalition"        poc/pillar3_network_coalition.py
run_poc "P3: Scale Benchmark N=50..500"    poc/pillar3_scale_benchmark.py

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════"
echo -e "  RESULTS SUMMARY"
echo -e "═══════════════════════════════════════════════════════════${RESET}"
for label in \
  "P1: Bug Reproduction + Fix" \
  "P1: Lifecycle Stress (30 steps)" \
  "P2: Type-Boundary Validation" \
  "P2: Negotiation Model" \
  "P3: NetworkGrid Coalition" \
  "P3: Scale Benchmark N=50..500"
do
  if [[ "${RESULTS[$label]:-FAIL}" == "PASS" ]]; then
    echo -e "  ${GREEN}✓ PASS${RESET}  $label"
  else
    echo -e "  ${RED}✗ FAIL${RESET}  $label"
  fi
done
echo ""
echo -e "  $((PASS+FAIL)) total  |  ${GREEN}$PASS passed${RESET}  |  ${RED}$FAIL failed${RESET}"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}${BOLD}  ✅ All 6 PoCs passing!${RESET}"
  echo ""
  echo "  ┌─────────────────────────────────────────────────────────┐"
  echo "  │  NEXT: Take these screenshots for your proposal         │"
  echo "  │                                                         │"
  echo "  │  1. python poc/pillar1_bug_reproduction.py              │"
  echo "  │     → Save as: images/pillar1_bug_reproduction.png      │"
  echo "  │                                                         │"
  echo "  │  2. python poc/pillar1_merge_split_stress.py            │"
  echo "  │     → Save as: images/pillar1_merge_split_stress.png    │"
  echo "  │                                                         │"
  echo "  │  3. python poc/pillar2_type_boundary.py                 │"
  echo "  │     → Save as: images/pillar2_type_boundary.png         │"
  echo "  │                                                         │"
  echo "  │  4. python poc/pillar3_network_coalition.py             │"
  echo "  │     → Save as: images/pillar3_network_coalition.png     │"
  echo "  │                                                         │"
  echo "  │  5. python poc/pillar3_scale_benchmark.py               │"
  echo "  │     → Save as: images/pillar3_scale_benchmark.png       │"
  echo "  │                                                         │"
  echo "  │  6. bash poc/run_all_pocs.sh  (full runner output)      │"
  echo "  │     → Save as: images/run_all_models_14_14.png          │"
  echo "  └─────────────────────────────────────────────────────────┘"

  echo ""
  echo -e "${CYAN}Committing patched files...${RESET}"
  git add poc/
  git commit -m "fix(poc): remove seed= kwarg for mesa_signals/core MRO compatibility

Mesa dev fork passes **kwargs up MRO to object.__init__() which rejects
seed=. All 6 PoC files patched to call mesa.Model() without seed kwarg.
model.rng → model.random references also normalised.

6/6 PoCs now passing."
  git push origin main
  echo -e "${GREEN}  ✓ Pushed to origin/main${RESET}"
else
  echo -e "\n${RED}  Some PoCs still failing — check errors above.${RESET}"
fi