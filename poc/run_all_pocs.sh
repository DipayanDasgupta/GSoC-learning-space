#!/usr/bin/env bash
# poc/run_all_pocs.sh  —  run all 6 new proposal PoCs
# Run from repo root: bash poc/run_all_pocs.sh
set -euo pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
PASS=0; FAIL=0; declare -A R; TIMEOUT=120

run() {
  local name="$1" script="poc/$2"
  echo -e "\n${CYAN}${BOLD}──── $name ────${RESET}"
  local out ec=0
  out=$(timeout "$TIMEOUT" python "$script" 2>&1) || ec=$?
  if [ $ec -ne 0 ]; then
    echo -e "${RED}FAILED (exit $ec)${RESET}"; echo "$out" | tail -20
    R["$name"]="FAIL"; FAIL=$((FAIL+1))
  else
    echo "$out"
    echo -e "${GREEN}  ✓ PASS${RESET}"
    R["$name"]="PASS"; PASS=$((PASS+1))
  fi
}

echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
echo -e "║  GSoC 2026 — Meta Agents Proposal PoC Runner                ║"
echo -e "╠══════════════════════════════════════════════════════════════╣"
echo -e "║  Pillar 1: Production Hardening                              ║"
echo -e "║  Pillar 2: LLM-Powered Coalition Evaluation                  ║"
echo -e "║  Pillar 3: DiscreteSpace-Aware Formation                     ║"
echo -e "╚══════════════════════════════════════════════════════════════╝${RESET}"

run "P1: Bug A & B Reproduction + Fix"  pillar1_bug_reproduction.py
run "P1: Lifecycle Stress Test (30 steps)" pillar1_merge_split_stress.py
run "P2: Type-Boundary Validation"       pillar2_type_boundary.py
run "P2: Non-Spatial Negotiation Model"  pillar2_negotiation_model.py
run "P3: NetworkGrid Coalition"          pillar3_network_coalition.py
run "P3: Scale Benchmark N={50..500}"    pillar3_scale_benchmark.py

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════"
echo -e "  RESULTS"
echo -e "═══════════════════════════════════════════════════════════${RESET}"
for n in "${!R[@]}"; do
  [[ "${R[$n]}" == "PASS" ]] \
    && echo -e "  ${GREEN}✓ PASS${RESET}  $n" \
    || echo -e "  ${RED}✗ FAIL${RESET}  $n"
done | sort
echo ""
TOTAL=$((PASS+FAIL))
echo -e "  $TOTAL total  |  ${GREEN}$PASS passed${RESET}  |  ${RED}$FAIL failed${RESET}"
[ "$FAIL" -eq 0 ] && echo -e "\n${GREEN}${BOLD}  ✓ All PoCs passing.${RESET}"
