"""
Coalition Stability Tracker — Extended Pillar 1 PoC  (Mesa 3.5.1)
==================================================================
Tracks coalition birth, lifetime, and dissolution across 30 steps.
Adds merge (two teams combining) to the lifecycle API.

Demonstrates:
  - Multi-step coalition dynamics with DataCollector
  - merge() as the fourth lifecycle method (join, leave, dissolve, merge)
  - Stability metric: fraction of coalitions surviving to step T

Run:  python models/coalition_stability/model.py
"""
from __future__ import annotations
import mesa
from mesa.experimental.meta_agents.meta_agent import find_combinations


class Worker(mesa.Agent):
    def __init__(self, model, skill: float) -> None:
        super().__init__(model)
        self.skill  = skill
        self.team: "Coalition | None" = None

    def step(self) -> None:
        # Skill drifts slightly each step
        self.skill = max(0.1, min(1.0,
            self.skill + float(self.model.rng.normal(0, 0.05))))


class Coalition(mesa.Agent):
    """MetaAgent with join / leave / dissolve / merge lifecycle."""

    def __init__(self, model, members: list[Worker]) -> None:
        super().__init__(model)
        self.members: set[Worker] = set(members)
        self.birth_step: int = model.steps
        for w in members:
            w.team = self

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def total_skill(self) -> float:
        return sum(w.skill for w in self.members)

    def join(self, worker: Worker) -> None:
        self.members.add(worker)
        worker.team = self

    def leave(self, worker: Worker) -> None:
        self.members.discard(worker)
        worker.team = None
        if self.size <= 1:
            self.dissolve()

    def dissolve(self) -> None:
        for w in list(self.members):
            w.team = None
        self.members.clear()
        if self in self.model.agents:
            self.remove()

    def merge(self, other: "Coalition") -> None:
        """Absorb another coalition; other is dissolved."""
        for w in list(other.members):
            other.members.discard(w)
            w.team = self
            self.members.add(w)
        if other in self.model.agents:
            other.remove()

    def step(self) -> None:
        # Coalitions with < 2 members dissolve naturally
        if self.size < 2:
            self.dissolve()


def team_value(group) -> float:
    return sum(w.skill for w in group)


class StabilityModel(mesa.Model):
    def __init__(self, n_workers: int = 30, seed: int = 42) -> None:
        super().__init__(seed=seed)
        Worker.create_agents(
            self, n_workers,
            skill=[self.rng.uniform(0.3, 1.0) for _ in range(n_workers)],
        )
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Coalitions": lambda m: sum(
                    1 for a in m.agents if isinstance(a, Coalition)),
                "FreeWorkers": lambda m: sum(
                    1 for a in m.agents
                    if isinstance(a, Worker) and a.team is None),
                "AvgCoalitionSize": lambda m: (
                    (sum(a.size for a in m.agents if isinstance(a, Coalition))
                     / max(1, sum(1 for a in m.agents if isinstance(a, Coalition))))
                ),
                "AvgCoalitionSkill": lambda m: (
                    (sum(a.total_skill for a in m.agents if isinstance(a, Coalition))
                     / max(1, sum(1 for a in m.agents if isinstance(a, Coalition))))
                ),
            }
        )

    def step(self) -> None:
        self.datacollector.collect(self)

        # 1. Workers update skills
        for w in [a for a in self.agents if isinstance(a, Worker)]:
            w.step()

        # 2. Existing coalitions may self-dissolve
        for c in [a for a in self.agents if isinstance(a, Coalition)]:
            c.step()

        # 3. Try to merge two smallest coalitions
        coalitions = sorted(
            [a for a in self.agents if isinstance(a, Coalition)],
            key=lambda c: c.total_skill
        )
        if len(coalitions) >= 2:
            c1, c2 = coalitions[0], coalitions[1]
            if c1 in self.agents and c2 in self.agents:
                c1.merge(c2)

        # 4. Form new coalitions from free workers
        free = [a for a in self.agents
                if isinstance(a, Worker) and a.team is None]
        if len(free) >= 3:
            combos = find_combinations(self, free, size=3,
                                       evaluation_func=team_value)
            if combos:
                best_group, _ = max(combos, key=lambda x: x[1])
                Coalition(self, list(best_group))


if __name__ == "__main__":
    print("=" * 60)
    print("Coalition Stability Tracker — Extended Pillar 1 PoC")
    print("=" * 60)
    model = StabilityModel(n_workers=30)
    for step in range(1, 31):
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    print(f"\n{'Step':>5} {'Coalitions':>12} {'FreeWorkers':>12} "
          f"{'AvgSize':>9} {'AvgSkill':>9}")
    print("-" * 55)
    for i, row in df.iterrows():
        print(f"  {i+1:3d}  {int(row['Coalitions']):>12}  "
              f"{int(row['FreeWorkers']):>12}  "
              f"{row['AvgCoalitionSize']:>9.2f}  "
              f"{row['AvgCoalitionSkill']:>9.2f}")
    print("\n  ✅ Coalition lifecycle (join/leave/dissolve/merge) across 30 steps.")
    print("=" * 60)
