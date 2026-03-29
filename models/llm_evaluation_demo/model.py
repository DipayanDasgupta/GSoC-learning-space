"""
LLM Evaluation Demo — Pillar 2 PoC  (Mesa 3.5.1 compatible)
=============================================================
LLMEvaluationAgent: callable drop-in for find_combinations evaluation_func.
MockLLM returns structured JSON — no API key needed.

Root cause fix: import find_combinations from .meta_agent submodule.

Run:  python models/llm_evaluation_demo/model.py
"""
from __future__ import annotations
import json
import random
from dataclasses import dataclass
from typing import Any

import mesa
# FIX A: correct import path
from mesa.experimental.meta_agents.meta_agent import find_combinations


@dataclass
class CoalitionScore:
    """Validated structured output from the LLM evaluator."""
    score: float
    rationale: str
    recommended: bool

    @classmethod
    def from_dict(cls, data: dict) -> "CoalitionScore":
        score = float(data["score"])
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"score must be [0,1], got {score}")
        return cls(score=score, rationale=str(data["rationale"]),
                   recommended=bool(data["recommended"]))


class MockLLM:
    """No-API-key mock LLM returning structured JSON coalition scores."""
    def invoke(self, prompt: str) -> str:
        score = round(random.uniform(0.3, 0.95), 2)
        rec   = score > 0.6
        return json.dumps({
            "score": score,
            "rationale": (
                f"Agents show {'complementary' if rec else 'conflicting'} "
                f"profiles. Compatibility: {score:.0%}."
            ),
            "recommended": rec,
        })


class LLMEvaluationAgent:
    """Abstract callable that wraps an LLM and returns a float score.

    Drop-in replacement for a plain evaluation_func in find_combinations().
    This is the core Pillar 2 prototype.
    """
    def __init__(self, llm: Any, system_prompt: str) -> None:
        self.llm = llm
        self.system_prompt = system_prompt
        self.evaluation_log: list[dict] = []

    def describe_group(self, group) -> str:
        raise NotImplementedError

    def __call__(self, group) -> float:
        prompt = f"{self.system_prompt}\n\n{self.describe_group(group)}\n\nJSON only."
        raw = self.llm.invoke(prompt)
        try:
            parsed = CoalitionScore.from_dict(json.loads(raw))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise TypeError(f"LLM bad response: {e}\nRaw: {raw}") from e
        self.evaluation_log.append({
            "group": [a.unique_id for a in group],
            "score": parsed.score,
            "rationale": parsed.rationale,
            "recommended": parsed.recommended,
        })
        return parsed.score


class NegotiationEvaluator(LLMEvaluationAgent):
    def describe_group(self, group) -> str:
        lines = [
            f"Agent {a.unique_id}: ideology={a.ideology:.2f}, "
            f"resources={a.resources:.2f}, cooperativeness={a.cooperativeness}"
            for a in group
        ]
        return "Evaluate negotiation coalition:\n" + "\n".join(lines)


class NegotiationAgent(mesa.Agent):
    def __init__(self, model, ideology: float, resources: float,
                 cooperativeness: str) -> None:
        super().__init__(model)
        self.ideology = ideology
        self.resources = resources
        self.cooperativeness = cooperativeness

    def step(self) -> None:
        pass


class NegotiationModel(mesa.Model):
    """20 agents form coalitions scored by a mock LLM."""

    def __init__(self, n_agents: int = 20, seed: int = 42) -> None:
        super().__init__(rng=seed)
        choices = ["high", "medium", "low"]
        NegotiationAgent.create_agents(
            self, n_agents,
            ideology=[self.rng.uniform(-1, 1) for _ in range(n_agents)],
            resources=[self.rng.uniform(0, 100) for _ in range(n_agents)],
            cooperativeness=[choices[self.rng.integers(0, 3)] for _ in range(n_agents)],
        )
        self.evaluator = NegotiationEvaluator(
            llm=MockLLM(),
            system_prompt=(
                "Evaluate negotiation coalitions on ideology, resources, "
                "cooperativeness. Return JSON: {score: float 0-1, "
                "rationale: str, recommended: bool}."
            ),
        )

    def step(self) -> None:
        combos = find_combinations(
            self, list(self.agents), size=3, evaluation_func=self.evaluator
        )
        if combos:
            best_group, best_score = max(combos, key=lambda x: x[1])
            last = self.evaluator.evaluation_log[-1]
            print(f"\n  Step {self.time}: Best score = {best_score:.3f}")
            print(f"    Agents:     {last['group']}")
            print(f"    Rationale:  {last['rationale']}")
            print(f"    Recommended:{last['recommended']}")


def run_demo() -> None:
    print("=" * 65)
    print("LLM Evaluation Demo — Pillar 2 PoC  [Mesa 3.5.1, no API key]")
    print("=" * 65)
    model = NegotiationModel(n_agents=20)
    for _ in range(3):
        model.step()
    total = len(model.evaluator.evaluation_log)
    print(f"\n  Total LLM evaluations: {total}")
    assert total > 0, "No evaluations ran!"
    print("  ✅ LLMEvaluationAgent working — Pillar 2 PoC complete.")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
