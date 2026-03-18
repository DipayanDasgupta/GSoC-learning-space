"""Alliance Formation Model — exploring meta_agents and evaluate_combination."""

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent
from mesa.experimental.meta_agents.meta_agent import find_combinations


class FactionAgent(CellAgent):
    """An agent with strength and ideology who can form alliances."""

    def __init__(self, model, strength=1, ideology=0.0):
        super().__init__(model)
        self.strength = strength
        self.ideology = ideology

    def step(self):
        pass


def alliance_value(group):
    """Score a potential alliance by combined strength minus ideological distance."""
    total_strength = sum(a.strength for a in group)
    ideology_spread = max(a.ideology for a in group) - min(a.ideology for a in group)
    return total_strength - ideology_spread


class AllianceModel(mesa.Model):
    """Model where agents form alliances based on strength and ideology."""

    def __init__(self, n_agents=10, rng=42):
        super().__init__(rng=rng)
        self.grid = OrthogonalMooreGrid(
            (5, 5), torus=True, random=self.random
        )
        cells = list(self.grid._cells.values())
        for i in range(n_agents):
            agent = FactionAgent(
                self,
                strength=self.random.randint(1, 5),
                ideology=self.random.uniform(-1.0, 1.0),
            )
            agent.move_to(self.random.choice(cells))

    def step(self):
        combos = find_combinations(
            self,
            list(self.agents),
            size=2,
            evaluation_func=alliance_value,
        )
        if combos:
            best = max(combos, key=lambda x: x[1])
            print(f"Best alliance value: {best[1]:.2f} "
                  f"between agents {[a.unique_id for a in best[0]]}")


if __name__ == "__main__":
    model = AllianceModel(n_agents=8)
    for i in range(3):
        print(f"Step {i+1}:")
        model.step()
