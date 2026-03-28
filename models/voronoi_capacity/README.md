# Voronoi Capacity Model

## What this model does

Places agents on a `VoronoiGrid` with an **explicit `capacity` argument** and
demonstrates that the capacity constraint is now correctly enforced — i.e. that
a `CellFullException` is raised when a cell is full.

Before PR #3544, `VoronoiGrid._build_cell_polygons` unconditionally overwrote
every cell's `capacity` with an area-derived value, silently discarding the
user's explicit argument. This meant `capacity=1` was a no-op on VoronoiGrid.

This model proves the fix: with `capacity=1`, attempting to place two agents
in the same cell raises `CellFullException` as expected.

## Output

```
VoronoiGrid capacity=1 test — 15 agents, 15 cells
Placed agent 0 → cell 0 ✓
Placed agent 1 → cell 1 ✓
...
Placed agent 14 → cell 14 ✓
Attempting to overfill cell 0...
✅ CellFullException raised correctly — PR #3544 fix confirmed.

Run 20 steps with shuffled agent movement...
All 20 steps completed without capacity violation. ✓
```

## Mesa features used

- `VoronoiGrid` from `mesa.discrete_space`
- `capacity` parameter (now respected after PR #3544)
- `CellFullException` from `mesa.discrete_space.cell`
- `CellAgent`, `shuffle_do`

## Connection to PR #3544

While building this model I wanted to simulate territorial agents where each
Voronoi region can hold at most one agent. Setting `capacity=1` had no effect —
agents could pile up without limit. Digging into `_build_cell_polygons` revealed
the unconditional overwrite. The fix is a one-line conditional guard.
