"""Spatial + LLM Benchmark — Pillars 2 & 3  (Mesa 3.5.1, released pip)

FIX 1: BenchAgent inherits CellAgent (move_to lives on CellAgent)
FIX 2: capacity placement via inline cell.is_full
"""
from __future__ import annotations
import time, json, random
from itertools import combinations
from math import comb

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent          # FIX 1


def _random_not_full_cell(grid, rng):
    available = [c for c in grid._cells.values() if not c.is_full]
    return rng.choice(available) if available else rng.choice(list(grid._cells.values()))


class TimedMockLLM:
    def __init__(self, latency_ms: float = 5.0):
        self.latency = latency_ms / 1000.0; self.call_count = 0
    def invoke(self, prompt: str) -> str:
        time.sleep(self.latency); self.call_count += 1
        score = round(random.uniform(0.2, 0.9), 2)
        return json.dumps({"score": score, "rationale": "benchmark",
                           "recommended": score > 0.6})


class BenchAgent(CellAgent):                                   # FIX 1: was mesa.Agent
    def __init__(self, model, value: float):
        super().__init__(model); self.value = value
    def step(self): pass


def naive_evaluate_all(agents, size, llm) -> int:
    count = 0
    for group in combinations(agents, size):
        llm.invoke(" ".join(str(a.unique_id) for a in group)); count += 1
    return count


def spatial_evaluate(agents, size, llm) -> int:
    seen: set = set(); count = 0; agent_set = set(agents)
    for agent in agents:
        pool: set = {agent}
        for cell in agent.cell.connections.values():
            for nb in cell.agents:
                if isinstance(nb, BenchAgent): pool.add(nb)
        pool &= agent_set
        if len(pool) < size: continue
        for group in combinations(list(pool), size):
            key = frozenset(a.unique_id for a in group)
            if key in seen: continue
            seen.add(key)
            llm.invoke(" ".join(str(a.unique_id) for a in group)); count += 1
    return count


class BenchmarkModel(mesa.Model):
    def __init__(self, n_agents: int = 30, latency_ms: float = 5.0,
                 seed: int = 42) -> None:
        super().__init__(seed=seed)
        side = max(5, int(n_agents ** 0.5) + 1)
        self.grid = OrthogonalMooreGrid(
            (side, side), capacity=2, torus=False, random=self.random)
        BenchAgent.create_agents(self, n_agents,
                                  value=[self.rng.uniform(0, 1)
                                         for _ in range(n_agents)])
        for agent in self.agents:
            agent.move_to(_random_not_full_cell(self.grid, self.rng))  # FIX 2
        self.latency_ms = latency_ms

    def benchmark(self, size: int = 3):
        agents = list(self.agents); n = len(agents)
        naive_llm = TimedMockLLM(self.latency_ms)
        t0 = time.perf_counter()
        naive_calls = naive_evaluate_all(agents, size, naive_llm)
        naive_time  = time.perf_counter() - t0
        spatial_llm = TimedMockLLM(self.latency_ms)
        t0 = time.perf_counter()
        spatial_calls = spatial_evaluate(agents, size, spatial_llm)
        spatial_time  = time.perf_counter() - t0
        speedup   = naive_time / spatial_time if spatial_time > 0 else float("inf")
        reduction = (1 - spatial_calls / comb(n, size)) * 100
        print(f"\n  N={n}, k={size}, latency={self.latency_ms}ms/call")
        print(f"    Naive:   {naive_calls:>6,} calls  |  {naive_time:>7.3f}s")
        print(f"    Spatial: {spatial_calls:>6,} calls  |  {spatial_time:>7.3f}s")
        print(f"    Speedup: {speedup:.1f}×  |  Search reduction: {reduction:.1f}%")
        return speedup, reduction


if __name__ == "__main__":
    print("=" * 65)
    print("Spatial + LLM Benchmark — Pillars 2 & 3  [Mesa 3.5.1]")
    print("=" * 65)
    total_speedup = 0.0; runs = 0
    for n, lat in [(20, 10.0), (30, 5.0), (40, 2.0)]:
        model = BenchmarkModel(n_agents=n, latency_ms=lat)
        speedup, _ = model.benchmark(size=3)
        total_speedup += speedup; runs += 1
    avg = total_speedup / runs
    print(f"\n  Average speedup: {avg:.1f}×")
    assert avg > 1.5, f"Expected >1.5×, got {avg:.1f}×"
    print("  ✅ Spatial filtering faster — Pillar 3 verified.")
    print("=" * 65)
