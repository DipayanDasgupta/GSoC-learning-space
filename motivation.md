# Why I Want to Work on Mesa-LLM

## The trading-desk origin story

My path to Mesa-LLM did not start in academia — it started in a terminal,
staring at order-book data during the **IMC Prosperity Trading Challenge 2025**
(Global Rank 66 / 12,000+ teams; India Rank 9) and the **Goldman Sachs India
Hackathon 2025** (AIR 5, national level). Both competitions required building
simulation environments where artificial agents interact under uncertainty,
incomplete information, and non-linear feedback loops. I built those
environments from scratch, and I ran into the same wall every time: the agents
were rigid. Their decision functions were lookup tables or hand-crafted
heuristics. They could not *reason*. They could not update beliefs based on the
history of what other agents had said or done. When conditions shifted, they
broke.

Agent-Based Modelling gave me the vocabulary to formalise what I was already
building. Mesa gave me the infrastructure. But even within Mesa, the agents I
could construct were behaviourally shallow — a `step()` is a deterministic
rule, not a deliberative process. I could model *what* agents do, but not *how
they think about what to do*.

## The Mesa-LLM moment

When I read the 2025 GSoC Mesa-LLM project and the `Reasoning` base class it
introduced, something clicked. LLMs don't just answer questions — they can
serve as a **bounded-rationality engine** for simulation agents. A
`ReasoningAgent` backed by GPT-4o or an open-weights model can evaluate context
clues, weigh conflicting evidence, and produce adaptive behaviour. That is
exactly the kind of cognitive richness that makes Agent-Based Modelling
interesting in the first place.

But the 2025 Mesa-LLM baseline has three gaps that make research-scale
simulations impossible:

1. **Ephemeral memory** — agents lose all context beyond a fixed window length.
   In a 500-step simulation, early interactions are silently discarded. An agent
   deciding whether to trust a rumour cannot recall the first time it heard that
   rumour fifty steps ago.

2. **No cyclic reasoning** — single-shot prompt→response cycles cannot capture
   *plan, observe, verify, revise* workflows. Real deliberation is iterative.

3. **O(N) step latency** — 100 synchronous LLM calls per step, at 1 s/call,
   means 100 seconds per model step. This is not a simulation; it is a batch job.

These gaps are not cosmetic. They are the reason Mesa-LLM cannot yet be used
for the class of social-science and economic research that motivated its
creation. Closing them is the core of my proposal.

## Why I am the right person

I have spent the past several months building the Mesa codebase familiarity
needed to execute this:

- **PR #3627** (merged): Diagnosed and fixed `Sheep.feed()` crash (`StopIteration`
  on bare generator) when `grass=False` — a bug that made a non-default
  configuration completely unusable. Added regression test.
- **PR #3542** (merged): Added `Grid.not_full_cells` and
  `select_random_not_full_cell()` — filling a genuine gap in Mesa's capacity API
  that I discovered while building the Boltzmann model.
- **PR #3544** (merged): Fixed `VoronoiGrid` silently overwriting user-provided
  `capacity` — a silent correctness bug that made the `capacity` parameter a
  no-op on Voronoi grids.
- **PR #3014** (merged): Fixed infinite loop in `select_random_empty_cell` when
  the grid is full — traced through the `_empties` property layer and added a
  heuristic early-exit guard.
- **PR #3011** (merged): Consolidated Solara and Altair CI test coverage.
- **Mesa-LLM PR #21** (merged): Added pytest coverage for the `Reasoning` base
  class — the first unit tests for the 2025 LLM integration.

Beyond code: I competed nationally in quantitative finance environments that
require exactly the kind of state-driven, multi-agent reasoning Mesa-LLM aims
to enable. I understand the *use case* from both ends.

## What I hope to build

A Mesa-LLM that researchers can actually use at scale:

- Agents that remember the entire simulation history, not just the last few
  messages, using per-agent FAISS / ChromaDB vector indices.
- Complex, cyclic reasoning workflows via native LangGraph integration —
  wrapping Mesa's spatial environment as callable tool nodes.
- Step latency that grows as O(⌈N/C⌉ · L) rather than O(N · L) via an
  async batch engine with token-bucket rate limiting and exponential-backoff
  retry on HTTP 429.

The culminating example — a Misinformation Spread simulation — exercises all
three pillars in a single model and will be contributed to `mesa-examples` with
a tutorial notebook. It is a direct descendant of the 2025 Sales Agent example,
showing reviewers exactly what was added and why it matters.

## Long-term commitment

I am not here just for the summer. I already review other contributors' PRs,
help diagnose issues in the Matrix channel, and have my own open issues
(#3541, #3543, #3566, #3282) that I am driving to resolution. The Mesa
community is the kind of place where rigorous software engineering and
scientific curiosity reinforce each other, and that is exactly the environment
I want to grow in.
