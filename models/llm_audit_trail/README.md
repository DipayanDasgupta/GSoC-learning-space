# LLM Audit Trail — Extended Pillar 2 PoC

**Proposal connection:** Pillar 2 (LLM-Powered Evaluation) — production-hardening demo

Extends the basic LLM evaluation demo with:
- Full audit trail (`list[CoalitionScore]`) with step, group IDs, score, rationale
- Retry logic: up to 3 retries on malformed LLM responses
- Score distribution histogram for qualitative analysis
- Threshold filtering: only LLM-recommended coalitions are formed

**Run:** `python models/llm_audit_trail/model.py`
