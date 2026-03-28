# Alliance Formation Model

## What this model does

Agents with `strength` and `ideology` attributes evaluate potential alliances
using `find_combinations()` from `mesa.experimental.meta_agents`. The best
alliance is the one with the highest combined strength minus ideological spread.

**Output:**
```
Step 1:
Best alliance value: 7.23 between agents [3, 7]
```

## Mesa features used

- `OrthogonalMooreGrid` from `mesa.discrete_space`
- `find_combinations` and `evaluate_combination` from `mesa.experimental.meta_agents`
- Custom `evaluation_func` returning a float score per agent group

## Connection to PR #3567 (evaluate_combination type validation)

While building this model I explored what happens when `evaluation_func`
returns a non-numeric value by mistake — for example returning a dict of
stats instead of a float. The error surfaces deep in `filter_func` with a
confusing message about comparison operators, far from the actual mistake.

PR #3567 adds a type check directly in `evaluate_combination` so the error
appears immediately at the call site with a clear message.

I also noticed that `find_combinations` had an unreachable `if result is not None`
check on line 107 — since `evaluate_combination` already returns `None` when
`evaluation_func` is `None`, and the outer check catches that, the inner check
was dead code. Removed in the same PR.

## What I learned

- `evaluate_combination` is a thin wrapper — the real work happens in
  `find_combinations` which itertools-chains all combinations and evaluates each.
- The `filter_func` parameter lets users post-process the list of
  `(group, score)` tuples — useful for keeping only top-N alliances.
- Negative scores are valid and meaningful (e.g. an alliance that costs more
  than it gains should score negative, not be rejected).

## What was harder than expected

Understanding the type signature of `filter_func` — it takes
`list[tuple[tuple[Agent, ...], float]]` and returns the same type.
Reading the existing tests in `test_meta_agents.py` was more useful
than the docstring for understanding this.

## Connection to GSoC Proposal (Pillar 2)

The alliance evaluation function `alliance_value(group) -> float` is structurally
identical to a LangGraph node: it takes a group (state) and returns a score
(action). In the PoC, `MockCompiledGraph.invoke(state) -> dict` plays the same
role — transforming state to scored action — but with LLM reasoning replacing
the deterministic scoring function. PR #3567's type validation ensures the
evaluation function returns a numeric value; the same invariant applies to
LangGraph nodes that must return a valid action.
