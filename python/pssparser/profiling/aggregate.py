"""Aggregation: roll per-file samples up to decisions, rules and totals.

Pure arithmetic over :mod:`.model` objects.  No parser, no corpus, no I/O --
which is what lets the tests for it run anywhere and be exhaustive.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .model import DecisionSample, FileProfile


@dataclass
class RuleRollup:
    """Every decision belonging to one grammar rule, summed."""
    rule: str
    grammar_line: int = 0
    decisions: int = 0
    invocations: int = 0
    sll_look: int = 0
    ll_look: int = 0
    ll_fallback: int = 0
    ambiguities: int = 0
    context_sensitivities: int = 0
    max_look: int = 0
    time_ns: int = 0

    @property
    def look_per_invocation(self) -> float:
        return (self.sll_look / self.invocations) if self.invocations else 0.0


@dataclass
class Totals:
    files: int = 0
    lines: int = 0
    tokens: int = 0
    parse_wall_ns: int = 0
    prediction_ns: int = 0
    sll_look: int = 0
    ll_look: int = 0
    sll_atn_transitions: int = 0
    ll_atn_transitions: int = 0
    ll_fallback: int = 0
    ambiguities: int = 0
    context_sensitivities: int = 0
    invocations: int = 0
    dfa_size: int = 0
    files_with_errors: int = 0

    @property
    def prediction_fraction(self) -> float:
        """Prediction time as a fraction of total parse wall time.

        Measured *under profiling*, which adds a clock read per prediction and
        disables fast paths, so it is an upper bound on the real share.  It is
        the number that tells a reader whether any of this is worth acting on.
        """
        return (self.prediction_ns / self.parse_wall_ns) if self.parse_wall_ns else 0.0


def merge_decisions(files: Iterable[FileProfile]) -> List[DecisionSample]:
    """Sum each decision across files, returning one sample per decision.

    Copies before merging: the per-file samples stay intact, so a caller can
    aggregate and then still drill into which file contributed what.
    """
    by_decision: Dict[int, DecisionSample] = {}
    for f in files:
        for d in f.decisions:
            existing = by_decision.get(d.decision)
            if existing is None:
                by_decision[d.decision] = copy.deepcopy(d)
            else:
                existing.merge(d)
    return sorted(by_decision.values(), key=lambda d: d.decision)


def rollup_by_rule(decisions: Iterable[DecisionSample]) -> List[RuleRollup]:
    """Group decisions by grammar rule.

    The tier that answers "which rule do I restructure?", as opposed to "which
    decision is expensive?".  A rule like ``expression`` owns several decisions
    and can be the top cost without any one of them standing out.
    """
    by_rule: Dict[str, RuleRollup] = {}
    for d in decisions:
        r = by_rule.get(d.rule)
        if r is None:
            r = RuleRollup(rule=d.rule, grammar_line=d.grammar_line)
            by_rule[d.rule] = r
        r.decisions += 1
        r.invocations += d.invocations
        r.sll_look += d.sll_look
        r.ll_look += d.ll_look
        r.ll_fallback += d.ll_fallback
        r.ambiguities += d.ambiguities
        r.context_sensitivities += d.context_sensitivities
        r.max_look = max(r.max_look, d.sll_max_look, d.ll_max_look)
        r.time_ns += d.time_ns
    return sorted(by_rule.values(), key=lambda r: r.sll_look, reverse=True)


def totals(files: List[FileProfile]) -> Totals:
    t = Totals()
    t.files = len(files)
    for f in files:
        t.lines += f.lines
        t.tokens += f.tokens
        t.parse_wall_ns += f.parse_wall_ns
        if f.syntax_errors:
            t.files_with_errors += 1
        # The DFA figure is process-cumulative, so the largest observation is
        # the end state -- summing it would multiply one number by 92.
        t.dfa_size = max(t.dfa_size, f.dfa_size)
        for d in f.decisions:
            t.prediction_ns += d.time_ns
            t.sll_look += d.sll_look
            t.ll_look += d.ll_look
            t.sll_atn_transitions += d.sll_atn_transitions
            t.ll_atn_transitions += d.ll_atn_transitions
            t.ll_fallback += d.ll_fallback
            t.ambiguities += d.ambiguities
            t.context_sensitivities += d.context_sensitivities
            t.invocations += d.invocations
    return t


def rank(decisions: Iterable[DecisionSample],
         key: str = "sll_look") -> List[DecisionSample]:
    """Hot decisions first.

    Defaults to total SLL lookahead: exact, cache-independent, and the closest
    proxy for "how much work does the grammar make the parser do here".
    """
    if key == "look_per_invocation":
        return sorted(decisions, key=lambda d: d.look_per_invocation, reverse=True)
    return sorted(decisions, key=lambda d: getattr(d, key), reverse=True)


def scale(decisions: List[DecisionSample], divisor: int) -> List[DecisionSample]:
    """Divide counters by *divisor*, for ``--repeat`` runs.

    Integer division. Min/max lookahead are *not* scaled -- they are extremes,
    not sums, and repeating the corpus does not change them.
    """
    if divisor <= 1:
        return decisions
    ret = []
    for d in decisions:
        c = copy.deepcopy(d)
        for fname in ("invocations", "sll_look", "ll_look", "sll_atn_transitions",
                      "ll_atn_transitions", "ll_fallback", "ambiguities",
                      "context_sensitivities", "errors", "predicate_evals",
                      "time_ns"):
            setattr(c, fname, getattr(c, fname) // divisor)
        ret.append(c)
    return ret
