"""
Registry Management PoC
Demonstrates _meta_membership index correctness across 30 steps.
Directly addresses the GSoC 2026 goal: "optimizing registry management".
Usage: python model.py
"""
import mesa
from mesa.experimental.meta_agents.meta_agent import create_meta_agent


class Worker(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)


class RegistryModel(mesa.Model):
    def __init__(self, n=30, seed=42):
        super().__init__(rng=seed)
        self._meta_membership: dict = {}   # agent -> set of coalitions
        Worker.create_agents(self, n)

    def _form_coalition(self, workers):
        """Form a coalition and register all members."""
        meta = create_meta_agent(self, "Coalition", workers, mesa.Agent)
        for w in workers:
            self._meta_membership.setdefault(w, set()).add(meta)
        return meta

    def _dissolve_coalition(self, meta):
        """Dissolve a coalition and clean the registry."""
        for w in list(meta._constituting_set):
            if w in self._meta_membership:
                self._meta_membership[w].discard(meta)
                if not self._meta_membership[w]:
                    del self._meta_membership[w]
        meta.remove()

    def _check_invariant(self):
        """Assert registry is consistent with live coalitions."""
        from mesa.experimental.meta_agents.meta_agent import MetaAgent
        coalitions = [a for a in self.agents if isinstance(a, MetaAgent)]
        members_in_coalitions = sum(
            len(c._constituting_set) for c in coalitions
        )
        registry_total = sum(
            len(v) for v in self._meta_membership.values()
        )
        # Each (agent, coalition) pair counted once in each direction
        assert registry_total == members_in_coalitions, (
            f"Registry out of sync: {registry_total} != {members_in_coalitions}"
        )
        return len([a for a in self.agents if isinstance(a, Worker)]), len(coalitions)

    def step(self):
        workers = [a for a in self.agents
                   if not hasattr(a, '_constituting_set')]
        # Occasionally form a coalition
        if len(workers) >= 3 and self.random.random() < 0.4:
            group = self.random.sample(workers, 3)
            self._form_coalition(group)

        # Occasionally dissolve one
        from mesa.experimental.meta_agents.meta_agent import MetaAgent
        coalitions = [a for a in self.agents if isinstance(a, MetaAgent)]
        if coalitions and self.random.random() < 0.3:
            self._dissolve_coalition(self.random.choice(coalitions))

        w, c = self._check_invariant()
        print(f"Step {int(self.time):3d}: workers={w:3d}  coalitions={c:2d}  "
              f"registry_entries={len(self._meta_membership):3d}")


if __name__ == "__main__":
    print("=" * 60)
    print("Registry Management PoC  [Mesa]")
    print("Verifying _meta_membership invariant across 30 steps")
    print("=" * 60)
    model = RegistryModel(n=30, seed=42)
    for _ in range(30):
        model.step()
    print("\n[OK] Registry invariant held across all 30 steps.")
