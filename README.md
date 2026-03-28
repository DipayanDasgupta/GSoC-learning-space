# Mesa GSoC Learning Space — Dipayan Dasgupta

> **GSoC 2026 Proposal:** *Persistent Vector Memory, LangGraph Integration,
> and Async API Infrastructure for Mesa-LLM*

---

## About me

B.Tech (Civil Engineering) sophomore at **IIT Madras**, applying for
Google Summer of Code 2026 with **Mesa** on the **Mesa-LLM** project.

Background: quantitative finance simulations (IMC Prosperity Trading
Challenge 2025 — Global Rank 66 / 12,000+ teams; India Rank 9;
Goldman Sachs India Hackathon 2025 — AIR 5), competitive programming
(Codeforces Specialist, max 1575), and full-stack AI/ML engineering.

- **Email:** deep.dasgupta2006@gmail.com
- **GitHub:** [DipayanDasgupta](https://github.com/DipayanDasgupta)
- **Proposal focus:** Three independently deployable extensions to the
  2025 Mesa-LLM baseline — vector memory, LangGraph integration, and
  async batch invocation.

---

## Mesa Contributions

### Merged Pull Requests

| PR | Repository | Description | What I learned |
|----|-----------|-------------|----------------|
| [#3627](https://github.com/mesa/mesa/pull/3627) | mesa | Fix `Sheep.feed()` `StopIteration` crash when `grass=False` | `next(gen)` vs `next(gen, default)`; Mesa DataCollector is conditionally dynamic — downstream viz must never assume every key exists |
| [#3542](https://github.com/mesa/mesa/pull/3542) | mesa | Add `Grid.not_full_cells` + `select_random_not_full_cell()` | Difference between `cell.empty` and `not cell.is_full`; maintained property layers beat lazy computation in hot paths |
| [#3544](https://github.com/mesa/mesa/pull/3544) | mesa | Fix `VoronoiGrid` silently overwriting user-provided `capacity` | Private methods in `DiscreteSpace` that mutate cell state must respect constructor contracts; motivated the `MesaToolkit` atomic write design |
| [#3014](https://github.com/mesa/mesa/pull/3014) | mesa | Fix infinite loop in `select_random_empty_cell` on full grid | `_empties` property layer architecture across all Grid subclasses; heuristic fallback pattern |
| [#3011](https://github.com/mesa/mesa/pull/3011) | mesa | Consolidate Solara + Altair CI test coverage | `SpaceRenderer` backend dispatch; pluggable visualisation architecture |
| [#21](https://github.com/mesa/mesa-llm/pull/21) | mesa-llm | First pytest suite for `Reasoning` base class | Provider-agnostic `invoke` interface; mock pattern for network-free CI |

### Open Pull Requests (under review)

| PR | Description |
|----|-------------|
| [#3567](https://github.com/mesa/mesa/pull/3567) | Type validation in `evaluate_combination` (`meta_agents`) — removes dead null check, adds actionable `TypeError` at call site |
| [#3283](https://github.com/mesa/mesa/pull/3283) | Migrate core examples from deprecated `draw_agents()` to `SpaceRenderer.render()` |
| [#3013](https://github.com/mesa/mesa/pull/3013) | Restore CI coverage reporting + codecov upload |

### Issues Opened & Diagnosed

| Issue | Description |
|-------|-------------|
| [#3597](https://github.com/mesa/mesa/issues/3597) | WolfSheep grass=False crash (→ fixed in PR #3627) |
| [#3541](https://github.com/mesa/mesa/issues/3541) | `Grid.empties` unusable with `capacity > 1` (→ fixed in PR #3542) |
| [#3543](https://github.com/mesa/mesa/issues/3543) | VoronoiGrid ignores user `capacity` (→ fixed in PR #3544) |
| [#3566](https://github.com/mesa/mesa/issues/3566) | `evaluate_combination` silent non-numeric return (→ PR #3567) |
| [#3282](https://github.com/mesa/mesa/issues/3282) | Core examples emit `FutureWarning` on deprecated renderer API (→ PR #3283) |

---

## Models Built

| Model | Directory | Key Mesa features | Connected PR |
|-------|-----------|-------------------|-------------|
| Boltzmann Wealth | `models/boltzmann_wealth/` | `OrthogonalMooreGrid`, `CellAgent`, `shuffle_do` | #3542 |
| Alliance Formation | `models/alliance_formation/` | `find_combinations`, `evaluate_combination`, `meta_agents` | #3567 |
| Wolf-Sheep Investigation | `models/wolf_sheep_investigation/` | `WolfSheep`, `Solara`, `DataCollector` | #3627 |
| Voronoi Capacity | `models/voronoi_capacity/` | `VoronoiGrid`, `capacity`, `CellFullException` | #3544 |
| Capacity-Aware Placement | `models/capacity_aware_placement/` | `select_random_not_full_cell`, `not_full_cells` | #3542 |
| SpaceRenderer Migration | `models/spacerenderer_migration/` | `SpaceRenderer.render()`, deprecated API removal | #3283 |

---

## Proof-of-Concept: Mesa-LLM Pillars

The `mesa_llm_poc/` directory contains working PoCs of all three proposed GSoC pillars:

| Module | Description |
|--------|-------------|
| `mesa_llm_poc/vector_memory.py` | Per-agent FAISS-backed semantic memory with retrieval |
| `mesa_llm_poc/async_engine.py` | Token-bucket rate limiter + exponential-backoff batch caller |
| `mesa_llm_poc/langgraph_agent.py` | Thin LangGraph wrapper + `MesaToolkit` spatial tool nodes |
| `mesa_llm_poc/demo/misinformation_spread.py` | Full demo model composing all three pillars |

Run the demo (no LLM API key needed — uses mocked completions):
```bash
cd mesa_llm_poc
pip install -e ".[dev]"     # installs mesa, faiss-cpu, langgraph
python demo/misinformation_spread.py
```

See [`mesa_llm_poc/README.md`](mesa_llm_poc/README.md) for full architecture
explanation and feasibility analysis.

---

## Repository Structure

```
GSoC-learning-space/
├── models/
│   ├── boltzmann_wealth/
│   ├── alliance_formation/
│   ├── wolf_sheep_investigation/
│   ├── voronoi_capacity/          ← new, PR #3544
│   ├── capacity_aware_placement/  ← new, PR #3542
│   └── spacerenderer_migration/   ← new, PR #3283
├── mesa_llm_poc/                  ← GSoC proposal PoC
│   ├── vector_memory.py
│   ├── async_engine.py
│   ├── langgraph_agent.py
│   └── demo/
│       └── misinformation_spread.py
├── motivation.md
└── README.md
```
