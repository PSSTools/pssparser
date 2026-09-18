"""Corpus self-validation.

`validate` is the one part of the suite that is a gate rather than a
measurement, so each rule gets a deliberately-corrupt case proving it fires --
and the real corpus gets a test proving it doesn't.
"""
from __future__ import annotations

import pytest

from pss_errsuite.validate import validate_corpus

GOOD = """//! case:    GOOD-01
//! class:   syntax.punct
//! title:   a well-formed case
//! expect:  error
//! detect:  recommended
//! at:      10:14
//! count:   1
//! fix:     10:     int a;
struct s {
    int a
}
"""


def errors(findings):
    return [f for f in findings if f.severity == "error"]


@pytest.fixture
def corpus_dir(tmp_path):
    def _make(**files):
        root = tmp_path / "cases"
        root.mkdir(exist_ok=True)
        for name, text in files.items():
            (root / name.replace("__", ".")).write_text(text)
        return root
    return _make


def test_a_good_case_passes(corpus_dir):
    assert errors(validate_corpus(corpus_dir(good__pss=GOOD))) == []


def test_duplicate_case_ids_are_rejected(corpus_dir):
    root = corpus_dir(a__pss=GOOD, b__pss=GOOD)
    assert any("duplicate case id" in f.message
               for f in errors(validate_corpus(root)))


def test_unknown_class_is_rejected(corpus_dir):
    text = GOOD.replace("syntax.punct", "syntax.invented")
    assert any("not in the taxonomy" in f.message
               for f in errors(validate_corpus(corpus_dir(a__pss=text))))


def test_a_case_with_no_control_is_rejected(corpus_dir):
    """Without a control, a tool that rejects our scaffolding scores a
    detection."""
    text = "\n".join(l for l in GOOD.splitlines()
                     if not l.startswith("//! fix:")) + "\n"
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("no control" in f.message for f in findings)


def test_a_fix_that_changes_nothing_is_rejected(corpus_dir):
    # One space after the colon is the separator, so this replacement is
    # byte-for-byte the line that is already there.
    text = GOOD.replace("//! fix:     10:     int a;",
                        "//! fix:     10:     int a")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("changed nothing" in f.message for f in findings)


def test_a_companion_control_satisfies_the_control_rule(corpus_dir):
    """The defect is in the companion, so the repair is too."""
    text = ("//! case:    MF-01\n//! class:   syntax.multifile\n"
            "//! expect:  error\n//! detect:  recommended\n"
            "//! files:   _lib.pss, a.pss\n//! at-file: _lib.pss\n"
            "//! at:      2:10\npackage p { }\n")
    root = corpus_dir(a__pss=text,
                      _lib__pss="struct s {\n    int a\n}\n")
    assert any("no control" in f.message for f in errors(validate_corpus(root)))

    (root / "_lib.ok.pss").write_text("struct s {\n    int a;\n}\n")
    assert errors(validate_corpus(root)) == []


def test_at_file_must_name_a_declared_file(corpus_dir):
    """A typo here silently turns every run of the case into a `missed`."""
    text = GOOD.replace("//! count:   1", "//! at-file: _typo.pss")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("at-file" in f.message for f in findings)


def test_required_without_an_lrm_citation_is_rejected(corpus_dir):
    """The promotion rule, enforced mechanically: `required` means the LRM says
    so, and the clause is attached."""
    text = GOOD.replace("detect:  recommended", "detect:  required")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("lrm" in f.message for f in findings)


def test_semantic_case_without_an_lrm_citation_is_rejected(corpus_dir):
    text = GOOD.replace("syntax.punct", "semantic.type")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("lrm" in f.message for f in findings)


def test_requires_solver_is_rejected(corpus_dir):
    """Solver-dependent defects are out of scope (design §1); this is where
    that decision is enforced rather than remembered."""
    text = GOOD.replace("//! count:   1", "//! requires: solver")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("out of scope" in f.message for f in findings)


def test_unknown_capability_is_rejected(corpus_dir):
    text = GOOD.replace("//! count:   1", "//! requires: telepathy")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("not a known capability" in f.message for f in findings)


def test_unknown_pss_version_is_rejected(corpus_dir):
    text = GOOD.replace("//! count:   1", "//! pss: 9.9")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("does not" in f.message or "not a version" in f.message
               for f in findings)


def test_a_term_cannot_be_both_cause_and_not_cause(corpus_dir):
    text = GOOD.replace("//! count:   1",
                        "//! cause: assign\n//! not_cause: Assign")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("cannot be both" in f.message for f in findings)


def test_names_must_occur_in_the_source(corpus_dir):
    text = GOOD.replace("//! count:   1", "//! names: nonexistent_field")
    findings = errors(validate_corpus(corpus_dir(a__pss=text)))
    assert any("does not occur" in f.message for f in findings)


def test_unknown_directive_is_reported_not_raised(corpus_dir):
    """One malformed case must not stop the other 399 from being checked."""
    bad = GOOD.replace("//! count:   1", "//! typo: x")
    findings = errors(validate_corpus(corpus_dir(a__pss=bad, b__pss=GOOD)))
    assert len(findings) == 1
    assert "unknown directive" in findings[0].message


def test_over_budget_case_is_rejected_over_target_only_warns(corpus_dir):
    padding = "\n".join(f"    int f{i};" for i in range(70))
    huge = GOOD.replace("    int a\n", "    int a\n" + padding + "\n")
    findings = validate_corpus(corpus_dir(a__pss=huge))
    assert any("budget" in f.message for f in errors(findings))

    medium = GOOD.replace(
        "    int a\n",
        "    int a\n" + "\n".join(f"    int f{i};" for i in range(35)) + "\n")
    findings = validate_corpus(corpus_dir(a__pss=medium))
    assert errors(findings) == []
    assert any("target" in f.message for f in findings)


# -- the real corpus ---------------------------------------------------------

def test_the_shipped_corpus_validates(corpus):
    findings = errors(validate_corpus(corpus))
    assert findings == [], "\n".join(str(f) for f in findings)


def test_the_fixture_corpus_validates(fixture_cases):
    findings = errors(validate_corpus(fixture_cases))
    assert findings == [], "\n".join(str(f) for f in findings)


def test_an_unconsumed_tool_directive_warns_but_does_not_gate(tmp_path):
    """A `<tool>.<key>` nobody reads is worth saying, but it must not fail the
    corpus: the namespace may belong to a tool this suite has never seen.

    The error version of this check lives in the runner, which knows the
    directive was addressed to the tool it is running.
    """
    (tmp_path / "w.pss").write_text(
        GOOD.replace("//! count:   1\n",
                     "//! count:   1\n//! vendorx.nonsense: 1\n"),
        encoding="utf-8")
    findings = validate_corpus(tmp_path)
    assert not errors(findings)
    warned = [f for f in findings if f.severity == "warning"
              and "vendorx.nonsense" in f.message]
    assert len(warned) == 1
    assert "will be ignored" in warned[0].message
