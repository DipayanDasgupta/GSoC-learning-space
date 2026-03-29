"""
llm_evaluation.py — Pillar 2: LLM-Powered Coalition Evaluation
===============================================================
GSoC 2026 Proposal PoC · Dipayan Dasgupta

This file implements the proposed LLMEvaluationAgent design:

  CoalitionScore   — Pydantic-style dataclass; validates the LLM JSON response
                     at the type boundary (same principle as PR #3567).

  LLMEvaluationAgent — Abstract base class. Callable protocol: __call__(group)
                        returns float, so it is a drop-in for evaluation_func
                        in find_combinations / spatial_find_combinations.

  MarketMakerEvaluator — Concrete reference implementation for the Financial
                         Market Coalition example model (from the proposal).

  MockLLMClient    — Network-free stand-in for CI. Returns structured JSON
                     that exercises the full validation path.

Usage:
    from models.meta_agents_proposal.llm_evaluation import (
        MarketMakerEvaluator, MockLLMClient
    )
    evaluator = MarketMakerEvaluator(llm=MockLLMClient())
    score = evaluator(group_of_agents)
"""
from __future__ import annotations
import json
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List


# ── Output type ───────────────────────────────────────────────────────────────

@dataclass
class CoalitionScore:
    """
    Validated output of one LLM coalition evaluation.

    Type validation is done at construction time so that a bad LLM response
    surfaces as a clear TypeError at the boundary, not as a confusing error
    deep in find_combinations — the exact same principle as PR #3567.
    """
    score:       float
    rationale:   str
    recommended: bool

    def __post_init__(self) -> None:
        # Enforce numeric score — matches the PR #3567 type-guard spirit
        if not isinstance(self.score, (int, float)):
            raise TypeError(
                f"CoalitionScore.score must be numeric, got {type(self.score).__name__!r}"
            )
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"CoalitionScore.score must be in [0, 1], got {self.score}"
            )
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise TypeError("CoalitionScore.rationale must be a non-empty string")
        if not isinstance(self.recommended, bool):
            raise TypeError(
                f"CoalitionScore.recommended must be bool, got {type(self.recommended).__name__!r}"
            )

    @classmethod
    def from_json(cls, raw: str) -> "CoalitionScore":
        """Parse LLM JSON response into a validated CoalitionScore.

        Strips markdown fences if the LLM wraps output in ```json...```.
        Raises ValueError with a clear message on malformed JSON.
        """
        # Strip ```json ... ``` fences that some LLMs add
        clean = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", raw, flags=re.S).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON: {exc}\nRaw response: {raw!r}"
            ) from exc

        try:
            return cls(
                score=float(data["score"]),
                rationale=str(data["rationale"]),
                recommended=bool(data["recommended"]),
            )
        except KeyError as exc:
            raise ValueError(
                f"LLM JSON missing required key {exc}. "
                f"Expected: {{score, rationale, recommended}}. Got keys: {list(data.keys())}"
            ) from exc


# ── Abstract base class ───────────────────────────────────────────────────────

