# Financial Market Coalition Model

**Proposal connection:** All three pillars (integration demo)

## What this model demonstrates

All three proposal pillars composing correctly in a single simulation:

| Pillar | Implementation |
|--------|---------------|
| **1. Production Hardening** | `Syndicate.leave()` and `Syndicate.dissolve()` with safe agent-count bookkeeping |
| **2. LLM Evaluation** | `MarketMakerEvaluator.__call__()` with `MockLLM` and `CoalitionScore` validation |
| **3. Spatial Formation** | `spatial_find_combinations()` filtering to Moore-1 neighbourhood |

## Domain

Market-maker agents on an `OrthogonalMooreGrid` (stylised trading floor)
form syndicates with spatial neighbours to pool liquidity. Coalition value
is assessed by an LLM that reads inventory positions, risk tolerances, and sectors.

This domain is chosen from the author's direct experience building market-maker
simulations for the IMC Prosperity Trading Challenge (Global Rank 66, 12,000+ teams)
and Goldman Sachs India Hackathon (AIR 5).

## Run

```bash
python models/financial_market_coalition/model.py
```

No API key required. Replace `MockLLM()` with a real client for live evaluation.

## Connection to PRs

- **PR #3542** (`select_random_not_full_cell`): used for agent placement.
- **PR #3627** (safe generator default): used in `Syndicate.leave()`.
- **Mesa-LLM PR #21** (mock pattern): `MockLLM` mirrors the `MagicMock` approach.
- **PR #3567** (type validation): `CoalitionScore.from_dict()` validates LLM output.
