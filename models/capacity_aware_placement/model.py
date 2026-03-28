"""Capacity-Aware Placement — PR #3542 demo  (Mesa 3.5.1, released pip)

FIX 2: cells_with_capacity / select_random_cell_with_capacity are NOT in the
        released pip 3.5.1 package — implement inline using cell.is_full.
"""
from __future__ import annotations
import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent

CELL_CAPACITY = 3
W, H = 10, 10


def gini(values):
    v = sorted(values); n = len(v)
    if n == 0 or sum(v) == 0: return 0.0
    return (2 * sum((i+1)*w for i,w in enumerate(v)) - (n+1)*sum(v)) / (n*sum(v))


def _not_full(grid):
    """Inline replacement for grid.cells_with_capacity (not in pip 3.5.1)."""
    return [c for c in grid._cells.values() if not c.is_full]


class FlatmateAgent(CellAgent):
    def __init__(self, model): super().__init__(model)
    def step(self):
        available = _not_full(self.model.grid)
        if not available: return
        target = self.model.rng.choice(available)
        if target is not self.cell:
            self.move_to(target)


class CapacityAwarePlacementModel(mesa.Model):
    def __init__(self, n_agents: int = 200, rng: int = 42):
        super().__init__(rng=rng)
        self.grid = OrthogonalMooreGrid(
            (W, H), torus=True, capacity=CELL_CAPACITY, random=self.random)
        for _ in range(n_agents):
            agent     = FlatmateAgent(self)
            available = _not_full(self.grid)
            cell      = (self.rng.choice(available) if available
                         else self.rng.choice(list(self.grid._cells.values())))
            agent.move_to(cell)
        self.datacollector = mesa.DataCollector(model_reporters={
            "FullCells":    lambda m: sum(1 for c in m.grid._cells.values()
                                          if c.is_full),
            "NotFullCells": lambda m: len(_not_full(m.grid)),
        })

    def step(self):
        self.datacollector.collect(self)
        if not _not_full(self.grid): return
        self.agents.shuffle_do("step")


if __name__ == "__main__":
    model = CapacityAwarePlacementModel(n_agents=200, rng=42)
    for step in range(50):
        model.step()
        df       = model.datacollector.get_model_vars_dataframe()
        full     = int(df["FullCells"].iloc[-1])
        not_full = int(df["NotFullCells"].iloc[-1])
        print(f"  Step {step:3d}: {full}/{W*H} full, {not_full} with capacity")
        if not_full == 0:
            print("  Grid saturated — stopping.")
            break
    occupancy = [len(list(c.agents)) for c in model.grid._cells.values()]
    print(f"\n  Avg: {sum(occupancy)/len(occupancy):.2f} "
          f"| Max: {max(occupancy)} | Gini: {gini(occupancy):.3f}")
    print("  ✅ Capacity-aware placement complete.")
