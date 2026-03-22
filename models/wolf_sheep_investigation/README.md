# Wolf-Sheep grass=False Investigation (Issue #3597)

## What I built / investigated
Reproduced and fixed a two-part crash in the WolfSheep example when
`grass=False` is passed via `WolfSheepScenario`.

## The two bugs

### Bug 1 — `StopIteration` in `Sheep.feed()`
`Sheep.feed()` used a bare generator expression inside `next()`:
```python
# Before (crashes when no GrassPatch in cell):
grass_patch = next(obj for obj in self.cell.agents if isinstance(obj, GrassPatch))

# After (safe default):
grass_patch = next(
    (obj for obj in self.cell.agents if isinstance(obj, GrassPatch)), None
)
if grass_patch is not None and grass_patch.fully_grown:
    ...
```
`next(generator)` with no default raises `StopIteration` when the
generator is empty. With `grass=False` no `GrassPatch` agents exist,
so every call to `Sheep.feed()` crashed.

### Bug 2 — `KeyError: 'Grass'` in `PlotMatplotlib`
When `grass=False` the DataCollector never registers a `"Grass"` reporter,
so the dataframe has no `Grass` column. The visualizer was plotting
all keys from the `measure` dict unconditionally — crashing when
`df.loc[:, "Grass"]` raised `KeyError`.

Fix: add `if m in df.columns:` guard before every `ax.plot()` call.

## What I learned
- `next(gen)` vs `next(gen, default)` — a one-character omission that
  causes a hard crash only on a non-default parameter path.
- Mesa's DataCollector reporters are conditionally registered — the
  visualization layer must not assume every metric always exists.
- How to write minimal regression tests that document the exact failure
  scenario so it can never silently regress.

## Mesa files changed
- `mesa/examples/advanced/wolf_sheep/agents.py`
- `mesa/visualization/components/matplotlib_components.py`
- `tests/examples/test_examples.py`

## PR
https://github.com/projectmesa/mesa/pull/3597
