# Mesa GSoC Learning Space — Dipayan Dasgupta

## About me
CS student interested in ML/NLP and agent-based modelling. Applying for GSoC 2026 with Mesa.

## Models built

| Model | Description | Mesa features |
|-------|-------------|---------------|
| [Boltzmann Wealth](models/boltzmann_wealth/) | Economy where agents exchange wealth on a grid | `OrthogonalMooreGrid`, `CellAgent`, `shuffle_do` |

## Mesa contributions

| PR | Description | Status |
|----|-------------|--------|
| [#3542](https://github.com/mesa/mesa/pull/3542) | Add `Grid.not_full_cells` and `select_random_not_full_cell()` | Open |
| [#3544](https://github.com/mesa/mesa/pull/3544) | Fix VoronoiGrid silently overwriting user-provided capacity | Open |

## Connection between the model and PR #3542

While building the Boltzmann Wealth model on a grid, I needed to place agents
into cells that still had remaining capacity — not just empty cells. Mesa's
existing `empties` / `select_random_empty_cell()` API only tracks cells with
zero agents. Once any agent enters a cell, `cell.empty` becomes `False` — even
if `capacity=5` and 4 slots remain.

This is the gap PR #3542 fills: `not_full_cells` and `select_random_not_full_cell()`
give models a correct, efficient way to find cells with available space.
