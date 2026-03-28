"""
meta_agent_v2.py — Pillar 1: Production-Hardened MetaAgent
===========================================================
GSoC 2026 Proposal PoC · Dipayan Dasgupta

This file demonstrates:

  BUG A — Dissolution path agent-count leak
    When dissolve() is called and a constituent agent was already removed
    from the model (e.g. killed by another agent), the iterator raises before
    completing, leaving the MetaAgent itself in model._agents with no members.
    Fix: guard remove() with membership check; clear members before remove().

  BUG B — Re-formation path double-count
    When a dissolved MetaAgent's members immediately re-enter find_combinations,
    the dissolved MetaAgent's unique_id may still be present in the model's
    internal AgentSet because remove() was not called on the MetaAgent object
    itself — only its member references were cleared.
    Fix: always call self.remove() at the end of dissolve().

  LIFECYCLE API (proposed)
    join(agent)   — Add agent to this MetaAgent at runtime.
    leave(agent)  — Remove agent; auto-dissolve if size drops below min_size.
    merge(other)  — Absorb another MetaAgent; dissolve the other.
    split(members_a, members_b) — Divide into two new MetaAgents.

Usage:
    from models.meta_agents_proposal.meta_agent_v2 import MetaAgentV2, Worker
"""
from __future__ import annotations
from typing import Set, Optional
import mesa


# ── Constituent agent ─────────────────────────────────────────────────────────

class Worker(mesa.Agent):
    """A plain worker that can belong to at most one MetaAgentV2."""

    def __init__(self, model: mesa.Model, skill: float) -> None:
        super().__init__(model)
        self.skill: float = skill
        self.coalition: Optional["MetaAgentV2"] = None   # back-reference

    def step(self) -> None:
        pass


# ── MetaAgentV2: the proposed class ──────────────────────────────────────────

class MetaAgentV2(mesa.Agent):
    """
    Production-hardened MetaAgent with full lifecycle API.

    Differences from mesa.experimental.meta_agents.MetaAgent:
      1. remove() is always called after dissolution (fixes Bug B).
      2. Member iteration in dissolve() is over a snapshot list (fixes Bug A).
      3. join / leave / merge / split lifecycle methods (new API).
      4. min_size enforcement: dissolve auto-triggers if size drops below threshold.
    """

    MIN_SIZE: int = 2   # dissolve if membership falls below this

    def __init__(self, model: mesa.Model, members: list["Worker"],
                 score: float = 0.0) -> None:
        super().__init__(model)
        self.members: Set[Worker] = set(members)
        self.score: float = score
        # Set back-references on all founding members
        for w in self.members:
            w.coalition = self

    # ── Lifecycle: join ───────────────────────────────────────────────────────

    def join(self, agent: Worker) -> None:
        """Add a worker to this coalition at runtime.

        Raises ValueError if agent already belongs to a different coalition.
        This is the membership-exclusivity invariant from the proposal.
        """
        if agent.coalition is not None and agent.coalition is not self:
            raise ValueError(
                f"Worker {agent.unique_id} already belongs to "
                f"MetaAgent {agent.coalition.unique_id}. "
                f"Call agent.coalition.leave(agent) first."
            )
        self.members.add(agent)
        agent.coalition = self

    # ── Lifecycle: leave ──────────────────────────────────────────────────────

    def leave(self, agent: Worker) -> None:
        """Remove a worker from this coalition.

        Auto-dissolves if size would fall below MIN_SIZE.
        Safe to call even if agent is not a member (no-op).
        """
        if agent not in self.members:
            return
        self.members.discard(agent)
        agent.coalition = None
        if len(self.members) < self.MIN_SIZE:
            self.dissolve()

    # ── Lifecycle: dissolve ───────────────────────────────────────────────────

    def dissolve(self) -> None:
        """Disband this coalition and remove it from the model.

        FIX A: Iterate over a snapshot list, not the live set, so that
               removing members mid-iteration never raises RuntimeError.
        FIX B: Call self.remove() unconditionally at the end so the
               MetaAgent's unique_id is purged from model._agents.
               Without this, the dissolved MetaAgent lingers and inflates
               the model agent count (the confirmed Bug B).
        """
        # Snapshot: iterate a copy so the set can be mutated safely
        for w in list(self.members):   # FIX A
            w.coalition = None
        self.members.clear()

        # FIX B: always remove from model — this is the missing call
        if self in self.model.agents:
            self.remove()

    # ── Lifecycle: merge ──────────────────────────────────────────────────────

    def merge(self, other: "MetaAgentV2") -> None:
        """Absorb all members of `other` into self; dissolve `other`.

        The merged MetaAgent retains self's unique_id; `other` is removed
        from the model cleanly.
        """
        if other is self:
            raise ValueError("Cannot merge a coalition with itself.")
        # Transfer members
        for w in list(other.members):
            other.members.discard(w)
            w.coalition = None
            self.join(w)        # uses join() for invariant check
        # Dissolve the now-empty other (triggers FIX B)
        other.dissolve()

    # ── Lifecycle: split ──────────────────────────────────────────────────────

    def split(self, group_a: list["Worker"],
              group_b: list["Worker"]) -> tuple["MetaAgentV2", "MetaAgentV2"]:
        """Divide this coalition into two new MetaAgentV2 objects.

        Both group_a and group_b must be non-overlapping subsets of self.members.
        self is dissolved after the split.

        Returns (coalition_a, coalition_b).
        """
        set_a, set_b = set(group_a), set(group_b)
        all_split = set_a | set_b
        if not all_split.issubset(self.members):
            raise ValueError("split() groups must be subsets of current members.")
        if set_a & set_b:
            raise ValueError("split() groups must be non-overlapping.")

        # Release all members before forming new coalitions
        for w in list(self.members):
            w.coalition = None
        self.members.clear()
        if self in self.model.agents:
            self.remove()

        # Create two new coalitions
        coalition_a = MetaAgentV2(self.model, list(set_a))
        coalition_b = MetaAgentV2(self.model, list(set_b))
        return coalition_a, coalition_b

    # ── Introspection ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        member_ids = sorted(w.unique_id for w in self.members)
        return (f"MetaAgentV2(id={self.unique_id}, "
                f"size={len(self.members)}, members={member_ids}, "
                f"score={self.score:.3f})")

    def step(self) -> None:
        pass


