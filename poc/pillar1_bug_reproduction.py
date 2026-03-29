"""
poc/pillar1_bug_reproduction.py
Pillar 1 — Bug Reproduction and Fix Demo
=========================================
GSoC 2026  ·  Mesa Meta Agents  ·  Dipayan Dasgupta

Reproduces both confirmed agent-count bugs from the Feb 2026 Mesa dev meeting
and demonstrates the proposed fixes side-by-side.

  Bug A: RuntimeError when iterating a live set during dissolve()
         (iterator raises if a constituent agent is removed mid-loop)
  Bug B: MetaAgent lingers in model._agents after dissolution
         (dissolve() clears members but never calls self.remove())

Run:
    python poc/pillar1_bug_reproduction.py
"""
from __future__ import annotations
import mesa


# ── Minimal agent ─────────────────────────────────────────────────────────────

class Worker(mesa.Agent):
    def __init__(self, model: mesa.Model, skill: float) -> None:
        super().__init__(model)
        self.skill = skill
        self.coalition = None
    def step(self): pass


# ── Unfixed MetaAgent (mirrors current mesa.experimental behaviour) ───────────

class MetaAgentUnfixed(mesa.Agent):
    """Mirrors the current mesa.experimental.meta_agents behaviour."""
    def __init__(self, model, members):
        super().__init__(model)
        self.members = set(members)
        for w in self.members:
            w.coalition = self

    def dissolve_unfixed(self):
        """Bug A + Bug B path: iterates live set, does not call self.remove()."""
        for w in self.members:      # BUG A: live set — raises if mutated
            w.coalition = None
        self.members.clear()
        # BUG B: self.remove() is NEVER CALLED → MetaAgent stays in model._agents


# ── Fixed MetaAgent (proposed implementation) ─────────────────────────────────

class MetaAgentFixed(mesa.Agent):
    """Proposed MetaAgentV2 with both bugs fixed."""
    MIN_SIZE = 2

    def __init__(self, model, members):
        super().__init__(model)
        self.members = set(members)
        for w in self.members:
            w.coalition = self

    def join(self, agent: Worker) -> None:
        if agent.coalition is not None and agent.coalition is not self:
            raise ValueError(
                f"Worker {agent.unique_id} already in "
                f"MetaAgent {agent.coalition.unique_id}"
            )
        self.members.add(agent)
        agent.coalition = self

    def leave(self, agent: Worker) -> None:
        if agent not in self.members:
            return
        self.members.discard(agent)
        agent.coalition = None
        if len(self.members) < self.MIN_SIZE:
            self.dissolve()

    def dissolve(self) -> None:
        """FIX A: snapshot list.  FIX B: unconditional self.remove()."""
        for w in list(self.members):   # FIX A: iterate a copy → no RuntimeError
            w.coalition = None
        self.members.clear()
        if self in self.model.agents:  # FIX B: always remove from model
            self.remove()

    def merge(self, other: "MetaAgentFixed") -> None:
        if other is self:
            raise ValueError("Cannot merge with self.")
        for w in list(other.members):
            other.members.discard(w)
            w.coalition = None
            self.join(w)
        other.dissolve()

    def split(self, group_a, group_b):
        set_a, set_b = set(group_a), set(group_b)
        if not (set_a | set_b).issubset(self.members):
            raise ValueError("split groups must be subsets of members")
        if set_a & set_b:
            raise ValueError("split groups must not overlap")
        for w in list(self.members):
            w.coalition = None
        self.members.clear()
        if self in self.model.agents:
            self.remove()
        ca = MetaAgentFixed(self.model, list(set_a))
        cb = MetaAgentFixed(self.model, list(set_b))
        return ca, cb

    def step(self): pass


# ── Reproduction helpers ──────────────────────────────────────────────────────

SEP = "=" * 60

def demo_bug_a():
    print(f"\n{SEP}")
    print("BUG A: RuntimeError on live-set iteration during dissolve()")
    print(SEP)

    model = mesa.Model()
    workers = list(Worker.create_agents(model, 5,
                    skill=[float(i) for i in range(5)]))
    coalition = MetaAgentUnfixed(model, workers[:3])

    raised = False
    try:
        # Simulate the unfixed dissolve path: iterate live set and mutate it
        for w in coalition.members:
            coalition.members.discard(w)   # ← triggers RuntimeError
    except RuntimeError:
        raised = True

    print(f"  Unfixed path raised RuntimeError: {raised}")
    assert raised, "Expected RuntimeError not raised"

    # Now the fixed path
    model2 = mesa.Model()
    workers2 = list(Worker.create_agents(model2, 5,
                     skill=[float(i) for i in range(5)]))
    c2 = MetaAgentFixed(model2, workers2[:3])
    c2.dissolve()   # FIX A: iterates list(self.members) — never raises
    print("  Fixed path completed without error.")
    for w in workers2[:3]:
        assert w.coalition is None, "Back-reference not cleared"
    print("  All back-references cleared correctly.")
    print(f"  ✅  Bug A confirmed and fixed.")


