"""
test_lifecycle.py — Pillar 1: MetaAgentV2 Lifecycle Tests
=========================================================
Tests:
  • Bug A reproduction: RuntimeError on direct-set iteration during dissolve
  • Bug B reproduction: dissolved coalition lingers in model._agents
  • Bug A fix: snapshot-list dissolve never raises
  • Bug B fix: model agent count decrements correctly after dissolve
  • join: membership exclusivity invariant
  • leave: auto-dissolve when size < MIN_SIZE
  • merge: both coalitions correct; source removed from model
  • split: both halves correct; original removed from model
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import mesa
from meta_agent_v2 import MetaAgentV2, Worker, reproduce_bug_a, reproduce_bug_b


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def model_and_workers():
    model   = mesa.Model(seed=42)
    workers = list(Worker.create_agents(
        model, 12, skill=[float(i) for i in range(12)]
    ))
    return model, workers


# ── Bug reproduction ──────────────────────────────────────────────────────────

def test_bug_a_reproduced():
    """Direct-set iteration raises RuntimeError — confirms the bug exists."""
    result = reproduce_bug_a()
    assert result["unfixed_raised"], (
        "Bug A could not be reproduced. The unfixed path should raise RuntimeError "
        "when the set is mutated during iteration."
    )


def test_bug_a_fixed():
    """Snapshot-list dissolve completes without RuntimeError."""
    result = reproduce_bug_a()
    assert result["fixed_passed"], (
        "Bug A fix failed: dissolve() with snapshot list should not raise."
    )


def test_bug_b_reproduced():
    """Unfixed dissolve leaves coalition in model._agents (count unchanged)."""
    result = reproduce_bug_b()
    assert result["bug_confirmed"], (
        "Bug B could not be reproduced. The unfixed dissolve path should leave "
        "the coalition object in model._agents."
    )


def test_bug_b_fixed():
    """Fixed dissolve removes coalition from model._agents (count decrements)."""
    result = reproduce_bug_b()
    assert result["fix_confirmed"], (
        "Bug B fix failed: dissolve() should call self.remove() so the coalition "
        "is removed from model._agents."
    )


# ── Lifecycle: join ───────────────────────────────────────────────────────────

def test_join_adds_member(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    c.join(workers[3])
    assert workers[3] in c.members
    assert workers[3].coalition is c


def test_join_sets_back_reference(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    c.join(workers[4])
    assert workers[4].coalition is c


def test_join_rejects_already_members(model_and_workers):
    """Joining the same agent to two different coalitions raises ValueError."""
    model, workers = model_and_workers
    c1 = MetaAgentV2(model, workers[:3])
    c2 = MetaAgentV2(model, workers[3:6])
    with pytest.raises(ValueError, match="already belongs to"):
        c2.join(workers[0])   # workers[0] is already in c1


def test_join_idempotent_same_coalition(model_and_workers):
    """Joining the same coalition twice is a no-op, not an error."""
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    c.join(workers[0])   # already a member
    assert len(c.members) == 3   # no duplicate


# ── Lifecycle: leave ──────────────────────────────────────────────────────────

def test_leave_removes_member(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:4])
    c.leave(workers[0])
    assert workers[0] not in c.members
    assert workers[0].coalition is None


def test_leave_clears_back_reference(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:4])
    c.leave(workers[1])
    assert workers[1].coalition is None


def test_leave_triggers_auto_dissolve(model_and_workers):
    """Coalition with 2 members auto-dissolves when one leaves."""
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:2])
    cid = c.unique_id
    c.leave(workers[0])
    # Coalition should be removed from model
    assert c not in list(model.agents), (
        "Coalition with 1 member should auto-dissolve and be removed from model"
    )


def test_leave_noop_for_non_member(model_and_workers):
    """leave() on a non-member is a safe no-op."""
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    before = len(c.members)
    c.leave(workers[9])   # not a member
    assert len(c.members) == before


# ── Lifecycle: dissolve ───────────────────────────────────────────────────────

def test_dissolve_removes_from_model(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    count_before = len(list(model.agents))
    c.dissolve()
    count_after = len(list(model.agents))
    assert count_after == count_before - 1, (
        "dissolve() must remove the MetaAgent from model._agents"
    )


def test_dissolve_clears_all_back_references(model_and_workers):
    model, workers = model_and_workers
    group = workers[:4]
    c = MetaAgentV2(model, group)
    c.dissolve()
    for w in group:
        assert w.coalition is None, (
            f"Worker {w.unique_id} still has coalition ref after dissolve()"
        )


def test_dissolve_idempotent(model_and_workers):
    """Double-dissolve should not raise."""
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    c.dissolve()
    c.dissolve()   # second call must be safe


# ── Lifecycle: merge ──────────────────────────────────────────────────────────

def test_merge_transfers_members(model_and_workers):
    model, workers = model_and_workers
    c1 = MetaAgentV2(model, workers[:3])
    c2 = MetaAgentV2(model, workers[3:6])
    c2_members = set(c2.members)
    c1.merge(c2)
    for m in c2_members:
        assert m in c1.members


def test_merge_removes_source(model_and_workers):
    model, workers = model_and_workers
    c1 = MetaAgentV2(model, workers[:3])
    c2 = MetaAgentV2(model, workers[3:6])
    c1.merge(c2)
    assert c2 not in list(model.agents)


def test_merge_self_raises(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:3])
    with pytest.raises(ValueError, match="Cannot merge"):
        c.merge(c)


# ── Lifecycle: split ──────────────────────────────────────────────────────────

def test_split_creates_two_coalitions(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:6])
    ca, cb = c.split(workers[:3], workers[3:6])
    assert len(ca.members) == 3
    assert len(cb.members) == 3


def test_split_removes_original(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:6])
    c.split(workers[:3], workers[3:6])
    assert c not in list(model.agents)


def test_split_invalid_overlap(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:6])
    with pytest.raises(ValueError, match="non-overlapping"):
        c.split(workers[:4], workers[2:6])   # workers[2:4] overlap


def test_split_invalid_non_member(model_and_workers):
    model, workers = model_and_workers
    c = MetaAgentV2(model, workers[:4])
    with pytest.raises(ValueError, match="subsets of current members"):
        c.split(workers[:2], workers[4:6])   # workers[4:6] not in c
