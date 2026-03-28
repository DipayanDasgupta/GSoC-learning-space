# Mesa-LLM Proof of Concept

This directory contains working PoCs for the three pillars proposed in my
GSoC 2026 proposal for Mesa-LLM.

**No LLM API key is required to run the demo** — all LLM calls are mocked.
The mocks satisfy the same interface that real LangChain / OpenAI clients use,
so swapping in a real client requires changing exactly one line.

## Architecture

```
mesa_llm_poc/
├── vector_memory.py     Pillar 1: Per-agent FAISS/Chroma vector memory
├── async_engine.py      Pillar 3: Token-bucket + async batch LLM caller
├── langgraph_agent.py   Pillar 2: LangGraph wrapper + MesaToolkit
└── demo/
    └── misinformation_spread.py   All three pillars composing together
```

## Feasibility Analysis

### Pillar 1 — Vector Memory ✅ High confidence

- FAISS is a C-backed library with a mature Python API (faiss-cpu on PyPI).
- Per-agent indexing is a `dict[int, FAISS]` — trivial to implement.
- The `retrieve() → store()` interface mirrors Generative Agents (Park et al., 2023).
- ChromaDB adds persistence (SQLite backend); same interface, different backend.
- **Main risk:** embedding costs per step. Mitigated by batching embeddings
  across all agents at once before the step runs (see `batch_embed()` in code).

### Pillar 2 — LangGraph Integration ✅ High confidence

- LangGraph has a stable `CompiledGraph.invoke()` API since v0.1.
- Mesa's `step()` lifecycle is synchronous; LangGraph graph execution is also
  synchronous by default. No event-loop friction.
- `MesaToolkit` wraps six read/write operations as plain callables decorated
  with `@tool`. This is the standard LangGraph tool pattern.
- **Main risk:** graph state serialisation across steps. Mitigated by storing
  `graph_state` as an agent attribute and passing it as `invoke(state)`.

### Pillar 3 — Async Engine ✅ High confidence

- `asyncio.gather` + `asyncio.Semaphore` is battle-tested Python.
- Token-bucket rate limiting via a `deque[float]` of timestamps is O(1) per
  request amortised.
- Integration with Mesa's synchronous `step()` via `asyncio.run()` is
  straightforward; no Mesa internals need to change.
- **Main risk:** providers cap concurrent connections. Mitigated by
  `max_parallel` parameter (default 20, configurable).

## Running the demo

```bash
# From this directory:
pip install mesa faiss-cpu langgraph          # real deps (PoC uses mocks)
python demo/misinformation_spread.py
```

Expected output:
```
=== Misinformation Spread Simulation ===
Pillar 3: AsyncLLMEngine initialised (max_rpm=60, max_parallel=5)
Pillar 1: VectorMemory initialised (backend=faiss, k=4)
Step  1: believers=1/20  | avg_memory_entries=0.05
Step  5: believers=4/20  | avg_memory_entries=0.95
Step 10: believers=9/20  | avg_memory_entries=2.30
Step 20: believers=15/20 | avg_memory_entries=5.10
Simulation complete. Final believers: 15/20
```
