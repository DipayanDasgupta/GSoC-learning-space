"""
Active/Dormant Network PoC
Directly implements Tom Pike's Discussion #3403 vision:
  "every agent has active and dormant links and based on the situation
   activates certain links versus others, which can trigger subclusters"

MetaAgents = currently active subclusters
dormant_links = past coalition partners eligible for reactivation
Usage: python model.py
"""
import mesa
from mesa.experimental.meta_agents.meta_agent import create_meta_agent


class NetworkAgent(mesa.Agent):
    def __init__(self, model, influence: float):
        super().__init__(model)
        self.influence = influence
        self.active_links: set = set()    # partners in current live MetaAgents
        self.dormant_links: set = set()   # past partners (can reactivate)

    def compatible_with(self, other) -> bool:
        return abs(self.influence - other.influence) < 0.3


class NetworkModel(mesa.Model):
    def __init__(self, n=20, seed=42):
        super().__init__(rng=seed)
        influences = [self.rng.uniform(0.1, 1.0) for _ in range(n)]
        NetworkAgent.create_agents(self, n, influences)

        # Seed some dormant links to make reactivation visible from step 1
        agents = list(self.agents)
        for i in range(0, len(agents) - 1, 2):
            agents[i].dormant_links.add(agents[i + 1])
            agents[i + 1].dormant_links.add(agents[i])

    def _active_clusters(self):
        from mesa.experimental.meta_agents.meta_agent import MetaAgent
        return [a for a in self.agents if isinstance(a, MetaAgent)]

    def step(self):
        agents = list(self.agents_by_type.get(NetworkAgent, []))

        # Try to REACTIVATE dormant links between compatible agents
        for a in agents:
            for b in list(a.dormant_links):
                if a.compatible_with(b) and self.random.random() < 0.3:
                    cluster = create_meta_agent(self, "Cluster", [a, b], mesa.Agent)
                    a.active_links.add(b)
                    b.active_links.add(a)
                    a.dormant_links.discard(b)
                    b.dormant_links.discard(a)

        # Randomly DISSOLVE some clusters (links become dormant, not deleted)
        clusters = self._active_clusters()
        for c in clusters:
            if self.random.random() < 0.2:
                members = list(c._constituting_set)
                for m in members:
                    for other in members:
                        if m is not other:
                            m.active_links.discard(other)
                            m.dormant_links.add(other)  # DORMANT, not gone
                c.remove()

        active = len(self._active_clusters())
        dormant_pairs = sum(len(a.dormant_links) for a in agents) // 2
        print(f"Step {int(self.time)}: active_clusters={active}  "
              f"dormant_pairs={dormant_pairs}  total_agents={len(self.agents)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Active/Dormant Network PoC  (Discussion #3403 Vision)")
    print("Agents have active_links (live MetaAgents) + dormant_links")
    print("Network topology adapts; no explicit coordination logic")
    print("=" * 60)
    model = NetworkModel(n=20, seed=42)
    for _ in range(15):
        model.step()
    print("\n[OK] Active/dormant network demo complete.")
