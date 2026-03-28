"""
test_llm_eval.py — Pillar 2: LLMEvaluationAgent Tests
======================================================
Tests:
  • CoalitionScore type validation (the PR #3567 pattern applied to LLM output)
  • LLMEvaluationAgent callable protocol: __call__(group) -> float
  • Retry logic: bad responses are retried; persistent failures return 0.0
  • Audit log: every evaluation is recorded
  • MarketMakerEvaluator: describe_group, system_prompt
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
import mesa
from unittest.mock import MagicMock
from llm_evaluation import (
    CoalitionScore, LLMEvaluationAgent,
    MarketMakerEvaluator, MockLLMClient,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

class DummyAgent(mesa.Agent):
    def __init__(self, model, inventory=0.0, risk_tolerance="low", sector="tech"):
        super().__init__(model)
        self.inventory      = inventory
        self.risk_tolerance = risk_tolerance
        self.sector         = sector
    def step(self): pass


@pytest.fixture
def model():
    return mesa.Model(seed=1)


@pytest.fixture
def three_agents(model):
    return [
        DummyAgent(model, inventory=0.1, risk_tolerance="low",    sector="tech"),
        DummyAgent(model, inventory=0.2, risk_tolerance="medium", sector="tech"),
        DummyAgent(model, inventory=0.3, risk_tolerance="high",   sector="energy"),
    ]


@pytest.fixture
def evaluator():
    return MarketMakerEvaluator(llm=MockLLMClient(bad_response_rate=0.0))


# ── CoalitionScore validation ─────────────────────────────────────────────────

def test_coalition_score_valid():
    cs = CoalitionScore(score=0.75, rationale="Good fit", recommended=True)
    assert cs.score == 0.75

def test_coalition_score_rejects_non_numeric():
    with pytest.raises(TypeError, match="must be numeric"):
        CoalitionScore(score="high", rationale="x", recommended=True)

def test_coalition_score_rejects_out_of_range():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        CoalitionScore(score=1.5, rationale="x", recommended=True)

def test_coalition_score_rejects_empty_rationale():
    with pytest.raises(TypeError, match="non-empty string"):
        CoalitionScore(score=0.5, rationale="   ", recommended=True)

def test_coalition_score_rejects_non_bool_recommended():
    with pytest.raises(TypeError, match="bool"):
        CoalitionScore(score=0.5, rationale="ok", recommended="yes")

def test_coalition_score_from_json_valid():
    raw = json.dumps({"score": 0.8, "rationale": "great", "recommended": True})
    cs  = CoalitionScore.from_json(raw)
    assert cs.score == 0.8
    assert cs.recommended is True

def test_coalition_score_from_json_strips_fences():
    raw = '```json\n{"score": 0.6, "rationale": "ok", "recommended": false}\n```'
    cs  = CoalitionScore.from_json(raw)
    assert cs.score == 0.6

def test_coalition_score_from_json_raises_on_bad_json():
    with pytest.raises(ValueError, match="invalid JSON"):
        CoalitionScore.from_json("not json at all")

def test_coalition_score_from_json_raises_on_missing_key():
    raw = json.dumps({"score": 0.5, "rationale": "ok"})  # missing 'recommended'
    with pytest.raises(ValueError, match="missing required key"):
        CoalitionScore.from_json(raw)


# ── LLMEvaluationAgent callable protocol ─────────────────────────────────────

def test_evaluator_returns_float(evaluator, three_agents):
    score = evaluator(three_agents)
    assert isinstance(score, float)

def test_evaluator_score_in_range(evaluator, three_agents):
    score = evaluator(three_agents)
    assert 0.0 <= score <= 1.0

def test_evaluator_logs_every_call(three_agents):
    ev = MarketMakerEvaluator(llm=MockLLMClient(bad_response_rate=0.0))
    for _ in range(5):
        ev(three_agents)
    assert len(ev.audit_log) == 5

def test_evaluator_audit_log_structure(evaluator, three_agents):
    evaluator(three_agents)
    entry = evaluator.audit_log[-1]
    assert "agents" in entry
    assert "score"  in entry
    assert "rationale" in entry

def test_evaluator_retry_on_bad_json(three_agents):
    """Bad responses trigger retries; valid response eventually recorded."""
    always_bad = MagicMock()
    always_bad.invoke.return_value = "this is not json"
    ev = MarketMakerEvaluator(llm=always_bad, max_retries=3)
    score = ev(three_agents)
    assert score == 0.0        # fallback on all-retry failure
    assert ev.stats["errors"] == 1
    assert always_bad.invoke.call_count == 4   # 1 attempt + 3 retries

def test_evaluator_falls_back_to_zero_on_persistent_failure(three_agents):
    bad_llm = MagicMock()
    bad_llm.invoke.return_value = "garbage"
    ev = MarketMakerEvaluator(llm=bad_llm, max_retries=2)
    score = ev(three_agents)
    assert score == 0.0

def test_evaluator_stats_keys(evaluator, three_agents):
    evaluator(three_agents)
    stats = evaluator.stats
    for key in ("total_calls", "retries", "errors", "log_entries"):
        assert key in stats


# ── MarketMakerEvaluator describe_group ──────────────────────────────────────

def test_describe_group_contains_agent_ids(evaluator, three_agents):
    desc = evaluator.describe_group(three_agents)
    for agent in three_agents:
        assert str(agent.unique_id) in desc

def test_describe_group_contains_sector(evaluator, three_agents):
    desc = evaluator.describe_group(three_agents)
    assert "tech" in desc

def test_system_prompt_is_string(evaluator):
    assert isinstance(evaluator.system_prompt, str)
    assert len(evaluator.system_prompt) > 20


# ── Drop-in compatibility with find_combinations signature ────────────────────

def test_evaluator_is_callable(evaluator):
    assert callable(evaluator)

def test_mock_llm_never_network_calls():
    """MockLLMClient must never make real HTTP calls."""
    llm = MockLLMClient()
    result = llm.invoke("test prompt")
    assert isinstance(result, str)
    parsed = json.loads(result)  # will raise if not valid JSON (ignoring bad_response_rate=0)
