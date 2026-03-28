# GSoC 2026 Learning Space — Dipayan Dasgupta

> **IIT Madras · Civil Engineering (B.Tech, Expected 2028)**  
> GSoC 2026 Applicant · Project: **Mesa Meta Agents**  
> Mentors: Tom Pike / Ewout

## About This Repository

This learning space documents my journey from zero to GSoC-ready with Mesa.
It contains original ABM models, proof-of-concept implementations for my
proposal pillars, and investigations that directly motivated my Mesa pull requests.

## My Mesa Contributions

### Merged Pull Requests

| PR | Title | What it taught me |
|----|-------|-------------------|
| [#3627](https://github.com/projectmesa/mesa/pull/3627) | Fix `Sheep.feed()` crash when `grass=False` | Safe generator defaults; conditional DataCollector reporters |
| [#3542](https://github.com/projectmesa/mesa/pull/3542) | Add `Grid.not_full_cells` and `select_random_not_full_cell()` | Capacity vs. emptiness semantics; hot-path property layers |
| [#3544](https://github.com/projectmesa/mesa/pull/3544) | Fix `VoronoiGrid` silently overwriting user `capacity` | Private method contracts in DiscreteSpace hierarchy |
| [#3014](https://github.com/projectmesa/mesa/pull/3014) | Fix infinite loop in `select_random_empty_cell` | Heuristic fallback pattern for grid queries |
| [#3011](https://github.com/projectmesa/mesa/pull/3011) | CI/test consolidation: Solara + Altair coverage | Test organisation across parametrised backends |
| [Mesa-LLM #21](https://github.com/projectmesa/mesa-llm/pull/21) | Pytest suite for `Reasoning` base class | Mock LLM pattern for network-free CI; `invoke()` interface |

### Open Pull Requests

| PR | Title | Status |
|----|-------|--------|
| [#3567](https://github.com/projectmesa/mesa/pull/3567) | Type validation in `evaluate_combination` (`meta_agents`) | Open, CI passing |
| [#3283](https://github.com/projectmesa/mesa/pull/3283) | Refactor core examples to new `SpaceRenderer` API | Open |
| [#3013](https://github.com/projectmesa/mesa/pull/3013) | CI coverage reporting restoration | Open |

### Issues Diagnosed

| Issue | Description |
|-------|-------------|
| [#3566](https://github.com/projectmesa/mesa/issues/3566) | `evaluate_combination` accepts non-numeric return values silently |
| [#3541](https://github.com/projectmesa/mesa/issues/3541) | Grid has no API for partial-capacity queries |
| [#3543](https://github.com/projectmesa/mesa/issues/3543) | VoronoiGrid silently overwrites user-provided capacity |
| [#3597](https://github.com/projectmesa/mesa/issues/3597) | WolfSheep crashes with StopIteration when grass=False |
| [#3282](https://github.com/projectmesa/mesa/issues/3282) | Core examples use deprecated draw_agents() |

## GSoC 2026 Proposal: Mesa Meta Agents

**Project slot:** Meta Agents (Medium, 175 hours) — Tom Pike / Ewout  
**Goal:** Graduate `mesa.experimental.meta_agents` to production with three pillars:

| Pillar | Description | Key PRs |
|--------|-------------|---------|
| 1. Production Hardening | Fix agent-count bugs, add lifecycle API (join/leave/merge/split), complete test suite | #3567, #3627 |
| 2. LLM-Powered Evaluation | `LLMEvaluationAgent` wrapping `mesa_llm.ReasoningAgent` with Pydantic validation | Mesa-LLM #21 |
| 3. DiscreteSpace-Aware Formation | `spatial_find_combinations()` filtering candidates to spatial neighbourhoods | #3542, #3544 |

## Models in This Repository

| Directory | Description | Proposal Pillar |
|-----------|-------------|-----------------|
| `models/meta_agents_poc/` | Lifecycle demo: join, leave, merge, split operations | Pillar 1 |
| `models/llm_evaluation_demo/` | LLM coalition evaluation with mock client | Pillar 2 |
| `models/spatial_coalition/` | Spatial candidate filtering: 97% search space reduction | Pillar 3 |
| `models/financial_market_coalition/` | All 3 pillars: market-makers on OrthogonalMooreGrid | All pillars |
| `models/alliance_formation/` | meta_agents investigation (motivated PR #3567) | Background |
| `models/boltzmann_wealth/` | Capacity-aware placement (motivated PR #3542) | Background |
| `models/wolf_sheep_investigation/` | grass=False bug investigation (motivated PR #3627) | Background |

## Motivation

See [motivation.md](motivation.md) for the full narrative.

## Contact

- **Email:** deep.dasgupta2006@gmail.com  
- **GitHub:** [DipayanDasgupta](https://github.com/DipayanDasgupta)  
- **LinkedIn:** [dipayan-dasgupta-24a24719b](https://linkedin.com/in/dipayan-dasgupta-24a24719b)
