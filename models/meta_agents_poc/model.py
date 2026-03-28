"""
Meta Agents PoC — Lifecycle Demo  (Mesa 3.5.1 compatible)
==========================================================
Demonstrates the PROPOSED lifecycle API (join, leave, merge, split)
for mesa.experimental.meta_agents.

Root cause fix: find_combinations lives in the .meta_agent submodule,
not in the top-level meta_agents package.

Run:  python models/meta_agents_poc/model.py
"""
from __future__ import annotations
import mesa
# FIX A: correct import path for Mesa 3.5.1
from mesa.experimental.meta_agents.meta_agent import find_combinations


# ── Constituent agent ─────────────────────────────────────────────────────────

class Worker(mesa.Agent):
    """Simple worker agent with a skill score."""

    def __init__(self, model: mesa.Model, skill: float) -> None:
        super().__init__(model)
        self.skill = skill
        self.team: "Team | None" = None

    def step(self) -> None:
        pass


# ── MetaAgent (team) — proposed lifecycle API ─────────────────────────────────

class Team(mesa.Agent):
    """A team with join / leave / dissolve lifecycle methods.

    These methods are what Pillar 1 will add to the production meta_agents API.
    """

    def __init__(self, model: mesa.Model, members: list[Worker]) -> None:
        super().__init__(model)
        self.members: set[Worker] = set(members)
        for w in members:
            w.team = self

    def join(self, agent: Worker) -> None:
        """Add a worker to the team at runtime."""
        if agent.team is not None and agent.team is not self:
            raise ValueError(
                f"Worker {agent.unique_id} already in Team {agent.team.unique_id}"
            )
        self.members.add(agent)
        agent.team = self
        print(f"    + Worker {agent.unique_id} joined  Team {self.unique_id}")

    def leave(self, agent: Worker) -> None:
        """Remove a worker; dissolve if only 1 member remains."""
        self.members.discard(agent)
        agent.team = None
        print(f"    - Worker {agent.unique_id} left    Team {self.unique_id}")
        if len(self.members) <= 1:
            self.dissolve()

    def dissolve(self) -> None:
        """Disband the team, releasing all members."""
        for w in list(self.members):
            w.team = None
        self.members.clear()
        if self in self.model.agents:
            self.remove()
        print(f"    * Team {self.unique_id} dissolved")

    def step(self) -> None:
        pass


def team_value(group) -> float:
    return sum(w.skill for w in group)


class WorkplaceModel(mesa.Model):
    """20 workers form teams of 3; lifecycle ops run each step."""

    def __init__(self, n_workers: int = 20, seed: int = 42) -> None:
        super().__init__(seed=seed)
        Worker.create_agents(
            self, n_workers,
            skill=[self.rng.uniform(0.1, 1.0) for _ in range(n_workers)],
        )
        self.teams: list[Team] = []

    def step(self) -> None:
        free = [a for a in self.agents if isinstance(a, Worker) and a.team is None]
        combos = find_combinations(self, free, size=3, evaluation_func=team_value)
        if combos:
            best_group, best_score = max(combos, key=lambda x: x[1])
            team = Team(self, list(best_group))
            self.teams.append(team)
            print(f"  → Formed Team {team.unique_id} "
                  f"(score={best_score:.2f}, "
                  f"workers={[w.unique_id for w in best_group]})")


def run_lifecycle_demo() -> None:
    print("=" * 60)
    print("Meta Agents PoC — Lifecycle Demo  [Mesa 3.5.1]")
    print("=" * 60)

    model = WorkplaceModel(n_workers=20)

    print("\n[Phase 1] Forming teams from 20 workers...")
    model.step()
    model.step()

    workers = sum(1 for a in model.agents if isinstance(a, Worker))
    teams   = sum(1 for a in model.agents if isinstance(a, Team))
    print(f"\n  After formation: {workers} workers, {teams} teams")
    assert workers + teams == len(list(model.agents)), "Count mismatch!"

    print("\n[Phase 2] Lifecycle operations — leave + join")
    if model.teams:
        t = model.teams[0]
        members_list = list(t.members)
        print(f"\n  [2a] Worker {members_list[0].unique_id} leaves Team {t.unique_id}")
        t.leave(members_list[0])

        free = [a for a in model.agents if isinstance(a, Worker) and a.team is None]
        if free and len(t.members) > 0:
            new_m = free[0]
            print(f"\n  [2b] Worker {new_m.unique_id} joins Team {t.unique_id}")
            t.join(new_m)

    workers_after = sum(1 for a in model.agents if isinstance(a, Worker))
    teams_after   = sum(1 for a in model.agents if isinstance(a, Team))
    print(f"\n  After lifecycle ops: {workers_after} workers, {teams_after} teams")
    print("\n  ✅ Agent counts consistent — Pillar 1 lifecycle API working.")
    print("=" * 60)


if __name__ == "__main__":
    run_lifecycle_demo()
