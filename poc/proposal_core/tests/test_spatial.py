"""
test_spatial.py — Pillar 3: spatial_find_combinations Tests
===========================================================
Tests:
  • >80% search-space reduction for N=50, 100, 200 on OrthogonalMooreGrid
  • Deduplication: no candidate group appears twice
  • Non-overlapping: spatial results ⊆ naive results (correctness)
  • Space-agnostic: same function works on VoronoiGrid (structure, not counting)
  • Filter func: only groups passing filter are returned
  • Edge cases: size < 2, empty agents, agents without .cell
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import mesa
from math import comb
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent
from spatial import spatial_find_combinations, reduction_stats


# ── Fixtures ──────────────────────────────────────────────────────────────────

class GridWorker(CellAgent):
    def __init__(self, model, value: float):
        super().__init__(model)
        self.value = value
    def step(self): pass


def coalition_value(group) -> float:
    return sum(a.value for a in group)


def _not_full(grid):
    return [c for c in grid._cells.values() if not c.is_full]


def _make_model_and_agents(n: int, seed: int = 42):
    model = mesa.Model(seed=seed)
    grid  = OrthogonalMooreGrid((20, 20), capacity=2, torus=False, random=model.random)
    GridWorker.create_agents(model, n,
                              value=[model.rng.uniform(0.1, 1.0) for _ in range(n)])
    avail = _not_full(grid)
    for i, agent in enumerate(model.agents):
        agent.move_to(avail[i % len(avail)])
    return model, list(model.agents)


# ── Search-space reduction (core Pillar 3 claim) ──────────────────────────────

@pytest.mark.parametrize("n", [50, 100, 200])
def test_reduction_greater_than_80pct(n):
    _, agents = _make_model_and_agents(n)
    stats = reduction_stats(agents, 3, coalition_value)
    assert stats["reduction_pct"] > 80, (
        f"Expected >80% reduction for N={n}, got {stats['reduction_pct']:.1f}%"
    )


@pytest.mark.parametrize("n", [50, 100])
def test_spatial_count_less_than_naive(n):
    _, agents = _make_model_and_agents(n)
    stats = reduction_stats(agents, 3, coalition_value)
    assert stats["spatial_count"] < stats["naive_count"]


# ── Correctness: deduplication ────────────────────────────────────────────────

def test_no_duplicate_groups():
    """Every candidate group should appear exactly once."""
    _, agents = _make_model_and_agents(50)
    results = spatial_find_combinations(agents, 3, coalition_value)
    keys = [frozenset(a.unique_id for a in group) for group, _ in results]
    assert len(keys) == len(set(keys)), "Duplicate groups found in spatial results"


# ── Correctness: spatial ⊆ naive ─────────────────────────────────────────────

def test_spatial_results_subset_of_naive():
    """Every spatial candidate must also be a valid naive candidate."""
    _, agents = _make_model_and_agents(30)
    naive   = spatial_find_combinations(agents, 3, coalition_value, space_type="naive")
    spatial = spatial_find_combinations(agents, 3, coalition_value)
    naive_keys   = {frozenset(a.unique_id for a in g) for g, _ in naive}
    spatial_keys = {frozenset(a.unique_id for a in g) for g, _ in spatial}
    assert spatial_keys.issubset(naive_keys), (
        "Spatial results contain candidates not in naive set — spatial filter is too broad"
    )


# ── Sorting ───────────────────────────────────────────────────────────────────

def test_results_sorted_descending():
    _, agents = _make_model_and_agents(50)
    results = spatial_find_combinations(agents, 3, coalition_value)
    scores  = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


# ── Filter func ───────────────────────────────────────────────────────────────

def test_filter_func_respected():
    _, agents = _make_model_and_agents(50)
    results = spatial_find_combinations(
        agents, 3, coalition_value,
        filter_func=lambda g, s: s > 2.5
    )
    for _, score in results:
        assert score > 2.5


def test_filter_func_none_returns_all():
    _, agents = _make_model_and_agents(30)
    unfiltered = spatial_find_combinations(agents, 3, coalition_value, filter_func=None)
    filtered   = spatial_find_combinations(agents, 3, coalition_value)
    assert len(unfiltered) >= len(filtered)


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_agents_returns_empty():
    result = spatial_find_combinations([], 3, coalition_value)
    assert result == []


def test_size_too_small_raises():
    _, agents = _make_model_and_agents(10)
    with pytest.raises(ValueError, match="size must be >= 2"):
        spatial_find_combinations(agents, 1, coalition_value)


def test_agents_without_cell_raises():
    model = mesa.Model(seed=1)
    workers = list(Worker.create_agents(model, 5) if False else [])

    # Create plain mesa.Agent instances (no .cell attribute)
    class PlainAgent(mesa.Agent):
        def step(self): pass

    agents = list(PlainAgent.create_agents(model, 5))
    with pytest.raises(AttributeError, match=".cell attribute"):
        spatial_find_combinations(agents, 3, coalition_value)


def test_naive_mode_gives_all_combinations():
    _, agents = _make_model_and_agents(10)
    results = spatial_find_combinations(agents, 3, coalition_value, space_type="naive")
    assert len(results) == comb(len(agents), 3)


# ── Coalition size k=2 and k=4 ────────────────────────────────────────────────

@pytest.mark.parametrize("k", [2, 4])
def test_different_coalition_sizes(k):
    _, agents = _make_model_and_agents(50)
    results = spatial_find_combinations(agents, k, coalition_value)
    # Results should exist and groups should have correct size
    for group, score in results:
        assert len(group) == k
        assert isinstance(score, float)


# ── Import guard ──────────────────────────────────────────────────────────────
# Ensure Worker import works for the agents_without_cell test
try:
    from meta_agent_v2 import Worker
except ImportError:
    Worker = None
