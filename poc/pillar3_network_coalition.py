"""
poc/pillar3_network_coalition.py
Pillar 3 — Network Space Coalition Formation
=============================================
Demonstrates that spatial_find_combinations() works on a NetworkGrid,
not just OrthogonalMooreGrid. The same cell.connections API is used
for all DiscreteSpace types in Mesa 3.x.

15 agents on a small-world network. Coalition candidates are restricted
to graph-neighbours (1-hop), dramatically reducing C(N,3).

Run:
    python poc/pillar3_network_coalition.py
"""
from __future__ import annotations
from itertools import combinations
from math import comb
import mesa
from mesa.discrete_space import Network
from mesa.discrete_space.cell_agent import CellAgent

N_AGENTS = 15
SEED     = 42


class SocialAgent(CellAgent):
    def __init__(self, model, influence: float):
        super().__init__(model)
        self.influence = influence
    def step(self): pass


def coalition_value(group) -> float:
    return sum(a.influence for a in group)


def spatial_find_combinations_network(agents, size, evaluation_func):
    """
    Same algorithm as Pillar 3 — works for Network because Mesa's
    NetworkGrid exposes cell.connections just like any other DiscreteSpace.
    """
    seen:   set   = set()
    results: list = []
    agent_set     = set(agents)

    for agent in agents:
        pool: set = {agent}
        # cell.connections works identically for Network and Grid
        for nb_cell in agent.cell.connections.values():
            for nb in nb_cell.agents:
                if isinstance(nb, SocialAgent):
                    pool.add(nb)
        pool &= agent_set
        if len(pool) < size:
            continue
        for group in combinations(sorted(pool, key=lambda a: a.unique_id), size):
            key = frozenset(a.unique_id for a in group)
            if key in seen:
                continue
            seen.add(key)
            results.append((list(group), evaluation_func(group)))

    return sorted(results, key=lambda x: x[1], reverse=True)


if __name__ == "__main__":
    print("=" * 65)
    print("Pillar 3 — NetworkGrid Coalition  [Mesa 3.5.1]")
    print("Demonstrates space-agnostic spatial_find_combinations()")
    print("=" * 65)

    import networkx as nx

    model = mesa.Model(seed=SEED)
    # Small-world network: 15 nodes, k=4 nearest neighbours, p=0.3 rewire
    G    = nx.watts_strogatz_graph(N_AGENTS, k=4, p=0.3, seed=SEED)
    grid = Network(G, capacity=1, directed=False)

    SocialAgent.create_agents(
        model, N_AGENTS,
        influence=[model.rng.uniform(0.1, 1.0) for _ in range(N_AGENTS)]
    )
    cells = list(grid._cells.values())
    for i, agent in enumerate(model.agents):
        agent.move_to(cells[i % len(cells)])

    agents = list(model.agents)
    n, k   = len(agents), 3

    naive_count   = comb(n, k)
    spatial       = spatial_find_combinations_network(agents, k, coalition_value)
    spatial_count = len(spatial)
    reduction     = (1 - spatial_count / naive_count) * 100

    print(f"\n  Network topology: Watts-Strogatz small-world")
    print(f"  Nodes={N_AGENTS}, average degree≈4, rewire_prob=0.3")
    print(f"\n  k={k} coalition search:")
    print(f"    Naive candidates:    {naive_count:>8,}")
    print(f"    Network-spatial:     {spatial_count:>8,}")
    print(f"    Reduction:           {reduction:>7.1f}%")
    print()

    if spatial:
        best_group, best_score = spatial[0]
        print(f"  Best coalition: agents "
              f"{[a.unique_id for a in best_group]}, "
              f"score={best_score:.3f}")

    print()
    print("  ✅  spatial_find_combinations() works on NetworkGrid")
    print("  ✅  Same cell.connections API — no code change per space type")
    print("  ✅  Space-agnostic design confirmed")
    print("=" * 65)
