# Boltzmann Wealth Model

## What this model does

Simulates a simple economy where agents on a grid exchange wealth randomly
with neighbours. Each agent starts with 1 unit of wealth. At each step an
agent picks a random neighbour and gives them 1 unit. Despite the symmetry,
wealth concentrates — a Boltzmann-Gibbs distribution emerges (Gini ~0.8),
matching real-world wealth distributions.

**Output from 100 agents, 50 steps:**
```
Total wealth: 100 | Gini: 0.798 | Min: 0 | Max: 13
```

## Mesa features used

- `OrthogonalMooreGrid` from `mesa.discrete_space`
- `CellAgent` — agents that live on grid cells
- `cell.connections` — neighbour lookup without manual coordinate arithmetic
- `agents.shuffle_do()` — randomised activation order each step

## Connection to PR #3542

While building this model I hit the gap that motivated
[PR #3542](https://github.com/mesa/mesa/pull/3542).

When placing 100 agents across a 10×10 grid with `capacity=2`, I needed
cells that still had room — not just cells that were completely empty.
`select_random_empty_cell()` stopped working the moment the first agent
entered a cell. What I actually needed was `select_random_not_full_cell()`.

This is a real friction point for any model where agents share cells up to
a capacity limit. The PR adds exactly this: `grid.not_full_cells` and
`grid.select_random_not_full_cell()`.

## What I learned

- The difference between `cell.empty` and `not cell.is_full` is subtle but
  matters a lot in capacity-bounded models. Empty = zero agents. Not full =
  still has room. These are completely different queries.
- Maintaining a `full` property layer (my first implementation) added overhead
  on every agent move — 2 numpy writes per step in the hot path. Removing it
  and computing lazily brought performance back to baseline.
- The two-phase random sampling heuristic (50 random attempts before falling
  back to an explicit list) is the right pattern for this kind of query.

## What was harder than expected

Getting a realistic Gini coefficient required more agents and steps than
expected. With only 20 agents the distribution was too noisy. 100 agents
over 50 steps converged to ~0.8, matching theoretical predictions.

## What I would do differently

Add a `DataCollector` from the start to track Gini per step and plot
the convergence curve rather than computing it only at the end.
