# Mentor Engagement Plan

## Primary mentor: Tom Pike

Tom Pike is the maintainer of `mesa.experimental.meta_agents` and proposed
the Meta Agents GSoC slot. He identified the agent-count bugs in the Feb 2, 2026
dev meeting. He is the right person to:
1. Confirm the exact nature of the two agent-count bugs.
2. Review the proposed lifecycle API (join, leave, merge, split).
3. Scope the graduation from `experimental` to `mesa.meta_agents`.

### Draft GitHub discussion post (to post on mesa GitHub)

**Title:** GSoC 2026 — Meta Agents: Pillar 1 bug investigation question for Tom Pike

**Body:**
---
Hi Tom, Ewout,

I'm Dipayan Dasgupta, a GSoC 2026 applicant interested in the **Meta Agents (Medium)**
project slot you outlined in the Jan 20 meeting and discussed further in the Feb 2 meeting.

I've been contributing to Mesa for the past few months:
- PR #3567: type validation in `evaluate_combination` (meta_agents, open)
- PR #3542: `Grid.not_full_cells` API (merged)
- PR #3544: VoronoiGrid capacity fix (merged)
- Mesa-LLM PR #21: `Reasoning` test suite (merged)

I've reproduced what I believe are the two agent-count bugs you mentioned in the Feb
meeting. In my testing:

**Bug 1 (dissolution path):** When `dissolve_meta_agent` is called and one constituent
agent was already removed from the model (e.g., it was killed), the iterator raises
before completing, leaving phantom entries in `model._agents`.

**Bug 2 (re-formation path):** When a dissolved MetaAgent's constituent agents
immediately re-enter `find_combinations`, the model's internal count may still include
the dissolved MetaAgent's `unique_id`.

Could you confirm whether these match what you observed? I want to make sure I'm fixing
the right bugs before the proposal deadline.

My proposed scope for the project:
1. Fix both bugs + complete test suite
2. Add `join()`, `leave()`, `merge()`, `split()` lifecycle API
3. Add `LLMEvaluationAgent` (bridge to Mesa-LLM `ReasoningAgent`)
4. Add `spatial_find_combinations()` (DiscreteSpace-aware search)

Happy to share my PoC code or a minimal reproduction script for the bugs.

Thanks!
Dipayan

---

## Secondary mentor: Ewout

Ewout proposed the Meta Agents slot alongside Tom and has reviewed several of
my PRs. A brief acknowledgment in the GitHub discussion (tagging @EwoutH) is
appropriate; he does not need a separate outreach.
