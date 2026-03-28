# Motivation: From Quantitative Finance to Mesa Meta Agents

## The Problem I Kept Running Into

Competing in the **IMC Prosperity Trading Challenge 2025** (Global Rank 66,
India Rank 9, 12,000+ teams) and the **Goldman Sachs India Hackathon 2025**
(AIR 5, National Level) forced me to solve the same problem repeatedly:
dynamic group formation under uncertainty.

Market-makers form syndicates with spatial neighbours to pool liquidity. These
syndicates break when prices move against them and re-form on the next
opportunity — within microseconds. I wrote coalition-detection routines by hand:
brute-force `itertools.combinations` loops, hand-coded scoring functions,
fragile dissolution logic that broke when an agent died mid-coalition.

When I discovered `mesa.experimental.meta_agents`, I recognised what it was
trying to do — and exactly what it was missing.

## Why Mesa

I started contributing to Mesa not to build a resume, but because I kept
running into bugs while building models. Every PR I opened was preceded by
an issue I diagnosed myself:

- **PR #3014**: Infinite loop in `select_random_empty_cell` — found while
  building a population model.
- **PR #3542**: No API for partial-capacity queries — found while trying to
  place agents into cells with `capacity=2`.
- **PR #3544**: VoronoiGrid silently overwriting capacity — found while
  building a geographic coalition model.
- **PR #3567**: `evaluate_combination` accepting non-numeric values — found
  while building the Alliance Formation model in this repository.

This pattern — find a bug, diagnose it, fix it, add a test — is exactly the
discipline that production-hardening `meta_agents` requires.

## Why Meta Agents, Not Mesa-LLM

The Mesa-LLM GSoC 2026 project is explicitly scoped to "push to production" —
stability, structured output, error handling. Important work, but narrowly
defined by the maintainers, and highly competitive.

The Meta Agents slot is where my specific combination of skills creates
differentiated value:
1. My quant finance background maps directly onto coalition formation problems.
2. My DiscreteSpace PRs (#3542, #3544) are the precise infrastructure that
   spatial-aware `meta_agents` requires.
3. My Mesa-LLM PR #21 means I have read every line of `ReasoningAgent` — the
   class I am proposing to wrap in `LLMEvaluationAgent`.
4. My PR #3567 means I have read every line of `meta_agents` — the module I
   am proposing to graduate from experimental.

Nobody else is connecting these dots.

## The Novel Intersection

The key insight: `evaluate_combination()` expects a callable that returns a
float. An `LLMEvaluationAgent` is a callable that (1) describes the candidate
group in natural language, (2) invokes `ReasoningAgent.invoke()`, and (3)
extracts a score via Pydantic validation.

This is the first integration of Mesa's group-formation primitive with the
2025 Mesa-LLM infrastructure. It did not exist before this proposal.
