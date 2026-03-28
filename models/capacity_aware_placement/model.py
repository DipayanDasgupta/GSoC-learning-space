"""Capacity-Aware Placement Model — demonstrating PR #3542 API.

Agents find cells with remaining capacity using not_full_cells and
select_random_not_full_cell() — impossible before PR #3542.
"""
from __future__ import annotations

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent


CELL_CAPACITY = 3
GRID_WIDTH = 10
GRID_HEIGHT = 10


def gini(values: list[float]) -> float:
    """Compute the Gini coefficient of a list of values."""
    v = sorted(values)
    n = len(v)
    if n == 0 or sum(v) == 0:
        return 0.0
    return (2 * sum((i + 1) * w for i, w in enumerate(v)) - (n + 1) * sum(v)) / (
        n * sum(v)
    )


class FlatmateAgent(CellAgent):
    """An agent looking for a not-full cell to live in."""

    def __init__(self, model: mesa.Model):
        super().__init__(model)

    def step(self):
        """Try to move to a random not-full cell."""
        if not self.model.grid.not_full_cells:
            return  # Grid saturated — stay put
        target = self.model.grid.select_random_not_full_cell()
        if target is not self.cell:
            self.move_to(target)


class CapacityAwarePlacementModel(mesa.Model):
    """Model demonstrating select_random_not_full_cell() (PR #3542)."""

    def __init__(
        self,
        n_agents: int = 200,
        width: int = GRID_WIDTH,
        height: int = GRID_HEIGHT,
        capacity: int = CELL_CAPACITY,
        rng: int = 42,
    ):
        super().__init__(rng=rng)
        self.grid = OrthogonalMooreGrid(
            (width, height),
            torus=True,
            capacity=capacity,
            random=self.random,
        )

        # Place agents using not_full_cells from the start
        for _ in range(n_agents):
            agent = FlatmateAgent(self)
            if self.grid.not_full_cells:
                cell = self.grid.select_random_not_full_cell()
                agent.move_to(cell)
            else:
                # Grid saturated during init — just pick any cell
                all_cells = list(self.grid._cells.values())
                agent.move_to(self.random.choice(all_cells))

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "FullCells": lambda m: sum(
                    1 for c in m.grid._cells.values()
                    if len(list(c.agents)) >= capacity
                ),
                "NotFullCells": lambda m: len(m.grid.not_full_cells),
            }
        )

    def step(self):
        self.datacollector.collect(self)
        if not self.grid.not_full_cells:
            return  # Grid saturated
        self.agents.shuffle_do("step")


if __name__ == "__main__":
    model = CapacityAwarePlacementModel(n_agents=200, rng=42)
    for step in range(50):
        model.step()
        df = model.datacollector.get_model_vars_dataframe()
        full = int(df["FullCells"].iloc[-1])
        not_full = int(df["NotFullCells"].iloc[-1])
        total = GRID_WIDTH * GRID_HEIGHT
        print(f"Step {step:3d}: {full}/{total} full cells, {not_full} not-full cells")
        if not_full == 0:
            print("Grid saturated — all cells at capacity. Stopping.")
            break

    # Summary statistics
    occupancy = [
        len(list(c.agents))
        for c in model.grid._cells.values()
    ]
    print(f"\nFinal occupancy — avg: {sum(occupancy)/len(occupancy):.2f} "
          f"| max: {max(occupancy)} | Gini: {gini(occupancy):.3f}")
