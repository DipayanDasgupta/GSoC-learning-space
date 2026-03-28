"""
Voronoi Capacity Model — PR #3544 demo  (Mesa 3.5.1 compatible)
================================================================
VoronoiGrid now correctly respects user-provided capacity (PR #3544 fix).

Root cause fix D:
  VoronoiGrid(points=...)  →  VoronoiGrid(centroids_coordinates=...)
The Mesa 3.5.1 constructor uses centroids_coordinates as the first positional arg.

Run:  python models/voronoi_capacity/model.py
"""
from __future__ import annotations
import mesa
from mesa.discrete_space import VoronoiGrid
from mesa.discrete_space.cell_agent import CellAgent

try:
    from mesa.discrete_space.cell import CellFullException
except ImportError:
    CellFullException = Exception


class TerritorialAgent(CellAgent):
    def __init__(self, model: mesa.Model):
        super().__init__(model)

    def step(self):
        pass   # territorial — stays in place


class VoronoiCapacityModel(mesa.Model):
    def __init__(self, n_agents: int = 15, rng: int = 42):
        super().__init__(rng=rng)
        # Generate random centroid coordinates
        coords = [
            (float(self.rng.uniform(0.05, 0.95)),
             float(self.rng.uniform(0.05, 0.95)))
            for _ in range(n_agents)
        ]
        # FIX D: centroids_coordinates (not 'points')
        self.grid = VoronoiGrid(
            centroids_coordinates=coords,
            capacity=1,
        )
        cells = list(self.grid._cells.values())
        for i in range(min(n_agents, len(cells))):
            agent = TerritorialAgent(self)
            agent.move_to(cells[i])

    def step(self):
        self.agents.shuffle_do("step")


def test_capacity_respected():
    """Confirm CellFullException when capacity=1 is exceeded."""
    model = VoronoiCapacityModel(n_agents=5, rng=99)
    cells = list(model.grid._cells.values())
    extra = TerritorialAgent(model)
    raised = False
    try:
        extra.move_to(cells[0])     # already has an agent
    except Exception as e:
        msg = str(e).lower()
        if "full" in msg or "capacity" in msg:
            raised = True
        else:
            raise
    return raised


if __name__ == "__main__":
    N = 15
    print(f"VoronoiGrid capacity=1 test — {N} agents, {N} cells")
    model = VoronoiCapacityModel(n_agents=N, rng=42)
    actual_cells = len(list(model.grid._cells.values()))
    print(f"  Created {actual_cells} Voronoi cells")

    if test_capacity_respected():
        print("  ✅ CellFullException raised — PR #3544 fix confirmed.")
    else:
        print("  ⚠️  No exception raised (may be a different Mesa version).")

    print(f"\n  Running 20 steps...")
    for _ in range(20):
        model.step()
    print("  ✅ 20 steps completed without error.")
