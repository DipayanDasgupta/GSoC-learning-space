# LLM Evaluation Demo — Pillar 2 PoC

**Proposal connection:** Pillar 2 (LLM-Powered Coalition Evaluation)

## What this model demonstrates

- `LLMEvaluationAgent`: a callable that wraps a (mock) LLM and returns a
  float score for `find_combinations()` — a drop-in replacement for a plain
  `evaluation_func`.
- `CoalitionScore`: Pydantic-style structured output validation.
  The same type boundary that PR #3567 enforces for Python callables is
  enforced here at the LLM output boundary.
- Natural-language rationale strings are logged for qualitative analysis.

## Run

```bash
python models/llm_evaluation_demo/model.py
```

No API key required. To use a real LLM, replace `MockLLM()` with:

```python
from openai import OpenAI
real_llm = OpenAI()  # reads OPENAI_API_KEY from environment
evaluator = NegotiationEvaluator(llm=real_llm, system_prompt=...)
```

## Connection to proposal

- **Pillar 2:** This IS the core Pillar 2 prototype.
- **Mesa-LLM PR #21:** The mock pattern here mirrors the `MagicMock` pattern
  from Mesa-LLM PR #21 — network-free CI without sacrificing interface fidelity.
- **PR #3567:** The `CoalitionScore.from_dict()` validator closes the same
  type-boundary gap that PR #3567 closes for plain callables.
