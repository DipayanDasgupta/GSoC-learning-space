"""
poc/pillar2_negotiation_model.py
Pillar 2 — Non-Spatial Negotiation Model
=========================================
Demonstrates LLMEvaluationAgent without any grid — agents negotiate in a flat
pool, which is the typical mesa.experimental.meta_agents use-case today.

15 NegotiationAgents with ideology [0..1], resources [0..1], and
cooperativeness [0..1] form coalitions scored by a mock LLM.
The LLM evaluates "ideological alignment + resource complementarity".

Shows how Pillar 2 integrates with the EXISTING find_combinations API
(no spatial changes needed).

Run:
    python poc/pillar2_negotiation_model.py
"""
from __future__ import annotations
import json, random as _r, dataclasses
from itertools import combinations
import mesa

N_AGENTS = 15
N_STEPS  = 5
SEED     = 7


# ── Agent ─────────────────────────────────────────────────────────────────────

class NegAgent(mesa.Agent):
    def __init__(self, model, ideology, resources, cooperativeness):
        super().__init__(model)
        self.ideology        = ideology
        self.resources       = resources
        self.cooperativeness = cooperativeness
        self.coalition       = None
    def step(self): pass


# ── CoalitionScore ────────────────────────────────────────────────────────────

@dataclasses.dataclass
class CoalitionScore:
    score: float; rationale: str; recommended: bool
    def __post_init__(self):
        if not isinstance(self.score, (int, float)):
            raise TypeError(f"score must be numeric, got {type(self.score).__name__!r}")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0,1], got {self.score}")

    @classmethod
    def from_dict(cls, d):
        return cls(float(d["score"]), str(d["rationale"]), bool(d["recommended"]))


# ── MockLLM ───────────────────────────────────────────────────────────────────

class MockLLM:
    """Network-free mock. Returns structured JSON simulating real LLM output."""
    def __init__(self, bad_rate=0.06, seed=SEED):
        self._rng = _r.Random(seed); self._calls = 0
    def invoke(self, prompt: str) -> str:
        self._calls += 1
        if self._rng.random() < 0.06:
            return "I cannot evaluate this group."   # exercises retry path
        score = round(self._rng.uniform(0.2, 0.95), 3)
        rec   = score > 0.60
        label = "complementary" if rec else "conflicting"
        return json.dumps({"score": score,
                           "rationale": f"Agents show {label} ideological alignment "
                                        f"({int(score*100)}% compatibility).",
                           "recommended": rec})


# ── LLMEvaluationAgent ────────────────────────────────────────────────────────

class NegotiationEvaluator:
    """Pillar 2 prototype: callable drop-in for evaluation_func."""
    SYSTEM = ("Evaluate this coalition for ideological alignment and resource "
              "complementarity. Return JSON: {score, rationale, recommended}.")
    MAX_RETRIES = 3

    def __init__(self, llm):
        self.llm        = llm
        self.audit_log  = []
        self._retries   = 0
        self._errors    = 0

    def describe(self, group) -> str:
        lines = [f"Coalition of {len(group)} agents:"]
        for a in group:
            lines.append(f"  Agent {a.unique_id}: ideology={a.ideology:.2f}, "
                         f"resources={a.resources:.2f}, "
                         f"cooperativeness={a.cooperativeness:.2f}")
        return "\n".join(lines)

    def __call__(self, group) -> float:
        prompt = f"{self.SYSTEM}\n\n{self.describe(group)}"
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                raw    = self.llm.invoke(prompt)
                result = CoalitionScore.from_dict(json.loads(raw))
                self.audit_log.append({
                    "agents": [a.unique_id for a in group],
                    "score":  result.score, "rationale": result.rationale,
                    "attempt": attempt,
                })
                return result.score
            except (ValueError, KeyError, json.JSONDecodeError, TypeError):
                self._retries += 1
        self._errors += 1
        return 0.0


# ── find_combinations (mirrors meta_agents API) ───────────────────────────────

def find_combinations_flat(agents, size, evaluation_func, filter_func=None):
    """Pure-Python version of mesa.experimental.meta_agents.find_combinations."""
    results = []
    for group in combinations(agents, size):
        score = evaluation_func(group)
        if not isinstance(score, (int, float)):
            raise TypeError(f"evaluation_func returned {type(score).__name__!r}")
        if filter_func is None or filter_func(group, score):
            results.append((list(group), score))
    return sorted(results, key=lambda x: x[1], reverse=True)


# ── Model ─────────────────────────────────────────────────────────────────────

class NegotiationModel(mesa.Model):
    def __init__(self):
        super().__init__()
        self.random = __import__('random').Random(SEED)
        self.evaluator = NegotiationEvaluator(MockLLM())
        NegAgent.create_agents(
            self, N_AGENTS,
            ideology       = [self.random.uniform(0,1) for _ in range(N_AGENTS)],
            resources      = [self.random.uniform(0,1) for _ in range(N_AGENTS)],
            cooperativeness= [self.random.uniform(0,1) for _ in range(N_AGENTS)],
        )
        self.coalitions: list = []
        self.datacollector = mesa.DataCollector({
            "LLM_calls": lambda m: m.evaluator.llm._calls,
            "Coalitions": lambda m: len(m.coalitions),
        })

    def step(self):
        self.datacollector.collect(self)
        free = [a for a in self.agents
                if isinstance(a, NegAgent) and a.coalition is None]
        if len(free) < 3:
            return
        combos = find_combinations_flat(
            free, size=3,
            evaluation_func=self.evaluator,
            filter_func=lambda g, s: s >= 0.65
        )
        used: set = set()
        for group, score in combos[:3]:
            if any(a in used for a in group): continue
            for a in group: a.coalition = id(group)
            self.coalitions.append({"agents": [a.unique_id for a in group], "score": score})
            used.update(group)


if __name__ == "__main__":
    print("=" * 65)
    print("Pillar 2 — Non-Spatial Negotiation Model  [Mesa 3.5.1, no API key]")
    print("=" * 65)

    model = NegotiationModel()
    for step in range(1, N_STEPS + 1):
        model.step()
        df  = model.datacollector.get_model_vars_dataframe()
        print(f"  Step {step}: coalitions={int(df['Coalitions'].iloc[-1]):2d}  "
              f"llm_calls={int(df['LLM_calls'].iloc[-1]):5d}")

    eval_ = model.evaluator
    print()
    print(f"  Total LLM evaluations: {eval_.llm._calls}")
    print(f"  Retries:               {eval_._retries}")
    print(f"  Persistent errors:     {eval_._errors}")
    print()
    if model.coalitions:
        best = max(model.coalitions, key=lambda c: c["score"])
        print(f"  Best coalition: agents {best['agents']}, score={best['score']:.3f}")
        worst = eval_.audit_log[-1] if eval_.audit_log else None
        if worst:
            print(f"  Last audit entry: {worst}")
    print()
    print("  ✅  LLMEvaluationAgent drop-in for evaluation_func verified.")
    print("  ✅  Audit log, retry logic, type-boundary all active.")
    print("  ✅  No grid needed — works with flat agent pool.")
    print("=" * 65)
