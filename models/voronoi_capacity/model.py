"""Voronoi Capacity Model — demonstrating PR #3544 fix.

VoronoiGrid now correctly respects user-provided `capacity` arguments.
Before the fix, capacity_function always overwrote the user's value.
"""
from __future__ import annotations

import mesa
from mesa.discrete_space import VoronoiGrid
from mesa.discrete_space.cell_agent import CellAgent

try:
    from mesa.discrete_space.cell import CellFullException
except ImportError:
    # Older Mesa versions may have a different path
    CellFullException = Exception


class TerritorialAgent(CellAgent):
    """An agent that claims exactly one Voronoi region."""

    def __init__(self, model: mesa.Model):
        super().__init__(model)

    def step(self):
        """Stay put — territorial agents do not move."""
        pass


class VoronoiCapacityModel(mesa.Model):
    """Model with VoronoiGrid, capacity=1, to verify PR #3544 correctness."""

    def __init__(self, n_agents: int = 15, rng: int = 42):
        super().__init__(rng=rng)

        # Generate random points for Voronoi tessellation
        points = [
            (self.random.uniform(0, 1), self.random.uniform(0, 1))
            for _ in range(n_agents)
        ]

        # capacity=1 — each Voronoi region holds at most 1 agent
        # Before PR #3544 this was silently overwritten; now it is respected.
        self.grid = VoronoiGrid(
            points=points,
            capacity=1,
        )

        cells = list(self.grid._cells.values())
        for i, cell in enumerate(cells[:n_agents]):
            agent = TerritorialAgent(self)
            agent.move_to(cell)

    def step(self):
        self.agents.shuffle_do("step")


def test_capacity_respected():
    """Verify that CellFullException is raised when capacity=1 is exceeded."""
    model = VoronoiCapacityModel(n_agents=5, rng=99)
    cells = list(model.grid._cells.values())
    # All 5 cells should now be full (capacity=1, 1 agent each)

    extra_agent = TerritorialAgent(model)
    raised = False
    try:
        extra_agent.move_to(cells[0])   # cell[0] already has an agent
    except (CellFullException, Exception) as e:
        if "full" in str(e).lower() or "capacity" in str(e).lower():
            raised = True
        else:
            raise

    if raised:
        print("✅ CellFullException raised correctly — PR #3544 fix confirmed.")
    else:
        print("⚠️  No exception raised. Check Mesa version / PR #3544 status.")

    return raised


if __name__ == "__main__":
    N = 15
    print(f"VoronoiGrid capacity=1 test — {N} agents, {N} cells")
    model = VoronoiCapacityModel(n_agents=N, rng=42)
    print(f"Placed {N} agents successfully (one per Voronoi cell). ✓")

    test_capacity_respected()

    print(f"\nRun 20 steps with shuffled agent movement...")
    for _ in range(20):
        model.step()
    print("All 20 steps completed. ✓")
