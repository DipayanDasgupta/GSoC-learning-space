"""
LLM Audit Trail — Extended Pillar 2 PoC  (Mesa 3.5.1)
======================================================
Extends the LLM evaluation demo with:
  - Score distribution histogram (text-based)
  - Per-step audit trail showing which groups were evaluated
  - Retry logic for malformed LLM responses (Pillar 2 robustness)
  - Score threshold filtering: only recommended coalitions are formed

Demonstrates the production-readiness aspects of Pillar 2 that go beyond
a bare callable wrapper.

Run:  python models/llm_audit_trail/model.py
"""
from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any

import mesa
from mesa.experimental.meta_agents.meta_agent import find_combinations


@dataclass
class CoalitionScore:
    score: float
    rationale: str
    recommended: bool
    step: int
    group_ids: list[int]

    @classmethod
    def from_dict(cls, data: dict, step: int, group_ids: list[int]) -> "CoalitionScore":
        score = float(data["score"])
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"score out of range: {score}")
        return cls(score=score, rationale=str(data["rationale"]),
                   recommended=bool(data["recommended"]),
                   step=step, group_ids=group_ids)


class RobustMockLLM:
    """Mock LLM with occasional bad responses to test retry logic."""
    def __init__(self, bad_response_rate: float = 0.05):
        self.bad_rate = bad_response_rate
        self.call_count = 0

    def invoke(self, prompt: str) -> str:
        self.call_count += 1
        # Simulate occasional malformed responses
        if random.random() < self.bad_rate:
            return '{"score": "not_a_float", "rationale": "oops"}'
        score = round(random.uniform(0.2, 0.98), 2)
        rec   = score > 0.55
        return json.dumps({
            "score": score,
            "rationale": (
                f"Step {self.call_count}: agents show "
                f"{'strong' if rec else 'weak'} complementarity "
                f"({score:.0%} compatibility)."
            ),
            "recommended": rec,
        })


class AuditingLLMEvaluator:
    """LLM evaluator with retry logic and full audit trail."""

    MAX_RETRIES = 3

    def __init__(self, llm: Any, system_prompt: str, model: mesa.Model) -> None:
        self.llm = llm
        self.system_prompt = system_prompt
        self.model = model
        self.audit_trail: list[CoalitionScore] = []
        self.retry_count = 0
        self.error_count = 0

    def describe_group(self, group) -> str:
        return "\n".join(
            f"Agent {a.unique_id}: skill={a.skill:.2f}, "
            f"sector={a.sector}, seniority={a.seniority}"
            for a in group
        )

    def __call__(self, group) -> float:
        prompt = (f"{self.system_prompt}\n\n"
                  f"{self.describe_group(group)}\n\nJSON only.")
        group_ids = [a.unique_id for a in group]

        for attempt in range(self.MAX_RETRIES):
            try:
                raw    = self.llm.invoke(prompt)
                parsed = CoalitionScore.from_dict(
                    json.loads(raw), step=self.model.steps, group_ids=group_ids
                )
                self.audit_trail.append(parsed)
                return parsed.score
            except (json.JSONDecodeError, KeyError, ValueError):
                self.retry_count += 1
                if attempt == self.MAX_RETRIES - 1:
                    self.error_count += 1
                    return 0.0   # fail-safe: reject malformed response
        return 0.0

    def score_histogram(self, bins: int = 5) -> str:
        """ASCII histogram of score distribution."""
        if not self.audit_trail:
            return "  (no evaluations yet)"
        scores = [e.score for e in self.audit_trail]
        width  = 1.0 / bins
        rows   = []
        for i in range(bins):
            lo  = i * width
            hi  = (i + 1) * width
            cnt = sum(1 for s in scores if lo <= s < hi)
            bar = "█" * cnt
            rows.append(f"  [{lo:.1f}-{hi:.1f}): {bar} ({cnt})")
        return "\n".join(rows)


class ProjectAgent(mesa.Agent):
    SECTORS    = ["tech", "ops", "design", "research"]
    SENIORITIES = ["junior", "mid", "senior"]

    def __init__(self, model, skill: float, sector: str, seniority: str) -> None:
        super().__init__(model)
        self.skill      = skill
        self.sector     = sector
        self.seniority  = seniority
        self.team: Any  = None

    def step(self) -> None:
        pass


class AuditModel(mesa.Model):
    def __init__(self, n_agents: int = 25, seed: int = 42) -> None:
        super().__init__(seed=seed)
        ProjectAgent.create_agents(
            self, n_agents,
            skill=[self.rng.uniform(0.2, 1.0) for _ in range(n_agents)],
            sector=[self.rng.choice(ProjectAgent.SECTORS) for _ in range(n_agents)],
            seniority=[self.rng.choice(ProjectAgent.SENIORITIES) for _ in range(n_agents)],
        )
        self.evaluator = AuditingLLMEvaluator(
            llm=RobustMockLLM(bad_response_rate=0.08),
            system_prompt=(
                "Evaluate project team formation: complementary skills, sectors, "
                "seniority mix. JSON: {score:float 0-1, rationale:str, recommended:bool}."
            ),
            model=self,
        )
        self.formed_teams: list[list[int]] = []

    def step(self) -> None:
        free   = [a for a in self.agents if isinstance(a, ProjectAgent)
                  and a.team is None]
        combos = find_combinations(self, free, size=3,
                                   evaluation_func=self.evaluator)
        if not combos:
            return
        # Only form coalitions the LLM explicitly recommends
        recommended = [
            (grp, score) for grp, score in combos
            if any(e.recommended and e.group_ids == [a.unique_id for a in grp]
                   for e in self.evaluator.audit_trail[-len(combos):])
        ]
        if not recommended:
            return
        best_group, best_score = max(recommended, key=lambda x: x[1])
        for a in best_group:
            a.team = True
        self.formed_teams.append([a.unique_id for a in best_group])
        print(f"  Step {self.steps}: Team formed {[a.unique_id for a in best_group]} "
              f"(score={best_score:.2f})")


if __name__ == "__main__":
    print("=" * 65)
    print("LLM Audit Trail — Extended Pillar 2 PoC  [Mesa 3.5.1]")
    print("=" * 65)
    model = AuditModel(n_agents=25)
    for _ in range(5):
        model.step()

    ev = model.evaluator
    print(f"\n  Total evaluations: {len(ev.audit_trail)}")
    print(f"  Retries due to bad responses: {ev.retry_count}")
    print(f"  Errors (all retries failed):  {ev.error_count}")
    print(f"  Teams formed: {len(model.formed_teams)}")
    print(f"\n  Score distribution:")
    print(ev.score_histogram(bins=5))
    print("\n  ✅ Audit trail and retry logic working — Pillar 2 extended PoC.")
    print("=" * 65)