class LLMEvaluationAgent(ABC):
    """
    Abstract base class for LLM-powered coalition evaluation.

    Implements the callable protocol: __call__(group) -> float
    so that any LLMEvaluationAgent is a drop-in replacement for the
    scalar evaluation_func currently accepted by find_combinations().

    Subclasses must implement:
        describe_group(group) -> str   # domain-specific agent description
        system_prompt (property)       # task instruction for the LLM

    The base class handles:
        - Prompt construction (system + description)
        - LLM invocation with configurable retry on bad JSON
        - CoalitionScore validation at the type boundary
        - Audit log of every evaluation (for Pillar 2 audit trail)
    """

    MAX_RETRIES: int = 3

    def __init__(self, llm: Any, max_retries: int = MAX_RETRIES) -> None:
        self.llm         = llm
        self.max_retries = max_retries
        self.audit_log:  List[dict] = []
        self._call_count: int       = 0
        self._retry_count: int      = 0
        self._error_count: int      = 0

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Task instruction prepended to every prompt."""

    @abstractmethod
    def describe_group(self, group) -> str:
        """Produce a natural-language description of the candidate group."""

    def __call__(self, group) -> float:
        """Evaluate a candidate coalition. Returns score in [0, 1].

        This is the drop-in replacement for evaluation_func.
        Retries up to max_retries times on bad JSON or type validation failure.
        Falls back to 0.0 on persistent failure (safe default for ABM steps).
        """
        prompt = f"{self.system_prompt}\n\n{self.describe_group(group)}\n\nRespond ONLY with JSON."
        last_err = None

        for attempt in range(self.max_retries + 1):
            self._call_count += 1
            try:
                raw    = self.llm.invoke(prompt)
                result = CoalitionScore.from_json(raw)

                self.audit_log.append({
                    "agents":      [a.unique_id for a in group],
                    "score":       result.score,
                    "rationale":   result.rationale,
                    "recommended": result.recommended,
                    "attempt":     attempt,
                })
                return result.score

            except (ValueError, TypeError) as exc:
                last_err = exc
                self._retry_count += 1

        # All retries exhausted
        self._error_count += 1
        self.audit_log.append({
            "agents":  [a.unique_id for a in group],
            "score":   0.0,
            "error":   str(last_err),
            "attempt": self.max_retries,
        })
        return 0.0

    @property
    def stats(self) -> dict:
        return {
            "total_calls":  self._call_count,
            "retries":      self._retry_count,
            "errors":       self._error_count,
            "log_entries":  len(self.audit_log),
        }


# ── Concrete implementation ───────────────────────────────────────────────────

class MarketMakerEvaluator(LLMEvaluationAgent):
    """
    Reference implementation from the proposal: evaluates market-maker syndicates.

    Agents are expected to have:
        inventory       (float)  — current position
        risk_tolerance  (str)    — 'low' | 'medium' | 'high'
        sector          (str)    — market sector
    """

    SYSTEM_PROMPT = (
        "You are a quantitative analyst evaluating a proposed market-maker syndicate. "
        "Assess whether these agents should form a coalition based on their inventory "
        "positions, risk tolerances, and sector overlap. "
        "Return a JSON object with exactly these keys:\n"
        "  score      (float 0.0–1.0, higher = better coalition)\n"
        "  rationale  (one sentence explanation)\n"
        "  recommended (bool, true if score > 0.6)\n"
        "No other text, no markdown fences."
    )

    @property
    def system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def describe_group(self, group) -> str:
        lines = [f"Candidate syndicate of {len(group)} agents:"]
        for a in group:
            inv  = getattr(a, "inventory",      0.0)
            risk = getattr(a, "risk_tolerance", "unknown")
            sec  = getattr(a, "sector",         "unknown")
            lines.append(
                f"  Agent {a.unique_id}: inventory={inv:+.2f}, "
                f"risk={risk}, sector={sec}"
            )
        return "\n".join(lines)


# ── Mock LLM for CI ───────────────────────────────────────────────────────────

class MockLLMClient:
    """
    Network-free LLM mock for CI. Returns valid JSON responses.

    Simulates occasional bad responses to exercise the retry path —
    the same mock pattern from Mesa-LLM PR #21.
    """

    def __init__(self, bad_response_rate: float = 0.08,
                 latency: float = 0.0) -> None:
        self.bad_response_rate = bad_response_rate
        self.latency           = latency
        self._call_count       = 0

    def invoke(self, prompt: str) -> str:
        self._call_count += 1
        if self.latency:
            time.sleep(self.latency)

        # Occasionally return a bad response to exercise retry logic
        if random.random() < self.bad_response_rate:
            return "Sorry, I cannot evaluate this."  # invalid JSON

        score = round(random.uniform(0.25, 0.95), 3)
        rec   = score > 0.6
        desc  = "complementary" if rec else "conflicting"
        return json.dumps({
            "score":       score,
            "rationale":   f"Agents show {desc} profiles. "
                           f"Compatibility: {int(score * 100)}%.",
            "recommended": rec,
        })


if __name__ == "__main__":
    import mesa

    print("=" * 65)
    print("Pillar 2 PoC — LLMEvaluationAgent Protocol")
    print("=" * 65)

    # ── Minimal agent for demo ────────────────────────────────────────────
    class MarketMaker(mesa.Agent):
        def __init__(self, model, inventory, risk_tolerance, sector):
            super().__init__(model)
            self.inventory      = inventory
            self.risk_tolerance = risk_tolerance
            self.sector         = sector
        def step(self): pass

    model  = mesa.Model(seed=7)
    makers = [
        MarketMaker(model, inventory=+0.42, risk_tolerance="low",    sector="tech"),
        MarketMaker(model, inventory=-0.18, risk_tolerance="medium", sector="tech"),
        MarketMaker(model, inventory=+0.05, risk_tolerance="high",   sector="energy"),
    ]

    evaluator = MarketMakerEvaluator(llm=MockLLMClient(bad_response_rate=0.3))
    score = evaluator(makers)

    print(f"\n  Group: agents {[m.unique_id for m in makers]}")
    print(f"  Score: {score:.3f}")
    print(f"  Stats: {evaluator.stats}")
    print(f"  Last audit entry: {evaluator.audit_log[-1]}")

    # ── Type validation test ──────────────────────────────────────────────
    print("\n[Type validation] Testing CoalitionScore.from_json():")
    try:
        CoalitionScore.from_json('{"score": "not-a-number", "rationale": "x", "recommended": true}')
    except TypeError as e:
        print(f"  ✅ Caught expected TypeError: {e}")

    try:
        CoalitionScore.from_json("this is not json at all")
    except ValueError as e:
        print(f"  ✅ Caught expected ValueError: {e}")

    print("\n  ✅ Pillar 2 LLMEvaluationAgent protocol verified.")
    print("=" * 65)
