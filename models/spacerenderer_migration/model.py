"""SpaceRenderer Migration Demo — showing new SpaceRenderer.render() API.

This mini Schelling model is intentionally kept small to show the API
pattern clearly without FutureWarning noise from deprecated draw calls.
"""
from __future__ import annotations

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent

EMPTY = 0
GROUP_A = 1
GROUP_B = 2


class SchellingAgent(CellAgent):
    """Agent that moves if its neighbourhood is too dissimilar."""

    def __init__(self, model: mesa.Model, group: int):
        super().__init__(model)
        self.group = group
        self.happy = False

    def step(self):
        neighbours = [
            a for cell in self.cell.connections.values()
            for a in cell.agents
            if isinstance(a, SchellingAgent)
        ]
        if not neighbours:
            self.happy = True
            return
        similar = sum(1 for n in neighbours if n.group == self.group)
        self.happy = similar / len(neighbours) >= self.model.homophily
        if not self.happy and self.model.grid.empties:
            self.move_to(self.model.grid.select_random_empty_cell())


class SchellingModel(mesa.Model):
    """Schelling segregation model — SpaceRenderer.render() demo."""

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        density: float = 0.8,
        fraction_a: float = 0.5,
        homophily: float = 0.3,
        rng: int = 42,
    ):
        super().__init__(rng=rng)
        self.homophily = homophily
        self.grid = OrthogonalMooreGrid(
            (width, height), torus=True, random=self.random
        )
        for cell in self.grid._cells.values():
            if self.random.random() < density:
                group = GROUP_A if self.random.random() < fraction_a else GROUP_B
                agent = SchellingAgent(self, group)
                agent.move_to(cell)

        self.datacollector = mesa.DataCollector(
            model_reporters={"Happy": lambda m: sum(
                1 for a in m.agents if isinstance(a, SchellingAgent) and a.happy
            )}
        )

    def step(self):
        self.datacollector.collect(self)
        self.agents.shuffle_do("step")


if __name__ == "__main__":
    model = SchellingModel(rng=42)
    for i in range(30):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    print(f"Step 30 — Happy agents: {int(df['Happy'].iloc[-1])}")
