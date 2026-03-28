"""Mesa-LLM PoC — Pillar 2: LangGraph Integration.

Implements:
  - MesaToolkit: wraps Mesa grid/neighbour API as LangGraph @tool callables
  - LangGraphAgent: thin Mesa agent subclass that accepts a CompiledGraph
  - build_simple_react_graph(): example ReAct graph (reason → act → verify loop)

Design principle:
  LangGraph owns within-step reasoning (LLM calls, tool nodes, conditional edges).
  Mesa owns across-step environment (grid, DataCollector, simulation clock).
  The wrapper keeps these responsibilities cleanly separated.

Usage:
    toolkit = MesaToolkit(model)
    graph   = build_simple_react_graph(llm_client, toolkit)

    class MyAgent(LangGraphAgent):
        def __init__(self, model):
            super().__init__(model, graph=graph)

        def step(self):
            obs    = self.observe()
            result = self.graph.invoke({
                "messages": [obs],
                "agent_id": self.unique_id,
                "action": None,
            })
            self.execute(result["action"])
"""
from __future__ import annotations

from typing import Any


# ── MesaToolkit ──────────────────────────────────────────────────────────────

class MesaToolkit:
    """Wraps common Mesa spatial operations as callable tool functions.

    In production, each method would be decorated with LangGraph's @tool
    decorator to expose it as a ToolNode. For the PoC we keep them as plain
    callables to avoid the langgraph dependency in CI.

    The six tools exposed map directly to the proposal's MesaToolkit table:
      get_neighbours       → cell.connections neighbour lookup
      get_property_layer   → PropertyLayer value at agent's cell
      get_agent_attribute  → Agent's own attribute read
      set_agent_attribute  → Atomic attribute write (step-safe)
      get_grid_density     → Fraction of occupied cells
      get_step_number      → model.steps read
    """

    def __init__(self, model: Any):
        self.model = model

    def get_neighbours(self, agent_id: int, radius: int = 1) -> list[dict]:
        """Return a list of neighbour agent summaries for the given agent."""
        agent = next(
            (a for a in self.model.agents if a.unique_id == agent_id), None
        )
        if agent is None or not hasattr(agent, "cell"):
            return []
        neighbours = []
        for cell in agent.cell.connections.values():
            for neighbour in cell.agents:
                if neighbour.unique_id != agent_id:
                    neighbours.append({
                        "unique_id": neighbour.unique_id,
                        "type": type(neighbour).__name__,
                    })
        return neighbours

    def get_property_layer(self, layer_name: str, agent_id: int) -> Any:
        """Return the value of a PropertyLayer at the agent's current cell."""
        agent = next(
            (a for a in self.model.agents if a.unique_id == agent_id), None
        )
        if agent is None or not hasattr(agent, "cell"):
            return None
        if hasattr(self.model, layer_name):
            layer = getattr(self.model, layer_name)
            if hasattr(layer, "data"):
                col, row = agent.cell.coordinate
                return layer.data[col, row]
        return None

    def get_agent_attribute(self, agent_id: int, attr: str) -> Any:
        """Return the value of an attribute on the given agent."""
        agent = next(
            (a for a in self.model.agents if a.unique_id == agent_id), None
        )
        return getattr(agent, attr, None)

    def set_agent_attribute(self, agent_id: int, attr: str, value: Any) -> bool:
        """Atomically set an attribute on the given agent. Returns True on success."""
        agent = next(
            (a for a in self.model.agents if a.unique_id == agent_id), None
        )
        if agent is None:
            return False
        setattr(agent, attr, value)
        return True

    def get_grid_density(self) -> float:
        """Return the fraction of grid cells that contain at least one agent."""
        if not hasattr(self.model, "grid"):
            return 0.0
        cells = list(self.model.grid._cells.values())
        occupied = sum(1 for c in cells if list(c.agents))
        return occupied / len(cells) if cells else 0.0

    def get_step_number(self) -> int:
        """Return the current simulation step number."""
        return self.model.steps


# ── LangGraphAgent base class ─────────────────────────────────────────────────

class LangGraphAgent:
    """Thin Mesa-compatible agent that executes a LangGraph CompiledGraph each step.

    The constructor accepts a pre-compiled LangGraph CompiledGraph. The class
    adds no new state of its own — graph definition stays entirely in user space.

    In production this would subclass mesa.llm.LLMAgent. For the PoC it is a
    plain Python class to keep langgraph as an optional dependency.
    """

    def __init__(self, model: Any, graph: Any, initial_state: dict | None = None):
        self.model = model
        self.graph = graph
        # Persistent graph state — survives across steps (unlike vanilla LLM context)
        self.graph_state: dict = initial_state or {"messages": [], "action": None}

    def observe(self) -> str:
        """Build an observation string from the current Mesa environment.

        Override in subclasses to include agent-specific context.
        """
        step = self.model.steps if hasattr(self.model, "steps") else "?"
        return f"[Step {step}] Observing environment."

    def execute(self, action: str | None) -> None:
        """Execute the action decided by the graph. Override in subclasses."""
        pass   # Default: no-op

    def step(self) -> None:
        """Run one graph invocation mapped to Mesa's step() lifecycle."""
        if self.graph is None:
            return
        obs = self.observe()
        self.graph_state["messages"].append({"role": "user", "content": obs})
        result = self.graph.invoke(self.graph_state)
        self.graph_state = result
        self.execute(result.get("action"))


# ── Simple mock graph (no langgraph dependency) ───────────────────────────────

class MockCompiledGraph:
    """Minimal mock of a LangGraph CompiledGraph for PoC / CI.

    In production, replace with:
        from langgraph.graph import StateGraph
        graph = StateGraph(AgentState).compile()
    """

    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def invoke(self, state: dict) -> dict:
        messages = state.get("messages", [])
        last_msg = messages[-1]["content"] if messages else ""
        response = self.llm.invoke(last_msg)
        # Simple ReAct step: reason → decide action
        action = "spread" if "credible" in response.lower() else "doubt"
        return {
            **state,
            "messages": messages + [{"role": "assistant", "content": response}],
            "action": action,
        }
