"""
LLM Evaluation Demo — Pillar 2 Proof of Concept
================================================
Demonstrates the LLMEvaluationAgent concept WITHOUT requiring an API key.
Uses a MockLLM that simulates structured JSON responses.

This PoC shows:
1. A callable evaluator that wraps an LLM interface
2. Pydantic-validated structured output (CoalitionScore)
3. Natural-language rationale strings logged to DataCollector
4. Drop-in replacement for a plain evaluation_func

Run with:
    python models/llm_evaluation_demo/model.py

No API key required — MockLLM simulates responses locally.
"""

import json
import random
from typing import Any
from dataclasses import dataclass, field

import mesa
from mesa.experimental.meta_agents import find_combinations


# ── Pydantic-style validation (stdlib only, no pydantic dependency) ───────────

@dataclass
class CoalitionScore:
    """Structured output schema for LLM evaluator."""
    score: float           # 0.0 to 1.0 compatibility score
    rationale: str         # natural-language explanation
    recommended: bool      # binary accept/reject decision

    @classmethod
    def from_dict(cls, data: dict) -> "CoalitionScore":
        score = float(data["score"])
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"score must be in [0, 1], got {score}")
        return cls(
            score=score,
            rationale=str(data["rationale"]),
            recommended=bool(data["recommended"]),
        )


# ── Mock LLM (no API key needed) ─────────────────────────────────────────────

class MockLLM:
    """
    Simulates an LLM client returning structured JSON for coalition evaluation.
    Replace with a real openai.OpenAI() client when you have an API key.
    """

    def invoke(self, prompt: str) -> str:
        """Return a mock JSON response evaluating a coalition."""
        # Simulate: compatible agents (similar risk) score higher
        score = round(random.uniform(0.3, 0.95), 2)
        recommended = score > 0.6
        rationale = (
            f"The agents share complementary attributes. "
            f"Estimated coalition compatibility: {score:.0%}. "
            f"{'Recommended for formation.' if recommended else 'Insufficient compatibility.'}"
        )
        return json.dumps({
            "score": score,
            "rationale": rationale,
            "recommended": recommended,
        })


# ── LLMEvaluationAgent (Pillar 2 prototype) ──────────────────────────────────

class LLMEvaluationAgent:
    """
    Abstract base for LLM-powered coalition evaluation.

    This is the core Pillar 2 concept: a callable that wraps an LLM
    and returns a CoalitionScore. It is a drop-in replacement for a
    plain evaluation_func in find_combinations().
    """

    def __init__(self, llm: Any, system_prompt: str) -> None:
        self.llm = llm
        self.system_prompt = system_prompt
        self.evaluation_log: list[dict] = []

    def describe_group(self, group) -> str:
        """Build a natural-language description of the candidate coalition."""
        raise NotImplementedError

    def __call__(self, group) -> float:
        """
        Invoke the LLM, parse the response, log the rationale, return the score.
        This is the callable interface that find_combinations() expects.
        """
        description = self.describe_group(group)
        prompt = f"{self.system_prompt}\n\n{description}\n\nRespond in JSON only."
        raw = self.llm.invoke(prompt)
        try:
            parsed = CoalitionScore.from_dict(json.loads(raw))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Type boundary enforcement — analogous to PR #3567
            raise TypeError(
                f"LLM returned an invalid response: {e}\nRaw: {raw}"
            ) from e
        # Log for DataCollector
        self.evaluation_log.append({
            "group": [a.unique_id for a in group],
            "score": parsed.score,
            "rationale": parsed.rationale,
            "recommended": parsed.recommended,
        })
        return parsed.score


# ── Concrete evaluator for negotiation agents ─────────────────────────────────

class NegotiationEvaluator(LLMEvaluationAgent):
    """LLM evaluator for negotiation-agent coalitions."""

    def describe_group(self, group) -> str:
        lines = [
            f"Agent {a.unique_id}: "
            f"ideology={a.ideology:.2f}, "
            f"resources={a.resources:.2f}, "
            f"cooperativeness={a.cooperativeness}"
            for a in group
        ]
        return (
            "Evaluate whether these agents should form a negotiation coalition:\n"
            + "\n".join(lines)
        )


# ── Agents ────────────────────────────────────────────────────────────────────

class NegotiationAgent(mesa.Agent):
    """Agent with ideology, resources, and cooperativeness attributes."""

    def __init__(self, model, ideology: float, resources: float,
                 cooperativeness: str) -> None:
        super().__init__(model)
        self.ideology = ideology
        self.resources = resources
        self.cooperativeness = cooperativeness  # "high" | "medium" | "low"

    def step(self) -> None:
        pass


# ── Model ─────────────────────────────────────────────────────────────────────

class NegotiationModel(mesa.Model):
    """
    20 negotiation agents form coalitions evaluated by a mock LLM.
    Demonstrates Pillar 2: LLM-powered coalition evaluation.
    """

    def __init__(self, n_agents: int = 20, seed: int = 42) -> None:
        super().__init__(seed=seed)
        cooperativeness_choices = ["high", "medium", "low"]
        NegotiationAgent.create_agents(
            self, n_agents,
            ideology=[self.rng.uniform(-1, 1) for _ in range(n_agents)],
            resources=[self.rng.uniform(0, 100) for _ in range(n_agents)],
            cooperativeness=[
                cooperativeness_choices[self.rng.integers(0, 3)]
                for _ in range(n_agents)
            ],
        )
        mock_llm = MockLLM()
        self.evaluator = NegotiationEvaluator(
            llm=mock_llm,
            system_prompt=(
                "You are evaluating potential negotiation coalitions. "
                "Consider ideology alignment, resource complementarity, and "
                "cooperativeness. Return a JSON object with keys: "
                "score (float 0-1), rationale (str), recommended (bool)."
            ),
        )

    def step(self) -> None:
        combos = find_combinations(
            self,
            list(self.agents),
            size=3,
            evaluation_func=self.evaluator,
        )
        if combos:
            best_group, best_score = max(combos, key=lambda x: x[1])
            print(f"\nStep {self.steps}: Best coalition score = {best_score:.3f}")
            # Print the LLM rationale for the best group
            last_eval = self.evaluator.evaluation_log[-1]
            print(f"  Agents: {last_eval['group']}")
            print(f"  Rationale: {last_eval['rationale']}")
            print(f"  Recommended: {last_eval['recommended']}")


def run_demo() -> None:
    print("=" * 65)
    print("LLM Evaluation Demo — Pillar 2 PoC (Mock LLM, no API key)")
    print("=" * 65)
    model = NegotiationModel(n_agents=20)
    for _ in range(3):
        model.step()
    total_evals = len(model.evaluator.evaluation_log)
    print(f"\nTotal LLM evaluations: {total_evals}")
    print("All evaluation logs accessible in model.evaluator.evaluation_log")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
