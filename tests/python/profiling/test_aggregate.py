"""Aggregation arithmetic, on synthetic samples.

No parser, no corpus, no grammar.  Aggregation is where a profiling harness is
most likely to be quietly wrong -- a wrong sum still produces a plausible
ranking -- so it is tested against inputs whose right answer is obvious by
inspection rather than against whatever the parser happens to emit.
"""
from __future__ import annotations

import pytest

from pssparser.profiling.aggregate import (
    merge_decisions, rank, rollup_by_rule, scale, totals)
from pssparser.profiling.model import DecisionSample, Event, FileProfile

pytestmark = pytest.mark.profiling


def mkdec(decision=1, rule="expression", **kw):
    return DecisionSample(decision=decision, rule=rule, **kw)


def mkfile(decisions, path="a.pss", **kw):
    return FileProfile(path=path, bucket="b", mode="warm",
                       decisions=decisions, **kw)


class TestMerge:

    def test_same_decision_across_files_sums(self):
        files = [
            mkfile([mkdec(invocations=3, sll_look=30)], "a.pss"),
            mkfile([mkdec(invocations=4, sll_look=40)], "b.pss"),
        ]
        merged = merge_decisions(files)
        assert len(merged) == 1
        assert merged[0].invocations == 7
        assert merged[0].sll_look == 70

    def test_distinct_decisions_stay_distinct(self):
        files = [mkfile([mkdec(decision=1), mkdec(decision=2)])]
        assert len(merge_decisions(files)) == 2

    def test_merge_does_not_mutate_the_inputs(self):
        """Per-file attribution must survive aggregation.

        A caller that aggregates and then wants to know which file contributed
        the cost has no way to recover it if merging edited the samples in
        place.
        """
        a = mkfile([mkdec(invocations=3, sll_look=30)], "a.pss")
        b = mkfile([mkdec(invocations=4, sll_look=40)], "b.pss")
        merge_decisions([a, b])
        assert a.decisions[0].invocations == 3
        assert b.decisions[0].sll_look == 40

    def test_max_lookahead_takes_the_extreme_not_the_sum(self):
        files = [
            mkfile([mkdec(sll_max_look=12)], "a.pss"),
            mkfile([mkdec(sll_max_look=30)], "b.pss"),
        ]
        assert merge_decisions(files)[0].sll_max_look == 30

    def test_min_lookahead_ignores_unobserved_zeros(self):
        """A decision not invoked reports min 0; that must not win.

        Letting it win would claim every decision has a free path, which is the
        opposite of the truth and would hide exactly the uniformly-expensive
        decisions the min/max split exists to expose.
        """
        files = [
            mkfile([mkdec(sll_min_look=0)], "a.pss"),
            mkfile([mkdec(sll_min_look=7)], "b.pss"),
            mkfile([mkdec(sll_min_look=4)], "c.pss"),
        ]
        assert merge_decisions(files)[0].sll_min_look == 4


class TestEventMerge:

    def _ev(self, kind):
        return Event(kind=kind, start_line=1, start_column=0, stop_line=1,
                     stop_column=1, token_count=1, text=kind)

    def test_ambiguity_survives_a_flood_of_max_look_events(self):
        """The regression that motivated the priority ordering.

        Eight files' worth of max-lookahead events used to fill the cap before
        the file that is actually ambiguous was reached, leaving a decision
        reporting ambiguities with no example of one.
        """
        noisy = [mkfile([mkdec(events=[self._ev("sll-max-look")])], "f%d" % i)
                 for i in range(10)]
        ambiguous = mkfile(
            [mkdec(ambiguities=1, events=[self._ev("ambiguity")])], "z.pss")
        merged = merge_decisions(noisy + [ambiguous])[0]
        assert merged.ambiguities == 1
        assert any(e.kind == "ambiguity" for e in merged.events)

    def test_events_are_capped(self):
        files = [mkfile([mkdec(events=[self._ev("error")])], "f%d" % i)
                 for i in range(40)]
        assert len(merge_decisions(files)[0].events) <= 8


