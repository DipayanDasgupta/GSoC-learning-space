# Spatial Coalition Demo — Pillar 3 PoC

**Proposal connection:** Pillar 3 (DiscreteSpace-Aware Formation)

## What this model demonstrates

The candidate count explosion problem:
- **Naive:** `find_combinations` on all 200 agents, k=3:
  C(200,3) = 1,313,400 candidate triples per step.
- **Spatial:** restrict to Moore-1 neighbourhood (8 cells):
  ~C(8,3) = 56 per agent → ~11,200 total after deduplication.
- **Reduction: ~99% fewer evaluations.**

## Run

```bash
python models/spatial_coalition/model.py
```

Expected output:
```
N=200 agents, k=3, Moore-1 neighbourhood
  Naive candidates:   1,313,400
  Spatial candidates: ~11,000
  Search space reduction: ~99.2%
```

## Connection to PRs

- **PR #3542** (`Grid.not_full_cells`): used to place agents on non-full cells
  and to gate coalition assembly at cells with remaining capacity.
- **PR #3544** (VoronoiGrid capacity fix): the same spatial filter generalises
  to VoronoiGrid once the capacity contract is correct.
