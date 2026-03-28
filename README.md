# GSoC 2026 — Mesa Meta Agents Learning Space

**Applicant:** Dipayan Dasgupta · IIT Madras  
**Project:** Meta Agents (Medium) — `mesa.experimental.meta_agents`  
**Mentors:** Tom Pike, Ewout  
**Status:** ✅ 14/14 models passing on Mesa 3.5.1 (released pip)

---

## Verified Results — All 14 Models Passing

```
═══════════════════════════════════════════════════════════════
  RESULTS SUMMARY
═══════════════════════════════════════════════════════════════

  ✓ PASS  Alliance Formation (PR#3567)
  ✓ PASS  All Pillars: Financial Market
  ✓ PASS  Boltzmann Wealth (PR#3542)
  ✓ PASS  Capacity-Aware Placement (PR#3542)
  ✓ PASS  Coalition Stability Tracker (new)
  ✓ PASS  LLM Audit Trail (new)
  ✓ PASS  Misinformation Spread (All LLM)
  ✓ PASS  Pillar 1: Meta Agents Lifecycle
  ✓ PASS  Pillar 2: LLM Evaluation Demo
  ✓ PASS  Pillar 3: Spatial Coalition
  ✓ PASS  SpaceRenderer Migration (PR#3283)
  ✓ PASS  Spatial+LLM Benchmark (new)
  ✓ PASS  Voronoi Capacity (PR#3544)
  ✓ PASS  WolfSheep grass=False (PR#3627)

  14 total  |  14 passed  |  0 failed
```

Reproduce with:
```bash
git clone https://github.com/DipayanDasgupta/GSoC-learning-space.git
cd GSoC-learning-space
pip install mesa
bash run_all_models.sh
```

---

## Repository Structure

```
GSoC-learning-space/
├── models/
│   ├── meta_agents_poc/          Pillar 1 — join/leave/dissolve lifecycle API
│   ├── llm_evaluation_demo/      Pillar 2 — LLMEvaluationAgent (no API key)
│   ├── spatial_coalition/        Pillar 3 — spatial_find_combinations() PoC
│   ├── financial_market_coalition/  All 3 pillars integrated
│   ├── coalition_stability/      Extended Pillar 1 — merge/split/step tracking
│   ├── llm_audit_trail/          Extended Pillar 2 — audit trail + retry logic
│   ├── spatial_llm_benchmark/    Pillars 2+3 — wall-clock speedup benchmark
│   ├── alliance_formation/       PR #3567 evidence
│   ├── boltzmann_wealth/         PR #3542 evidence
│   ├── capacity_aware_placement/ PR #3542 evidence
│   ├── voronoi_capacity/         PR #3544 evidence
│   ├── spacerenderer_migration/  PR #3283 evidence
│   └── wolf_sheep_investigation/ PR #3627 evidence
└── mesa_llm_poc/
    ├── vector_memory.py          Pillar 1: VectorMemory
    ├── async_engine.py           Pillar 3: AsyncLLMEngine + TokenBucket
    ├── langgraph_agent.py        Pillar 2: LangGraphAgent + MesaToolkit
    └── demo/
        └── misinformation_spread.py  All three pillars composed
```

---

## Proposal Pillars

### Pillar 1 — Meta Agents Lifecycle API
Fix two known agent-count bugs in `mesa.experimental.meta_agents`, then add
`join()`, `leave()`, `merge()`, `split()` lifecycle methods with a full test suite.
Graduation path: `experimental` → `mesa.meta_agents`.

**PoC output (Pillar 1):**
```
[Phase 1] Forming teams from 20 workers...
  → Formed Team 21 (score=2.78, workers=[3, 6, 12])
  → Formed Team 22 (score=2.49, workers=[8, 14, 19])

[Phase 2] Lifecycle operations — leave + join
  - Worker 12 left    Team 21
  + Worker 1 joined   Team 21

  ✅ Agent counts consistent — Pillar 1 lifecycle API working.
```

### Pillar 2 — LLM Evaluation Agent
`LLMEvaluationAgent` bridges `meta_agents` and Mesa-LLM's `ReasoningAgent`.
Evaluates coalition candidates via LLM scoring with audit trail + retry logic.

**PoC output (Pillar 2):**
```
  Step 1: Best score = 0.950 | Agents: [18, 19, 20] | Recommended: True
  Step 2: Best score = 0.950 | Agents: [18, 19, 20] | Recommended: True
  Step 3: Best score = 0.950 | Agents: [18, 19, 20] | Recommended: True
  Total LLM evaluations: 3420
  ✅ LLMEvaluationAgent working — Pillar 2 PoC complete.
```

### Pillar 3 — Spatial Coalition Search
`spatial_find_combinations()` filters candidates to Moore-1 neighbourhoods,
reducing search space from O(C(N,k)) to O(N × neighbourhood^(k-1)).

**PoC output (Pillar 3):**
```
  N=50  agents, k=3 → Naive: 19,600  | Spatial:     22 | Reduction: 99.9%
  N=100 agents, k=3 → Naive: 161,700 | Spatial:    237 | Reduction: 99.9%
  N=200 agents, k=3 → Naive: 1,313,400 | Spatial: 1,667 | Reduction: 99.9%
  ✅ Spatial filtering confirmed >80% search-space reduction.
```

**Benchmark (Pillars 2+3 combined):**
```
  N=20, latency=10ms/call  → Speedup:  4.7× | Search reduction: 78.6%
  N=30, latency= 5ms/call  → Speedup: 10.6× | Search reduction: 90.6%
  N=40, latency= 2ms/call  → Speedup: 14.4× | Search reduction: 92.9%
  Average speedup: 9.9×
```

---

## Mesa Contributions (Pre-GSoC)

| PR | Title | Status |
|----|-------|--------|
| [#3567](https://github.com/projectmesa/mesa/pull/3567) | Type validation in `evaluate_combination` (meta_agents) | Open |
| [#3542](https://github.com/projectmesa/mesa/pull/3542) | `Grid.not_full_cells` API | Merged |
| [#3544](https://github.com/projectmesa/mesa/pull/3544) | VoronoiGrid capacity fix | Merged |
| Mesa-LLM #21 | `Reasoning` test suite | Merged |

---

## Quick Start

```bash
pip install mesa
bash run_all_models.sh            # run all 14 models
python models/meta_agents_poc/model.py          # Pillar 1
python models/llm_evaluation_demo/model.py      # Pillar 2
python models/spatial_coalition/model.py        # Pillar 3
python mesa_llm_poc/demo/misinformation_spread.py  # All pillars
```

No API key required. All LLM calls use `MockLLMClient`.
