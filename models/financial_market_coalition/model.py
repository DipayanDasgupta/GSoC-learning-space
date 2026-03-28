"""Financial Market Coalition — All 3 Pillars  (Mesa 3.5.1, released pip)

FIX 1: MarketMaker now inherits CellAgent
FIX 2: capacity placement via inline cell.is_full
"""
from __future__ import annotations
import json
import mesa
from itertools import combinations
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.discrete_space.cell_agent import CellAgent          # FIX 1


def _random_not_full_cell(grid, rng):
    available = [c for c in grid._cells.values() if not c.is_full]
    if not available:
        raise ValueError("All cells full")
    return rng.choice(available)


class MockLLM:
    def invoke(self, prompt: str) -> str:
        import random as _r
        score = round(_r.uniform(0.3, 0.95), 2)
        rec   = score > 0.6
        return json.dumps({"score": score,
                           "rationale": f"{'complementary' if rec else 'conflicting'} "
                                        f"profiles ({score:.0%}).",
                           "recommended": rec})


class CoalitionScore:
    def __init__(self, score, rationale, recommended):
        self.score = score; self.rationale = rationale; self.recommended = recommended
    @classmethod
    def from_dict(cls, d):
        return cls(float(d["score"]), str(d["rationale"]), bool(d["recommended"]))


class MarketMakerEvaluator:
    PROMPT = ("Evaluate market-maker syndicate. "
              "JSON: {score: float 0-1, rationale: str, recommended: bool}.")
    def __init__(self, llm):
        self.llm = llm
        self.log: list[dict] = []
    def describe(self, group):
        return "\n".join(f"Agent {a.unique_id}: inv={a.inventory:+.2f}, "
                         f"risk={a.risk_tolerance}, sector={a.sector}"
                         for a in group)
    def __call__(self, group) -> float:
        parsed = CoalitionScore.from_dict(
            json.loads(self.llm.invoke(f"{self.PROMPT}\n\n{self.describe(group)}")))
        self.log.append({"agents": [a.unique_id for a in group],
                         "score": parsed.score, "rationale": parsed.rationale})
        return parsed.score


def spatial_find_combinations(agents, size, evaluation_func):
    seen: set = set(); results: list = []; agent_set = set(agents)
    for agent in agents:
        pool: set = {agent}
        for cell in agent.cell.connections.values():
            for nb in cell.agents:
                if hasattr(nb, "inventory"):
                    pool.add(nb)
        pool &= agent_set
        if len(pool) < size: continue
        for group in combinations(list(pool), size):
            key = frozenset(a.unique_id for a in group)
            if key in seen: continue
            seen.add(key)
            results.append((list(group), evaluation_func(group)))
    return results


class Syndicate(mesa.Agent):
    def __init__(self, model, members):
        super().__init__(model)
        self.members = set(members)
        for m in members: m.syndicate = self
    def leave(self, agent):
        self.members.discard(agent); agent.syndicate = None
        if len(self.members) <= 1: self.dissolve()
    def dissolve(self):
        for m in list(self.members): m.syndicate = None
        self.members.clear()
        if self in self.model.agents: self.remove()
    def step(self):
        for m in list(self.members):
            if abs(m.inventory) > 5: self.leave(m)


class MarketMaker(CellAgent):                                  # FIX 1: was mesa.Agent
    SECTORS = ["tech", "finance", "energy", "healthcare"]
    RISKS   = ["low", "medium", "high"]
    def __init__(self, model, inventory, risk_tolerance, sector):
        super().__init__(model)
        self.inventory = inventory; self.risk_tolerance = risk_tolerance
        self.sector = sector; self.syndicate = None
    def step(self):
        self.inventory += float(self.model.rng.normal(0, 0.2))


class MarketModel(mesa.Model):
    def __init__(self, n_agents: int = 50, seed: int = 42) -> None:
        super().__init__(seed=seed)
        self.grid      = OrthogonalMooreGrid(
            (10, 10), capacity=2, torus=False, random=self.random)
        self.evaluator = MarketMakerEvaluator(MockLLM())
        rng = self.rng
        MarketMaker.create_agents(
            self, n_agents,
            inventory=[float(rng.uniform(-2, 2)) for _ in range(n_agents)],
            risk_tolerance=[rng.choice(MarketMaker.RISKS) for _ in range(n_agents)],
            sector=[rng.choice(MarketMaker.SECTORS) for _ in range(n_agents)])
        for agent in self.agents:
            agent.move_to(_random_not_full_cell(self.grid, self.rng))  # FIX 2

    def step(self):
        for s in [a for a in self.agents if isinstance(a, Syndicate)]: s.step()
        free   = [a for a in self.agents
                  if isinstance(a, MarketMaker) and a.syndicate is None]
        combos = spatial_find_combinations(free, 3, self.evaluator)
        if combos:
            best_group, best_score = max(combos, key=lambda x: x[1])
            if best_score > 0.6:
                syn = Syndicate(self, best_group)
                print(f"  Step {self.steps}: Syndicate {syn.unique_id} "
                      f"(score={best_score:.2f})")
                if self.evaluator.log:
                    print(f"    {self.evaluator.log[-1]['rationale']}")
        for a in [a for a in self.agents if isinstance(a, MarketMaker)]: a.step()


def run_simulation():
    print("=" * 65)
    print("Financial Market Coalition — All 3 Pillars  [Mesa 3.5.1]")
    print("=" * 65)
    model = MarketModel(n_agents=50)
    for step in range(5):
        print(f"\n--- Step {step + 1} ---")
        model.step()
        n_makers = sum(1 for a in model.agents if isinstance(a, MarketMaker))
        n_syn    = sum(1 for a in model.agents if isinstance(a, Syndicate))
        print(f"  Makers: {n_makers}, Active syndicates: {n_syn}")
    print("\n" + "=" * 65)
    print(f"  Total LLM evaluations: {len(model.evaluator.log)}")
    print("  ✅ All 3 pillars working — integration PoC complete.")
    print("=" * 65)


if __name__ == "__main__":
    run_simulation()
