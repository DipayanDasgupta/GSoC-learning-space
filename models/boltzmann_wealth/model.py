"""Boltzmann Wealth Model — Mesa learning space implementation."""

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent


class MoneyAgent(CellAgent):
    """An agent with fixed initial wealth who gives money to neighbours."""

    def __init__(self, model):
        super().__init__(model)
        self.wealth = 1

    def step(self):
        if self.wealth == 0:
            return
        neighbours = [
            a
            for cell in self.cell.connections.values()
            for a in cell.agents
            if a is not self
        ]
        if neighbours:
            recipient = self.random.choice(neighbours)
            recipient.wealth += 1
            self.wealth -= 1


class BoltzmannWealthModel(mesa.Model):
    """Model with N agents on a grid exchanging wealth randomly."""

    def __init__(self, n_agents=50, width=10, height=10, rng=42):
        super().__init__(rng=rng)
        self.grid = OrthogonalMooreGrid(
            (width, height), torus=True, random=self.random
        )
        cells = list(self.grid._cells.values())
        for _ in range(n_agents):
            agent = MoneyAgent(self)
            agent.move_to(self.random.choice(cells))

    def step(self):
        self.agents.shuffle_do("step")


if __name__ == "__main__":
    model = BoltzmannWealthModel(n_agents=50)
    for _ in range(20):
        model.step()
    wealth = model.agents.get("wealth")
    print(f"Total wealth: {sum(wealth)} | Gini: {gini(wealth):.3f}")


def gini(values):
    """Compute Gini coefficient."""
    v = sorted(values)
    n = len(v)
    return (2 * sum((i + 1) * w for i, w in enumerate(v)) - (n + 1) * sum(v)) / (
        n * sum(v)
    )
