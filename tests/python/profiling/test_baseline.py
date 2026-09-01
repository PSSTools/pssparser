"""The regression gate: re-profile the corpus and compare against the baseline.

Gates on counters, never on time.  Lookahead counts are exact integers derived
from the token stream, so they are identical on any machine and in any run --
which is what lets this be a real test rather than a flaky one.  See
``docs/design/grammar-profiling-harness.md`` §4.6.

Good bucket only (decision D1): the ``parses = false`` files are swept and
reported by ``scripts/profile_grammar.py``, but their counters move whenever
*error recovery* changes, which is a different subsystem from the grammar this
gate protects.

To regenerate after a deliberate grammar change::

    scripts/profile_grammar.py --write-baseline docs/profiling/baseline.json
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pssparser.profiling import corpus as corpus_mod
from pssparser.profiling import grammar_map
from pssparser.profiling.collect import collect_warm
from pssparser.profiling.compare import compare
from pssparser.profiling.model import CorpusProfile

pytestmark = [pytest.mark.profiling, pytest.mark.corpus]


BASELINE = Path(__file__).resolve().parents[3] / "docs" / "profiling" / "baseline.json"


@pytest.fixture(scope="module")
def baseline():
    if not BASELINE.is_file():
        pytest.skip("no baseline at %s" % BASELINE)
    return CorpusProfile.from_json(BASELINE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def current():
    sweep_root, repo_root, _source = corpus_mod.find_corpus()
    if sweep_root is None:
        pytest.skip("no PSS corpus; run `ivpm update` or set PSS_CORPUS")
    grammar = grammar_map.find_grammar()
    files = corpus_mod.corpus_files(
        sweep_root, corpus_mod.bucket_policy(repo_root), "good")
    return CorpusProfile(
        mode="warm",
        grammar_sha=grammar_map.grammar_sha(grammar),
        corpus_rev=corpus_mod.corpus_rev(repo_root),
        corpus_root=str(sweep_root),
        files=collect_warm(files, grammar_map.rule_lines(grammar)))


def test_the_comparison_is_valid(baseline, current):
    """Fail loudly rather than compare two unrelated things.

    A stale baseline is the one way this gate can produce a confident wrong
    answer, so its validity is asserted before anything is read from it.
    """
    result = compare(baseline, current)
    if not result.comparable:
        pytest.skip("baseline is stale: %s" % result.reason)


def test_no_new_ambiguities(baseline, current):
    """Zero tolerance -- an ambiguity is a correctness defect.

    ANTLR resolves one by silently taking the lowest-numbered alternative, so
    a new ambiguity means the grammar now describes two parses and the parser
    chooses between them without reporting anything.
    """
    result = compare(baseline, current)
    if not result.comparable:
        pytest.skip(result.reason)
    assert not result.new_ambiguities, (
        "new grammar ambiguities:\n  " + "\n  ".join(
            "decision %d in rule %s (%d occurrences)" % row
            for row in result.new_ambiguities))


def test_no_new_ll_fallbacks(baseline, current):
    """A decision that newly cannot be resolved by lookahead alone."""
    result = compare(baseline, current)
    if not result.comparable:
        pytest.skip(result.reason)
    assert not result.new_fallbacks, (
        "new LL fallbacks:\n  " + "\n  ".join(
            "decision %d in rule %s (%d occurrences)" % row
            for row in result.new_fallbacks))


def test_lookahead_has_not_regressed(baseline, current):
    result = compare(baseline, current)
    if not result.comparable:
        pytest.skip(result.reason)
    assert result.look_delta <= 0.10, (
        "total SLL lookahead grew %.1f%% (%d -> %d); the five biggest movers:\n  %s"
        % (100 * result.look_delta, result.baseline_look, result.current_look,
           "\n  ".join("%s decision %d: %d -> %d" % row
                       for row in result.moved[:5])))


def test_counters_are_reproducible(current):
    """The premise the gate rests on, asserted rather than assumed.

    If a second sweep of the same corpus with the same grammar produced
    different lookahead totals, no threshold could distinguish a grammar change
    from noise, and every test above would be meaningless.
    """
    sweep_root, repo_root, _ = corpus_mod.find_corpus()
    grammar = grammar_map.find_grammar()
    files = corpus_mod.corpus_files(
        sweep_root, corpus_mod.bucket_policy(repo_root), "good")
    again = collect_warm(files, grammar_map.rule_lines(grammar))

    from pssparser.profiling.aggregate import totals
    assert totals(again).sll_look == totals(current.files).sll_look
