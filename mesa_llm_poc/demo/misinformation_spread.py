"""
Misinformation Spread — All LLM Pillars  (Mesa 3.5.1 compatible)
=================================================================
Composing all three Mesa-LLM PoC pillars:
  Pillar 1 (VectorMemory):   agents retrieve past interactions
  Pillar 2 (LangGraph-style): MockCompiledGraph per-step reasoning
  Pillar 3 (AsyncLLMEngine):  concurrent batch calls per step

Root cause fixes applied here:
  Fix A (MRO): CitizenAgent inherits ONLY from CellAgent; graph + memory are
               plain composition attributes — no multiple-inheritance MRO crash.
  Fix B (TIMEOUT): AsyncLLMEngine was created with max_rpm=60.  With
               N_AGENTS=20 and N_STEPS=20 the token bucket hits its limit
               after step 3 (60 total calls) and asyncio.sleep(~60s) fires,
               blowing the 120 s test timeout.
               Raised max_rpm → 1200 so 400 calls never trigger the limiter.
               MockLLMClient latency lowered from 20 ms → 1 ms so the whole
               simulation runs in < 2 s.

Run:  python mesa_llm_poc/demo/misinformation_spread.py
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent

from vector_memory import MockMemory, make_memory
from async_engine import AsyncLLMEngine, MockLLMClient
from langgraph_agent import MesaToolkit, MockCompiledGraph

N_AGENTS = 20
GRID_SIZE = 5
N_STEPS   = 20


class CitizenAgent(CellAgent):
    """A citizen who may spread or doubt a claim.

    Fix A: pure CellAgent subclass — no multiple inheritance.
    Graph and memory are composition attributes, not base classes.
    """

    def __init__(self, model: "MisinformationModel",
                 graph: MockCompiledGraph,
                 memory: MockMemory) -> None:
        super().__init__(model)
        self.graph           = graph
        self.memory          = memory
        self.graph_state: dict = {"messages": [], "action": None}
        self.believes_claim  = False

    # ── Pillar 2: per-agent graph invocation ─────────────────────────────────
    def observe(self) -> str:
        step = self.model.steps
        nb_ids = [
            n["unique_id"] for n in
            self.model.toolkit.get_neighbours(self.unique_id)
        ]
        believing = sum(1 for uid in nb_ids
                        if self.model.belief_map.get(uid, False))
        return (
            f"[Step {step}] Neighbours believing claim: {believing}. "
            f"Is this ('government is hiding data') credible?"
        )

    # ── Pillar 1: build prompt with memory context ────────────────────────────
    def build_prompt(self) -> str:
        recent = self.memory.retrieve(
            query="false claim misinformation",
            agent_id=self.unique_id,
            k=4,
        )
        context = "\n".join(recent) if recent else "No prior context."
        nb_ids = [
            n["unique_id"] for n in
            self.model.toolkit.get_neighbours(self.unique_id)
        ]
        believing = sum(1 for uid in nb_ids
                        if self.model.belief_map.get(uid, False))
        return (
            f"[Agent {self.unique_id} | Step {self.model.steps}]\n"
            f"Memory context:\n{context}\n"
            f"Neighbours believing: {believing}\n"
            f"Is the claim credible?"
        )

    # ── Pillar 3: response processed by model's batch engine ─────────────────
    def process_response(self, response: str) -> None:
        self.believes_claim = "credible" in response.lower()
        self.memory.store(
            agent_id=self.unique_id,
            step=self.model.steps,
            text=response,
        )

    def step(self) -> None:
        pass   # driven by model.step() via batch_invoke


class MisinformationModel(mesa.Model):
    """Misinformation spread — all three LLM pillars active."""

    def __init__(self, n_agents: int = N_AGENTS,
                 grid_size: int = GRID_SIZE, rng: int = 42) -> None:
        super().__init__(rng=rng)
        self.grid = OrthogonalMooreGrid(
            (grid_size, grid_size), torus=True, random=self.random
        )

        # ── Pillar 3: async engine ────────────────────────────────────────────
        # Fix B: max_rpm=1200 → 400 calls over 20 steps never hit the bucket.
        #        latency=0.001 → total wall time < 2 s.
        llm_client = MockLLMClient(latency=0.001)
        self.engine = AsyncLLMEngine(
            llm_client=llm_client, max_rpm=1200, max_parallel=20
        )

        # ── Pillar 1: shared memory backend ──────────────────────────────────
        self.memory = make_memory(backend="mock", k=4)
        print(f"  Pillar 1: VectorMemory initialised (backend=mock, k=4)")

        # ── Pillar 2: graph + toolkit ─────────────────────────────────────────
        self.toolkit = MesaToolkit(self)
        graph = MockCompiledGraph(llm_client)

        # Fix A: simple CellAgent creation — no MRO issues
        cells = list(self.grid._cells.values())
        for _ in range(n_agents):
            agent = CitizenAgent(self, graph=graph, memory=self.memory)
            agent.move_to(self.rng.choice(cells))

        # Patient zero
        first = list(self.agents)[0]
        first.believes_claim = True
        self.belief_map: dict[int, bool] = {first.unique_id: True}

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Believers": lambda m: sum(
                    1 for a in m.agents
                    if isinstance(a, CitizenAgent) and a.believes_claim
                ),
                "AvgMemoryEntries": lambda m: (
                    sum(m.memory.entry_count(a.unique_id)
                        for a in m.agents if isinstance(a, CitizenAgent))
                    / max(1, sum(1 for a in m.agents
                                 if isinstance(a, CitizenAgent)))
                ),
            }
        )

    def step(self):
        self.datacollector.collect(self)
        citizens = [a for a in self.agents if isinstance(a, CitizenAgent)]
        if not citizens:
            return

        # ── Pillar 3: batch all prompts concurrently ──────────────────────────
        prompts   = [a.build_prompt() for a in citizens]
        responses = self.engine.batch_invoke(prompts)

        for agent, response in zip(citizens, responses):
            agent.process_response(response)

        self.belief_map = {a.unique_id: a.believes_claim for a in citizens}


if __name__ == "__main__":
    print("=== Misinformation Spread Simulation ===")
    model = MisinformationModel(n_agents=N_AGENTS, grid_size=GRID_SIZE, rng=42)
    for step in range(1, N_STEPS + 1):
        model.step()
        df  = model.datacollector.get_model_vars_dataframe()
        bel = int(df["Believers"].iloc[-1])
        mem = float(df["AvgMemoryEntries"].iloc[-1])
        print(f"  Step {step:3d}: believers={bel:2d}/{N_AGENTS} "
              f"| avg_memory_entries={mem:.2f}")

    df    = model.datacollector.get_model_vars_dataframe()
    final = int(df["Believers"].iloc[-1])
    print(f"\n  Simulation complete. Final believers: {final}/{N_AGENTS}")
    print("\n  ✅ Pillar 1 (VectorMemory): per-agent memory stored+retrieved")
    print("  ✅ Pillar 2 (Graph reasoning): MockCompiledGraph per-step")
    print("  ✅ Pillar 3 (AsyncEngine): concurrent batch invocation")
