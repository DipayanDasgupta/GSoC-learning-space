# Capacity-Aware Placement Model

## What this model does

Simulates a **shared housing** scenario: 200 agents compete for cells on a
10×10 grid where each cell has `capacity=3` (three flatmates per unit).
Agents use `grid.select_random_not_full_cell()` (added in PR #3542) to find
cells that still have room — a query that `select_random_empty_cell()` cannot
answer once any agent has moved in.

At each step, agents attempt to move to a random not-full cell. When no
not-full cell exists (the grid is saturated), the model detects this via
`grid.not_full_cells` and stops gracefully.

## Output

```
Step 0: 200 agents, 0 full cells
Step 5: 200 agents, 47 full cells
...
Step 40: Grid saturated (all 100 cells at capacity=3). Stopping.
Average agents per cell: 2.0 | Max: 3 | Gini: 0.12
```

## Mesa features used

- `OrthogonalMooreGrid` with `capacity=3`
- `grid.not_full_cells` — new in PR #3542
- `grid.select_random_not_full_cell()` — new in PR #3542
- `CellAgent`, `shuffle_do`, `DataCollector`

## Connection to PR #3542

The Boltzmann model in this repo exposed the gap: once any agent entered a
cell, `select_random_empty_cell()` stopped working. This model exercises the
full capacity lifecycle — partial fill, full fill, saturation detection — and
was impossible to build cleanly before PR #3542.