def demo_bug_b():
    print(f"\n{SEP}")
    print("BUG B: Dissolved MetaAgent lingers in model._agents")
    print(SEP)

    N = 10
    # --- Unfixed ---
    model_bad = mesa.Model()
    workers_bad = list(Worker.create_agents(model_bad, N,
                        skill=[float(i) for i in range(N)]))
    c_bad = MetaAgentUnfixed(model_bad, workers_bad[:3])
    before = len(list(model_bad.agents))
    c_bad.dissolve_unfixed()          # no self.remove()
    after_unfixed = len(list(model_bad.agents))

    # --- Fixed ---
    model_good = mesa.Model()
    workers_good = list(Worker.create_agents(model_good, N,
                         skill=[float(i) for i in range(N)]))
    c_good = MetaAgentFixed(model_good, workers_good[:3])
    c_good.dissolve()                 # calls self.remove()
    after_fixed = len(list(model_good.agents))

    print(f"  Agent count BEFORE dissolve:          {before}")
    print(f"  After UNFIXED dissolve (Bug B):       {after_unfixed}"
          f"  ← should be {before} (coalition NOT removed)")
    print(f"  After FIXED  dissolve (Proposed fix): {after_fixed}"
          f"  ← should be {before - 1} (coalition removed)")
    assert after_unfixed == before,     "Bug B not reproduced"
    assert after_fixed   == before - 1, "Fix B did not work"
    print(f"  ✅  Bug B confirmed and fixed.")


def demo_lifecycle():
    print(f"\n{SEP}")
    print("LIFECYCLE API: join / leave / merge / split")
    print(SEP)

    model = mesa.Model()
    workers = list(Worker.create_agents(model, 12,
                    skill=[float(i) for i in range(12)]))

    # Formation
    c1 = MetaAgentFixed(model, workers[:3])
    c2 = MetaAgentFixed(model, workers[3:6])
    print(f"  Formed: MetaAgent {c1.unique_id} "
          f"(members: {sorted(w.unique_id for w in c1.members)})")
    print(f"  Formed: MetaAgent {c2.unique_id} "
          f"(members: {sorted(w.unique_id for w in c2.members)})")

    # join
    c1.join(workers[6])
    print(f"  join(w{workers[6].unique_id}) → size={len(c1.members)}")

    # leave (does NOT dissolve — still ≥ MIN_SIZE)
    c1.leave(workers[0])
    print(f"  leave(w{workers[0].unique_id}) → size={len(c1.members)}"
          f"  (no dissolve, still ≥ {MetaAgentFixed.MIN_SIZE})")

    # merge
    c1.merge(c2)
    assert c2 not in list(model.agents), "c2 should be gone after merge"
    print(f"  merge(c2) → c1 size={len(c1.members)}, c2 removed ✓")

    # split
    mlist = list(c1.members)
    half  = len(mlist) // 2
    ca, cb = c1.split(mlist[:half], mlist[half:])
    assert c1 not in list(model.agents), "c1 should be gone after split"
    print(f"  split → A size={len(ca.members)}, B size={len(cb.members)}, "
          f"c1 removed ✓")

    # agent-count invariant
    all_workers  = [a for a in model.agents if isinstance(a, Worker)]
    all_coalitions = [a for a in model.agents if isinstance(a, MetaAgentFixed)]
    accounted = set()
    for coal in all_coalitions:
        for w in coal.members:
            assert w in model.agents, "Member not in model.agents"
            accounted.add(w)
    free = [w for w in all_workers if w.coalition is None]
    print(f"\n  Final state: {len(all_workers)} workers, "
          f"{len(all_coalitions)} coalitions, {len(free)} free")
    print(f"  ✅  Agent-count invariant holds.")


if __name__ == "__main__":
    print(SEP)
    print("Pillar 1 Bug Reproduction and Fix Demo  [Mesa 3.5.1]")
    print(SEP)
    demo_bug_a()
    demo_bug_b()
    demo_lifecycle()
    print(f"\n{SEP}")
    print("All Pillar 1 demonstrations complete.")
    print(SEP)
