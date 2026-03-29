"""
poc/pillar2_type_boundary.py
Pillar 2 — Type Boundary Validation Demo
=========================================
Shows what happens in three scenarios:

  OLD (pre-PR #3572): evaluation_func returns wrong type → silent failure
                      or confusing TypeError deep in filter_func
  PR #3572:           TypeError raised AT THE CALL SITE (Python callable)
  PILLAR 2 (proposed):CoalitionScore raises at the LLM-output boundary before
                      the bad value ever reaches find_combinations

Run:
    python poc/pillar2_type_boundary.py
"""
from __future__ import annotations
import json
import dataclasses

SEP = "=" * 65

# ── CoalitionScore — proposed Pydantic-style dataclass ───────────────────────

@dataclasses.dataclass
class CoalitionScore:
    score:       float
    rationale:   str
    recommended: bool

    def __post_init__(self):
        if not isinstance(self.score, (int, float)):
            raise TypeError(
                f"score must be numeric, got {type(self.score).__name__!r}"
            )
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0,1], got {self.score}")
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise TypeError("rationale must be a non-empty string")
        if not isinstance(self.recommended, bool):
            raise TypeError(
                f"recommended must be bool, got {type(self.recommended).__name__!r}"
            )

    @classmethod
    def from_json(cls, raw: str) -> "CoalitionScore":
        import re
        clean = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", raw, flags=re.S).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}\nRaw: {raw!r}") from exc
        try:
            return cls(
                score       = float(data["score"]),
                rationale   = str(data["rationale"]),
                recommended = bool(data["recommended"]),
            )
        except KeyError as exc:
            raise ValueError(
                f"LLM JSON missing key {exc}. "
                f"Expected {{score, rationale, recommended}}, got {list(data)}"
            ) from exc


# ── Old evaluate_combination (unfixed) ───────────────────────────────────────

def find_combinations_old(agents, evaluation_func):
    """Mirrors current meta_agents behaviour: no type check."""
    results = []
    for i, a in enumerate(agents):
        for j, b in enumerate(agents):
            if i >= j: continue
            group = [a, b]
            value = evaluation_func(group)
            # BUG: if value is a string, the comparison below raises a confusing
            # TypeError deep in the pipeline, not at the call site
            if value is not None:
                results.append((group, value))
    return sorted(results, key=lambda x: x[1], reverse=True)  # ← TypeError here


# ── evaluate_combination (with PR #3572 fix) ─────────────────────────────────

def find_combinations_fixed(agents, evaluation_func):
    """PR #3572 version: type-checked at call site."""
    results = []
    for i, a in enumerate(agents):
        for j, b in enumerate(agents):
            if i >= j: continue
            group = [a, b]
            value = evaluation_func(group)
            if not isinstance(value, (int, float)) and not hasattr(value, "__float__"):
                raise TypeError(
                    f"evaluation_func must return numeric, got {type(value).__name__!r}"
                )
            results.append((group, value))
    return sorted(results, key=lambda x: x[1], reverse=True)


class DummyAgent:
    def __init__(self, uid): self.unique_id = uid


if __name__ == "__main__":
    print(SEP)
    print("Pillar 2 — Type Boundary Validation Demo")
    print(SEP)
    agents = [DummyAgent(i) for i in range(4)]

    # ── Scenario A: string-returning evaluation_func, unfixed pipeline ────────
    print("\n[A] evaluation_func returns a string (old pipeline, no fix):")
    bad_func = lambda g: "high compatibility"    # returns str, not float
    try:
        find_combinations_old(agents, bad_func)
        print("  No error raised (silent failure or wrong sort).")
    except TypeError as e:
        print(f"  TypeError deep in sorted(): {e}")
        print("  → Error is confusing: no indication which function is wrong.")

    # ── Scenario B: string-returning, PR #3572 fix ────────────────────────────
    print("\n[B] evaluation_func returns a string (PR #3572 type guard):")
    try:
        find_combinations_fixed(agents, bad_func)
    except TypeError as e:
        print(f"  TypeError at call site: {e}")
        print("  → Error is clear: raised immediately when bad value returned.")

    # ── Scenario C: LLM returns bad JSON, Pillar 2 boundary ──────────────────
    print("\n[C] LLM returns bad JSON (Pillar 2 CoalitionScore boundary):")
    bad_json_responses = [
        ('{"score": "very high", "rationale": "good fit", "recommended": true}',
         "score is a string not float"),
        ('{"score": 0.8, "rationale": "good fit"}',
         "missing recommended key"),
        ("this is not json at all",
         "invalid JSON"),
        ('{"score": 1.7, "rationale": "great", "recommended": true}',
         "score out of range [0,1]"),
    ]
    for raw, description in bad_json_responses:
        try:
            CoalitionScore.from_json(raw)
            print(f"  [{description}] → No error (unexpected!)")
        except (TypeError, ValueError) as e:
            print(f"  [{description}]\n    → {type(e).__name__}: {e}")

    # ── Scenario D: valid LLM response ───────────────────────────────────────
    print("\n[D] Valid LLM response parsed correctly:")
    good_raw = json.dumps({
        "score": 0.87, "rationale": "complementary profiles", "recommended": True
    })
    cs = CoalitionScore.from_json(good_raw)
    print(f"  CoalitionScore(score={cs.score}, recommended={cs.recommended})")
    print(f"  → {cs.rationale}")

    # Markdown-fence stripping (common LLM quirk)
    fenced = f"```json\n{good_raw}\n```"
    cs2 = CoalitionScore.from_json(fenced)
    print(f"  Markdown-fenced JSON also parsed: score={cs2.score}")

    print(f"\n  ✅  Type boundary validated at two levels:")
    print(f"      • Python callable:  PR #3572 (call-site TypeError)")
    print(f"      • LLM JSON output:  Pillar 2 CoalitionScore (JSON boundary)")
    print(SEP)
