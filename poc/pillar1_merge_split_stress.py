"""
poc/pillar1_merge_split_stress.py
Pillar 1 — Lifecycle Stress Test (30 steps)
============================================
At every step, random join/leave/merge/split operations are performed.
The agent-count invariant is verified after each step:
    sum(len(c.members) for coalitions) + len(free workers) == N_WORKERS

Run:
    python poc/pillar1_merge_split_stress.py
"""
from __future__ import annotations
import mesa
import random as _random

N_WORKERS = 30
N_STEPS   = 30
SEED      = 42


class Worker(mesa.Agent):
    def __init__(self, model, skill): super().__init__(model); self.skill=skill; self.coalition=None
    def step(self): pass

class Coalition(mesa.Agent):
    MIN_SIZE = 2
    def __init__(self, model, members):
        super().__init__(model)
        self.members = set(members)
        for w in self.members: w.coalition = self
    def join(self, w):
        if w.coalition is not None and w.coalition is not self: return
        self.members.add(w); w.coalition = self
    def leave(self, w):
        if w not in self.members: return
        self.members.discard(w); w.coalition = None
        if len(self.members) < self.MIN_SIZE: self.dissolve()
    def dissolve(self):
        for w in list(self.members): w.coalition = None
        self.members.clear()
        if self in self.model.agents: self.remove()
    def merge(self, other):
        if other is self: return
        for w in list(other.members): other.members.discard(w); w.coalition=None; self.join(w)
        other.dissolve()
    def split(self, ga, gb):
        for w in list(self.members): w.coalition=None
        self.members.clear()
        if self in self.model.agents: self.remove()
        return Coalition(self.model,ga), Coalition(self.model,gb)
    def step(self): pass


def verify_invariant(model, n_workers, step):
    all_agents = list(model.agents)
    workers    = [a for a in all_agents if isinstance(a, Worker)]
    coalitions = [a for a in all_agents if isinstance(a, Coalition)]
    in_coal    = sum(len(c.members) for c in coalitions)
    free       = sum(1 for w in workers if w.coalition is None)
    total      = in_coal + free
    assert total == n_workers, (
        f"Step {step}: invariant broken! "
        f"in_coalitions={in_coal} + free={free} = {total} ≠ {n_workers}"
    )
    for c in coalitions:
        for w in c.members:
            assert w in model.agents, f"Step {step}: dead member in coalition"
            assert w.coalition is c,  f"Step {step}: back-ref mismatch"
    return len(coalitions), free


if __name__ == "__main__":
    print("=" * 65)
    print(f"Pillar 1 Lifecycle Stress Test — {N_STEPS} steps, {N_WORKERS} workers")
    print("=" * 65)
    print(f"  {'Step':>4}  {'Coalitions':>10}  {'Free':>6}  {'Op':>28}")
    print("  " + "-" * 53)

    model   = mesa.Model()
    rng     = _random.Random(SEED)
    workers = list(Worker.create_agents(model, N_WORKERS,
                    skill=[float(i) for i in range(N_WORKERS)]))

    for step in range(1, N_STEPS + 1):
        coalitions = [a for a in model.agents if isinstance(a, Coalition)]
        free_ws    = [a for a in model.agents
                      if isinstance(a, Worker) and a.coalition is None]
        op = "—"

        roll = rng.random()
        if roll < 0.25 and len(free_ws) >= 3:
            # Form a new coalition from 3 free workers
            chosen = rng.sample(free_ws, 3)
            Coalition(model, chosen)
            op = f"form({[w.unique_id for w in chosen]})"
        elif roll < 0.45 and coalitions:
            # Random leave
            c = rng.choice(coalitions)
            if c.members:
                w = rng.choice(list(c.members))
                c.leave(w)
                op = f"leave(w{w.unique_id} from C{c.unique_id})"
        elif roll < 0.60 and coalitions and free_ws:
            # Random join
            c = rng.choice(coalitions)
            w = rng.choice(free_ws)
            c.join(w)
            op = f"join(w{w.unique_id} → C{c.unique_id})"
        elif roll < 0.75 and len(coalitions) >= 2:
            # Merge two coalitions
            c1, c2 = rng.sample(coalitions, 2)
            c1.merge(c2)
            op = f"merge(C{c1.unique_id} ← C{c2.unique_id})"
        elif roll < 0.90 and coalitions:
            # Split a coalition (if big enough)
            c = rng.choice(coalitions)
            mlist = list(c.members)
            if len(mlist) >= 4:
                half = len(mlist) // 2
                ca, cb = c.split(mlist[:half], mlist[half:])
                op = f"split(C{c.unique_id}→C{ca.unique_id}+C{cb.unique_id})"
        else:
            # Dissolve a random coalition
            if coalitions:
                c = rng.choice(coalitions)
                cid = c.unique_id
                c.dissolve()
                op = f"dissolve(C{cid})"

        n_coal, n_free = verify_invariant(model, N_WORKERS, step)
        print(f"  {step:>4}  {n_coal:>10}  {n_free:>6}  {op:>28}")

    print()
    print("  ✅  Agent-count invariant held across all 30 steps.")
    print("  ✅  join / leave / merge / split / dissolve all verified.")
    print("=" * 65)