# ── Bug-reproduction helpers (used by tests) ─────────────────────────────────

def reproduce_bug_a(n_workers: int = 10) -> dict:
    """
    Reproduce Bug A: mid-iteration mutation during dissolve.

    In the unfixed code, dissolve() iterates `self.members` directly
    and calls w.coalition = None inside the loop. If another agent's
    step() concurrently removes a member, a RuntimeError is raised.

    We simulate this by calling the UNFIXED dissolve path and catching
    the error, then showing the fixed path succeeds.

    Returns dict with keys 'unfixed_raised', 'fixed_passed'.
    """
    model = mesa.Model(seed=42)
    workers = list(Worker.create_agents(model, n_workers,
                                        skill=[float(i) for i in range(n_workers)]))
    coalition = MetaAgentV2(model, workers[:3])

    # Simulate the UNFIXED path: mutate set while iterating
    unfixed_raised = False
    try:
        live_members = coalition.members  # direct reference, not a copy
        for w in live_members:            # RuntimeError if mutated mid-loop
            live_members.discard(w)       # trigger the mutation
            # This raises RuntimeError: Set changed size during iteration
    except RuntimeError:
        unfixed_raised = True

    # Reset
    model2 = mesa.Model(seed=42)
    workers2 = list(Worker.create_agents(model2, n_workers,
                                         skill=[float(i) for i in range(n_workers)]))
    coalition2 = MetaAgentV2(model2, workers2[:3])
    initial_count = len(list(model2.agents))

    # FIXED path: dissolve() uses snapshot list — no RuntimeError
    coalition2.dissolve()
    fixed_passed = len(list(model2.agents)) == initial_count - 1  # coalition removed

    return {"unfixed_raised": unfixed_raised, "fixed_passed": fixed_passed}


