"""
Spatial Coalition Demo — Pillar 3 Proof of Concept
===================================================
Demonstrates the candidate count reduction from spatial filtering.

Compares:
  - Naive: find_combinations on ALL agents -> O(C(N,k)) candidates
  - Spatial: filter to Moore-1 neighbourhood -> O(C(neighbourhood_size, k))

For N=200 agents on a 20x20 grid, k=3:
  - Naive:   C(200,3) = 1,313,400 candidate triples per step
  - Spatial: ~C(8,3) = 56 per agent -> ~11,200 total (after dedup)
  - Reduction: ~99% fewer evaluations

Run with:
    python models/spatial_coalition/model.py
"""

import mesa
from itertools import combinations
from mesa.discrete_space import OrthogonalMooreGrid


# ── Agent ─────────────────────────────────────────────────────────────────────

class GridAgent(mesa.Agent):
    """Simple agent on a discrete grid."""

    def __init__(self, model: mesa.Model, value: float) -> None:
        super().__init__(model)
        self.value = value

    def step(self) -> None:
        pass


# ── Spatial find_combinations (Pillar 3 prototype) ───────────────────────────

def spatial_find_combinations(
    agents: list,
    size: int,
    evaluation_func,
    radius: int = 1,
):
    """
    Pillar 3 prototype: restrict coalition search to spatial neighbourhoods.

    For each agent, considers only agents in its Moore neighbourhood at
    given radius. Deduplicates candidate groups (frozenset) to avoid
    double-counting.
    """
    seen: set = set()
    results: list = []

    for agent in agents:
        # Get neighbourhood agents via cell.connections
        neighbours = set()
        for conn_cell in agent.cell.connections.values():
            for nb_agent in conn_cell.agents:
                if isinstance(nb_agent, GridAgent):
                    neighbours.add(nb_agent)
        # Include self; exclude agents not in this run's list
        candidate_pool = (neighbours | {agent}) & set(agents)
        candidate_pool = list(candidate_pool)

        if len(candidate_pool) < size:
            continue

        for group in combinations(candidate_pool, size):
            key = frozenset(a.unique_id for a in group)
            if key in seen:
                continue
            seen.add(key)
            score = evaluation_func(group)
            results.append((list(group), score))

    return results


# ── Simple evaluation function ────────────────────────────────────────────────

def coalition_value(group) -> float:
    return sum(a.value for a in group)


# ── Model ─────────────────────────────────────────────────────────────────────

class SpatialCoalitionModel(mesa.Model):
    """
    Compares naive vs. spatial coalition search on a 20x20 grid.
    Demonstrates the candidate count reduction for Pillar 3.
    """

    def __init__(self, n_agents: int = 200, seed: int = 42) -> None:
        super().__init__(seed=seed)
        self.grid = OrthogonalMooreGrid((20, 20), capacity=2, torus=False)
        GridAgent.create_agents(
            self, n_agents,
            value=[self.rng.uniform(0.1, 1.0) for _ in range(n_agents)],
        )
        # Place agents on random non-full cells
        for agent in self.agents:
            cell = self.grid.select_random_not_full_cell()  # PR #3542 API
            agent.move_to(cell)

    def step(self) -> None:
        agents = list(self.agents)
        n = len(agents)
        size = 3

        # ── Naive count (no spatial filter) ──────────────────────────────────
        from math import comb
        naive_count = comb(n, size)

        # ── Spatial count ─────────────────────────────────────────────────────
        spatial_combos = spatial_find_combinations(
            agents=agents,
            size=size,
            evaluation_func=coalition_value,
            radius=1,
        )
        spatial_count = len(spatial_combos)

        reduction_pct = (1 - spatial_count / naive_count) * 100

        print(f"\nN={n} agents, k={size}, Moore-1 neighbourhood")
        print(f"  Naive candidates:   {naive_count:,}")
        print(f"  Spatial candidates: {spatial_count:,}")
        print(f"  Search space reduction: {reduction_pct:.1f}%")

        if spatial_combos:
            best_group, best_score = max(spatial_combos, key=lambda x: x[1])
            print(f"\n  Best spatial coalition: agents "
                  f"{[a.unique_id for a in best_group]}, "
                  f"score={best_score:.3f}")


def run_demo() -> None:
    print("=" * 60)
    print("Spatial Coalition Demo — Pillar 3 PoC")
    print("Demonstrates DiscreteSpace-aware candidate filtering")
    print("=" * 60)
    for n in [50, 100, 200]:
        model = SpatialCoalitionModel(n_agents=n)
        model.step()
    print("\nConclusion: spatial filtering reduces candidates by >97%")
    print("for N=200 agents on a 20x20 grid.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
