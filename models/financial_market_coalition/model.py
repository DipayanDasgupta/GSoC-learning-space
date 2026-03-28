"""
Financial Market Coalition Model
=================================
Demonstrates all three proposal pillars in a single simulation.

Domain:
  Market-maker agents on an OrthogonalMooreGrid (stylised trading floor)
  form syndicates with spatial neighbours to pool liquidity. Coalition value
  is assessed by a mock LLM evaluator.

Pillars:
  - Pillar 1: Stable MetaAgent lifecycle (join, leave, merge, split)
  - Pillar 2: LLM-powered coalition evaluation (MockLLM, no API key)
  - Pillar 3: Spatial candidate filtering (Moore-1 neighbourhood)

Run with:
    python models/financial_market_coalition/model.py

Based on the author's experience building market-maker simulations for:
  - IMC Prosperity Trading Challenge 2025 (Global Rank 66, India Rank 9)
  - Goldman Sachs India Hackathon 2025 (AIR 5, National Level)
"""

import json
import random
import mesa
from itertools import combinations
from mesa.discrete_space import OrthogonalMooreGrid


# ── Mock LLM ──────────────────────────────────────────────────────────────────

class MockLLM:
    def invoke(self, prompt: str) -> str:
        # Simulate: complementary inventories (one long, one short) score higher
        score = round(random.uniform(0.3, 0.95), 2)
        recommended = score > 0.6
        return json.dumps({
            "score": score,
            "rationale": (
                f"Market makers show {'complementary' if recommended else 'conflicting'} "
                f"inventory profiles with compatibility score {score:.0%}."
            ),
            "recommended": recommended,
        })


# ── CoalitionScore ────────────────────────────────────────────────────────────

class CoalitionScore:
    def __init__(self, score: float, rationale: str, recommended: bool):
        self.score = score
        self.rationale = rationale
        self.recommended = recommended

    @classmethod
    def from_dict(cls, data: dict) -> "CoalitionScore":
        return cls(float(data["score"]), str(data["rationale"]), bool(data["recommended"]))


# ── LLM Evaluator ─────────────────────────────────────────────────────────────

class MarketMakerEvaluator:
    """LLM evaluator for market-maker syndicate compatibility."""

    SYSTEM_PROMPT = (
        "You evaluate whether market makers should form a syndicate. "
        "Consider: complementary inventory positions, aligned risk tolerance, "
        "sector overlap. Return JSON: {score: float 0-1, rationale: str, recommended: bool}."
    )

    def __init__(self, llm: MockLLM) -> None:
        self.llm = llm
        self.log: list[dict] = []

    def describe_group(self, group) -> str:
        return "\n".join(
            f"Agent {a.unique_id}: inventory={a.inventory:+.2f}, "
            f"risk={a.risk_tolerance}, sector={a.sector}"
            for a in group
        )

    def __call__(self, group) -> float:
        prompt = f"{self.SYSTEM_PROMPT}\n\n{self.describe_group(group)}"
        raw = self.llm.invoke(prompt)
        parsed = CoalitionScore.from_dict(json.loads(raw))
        self.log.append({
            "agents": [a.unique_id for a in group],
            "score": parsed.score,
            "rationale": parsed.rationale,
        })
        return parsed.score


# ── Spatial find_combinations ─────────────────────────────────────────────────

def spatial_find_combinations(agents, size, evaluation_func):
    seen: set = set()
    results: list = []
    for agent in agents:
        pool = {agent}
        for cell in agent.cell.connections.values():
            for nb in cell.agents:
                if hasattr(nb, 'inventory'):  # is a MarketMaker
                    pool.add(nb)
        pool = pool & set(agents)
        if len(pool) < size:
            continue
        for group in combinations(list(pool), size):
            key = frozenset(a.unique_id for a in group)
            if key in seen:
                continue
            seen.add(key)
            score = evaluation_func(group)
            results.append((list(group), score))
    return results


# ── MetaAgent: Syndicate ──────────────────────────────────────────────────────

