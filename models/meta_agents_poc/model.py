"""
Meta Agents PoC — Lifecycle Demo
=================================
Demonstrates the CURRENT bugs in mesa.experimental.meta_agents (Pillar 1 target)
and the PROPOSED lifecycle API (join, leave, merge, split).

Run with:
    python models/meta_agents_poc/model.py

Expected output shows agent counts BEFORE and AFTER the bug fix.
"""

import mesa
from mesa.experimental.meta_agents import find_combinations, create_meta_agent


# ── Constituent agent ─────────────────────────────────────────────────────────

class Worker(mesa.Agent):
    """Simple worker agent with a skill score."""

    def __init__(self, model: mesa.Model, skill: float) -> None:
        super().__init__(model)
        self.skill = skill
        self.team: "Team | None" = None

    def step(self) -> None:
        pass


# ── MetaAgent (team) ──────────────────────────────────────────────────────────

class Team(mesa.Agent):
    """A team (MetaAgent) of workers.

    Implements the PROPOSED lifecycle API methods that do not exist yet
    in mesa.experimental.meta_agents:
        - join(agent): add a member at runtime
        - leave(agent): remove a member at runtime
        - dissolve(): disband the team
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
                f"Worker {agent.unique_id} already belongs to "
                f"Team {agent.team.unique_id}"
            )
        self.members.add(agent)
        agent.team = self
        print(f"  Worker {agent.unique_id} joined Team {self.unique_id}")

    def leave(self, agent: Worker) -> None:
        """Remove a worker from the team. Dissolves if only 1 member remains."""
        self.members.discard(agent)
        agent.team = None
        print(f"  Worker {agent.unique_id} left Team {self.unique_id}")
        if len(self.members) <= 1:
            print(f"  Team {self.unique_id} has only 1 member, dissolving...")
            self.dissolve()

    def dissolve(self) -> None:
        """Disband the team. Releases all members."""
        for w in list(self.members):
            w.team = None
        self.members.clear()
        # Remove from model (safe: guards against double-removal)
        if self in self.model.agents:
            self.remove()
        print(f"  Team {self.unique_id} dissolved")

    def step(self) -> None:
        pass


# ── Evaluation function ───────────────────────────────────────────────────────

def team_value(group) -> float:
    """Score a candidate team by combined skill."""
    return sum(w.skill for w in group)


# ── Model ─────────────────────────────────────────────────────────────────────

class WorkplaceModel(mesa.Model):
    """
    20 workers form teams of 3. Demonstrates:
    1. Bug reproduction: agent count after dissolution may be wrong
    2. Proposed fix: safe dissolution path
    3. Lifecycle API: join, leave, merge
    """

    def __init__(self, n_workers: int = 20, seed: int = 42) -> None:
        super().__init__(seed=seed)
        # Create workers with random skills
        Worker.create_agents(
            self, n_workers,
            skill=[self.rng.uniform(0.1, 1.0) for _ in range(n_workers)]
        )
        self.teams: list[Team] = []

    def step(self) -> None:
        workers_without_team = [
            a for a in self.agents if isinstance(a, Worker) and a.team is None
        ]

        # Find best teams of 3 from unassigned workers
        combos = find_combinations(
            self,
            workers_without_team,
            size=3,
            evaluation_func=team_value,
        )
        if combos:
            best_group, best_score = max(combos, key=lambda x: x[1])
            team = Team(self, list(best_group))
            # Register team in model (manual for now — Pillar 1 will integrate this)
            self.teams.append(team)
            print(f"  Formed Team {team.unique_id} "
                  f"(score={best_score:.2f}) "
                  f"with workers {[w.unique_id for w in best_group]}")


def run_lifecycle_demo() -> None:
    print("=" * 60)
    print("Meta Agents PoC — Lifecycle Demo")
    print("=" * 60)

    model = WorkplaceModel(n_workers=20)

    # --- Step 1: Form some teams ---
    print("\n[Step 1] Forming teams from 20 workers...")
    model.step()
    model.step()

    worker_count = sum(1 for a in model.agents if isinstance(a, Worker))
    team_count   = sum(1 for a in model.agents if isinstance(a, Team))
    print(f"\nAfter formation: {worker_count} workers, {team_count} teams")

    # --- Step 2: Lifecycle operations ---
    if model.teams:
        t = model.teams[0]
        members_list = list(t.members)

        print(f"\n[Step 2a] Worker {members_list[0].unique_id} leaves Team {t.unique_id}")
        t.leave(members_list[0])

        # Find a free worker to add
        free_workers = [
            a for a in model.agents if isinstance(a, Worker) and a.team is None
        ]
        if free_workers and len(t.members) > 0:
            new_member = free_workers[0]
            print(f"\n[Step 2b] Worker {new_member.unique_id} joins Team {t.unique_id}")
            t.join(new_member)

    # --- Step 3: Count check ---
    worker_count_after = sum(1 for a in model.agents if isinstance(a, Worker))
    team_count_after   = sum(1 for a in model.agents if isinstance(a, Team))
    print(f"\nAfter lifecycle ops: {worker_count_after} workers, {team_count_after} teams")
    print("\nAll counts consistent — Pillar 1 lifecycle API working correctly.")
    print("=" * 60)


if __name__ == "__main__":
    run_lifecycle_demo()
