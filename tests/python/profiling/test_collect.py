"""Collection against the real parser, on inputs small enough to reason about.

These are the tests that would catch the profiling plumbing going quietly
dead -- a rename in the Cython layer, a `setProfile` that stops being called --
which the aggregation tests, running on synthetic data, cannot.
"""
from __future__ import annotations

import pytest

from pssparser.profiling.collect import ProfileCollector
from pssparser.profiling.grammar_map import find_grammar, grammar_sha, rule_lines

pytestmark = pytest.mark.profiling


SIMPLE = """
component pss_top {
    action A {
        rand int x;
        constraint { x > 0 && x < 100; }
    }
    action B { A a1; activity { a1; } }
}
"""


@pytest.fixture(scope="module")
def collector():
    return ProfileCollector(rule_lines(find_grammar()))


class TestCollect:

    def test_collects_active_decisions(self, collector):
        p = collector.collect_text("t.pss", SIMPLE)
        assert p.parsed
        assert p.decisions, "profiling produced no decisions"

    def test_every_decision_is_named_with_a_grammar_rule(self, collector):
        """The point of the whole exercise.

        A decision number names nothing anyone can edit; the rule name is what
        makes a profile a work order.  An empty or `<unknown>` rule means the
        ATN-to-rule mapping has come unstuck.
        """
        p = collector.collect_text("t.pss", SIMPLE)
        for d in p.decisions:
            assert d.rule and d.rule != "<unknown>", \
                "decision %d has no rule name" % d.decision

    def test_rules_resolve_to_grammar_lines(self, collector):
        p = collector.collect_text("t.pss", SIMPLE)
        located = [d for d in p.decisions if d.grammar_line]
        assert located, "no decision resolved to a line in PSSParser.g4"

    def test_only_invoked_decisions_are_reported(self, collector):
        """The grammar has hundreds of decisions; a small file uses a few.

        Carrying the uninvoked ones would make a corpus profile far larger than
        the corpus and tell the reader nothing.
        """
        p = collector.collect_text("t.pss", SIMPLE)
        assert all(d.invocations > 0 for d in p.decisions)

    def test_counts_tokens_and_lines(self, collector):
        p = collector.collect_text("t.pss", SIMPLE)
        assert p.tokens > 0
        assert p.lines == SIMPLE.count("\n") + 1

    def test_lookahead_is_at_least_one_per_invocation(self, collector):
        """A prediction always consumes at least one token of lookahead.

        Cheap, but it is the invariant that would break first if the SLL
        counters were ever read from the wrong field.
        """
        p = collector.collect_text("t.pss", SIMPLE)
        for d in p.decisions:
            assert d.sll_look >= d.invocations, \
                "decision %d: %d look over %d invocations" % (
                    d.decision, d.sll_look, d.invocations)

    def test_max_lookahead_bounds_min(self, collector):
        p = collector.collect_text("t.pss", SIMPLE)
        for d in p.decisions:
            if d.sll_min_look and d.sll_max_look:
                assert d.sll_min_look <= d.sll_max_look


class TestEvents:

    def test_ambiguity_events_carry_a_source_location(self, collector):
        """G2: the events must resolve to line/column and text.

        They are recorded by ANTLR as raw pointers into the token stream, and
        are resolved during extraction because nothing they point at outlives
        the parse.  A zero line means that resolution stopped happening.
        """
        p = collector.collect_text("t.pss", SIMPLE)
        events = [e for d in p.decisions for e in d.events]
        assert events, "no profiler events recorded at all"
        for e in events:
            assert e.start_line > 0, "event %r has no source line" % (e,)
            assert e.token_count >= 1

    def test_event_text_matches_the_reported_span(self, collector):
        """An event's text must come from where it says it does.

        This is the check that a mis-resolved span would fail: the text is
        pulled from the token stream by index and the line is read off the
        token, so they can only agree if both refer to the same tokens.
        """
        lines = SIMPLE.split("\n")
        p = collector.collect_text("t.pss", SIMPLE)
        checked = 0
        for d in p.decisions:
            for e in d.events:
                if not e.text or e.start_line != e.stop_line:
                    continue
                source_line = lines[e.start_line - 1]
                first_token = e.text.split()[0]
                assert first_token in source_line, (
                    "event claims %d:%d but %r is not on that line (%r)"
                    % (e.start_line, e.start_column, first_token, source_line))
                checked += 1
        assert checked, "no single-line event to check"


class TestDeterminism:

    def test_counters_repeat_exactly(self, collector):
        """Counters must be exact, not sampled.

        The regression gate depends on this: if a second parse of identical
        text produced different lookahead figures, no threshold could tell a
        grammar change from noise.  Note this holds despite the DFA being warm
        the second time -- which is precisely why lookahead, and not
        ATN transitions, is what the gate compares.
        """
        a = collector.collect_text("t.pss", SIMPLE)
        b = collector.collect_text("t.pss", SIMPLE)
        as_map = {d.decision: d.sll_look for d in a.decisions}
        bs_map = {d.decision: d.sll_look for d in b.decisions}
        assert as_map == bs_map

    def test_atn_transitions_fall_to_zero_once_warm(self, collector):
        """The cache-dependence the design turns on, stated as a test.

        The second parse of the same text learns nothing new, so it makes no
        ATN transitions.  This is why ATN transitions are reported but never
        ranked or gated on: they measure the process, not the grammar.
        """
        collector.collect_text("warm.pss", SIMPLE)
        second = collector.collect_text("warm.pss", SIMPLE)
        assert sum(d.sll_atn_transitions for d in second.decisions) == 0


class TestBadInput:

    def test_invalid_input_is_profiled_rather_than_raising(self, collector):
        """The parses=false bucket has to be measurable.

        ``Parser.parse()`` raises on the first syntax error, which is why the
        collector drives the builder directly.  Error recovery drives
        prediction hard and in different places than clean input, and an editor
        sees invalid input on every keystroke.
        """
        p = collector.collect_text("bad.pss", "component { action ;; }")
        assert not p.parsed
        assert p.syntax_errors > 0
        assert p.decisions, "no profile collected for invalid input"


class TestGrammarMap:

    def test_finds_the_grammar_and_its_rules(self):
        grammar = find_grammar()
        assert grammar is not None and grammar.is_file()
        rules = rule_lines(grammar)
        # Rules named in the LRM's B.x grammar; if these are missing the scan
        # regex has stopped matching declarations.
        for name in ("expression", "component_body_item", "data_type"):
            assert name in rules, "%s not found in the grammar scan" % name
            assert rules[name] > 0

    def test_sha_is_stable_and_not_unknown(self):
        grammar = find_grammar()
        assert grammar_sha(grammar) == grammar_sha(grammar)
        assert grammar_sha(grammar) != "unknown"
