"""The regression gate's comparison logic, on synthetic profiles.

Tested apart from the corpus so that every branch -- including the refusals,
which a real run will almost never take -- is actually exercised.
"""
from __future__ import annotations

import pytest

from pssparser.profiling.compare import LOOK_REGRESSION_THRESHOLD, compare
from pssparser.profiling.model import CorpusProfile, DecisionSample, FileProfile

pytestmark = pytest.mark.profiling


def mkprofile(decisions, *, mode="warm", corpus_rev="abc", synthetic=False,
              repeat=1):
    f = FileProfile(path="a.pss", bucket="b", mode=mode, decisions=decisions)
    return CorpusProfile(mode=mode, corpus_rev=corpus_rev, files=[f],
                         synthetic=synthetic, repeat=repeat)


def dec(decision=1, rule="expression", **kw):
    return DecisionSample(decision=decision, rule=rule, **kw)


class TestRefusals:

    def test_a_different_corpus_is_not_comparable(self):
        """A corpus change invalidates the comparison; a grammar change is the point.

        Reading a corpus difference as a grammar regression is the single most
        likely way for this gate to lie, so it is refused outright rather than
        thresholded.
        """
        base = mkprofile([dec(sll_look=100)], corpus_rev="aaa")
        cur = mkprofile([dec(sll_look=100)], corpus_rev="bbb")
        result = compare(base, cur)
        assert not result.comparable
        assert "corpus revision" in result.reason
        assert not result.failed

    def test_a_synthetic_run_cannot_be_compared(self):
        base = mkprofile([dec(sll_look=100)])
        cur = mkprofile([dec(sll_look=300)], synthetic=True, repeat=3)
        assert not compare(base, cur).comparable

    def test_modes_must_match(self):
        base = mkprofile([dec(sll_look=100)], mode="warm")
        cur = mkprofile([dec(sll_look=100)], mode="cold")
        assert not compare(base, cur).comparable


class TestCostRegression:

    def test_unchanged_profile_passes(self):
        base = mkprofile([dec(sll_look=100, invocations=10)])
        cur = mkprofile([dec(sll_look=100, invocations=10)])
        result = compare(base, cur)
        assert not result.failed
        assert result.look_delta == 0.0

    def test_lookahead_growth_past_the_threshold_fails(self):
        base = mkprofile([dec(sll_look=100)])
        cur = mkprofile([dec(sll_look=120)])
        result = compare(base, cur)
        assert result.look_delta == pytest.approx(0.20)
        assert result.failed

    def test_growth_inside_the_threshold_passes(self):
        base = mkprofile([dec(sll_look=100)])
        cur = mkprofile([dec(sll_look=105)])
        assert not compare(base, cur).failed

    def test_an_improvement_never_fails(self):
        """A grammar change that halves lookahead is the goal, not a regression."""
        base = mkprofile([dec(sll_look=100)])
        cur = mkprofile([dec(sll_look=50)])
        result = compare(base, cur)
        assert result.look_delta < 0
        assert not result.failed


class TestCorrectnessRegression:

    def test_a_new_ambiguity_fails_at_zero_tolerance(self):
        """Ambiguity is a correctness signal, not a cost signal.

        ANTLR resolves an ambiguity by silently taking the lowest alternative,
        so a new one means the grammar now says two things and the parser picks
        one without telling anybody.  No threshold applies to that.
        """
        base = mkprofile([dec(sll_look=100, ambiguities=0)])
        cur = mkprofile([dec(sll_look=100, ambiguities=1)])
        result = compare(base, cur)
        assert result.failed
        assert result.new_ambiguities == [(1, "expression", 1)]

    def test_a_new_ll_fallback_fails(self):
        base = mkprofile([dec(sll_look=100, ll_fallback=0)])
        cur = mkprofile([dec(sll_look=100, ll_fallback=5)])
        assert compare(base, cur).failed

    def test_a_pre_existing_ambiguity_getting_worse_is_not_a_new_one(self):
        """The gate catches *new* defects; existing ones are the baseline's job.

        Gating on the count would make every corpus addition that touches an
        already-ambiguous construct fail, and a gate that fires on unrelated
        work gets disabled.
        """
        base = mkprofile([dec(sll_look=100, ambiguities=3)])
        cur = mkprofile([dec(sll_look=100, ambiguities=9)])
        result = compare(base, cur)
        assert not result.new_ambiguities
        assert not result.failed

    def test_an_ambiguity_on_a_decision_absent_from_the_baseline_is_new(self):
        base = mkprofile([dec(decision=1)])
        cur = mkprofile([dec(decision=1), dec(decision=2, ambiguities=1)])
        assert compare(base, cur).new_ambiguities == [(2, "expression", 1)]


class TestDescription:

    def test_describe_names_the_rule_not_just_the_decision(self):
        base = mkprofile([dec(sll_look=100)])
        cur = mkprofile([dec(sll_look=100, rule="constraint_body_item",
                             ambiguities=1)])
        text = compare(base, cur).describe()
        assert "constraint_body_item" in text
        assert "NEW ambiguity" in text

    def test_describe_explains_an_incomparable_pair(self):
        base = mkprofile([dec()], corpus_rev="aaa")
        cur = mkprofile([dec()], corpus_rev="bbb")
        assert "not comparable" in compare(base, cur).describe()
