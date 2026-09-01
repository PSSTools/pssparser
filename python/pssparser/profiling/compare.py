"""Baseline comparison -- the regression gate.

Gates on **counters only**.  They are exact integers computed from the token
stream, so two runs of the same grammar over the same corpus produce identical
values on any machine; a timing gate would be a flaky test that eventually gets
deleted, taking the real gate with it.

Two rules, and they are different in kind:

* total lookahead regressing past a threshold -- a *cost* regression;
* a decision acquiring a **new** ambiguity or LL fallback where the baseline
  had none -- a *correctness* regression, gated at zero tolerance because an
  ambiguity means the grammar says two things and ANTLR silently picks one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .aggregate import merge_decisions, totals
from .model import CorpusProfile, DecisionSample


#: Fractional growth in total SLL lookahead that fails the gate.  Loose enough
#: that adding corpus coverage of an existing construct does not trip it,
#: tight enough to catch a decision that stops being left-factored.
LOOK_REGRESSION_THRESHOLD = 0.10


@dataclass
class Comparison:
    comparable: bool = True
    reason: str = ""
    baseline_look: int = 0
    current_look: int = 0
    new_ambiguities: List[Tuple[int, str, int]] = field(default_factory=list)
    new_fallbacks: List[Tuple[int, str, int]] = field(default_factory=list)
    moved: List[Tuple[str, int, int, int]] = field(default_factory=list)

    @property
    def look_delta(self) -> float:
        if not self.baseline_look:
            return 0.0
        return (self.current_look - self.baseline_look) / self.baseline_look

    @property
    def failed(self) -> bool:
        if not self.comparable:
            return False
        return bool(self.new_ambiguities) or bool(self.new_fallbacks) \
            or self.look_delta > LOOK_REGRESSION_THRESHOLD

    def describe(self) -> str:
        if not self.comparable:
            return "not comparable: %s" % self.reason
        out = ["total SLL lookahead %s -> %s (%+.1f%%)" % (
            "{:,}".format(self.baseline_look),
            "{:,}".format(self.current_look),
            100.0 * self.look_delta)]
        for label, rows in (("NEW ambiguity", self.new_ambiguities),
                            ("NEW LL fallback", self.new_fallbacks)):
            for decision, rule, count in rows:
                out.append("  %s: decision %d (%s), %d occurrences"
                           % (label, decision, rule, count))
        if self.look_delta > LOOK_REGRESSION_THRESHOLD:
            out.append("  lookahead regressed past the %.0f%% threshold"
                       % (100 * LOOK_REGRESSION_THRESHOLD))
        return "\n".join(out)


def compare(baseline: CorpusProfile, current: CorpusProfile) -> Comparison:
    ret = Comparison()

    # A different corpus invalidates the comparison outright.  A different
    # grammar does not -- that is the whole point of running this.
    if baseline.corpus_rev != current.corpus_rev:
        ret.comparable = False
        ret.reason = ("corpus revision differs (%s vs %s); regenerate the "
                      "baseline rather than reading this as a grammar change"
                      % (baseline.corpus_rev, current.corpus_rev))
        return ret
    if baseline.mode != current.mode:
        ret.comparable = False
        ret.reason = "modes differ (%s vs %s)" % (baseline.mode, current.mode)
        return ret
    if baseline.synthetic or current.synthetic:
        ret.comparable = False
        ret.reason = "a --repeat run is synthetic and cannot serve as a baseline"
        return ret

    base_by_decision: Dict[int, DecisionSample] = {
        d.decision: d for d in merge_decisions(baseline.files)}
    cur_by_decision: Dict[int, DecisionSample] = {
        d.decision: d for d in merge_decisions(current.files)}

    ret.baseline_look = totals(baseline.files).sll_look
    ret.current_look = totals(current.files).sll_look

    for decision, cur in sorted(cur_by_decision.items()):
        base = base_by_decision.get(decision)
        if cur.ambiguities and (base is None or not base.ambiguities):
            ret.new_ambiguities.append((decision, cur.rule, cur.ambiguities))
        if cur.ll_fallback and (base is None or not base.ll_fallback):
            ret.new_fallbacks.append((decision, cur.rule, cur.ll_fallback))
        base_look = base.sll_look if base else 0
        if cur.sll_look != base_look:
            ret.moved.append((cur.rule, decision, base_look, cur.sll_look))

    ret.moved.sort(key=lambda r: abs(r[3] - r[2]), reverse=True)
    return ret
