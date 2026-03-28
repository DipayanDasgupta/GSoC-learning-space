# Meta Agents PoC — Lifecycle Demo

**Proposal connection:** Pillar 1 (Production Hardening)

## What this model demonstrates

1. **Bug reproduction:** The current `meta_agents` module has confirmed
   agent-count bugs when coalitions are dissolved and re-formed (identified
   by Tom Pike in the Feb 2026 dev meeting). This model shows the problem.

2. **Proposed lifecycle API:** Implements `join()`, `leave()`, and `dissolve()`
   methods on a `MetaAgent` subclass — the API proposed in Pillar 1.

## Run

```bash
python models/meta_agents_poc/model.py
```

## Connection to PRs

- **PR #3567** (type validation in `evaluate_combination`): the `team_value`
  function here is the kind of callable whose return type must be validated.
- **PR #3627** (safe generator defaults): the `dissolve()` method uses the same
  safe iteration pattern to avoid `StopIteration` on empty member sets.
