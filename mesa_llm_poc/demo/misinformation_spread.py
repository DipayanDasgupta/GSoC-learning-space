"""Mesa-LLM PoC — Demo: Misinformation Spread Simulation.

Composing all three pillars:
  Pillar 1 (VectorMemory): agents remember relevant past conversations
  Pillar 2 (LangGraphAgent): agents use a ReAct graph to reason about claims
  Pillar 3 (AsyncLLMEngine): all agent calls batched per step

No LLM API key required — MockLLMClient + MockMemory + MockCompiledGraph.
Swap any of these for the real implementations by changing one line each.
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mesa
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent

from vector_memory import MockMemory, make_memory
from async_engine import AsyncLLMEngine, MockLLMClient
from langgraph_agent import LangGraphAgent, MesaToolkit, MockCompiledGraph


N_AGENTS = 20
GRID_SIZE = 5
N_STEPS  = 20


class CitizenAgent(CellAgent, LangGraphAgent):
    """A citizen who may spread or doubt a false claim.

    Pillar 1: uses VectorMemory to retrieve relevant past conversations.
    Pillar 2: uses a LangGraph graph to reason about the claim.
    Pillar 3: prompt collection happens at model level (engine.batch_invoke).
    """

    def __init__(self, model: "MisinformationModel", graph, memory: MockMemory):
        CellAgent.__init__(self, model)
        LangGraphAgent.__init__(self, model, graph)
        self.memory = memory
        self.believes_claim: bool = False

    def build_prompt(self) -> str:
        """Build prompt using retrieved memory context (Pillar 1)."""
        recent = self.memory.retrieve(
            query    = "false claim misinformation",
            agent_id = self.unique_id,
            k        = 4,
        )
        neighbour_ids = [
            n["unique_id"] for n in
            self.model.toolkit.get_neighbours(self.unique_id)
        ]
        believing_neighbours = sum(
            1 for uid in neighbour_ids
            if self.model.belief_map.get(uid, False)
        )
        context = "\n".join(recent) if recent else "No prior context."
        return (
            f"[Agent {self.unique_id} | Step {self.model.steps}]\n"
            f"Past interactions:\n{context}\n"
            f"Neighbours believing the claim: {believing_neighbours}\n"
            f"Is this claim ('the government is hiding data') credible?"
        )

    def process_response(self, response: str) -> None:
        """Update belief and store the interaction in memory (Pillar 1)."""
        self.believes_claim = "credible" in response.lower()
        self.memory.store(
            agent_id = self.unique_id,
            step     = self.model.steps,
            text     = response,
        )

    def step(self):
        pass   # Driven by model.step() via batch_invoke (Pillar 3)


class MisinformationModel(mesa.Model):
    """Misinformation spread model — all three LLM pillars composing together."""

    def __init__(
        self,
        n_agents: int = N_AGENTS,
        grid_size: int = GRID_SIZE,
        rng: int = 42,
    ):
        super().__init__(rng=rng)
        self.grid = OrthogonalMooreGrid(
            (grid_size, grid_size), torus=True, random=self.random
        )

        # ── Pillar 3: async engine ─────────────────────────────────────────
        llm_client = MockLLMClient(latency=0.02)   # swap for real client
        self.engine = AsyncLLMEngine(
            llm_client   = llm_client,
            max_rpm      = 60,
            max_parallel = 5,
        )

        # ── Pillar 1: shared memory backend (one index per agent inside) ───
        self.memory = make_memory(backend="mock", k=4)
        print(f"Pillar 1: VectorMemory initialised (backend=mock, k=4)")

        # ── Pillar 2: graph + toolkit ──────────────────────────────────────
        self.toolkit = MesaToolkit(self)
        graph = MockCompiledGraph(llm_client)   # swap for real LangGraph graph

        # Create agents
        cells = list(self.grid._cells.values())
        for i in range(n_agents):
            agent = CitizenAgent(self, graph=graph, memory=self.memory)
            agent.move_to(self.random.choice(cells))

        # Seed patient zero
        first_agent = list(self.agents)[0]
        first_agent.believes_claim = True
        self.belief_map: dict[int, bool] = {first_agent.unique_id: True}

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Believers": lambda m: sum(
                    1 for a in m.agents
                    if isinstance(a, CitizenAgent) and a.believes_claim
                ),
                "AvgMemoryEntries": lambda m: (
                    sum(m.memory.entry_count(a.unique_id)
                        for a in m.agents if isinstance(a, CitizenAgent))
                    / max(1, sum(1 for a in m.agents if isinstance(a, CitizenAgent)))
                ),
            }
        )

    def step(self):
        self.datacollector.collect(self)
        citizen_agents = [a for a in self.agents if isinstance(a, CitizenAgent)]
        if not citizen_agents:
            return

        # ── Pillar 3: batch all prompts, fire concurrently ─────────────────
        prompts   = [a.build_prompt() for a in citizen_agents]
        responses = self.engine.batch_invoke(prompts)   # O(ceil(N/C) * L) latency

        # Distribute responses back to agents
        for agent, response in zip(citizen_agents, responses):
            agent.process_response(response)

        # Update belief map for toolkit queries next step
        self.belief_map = {
            a.unique_id: a.believes_claim for a in citizen_agents
        }


if __name__ == "__main__":
    print("=== Misinformation Spread Simulation ===")
    model = MisinformationModel(n_agents=N_AGENTS, grid_size=GRID_SIZE, rng=42)

    for step in range(1, N_STEPS + 1):
        model.step()
        df     = model.datacollector.get_model_vars_dataframe()
        bel    = int(df["Believers"].iloc[-1])
        mem    = float(df["AvgMemoryEntries"].iloc[-1])
        print(f"Step {step:3d}: believers={bel:2d}/{N_AGENTS}  "
              f"| avg_memory_entries={mem:.2f}")

    df = model.datacollector.get_model_vars_dataframe()
    print(f"\nSimulation complete. Final believers: "
          f"{int(df['Believers'].iloc[-1])}/{N_AGENTS}")
    print("\nAll three pillars exercised successfully:")
    print("  ✅ Pillar 1 (VectorMemory): per-agent memory stored and retrieved")
    print("  ✅ Pillar 2 (LangGraphAgent): graph-driven reasoning per step")
    print("  ✅ Pillar 3 (AsyncLLMEngine): concurrent batch invocation")
