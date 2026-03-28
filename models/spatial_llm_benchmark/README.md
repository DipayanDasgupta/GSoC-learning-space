# Spatial + LLM Benchmark

**Proposal connection:** Pillars 2 & 3 combined benchmark

Measures the wall-clock speedup of `spatial_find_combinations()` (Pillar 3)
when LLM calls have realistic latency (Pillar 2).

| N agents | LLM latency | Naive calls | Spatial calls | Speedup |
|----------|-------------|-------------|---------------|---------|
| 20       | 10 ms       | C(20,3)=1140| ~200          | ~5×     |
| 30       | 5 ms        | C(30,3)=4060| ~300          | ~13×    |
| 40       | 2 ms        | C(40,3)=9880| ~400          | ~25×    |

**Run:** `python models/spatial_llm_benchmark/model.py`