class TestRollup:

    def test_groups_decisions_by_rule(self):
        decisions = [
            mkdec(decision=1, rule="expression", sll_look=10, invocations=1),
            mkdec(decision=2, rule="expression", sll_look=20, invocations=2),
            mkdec(decision=3, rule="primary", sll_look=5, invocations=1),
        ]
        rules = {r.rule: r for r in rollup_by_rule(decisions)}
        assert rules["expression"].decisions == 2
        assert rules["expression"].sll_look == 30
        assert rules["primary"].sll_look == 5

    def test_ordered_by_lookahead(self):
        decisions = [
            mkdec(decision=1, rule="cheap", sll_look=1),
            mkdec(decision=2, rule="costly", sll_look=100),
        ]
        assert [r.rule for r in rollup_by_rule(decisions)] == ["costly", "cheap"]


class TestRank:

    def test_default_key_is_total_lookahead(self):
        hot = mkdec(decision=1, sll_look=1000, invocations=1000)
        deep = mkdec(decision=2, sll_look=100, invocations=2)
        assert rank([deep, hot])[0].decision == 1

    def test_look_per_invocation_finds_the_structural_case(self):
        """The metric that separates 'hot' from 'badly factored'.

        A decision invoked 1000 times at 1 token each is fine.  One invoked
        twice at 50 tokens each is the grammar failing to tell alternatives
        apart, and it must not be buried by the first.
        """
        hot = mkdec(decision=1, sll_look=1000, invocations=1000)
        deep = mkdec(decision=2, sll_look=100, invocations=2)
        assert rank([hot, deep], "look_per_invocation")[0].decision == 2

    def test_look_per_invocation_of_an_uninvoked_decision_is_zero(self):
        assert mkdec(invocations=0, sll_look=0).look_per_invocation == 0.0


class TestTotals:

    def test_sums_across_files(self):
        files = [
            mkfile([mkdec(sll_look=10, invocations=1)], "a.pss", lines=5, tokens=20),
            mkfile([mkdec(sll_look=20, invocations=2)], "b.pss", lines=7, tokens=30),
        ]
        t = totals(files)
        assert (t.files, t.lines, t.tokens) == (2, 12, 50)
        assert t.sll_look == 30
        assert t.invocations == 3

    def test_dfa_size_is_a_maximum_not_a_sum(self):
        """The DFA is process-global and cumulative.

        Summing the per-file observations would report a figure 92x too large
        on a 92-file sweep, and it would grow with corpus size rather than with
        the grammar -- which is the opposite of what it measures.
        """
        files = [
            mkfile([], "a.pss", dfa_size=100),
            mkfile([], "b.pss", dfa_size=180),
        ]
        assert totals(files).dfa_size == 180

    def test_prediction_fraction_is_safe_when_nothing_was_parsed(self):
        assert totals([]).prediction_fraction == 0.0

    def test_files_with_errors_are_counted(self):
        files = [
            mkfile([], "a.pss", syntax_errors=0),
            mkfile([], "b.pss", syntax_errors=3),
        ]
        assert totals(files).files_with_errors == 1


class TestScale:

    def test_divides_counters_by_the_repeat_factor(self):
        scaled = scale([mkdec(invocations=30, sll_look=300)], 3)[0]
        assert scaled.invocations == 10
        assert scaled.sll_look == 100

    def test_does_not_scale_extremes(self):
        """Min and max are extremes, not sums; repeating changes neither."""
        scaled = scale([mkdec(sll_max_look=40, sll_min_look=2)], 4)[0]
        assert scaled.sll_max_look == 40
        assert scaled.sll_min_look == 2

    def test_repeat_of_one_is_a_no_op(self):
        original = [mkdec(invocations=7)]
        assert scale(original, 1) is original