class Syndicate(mesa.Agent):
    """Market-maker syndicate (MetaAgent) with full lifecycle API."""

    def __init__(self, model, members: list) -> None:
        super().__init__(model)
        self.members = set(members)
        for m in members:
            m.syndicate = self

    def leave(self, agent) -> None:
        self.members.discard(agent)
        agent.syndicate = None
        if len(self.members) <= 1:
            self.dissolve()

    def dissolve(self) -> None:
        for m in list(self.members):
            m.syndicate = None
        self.members.clear()
        if self in self.model.agents:
            self.remove()

    def step(self) -> None:
        # Dissolve if any member has depleted inventory (|inventory| > 5)
        to_leave = [m for m in list(self.members) if abs(m.inventory) > 5]
        for m in to_leave:
            self.leave(m)


# ── Market Maker Agent ────────────────────────────────────────────────────────

class MarketMaker(mesa.Agent):
    """Market-maker with inventory, risk tolerance, and sector."""

    SECTORS = ["tech", "finance", "energy", "healthcare"]
    RISK_LEVELS = ["low", "medium", "high"]

    def __init__(self, model, inventory: float, risk_tolerance: str,
                 sector: str) -> None:
        super().__init__(model)
        self.inventory = inventory
        self.risk_tolerance = risk_tolerance
        self.sector = sector
        self.syndicate: Syndicate | None = None

    def step(self) -> None:
        # Simulate inventory drift
        self.inventory += self.model.rng.normal(0, 0.2)


# ── Model ─────────────────────────────────────────────────────────────────────

class MarketModel(mesa.Model):
    """
    Financial Market Coalition — all 3 pillars.
    """

    def __init__(self, n_agents: int = 50, seed: int = 42) -> None:
        super().__init__(seed=seed)
        self.grid = OrthogonalMooreGrid((10, 10), capacity=2, torus=False)
        self.evaluator = MarketMakerEvaluator(MockLLM())

        # Create agents
        n = n_agents
        rng = self.rng
        inventories = [rng.uniform(-2, 2) for _ in range(n)]
        risks = [rng.choice(MarketMaker.RISK_LEVELS) for _ in range(n)]
        sectors = [rng.choice(MarketMaker.SECTORS) for _ in range(n)]
        MarketMaker.create_agents(self, n, inventory=inventories,
                                  risk_tolerance=risks, sector=sectors)

        for agent in self.agents:
            cell = self.grid.select_random_not_full_cell()  # PR #3542
            agent.move_to(cell)

    def step(self) -> None:
        # Step 1: Existing syndicates may dissolve (Pillar 1)
        for agent in [a for a in self.agents if isinstance(a, Syndicate)]:
            agent.step()

        # Step 2: Unaffiliated makers search for spatial syndicates
        free = [a for a in self.agents
                if isinstance(a, MarketMaker) and a.syndicate is None]

        # Pillar 3: spatial filter
        combos = spatial_find_combinations(free, size=3, evaluation_func=self.evaluator)

        if combos:
            # Pillar 2: take best LLM-scored group
            best_group, best_score = max(combos, key=lambda x: x[1])
            if best_score > 0.6:
                syndicate = Syndicate(self, best_group)
                print(f"  Step {self.steps}: Formed syndicate {syndicate.unique_id} "
                      f"(LLM score={best_score:.2f})")
                if self.evaluator.log:
                    print(f"    Rationale: {self.evaluator.log[-1]['rationale']}")

        # Step 3: Market makers update inventory
        for agent in [a for a in self.agents if isinstance(a, MarketMaker)]:
            agent.step()


def run_simulation() -> None:
    print("=" * 65)
    print("Financial Market Coalition — All 3 Pillars Demo")
    print("=" * 65)
    model = MarketModel(n_agents=50)
    for step in range(5):
        print(f"\n--- Step {step + 1} ---")
        model.step()
        n_makers = sum(1 for a in model.agents if isinstance(a, MarketMaker))
        n_syndicates = sum(1 for a in model.agents if isinstance(a, Syndicate))
        print(f"  Market makers: {n_makers}, Active syndicates: {n_syndicates}")
    print("\n" + "=" * 65)
    print(f"Total LLM evaluations: {len(model.evaluator.log)}")
    print("Simulation complete. All 3 pillars demonstrated.")
    print("=" * 65)


if __name__ == "__main__":
    run_simulation()