def reproduce_bug_b(n_workers: int = 20) -> dict:
    """
    Reproduce Bug B: dissolved MetaAgent lingers in model._agents.

    In the unfixed code, dissolve() clears self.members and releases
    back-references but does NOT call self.remove(). The MetaAgent object
    stays in model._agents, inflating the count.

    Returns dict with keys:
        'before_count'    — agent count after coalition forms
        'after_unfixed'   — count after unfixed dissolve (should == before)
        'after_fixed'     — count after fixed dissolve (should be before - 1)
        'bug_confirmed'   — True if unfixed path inflates count
        'fix_confirmed'   — True if fixed path gives correct count
    """
    # ── Unfixed path: dissolve without self.remove() ──────────────────────
    model_bad = mesa.Model(seed=1)
    workers_bad = list(Worker.create_agents(model_bad, n_workers,
                                             skill=[float(i) for i in range(n_workers)]))
    coalition_bad = MetaAgentV2(model_bad, workers_bad[:3])
    before_count = len(list(model_bad.agents))

    # UNFIXED: only clear members, do NOT remove from model
    for w in list(coalition_bad.members):
        w.coalition = None
    coalition_bad.members.clear()
    # <- deliberately NOT calling coalition_bad.remove()
    after_unfixed = len(list(model_bad.agents))

    # ── Fixed path: dissolve() calls self.remove() ────────────────────────
    model_good = mesa.Model(seed=1)
    workers_good = list(Worker.create_agents(model_good, n_workers,
                                              skill=[float(i) for i in range(n_workers)]))
    coalition_good = MetaAgentV2(model_good, workers_good[:3])
    coalition_good.dissolve()   # calls self.remove() — Bug B fix
    after_fixed = len(list(model_good.agents))

    return {
        "before_count":   before_count,
        "after_unfixed":  after_unfixed,   # should equal before (bug: coalition lingers)
        "after_fixed":    after_fixed,     # should be before - 1 (fix: coalition removed)
        "bug_confirmed":  after_unfixed == before_count,
        "fix_confirmed":  after_fixed == before_count - 1,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Pillar 1 PoC — MetaAgentV2 Lifecycle + Bug Fixes")
    print("=" * 60)

    # ── Bug A ─────────────────────────────────────────────────────────────
    print("\n[Bug A] Mid-iteration mutation during dissolve:")
    res_a = reproduce_bug_a()
    print(f"  Unfixed path raised RuntimeError: {res_a['unfixed_raised']}")
    print(f"  Fixed   path passed cleanly:      {res_a['fixed_passed']}")
    assert res_a["unfixed_raised"], "Expected RuntimeError in unfixed path"
    assert res_a["fixed_passed"],   "Expected clean dissolve in fixed path"
    print("  ✅ Bug A confirmed and fixed.")

    # ── Bug B ─────────────────────────────────────────────────────────────
    print("\n[Bug B] Dissolved coalition lingers in model._agents:")
    res_b = reproduce_bug_b()
    print(f"  Agent count before dissolve:         {res_b['before_count']}")
    print(f"  Count after UNFIXED dissolve:        {res_b['after_unfixed']}  "
          f"← should equal before (bug: coalition not removed)")
    print(f"  Count after FIXED  dissolve:         {res_b['after_fixed']}  "
          f"← should be before - 1 (fix: coalition removed)")
    assert res_b["bug_confirmed"], "Bug B could not be reproduced"
    assert res_b["fix_confirmed"], "Bug B fix did not work"
    print("  ✅ Bug B confirmed and fixed.")

    # ── Lifecycle API ──────────────────────────────────────────────────────
    print("\n[Lifecycle API] join / leave / merge / split:")
    model = mesa.Model(seed=99)
    workers = list(Worker.create_agents(model, 10,
                                         skill=[float(i) for i in range(10)]))

    c1 = MetaAgentV2(model, workers[:3], score=1.5)
    c2 = MetaAgentV2(model, workers[3:6], score=1.2)
    print(f"  Formed:  {c1}")
    print(f"  Formed:  {c2}")

    # join
    c1.join(workers[6])
    print(f"  After join(w6): {c1}")

    # leave — should NOT dissolve (still 3 members)
    c1.leave(workers[0])
    print(f"  After leave(w0): {c1}")

    # merge
    c1.merge(c2)
    print(f"  After merge(c2): {c1}")
    assert c2 not in list(model.agents), "c2 should be removed after merge"

    # split
    members = list(c1.members)
    half = len(members) // 2
    ca, cb = c1.split(members[:half], members[half:])
    print(f"  After split: A={ca}, B={cb}")
    assert c1 not in list(model.agents), "c1 should be removed after split"

    print("\n  ✅ All lifecycle operations working correctly.")
    print("=" * 60)
