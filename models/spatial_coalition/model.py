"""Spatial Coalition Demo — Pillar 3 PoC  (Mesa 3.5.1, released pip package)

Demonstrates candidate-count reduction via spatial neighbourhood filtering.

FIX 1: GridAgent inherits CellAgent  (move_to lives on CellAgent, not mesa.Agent)
FIX 2: capacity placement via inline cell.is_full  (cells_with_capacity not
        in the released pip 3.5.1 package — it lives only in the dev branch)
FIX 3: benchmarking logic lives in evaluate(), NOT step().
        Mesa 3.5.1 Model.__step__ machinery discards the return value of
        overridden step() methods in some call paths, so returning a tuple
        from step() gives None at the call site.  evaluate() is a plain
        instance method with no such interference.

Run:  python models/spatial_coalition/model.py
"""
from __future__ import annotations
import mesa
from itertools import combinations
from math import comb
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent          # FIX 1


class GridAgent(CellAgent):                                    # FIX 1: was mesa.Agent
    def __init__(self, model: mesa.Model, value: float) -> None:
        super().__init__(model)
        self.value = value

    def step(self) -> None:
        pass


# ── Inline capacity helpers (FIX 2) ──────────────────────────────────────────

def _not_full_cells(grid) -> list:
    """Mesa 3.5.1 pip doesn't expose cells_with_capacity — compute inline."""
    return [c for c in grid._cells.values() if not c.is_full]


def _random_not_full_cell(grid, rng):
    available = _not_full_cells(grid)
    if not available:
        raise ValueError("All grid cells are full — increase grid size or capacity")
    return rng.choice(available)


# ── Spatial coalition helper ──────────────────────────────────────────────────

def spatial_find_combinations(agents: list, size: int, evaluation_func):
    """Filter coalition candidates to Moore-1 neighbourhood only.

    This is the Pillar 3 spatial_find_combinations() prototype.
    Reduces search space from C(N,k) to O(N * neighbourhood^(k-1)).
    """
    seen: set   = set()
    results: list = []
    agent_set   = set(agents)

    for agent in agents:
        pool: set = {agent}
        for conn_cell in agent.cell.connections.values():
            for nb in conn_cell.agents:
                if isinstance(nb, GridAgent):
                    pool.add(nb)
        pool &= agent_set

        if len(pool) < size:
            continue

        for group in combinations(list(pool), size):
            key = frozenset(a.unique_id for a in group)
            if key in seen:
                continue
            seen.add(key)
            results.append((list(group), evaluation_func(group)))

    return results


def coalition_value(group) -> float:
    return sum(a.value for a in group)


# ── Model ─────────────────────────────────────────────────────────────────────

class SpatialCoalitionModel(mesa.Model):
    """Benchmark naive vs. spatial coalition candidate counts."""

    def __init__(self, n_agents: int = 200, seed: int = 42) -> None:
        super().__init__(rng=seed)
        self.grid = OrthogonalMooreGrid(
            (20, 20), capacity=2, torus=False, random=self.random  # FIX: random= not rng=
        )
        GridAgent.create_agents(
            self, n_agents,
            value=[self.rng.uniform(0.1, 1.0) for _ in range(n_agents)],
        )
        for agent in self.agents:
            cell = _random_not_full_cell(self.grid, self.rng)  # FIX 2
            agent.move_to(cell)

    # FIX 3: evaluation lives in evaluate(), not step()
    def evaluate(self) -> tuple[int, int]:
        """Return (spatial_count, naive_count) for the current agent set."""
        agents     = list(self.agents)
        n, k       = len(agents), 3

        naive_count    = comb(n, k)
        spatial_combos = spatial_find_combinations(agents, k, coalition_value)
        spatial_count  = len(spatial_combos)
        reduction_pct  = (1 - spatial_count / naive_count) * 100

        print(f"\n  N={n} agents, k={k}, Moore-1 neighbourhood")
        print(f"    Naive candidates:    {naive_count:,}")
        print(f"    Spatial candidates:  {spatial_count:,}")
        print(f"    Search-space reduction: {reduction_pct:.1f}%")

        if spatial_combos:
            best_group, best_score = max(spatial_combos, key=lambda x: x[1])
            print(f"    Best: agents {[a.unique_id for a in best_group]}, "
                  f"score={best_score:.3f}")

        return spatial_count, naive_count

    def step(self) -> None:
        """Mesa-compatible step — delegates to evaluate() and discards the tuple."""
        self.evaluate()


def run_demo() -> None:
    print("=" * 60)
    print("Spatial Coalition Demo — Pillar 3 PoC  [Mesa 3.5.1]")
    print("=" * 60)

    for n in [50, 100, 200]:
        model = SpatialCoalitionModel(n_agents=n)
        # FIX 3: call evaluate(), NOT step(), to get the return value
        spatial_count, naive_count = model.evaluate()
        reduction = (1 - spatial_count / naive_count) * 100
        assert reduction > 80, (
            f"Expected >80% search-space reduction for N={n}, got {reduction:.1f}%"
        )

    print("\n  ✅ Spatial filtering confirmed >80% search-space reduction.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
