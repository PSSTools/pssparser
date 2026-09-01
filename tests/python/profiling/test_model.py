"""The profile data model: serialization and its refusals.

A profile is written to disk and read back weeks later to compare against.
What matters is that the round trip is lossless and that a mismatched schema
is *refused* rather than half-read -- a baseline that silently loses its events
or its min/max fields would produce a comparison that looks fine and means
nothing.
"""
from __future__ import annotations

import pytest

from pssparser.profiling.model import (
    SCHEMA_VERSION, CorpusProfile, DecisionSample, Event, FileProfile)

pytestmark = pytest.mark.profiling


def sample_profile():
    event = Event(kind="ambiguity", start_line=12, start_column=4,
                  stop_line=12, stop_column=20, token_count=6,
                  text="x > 0 && x < 100")
    decision = DecisionSample(
        decision=302, rule="expression", rule_index=91, grammar_line=1780,
        invocations=7, sll_look=9, sll_min_look=1, sll_max_look=3,
        ll_look=4, ll_fallback=3, ambiguities=1, time_ns=1234,
        events=[event])
    f = FileProfile(path="a.pss", bucket="stdlib", mode="warm", lines=40,
                    tokens=180, parse_wall_ns=99, decisions=[decision])
    return CorpusProfile(mode="warm", grammar_sha="abc123", corpus_rev="deadbee",
                         corpus_root="/corpus", files=[f])


class TestRoundTrip:

    def test_round_trip_is_lossless(self):
        original = sample_profile()
        restored = CorpusProfile.from_json(original.to_json())
        assert restored == original

    def test_events_survive_the_round_trip(self):
        """Events are the evidence tier; losing them empties the report."""
        restored = CorpusProfile.from_json(sample_profile().to_json())
        event = restored.files[0].decisions[0].events[0]
        assert event.kind == "ambiguity"
        assert event.text == "x > 0 && x < 100"
        assert event.start_line == 12

    def test_rule_names_survive_the_round_trip(self):
        restored = CorpusProfile.from_json(sample_profile().to_json())
        assert restored.files[0].decisions[0].rule == "expression"
        assert restored.files[0].decisions[0].grammar_line == 1780


class TestSchema:

    def test_a_profile_carries_the_current_schema(self):
        assert sample_profile().schema == SCHEMA_VERSION

    def test_an_unknown_schema_is_refused(self):
        """Refused, not coerced.

        A stale baseline read under a newer model would compare fields that no
        longer mean the same thing, and report the difference as a grammar
        regression.
        """
        text = sample_profile().to_json().replace(
            '"schema": %d' % SCHEMA_VERSION, '"schema": 999')
        with pytest.raises(ValueError, match="schema"):
            CorpusProfile.from_json(text)


class TestDerived:

    def test_active_decisions_excludes_the_uninvoked(self):
        f = FileProfile(path="a", bucket="b", mode="warm", decisions=[
            DecisionSample(decision=1, rule="r", invocations=4),
            DecisionSample(decision=2, rule="r", invocations=0),
        ])
        assert [d.decision for d in f.active_decisions] == [1]

    def test_look_per_invocation(self):
        d = DecisionSample(decision=1, rule="r", invocations=4, sll_look=10)
        assert d.look_per_invocation == 2.5

    def test_merging_unlike_decisions_is_refused(self):
        """Silently merging two different decisions would corrupt every total."""
        a = DecisionSample(decision=1, rule="r")
        b = DecisionSample(decision=2, rule="r")
        with pytest.raises(AssertionError):
            a.merge(b)
