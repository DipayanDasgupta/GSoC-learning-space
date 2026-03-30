# Mesa 4.0 Compatibility Notes

## Status
Models verified against: Mesa 3.5.1 (pip, released)
Mesa 4.0.dev testing: TBD (will run against mesa/mesa:main before June 1)

## Model Compatibility Matrix

| Model | Mesa 3.5.1 | Mesa 4.0.dev | Migration Notes |
|-------|------------|--------------|-----------------|
| meta_agents_poc | ✅ PASS | TBD | |
| registry_management | ✅ PASS | TBD | |
| warehouse_lifecycle | ✅ PASS | TBD | |
| active_dormant_network | ✅ PASS | TBD | |
| financial_market_coalition | ✅ PASS | TBD | |
| spatial_coalition | ✅ PASS | TBD | |
| llm_evaluation_demo | ✅ PASS | TBD | |

## Known 4.0 Exposure Points
- [ ] `agents_by_type` implementation (data collection redesign)
- [ ] `AgentSet` method names (may rename in 4.0)
- [ ] `experimental` module restructuring
- [ ] `DataCollector` reporter registration API

## Mitigation Strategy
- All Pillar 1 code uses only public `Agent` / `AgentSet` API surface
- `LLMEvaluationAgent` uses narrow ABC, not `ReasoningAgent` subclass
- `_meta_membership` is a model-level dict, decoupled from Mesa internals
- Will coordinate with Jackie/Colin on mesa-llm 2026 API changes

## To test against Mesa 4.0 dev:
```bash
python -m venv venv_mesa4 && source venv_mesa4/bin/activate
pip install git+https://github.com/mesa/mesa.git@main
python models/registry_management/model.py
python models/warehouse_lifecycle/model.py
python models/active_dormant_network/model.py
deactivate
```
