"""Tier-A grading (design §5).

The proxy tests are written as `(message, case metadata) -> expected score`
tables that include the boundary between *every pair of adjacent anchors*,
because the anchors are the thing under test: a rubric whose 2 and 3 are not
distinguishable by an example is a rubric two raters will score differently.

Two properties get their own tests and should stay that way -- the accuracy
gate (the rule most likely to be refactored away) and "unmeasured is null, not
zero" (the rule that decides whether a thin corpus reads as bad messages).
"""
from __future__ import annotations

import json

import pytest

from pss_errsuite import rubric as R


def case_doc(message="cannot assign 'string' to field 'a' of type 'bit[8]'",
             *, status="detected", cause=None, not_cause=None, names=None,
             at=(10, 23), line=10, col=23, end_col=26, end_line=None,
             code="FAKE001", suggestion=None, related=None, also=None,
             count=1, error_count=1, primary_index=0, has_related=False,
             fixit=None, file=None, case_file="c.pss", at_file=None,
             files=None, source=None,
             cls="fixture.harness", extra_diags=()):
    """One case document shaped exactly as a run file carries it."""
    primary = {"severity": "error", "message": message,
               "file": file or case_file, "line": line, "col": col}
    if end_col is not None:
        primary["end_col"] = end_col
        primary["end_line"] = end_line if end_line is not None else line
    if code:
        primary["code"] = code
    if suggestion is not None:
        primary["suggestion"] = suggestion
    if related:
        primary["related"] = related
    diags = list(extra_diags)
    diags.insert(primary_index, primary)

    expect = {"kind": "error", "detect": "recommended", "count": count,
              "pss": "3.0"}
    if at is not None:
        expect["at"] = {"line": at[0], "col": at[1]}
        if len(at) > 2:
            expect["at"]["end_col"] = at[2]
        # `report.case_document` always records which file `at:` counts from.
        expect["at"]["file"] = at_file or case_file
    for key, value in (("cause", cause), ("not_cause", not_cause),
                       ("names", names), ("also", also)):
        if value:
            expect[key] = value
    return {
        "case": "FX-1", "class": cls, "title": "t",
        "files": files if files is not None else [case_file],
        "case_file": case_file,
        "source": source if source is not None
        else "//! case: FX-1\nstruct s { bit[8] a = \"x\"; }\n",
        "expect": expect,
        "status": status,
        "observations": {"error_count": error_count, "warning_count": 0,
                         "noise": 0, "has_code": bool(code),
                         "has_related": has_related,
                         "has_suggestion": suggestion is not None,
                         "primary_index": primary_index, "duration_s": 0.0,
                         "lints": [], "fixit": fixit},
        "result": {"exit_code": 1, "duration_s": 0.0, "timed_out": False,
                   "crashed": False, "parse_confidence": "structured",
                   "diagnostics": diags, "stdout": "", "stderr": ""},
    }


def score(doc, dim):
    return R.score_case(doc)[dim]


# -- term matching --------------------------------------------------------

@pytest.mark.parametrize("term,message,expected", [
    ("assign", "cannot assign here", True),
    ("assign", "assignment is illegal", True),      # lemma, not exact string
    ("assign", "assigned to 'a'", True),
    ("assign", "reassignment", False),              # not a word boundary
    (";", "missing ';' here", True),                # punctuation: substring
    ("}", "expected '}'", True),
    ("unknown type", "unknown  type 'foo'", True),  # whitespace-insensitive
    ("unknown type", "type is unknown", False),     # order matters
    ("bit[8]", "of type 'bit[8]'", True),
])
def test_term_matching_is_lemma_ish_and_punctuation_aware(term, message,
                                                          expected):
    assert R.term_matches(term, message) is expected


# -- D1 accuracy ----------------------------------------------------------

@pytest.mark.parametrize("message,cause,not_cause,expected", [
    # 0/1 boundary: the declared misdiagnosis, alone, versus alongside the
    # actual cause.
    ("unknown type 'string'", ["assign"], ["unknown type"], 0),
    ("cannot assign to unknown type 'x'", ["assign"], ["unknown type"], 1),
    # 1/2 boundary: none of the cause terms versus some of them.
    ("something is wrong here", ["assign", "bit"], [], 1),
    ("cannot assign this", ["assign", "bit"], [], 2),
    # 2/3 boundary: some versus all.
    ("cannot assign 'string' to 'bit[8]'", ["assign", "bit[8]"], [], 3),
    # A generic message with a declared cause is a 1, not a 0: it is not
    # *wrong*, it just excludes nothing.
    ("syntax error", ["assign"], [], 1),
])
def test_d1_anchors(message, cause, not_cause, expected):
    assert score(case_doc(message, cause=cause, not_cause=not_cause),
                 "d1") == expected


def test_d1_is_null_when_the_case_declares_no_cause():
    """The load-bearing one: ~90% of the corpus has no `cause:` today, and a
    zero there would report our metadata gap as bad messages."""
    block = R.score_case(case_doc("anything at all"))
    assert block["d1"] is None
    assert R.F_D1_UNMEASURED in block["flags"]
    assert "no `cause:`" in block["notes"]["d1"]
    assert block["composite"] > 0


def test_a_sub_three_score_always_carries_a_note():
    """Design §6 wants `rubric.notes` actionable; "D4: 1" alone is not."""
    doc = case_doc("syntax error", cause=["assign"], code=None,
                   suggestion=None, end_col=None, names=["a"], at=(1, 1),
                   line=99, col=1, error_count=9)
    block = R.score_case(doc)
    for dim in R.DIMENSIONS:
        if block[dim] is not None and block[dim] < 3:
            assert block.get("notes", {}).get(dim), f"{dim} scored without a note"


# -- D2 location ----------------------------------------------------------

def test_d2_zero_without_a_location():
    doc = case_doc(line=None, col=None, end_col=None)
    doc["result"]["diagnostics"][0]["line"] = None
    assert score(doc, "d2") == 0


def test_d2_zero_when_it_points_at_another_file():
    assert score(case_doc(file="elsewhere.pss"), "d2") == 0
    # ...and the case's own file is read from `files`, never guessed.
    assert score(case_doc(), "d2") == 3


def test_d2_reads_at_file_rather_than_guessing_from_files():
    """A multifile case whose defect is in the *second* file.

    `report.case_document` used to drop `at-file:`, and the rubric fell back to
    `files[0]` -- so five `syntax.multifile` cases that pointed at exactly the
    right file were scored D2 = 0, and the class looked like the second-worst
    in the corpus.  `classify` never had this bug, so the same run recorded
    them as `detected`: the two disagreed.
    """
    doc = case_doc(files=["a.pss", "b.pss"], case_file="a.pss",
                   at_file="b.pss", file="b.pss")
    assert score(doc, "d2") == 3
    # ...and pointing at the first file is now the wrong file, not the right one
    assert score(case_doc(files=["a.pss", "b.pss"], case_file="a.pss",
                          at_file="b.pss", file="a.pss"), "d2") == 0


def test_d2_falls_back_to_the_case_file_not_the_first_companion():
    """With no `at:` there is still a file the case is about; `files[0]` is a
    guess, and a wrong one whenever the case body is not listed first."""
    doc = case_doc(at=None, files=["companion.pss", "c.pss"], file="c.pss")
    assert score(doc, "d2") != 0


def test_d2_one_when_mislocated():
    assert score(case_doc(status="detected_mislocated", line=40), "d2") == 1


@pytest.mark.parametrize("kwargs,expected", [
    ({"end_col": None}, 2),                       # a point, not a span
    ({"line": 10, "col": 24}, 2),                 # within tolerance, not exact
    ({}, 3),                                      # exact span
])
def test_d2_two_three_boundary(kwargs, expected):
    assert score(case_doc(**kwargs), "d2") == expected


def test_d2_caps_at_two_when_a_second_site_is_declared_and_unreported():
    """Design §5.1: a two-sited defect needs the other half of the story."""
    also = [{"line": 3, "col": 5, "label": "declared here"}]
    assert score(case_doc(also=also), "d2") == 2
    assert score(case_doc(also=also, has_related=True), "d2") == 3


# -- D3 specificity -------------------------------------------------------

@pytest.mark.parametrize("message,names,expected", [
    ("no viable alternative at input '}'", ["a"], 0),        # jargon
    ("cannot convert the value", ["a"], 0),                  # nothing quoted
    ("unexpected '}'", ["a"], 1),                            # a lexeme only
    ("field 'a' is not assignable", ["a"], 2),               # one side
    ("field 'a' has no member here", ["a", "b"], 2),         # one of two
    ("field 'a' of type 'bit8' has no member 'a2'", ["a", "bit8"], 3),
])
def test_d3_anchors(message, names, expected):
    assert score(case_doc(message, names=names), "d3") == expected


def test_d3_without_names_still_decides_the_zero_case():
    """`names:` is absent on most of the corpus, but "contains nothing of the
    user's program" is decidable from the source alone."""
    source = "//! case: FX-1\nstruct s { bit[8] widget; }\n"
    assert score(case_doc("illegal declaration", source=source,
                          end_col=None, code=None), "d3") == 0
    assert R.score_case(case_doc("no member 'widget'",
                                 source=source))["d3"] is None


# -- D4 actionability -----------------------------------------------------

@pytest.mark.parametrize("kwargs,expected", [
    ({"message": "invalid", "code": None}, 0),
    ({"message": "this construct is not permitted here", "code": None}, 1),
    ({"message": "this is not permitted", "code": "E1"}, 2),
    ({"message": "expected ';' here", "code": None}, 2),
    ({"message": "expected ';'", "suggestion": ";", "end_col": None,
      "code": None}, 2),                     # replacement text, but no span
    ({"message": "expected ';'", "suggestion": ";", "code": None}, 2),
    ({"message": "expected ';'", "suggestion": ";", "fixit": "verified"}, 3),
])
def test_d4_anchors(kwargs, expected):
    assert score(case_doc(**kwargs), "d4") == expected


def test_a_fix_that_does_not_fix_is_flagged_not_credited():
    """Design §5.3: worse than offering none at all."""
    block = R.score_case(case_doc(suggestion=";", fixit="invalid"))
    assert block["d4"] == 1
    assert R.F_FIXIT_INVALID in block["flags"]


# -- D5 clarity -----------------------------------------------------------

@pytest.mark.parametrize("message,expected", [
    ("mismatched input '}' expecting ';'", 0),
    ("line one\nline two", 0),
    ("'}'", 0),
    ("x" * 121, 1),
    ("possibly missing a semicolon", 1),
    ("Something failed. Try again later", 1),
    ("field 'a' cannot hold a string", 2),
])
def test_d5_anchors(message, expected):
    assert score(case_doc(message), "d5") == expected


def test_d5_stops_at_two_and_says_why():
    """The out-of-context test is not mechanically decidable, so Tier A does
    not award it -- and the note has to admit that, or a reader will take 2 as
    a criticism of a perfectly good message."""
    block = R.score_case(case_doc("field 'a' cannot hold a string"))
    assert block["d5"] == 2
    assert "human" in block["notes"]["d5"]


# -- D6 economy -----------------------------------------------------------

@pytest.mark.parametrize("kwargs,expected", [
    ({"error_count": 9, "primary_index": 4}, 0),    # cascade, true one buried
    ({"error_count": 9}, 1),                        # cascade, true one first
    ({"error_count": 3}, 1),                        # 2-3x
    ({"error_count": 2, "primary_index": 1}, 1),    # buried under a consequence
    ({"error_count": 2}, 2),                        # within tolerance
    ({"has_related": True}, 3),                     # exact, first, related
    ({}, 2),
])
def test_d6_anchors(kwargs, expected):
    if kwargs.get("primary_index"):
        kwargs.setdefault("extra_diags", [
            {"severity": "error", "message": "consequence", "file": "c.pss",
             "line": 1, "col": 1}] * kwargs["primary_index"])
    assert score(case_doc(**kwargs), "d6") == expected


# -- the gate -------------------------------------------------------------

def test_the_accuracy_gate_zeroes_everything_else():
    """A precisely-located, fix-it-carrying message about the wrong thing."""
    doc = case_doc("unknown type 'string'", cause=["assign"],
                   not_cause=["unknown type"], names=["a"],
                   suggestion="x", fixit="verified", has_related=True)
    block = R.score_case(doc)
    assert block["d1"] == 0
    assert block["d2"] == 3 and block["d4"] == 3
    assert block["composite"] == 0.0
    assert R.F_GATED in block["flags"]


@pytest.mark.parametrize("d1,expected", [
    (0, 0.0),
    (1, 0.75),
    (None, 0.75),     # unmeasured must NOT gate -- silence is not a zero
])
def test_apply_accuracy_gate_in_isolation(d1, expected):
    assert R.apply_accuracy_gate(d1, 0.75) == expected


def test_composite_averages_only_what_was_measured():
    scores = {"d1": None, "d2": 3, "d3": None, "d4": 3, "d5": 3, "d6": 3}
    assert R.composite(scores) == 1.0
    assert R.composite({d: None for d in R.DIMENSIONS}) is None


def test_the_measured_count_travels_with_the_score():
    block = R.score_case(case_doc())        # no cause:, no names:
    assert block["measured"] == 4
    assert block["composite"] == round((3 + 2 + 2 + 2) / 12, 4)
    assert block["d1"] is None and block["d3"] is None


def test_a_detected_case_whose_message_misses_the_cause_is_flagged_for_a_human():
    block = R.score_case(case_doc("something went wrong", cause=["assign"]))
    assert R.F_D1_DISAGREES in block["flags"]


def test_non_gradeable_statuses_get_no_block():
    for status in ("missed", "clean", "spurious", "skipped", "control_failed"):
        assert R.score_case(case_doc(status=status)) is None


# -- fix-it application ---------------------------------------------------

def test_apply_fixit_replaces_the_diagnostic_span():
    source = "struct s {\n  bit[8] a = \"x\"\n}\n"
    # `end_col` is exclusive, matching how the CLI renderer computes its
    # underline span (`span = end_col - col`).
    diag = {"line": 2, "col": 17, "end_line": 2, "end_col": 17,
            "suggestion": ";"}
    assert R.apply_fixit(source, diag) == "struct s {\n  bit[8] a = \"x\";\n}\n"


def test_apply_fixit_spans_lines():
    source = "a\nb\nc\n"
    diag = {"line": 1, "col": 1, "end_line": 3, "end_col": 1,
            "suggestion": "Z"}
    assert R.apply_fixit(source, diag) == "Zc\n"


@pytest.mark.parametrize("diag", [
    {"line": 1, "col": 1, "end_col": 2},                       # no suggestion
    {"line": 1, "col": 1, "suggestion": ";"},                  # no span
    {"line": 99, "col": 1, "end_col": 2, "suggestion": ";"},   # off the end
    {"line": 2, "col": 5, "end_line": 1, "end_col": 1, "suggestion": ";"},
])
def test_apply_fixit_declines_what_it_cannot_apply(diag):
    assert R.apply_fixit("a\nb\n", diag) is None


# -- rollups --------------------------------------------------------------

def test_rollup_reports_per_class_and_per_dimension_never_a_headline():
    cases = [dict(case_doc(cls="syntax.punct"), case="A"),
             dict(case_doc(cls="syntax.braces", cause=["assign"]), case="B")]
    for case in cases:
        case["rubric"] = R.score_case(case)
    roll = R.rollup(cases)
    assert set(roll["by_class"]) == {"syntax.punct", "syntax.braces"}
    assert roll["dimensions"]["d1"]["measured"] == 1
    assert roll["dimensions"]["d1"]["unmeasured"] == 1
    assert roll["tier"] == {"A": 2, "B": 0}
    assert "quality" not in roll and "score" not in roll


def test_coverage_is_the_backfill_queue():
    cases = [dict(case_doc(), case="A"),
             dict(case_doc(cause=["x"], names=["a"]), case="B"),
             dict(case_doc(status="missed"), case="C")]
    coverage = R.metadata_coverage(cases)
    assert coverage == {"gradeable": 2, "cause": 1, "not_cause": 0, "names": 1}
    assert R.cases_missing_metadata(cases, "cause") == ["A"]


# -- Tier B sample and cache ----------------------------------------------

def make_run_doc(cases):
    return {"schema": "pss-errsuite/run/1",
            "run": {"policy": {"tolerance": "token:2",
                               "severity_floor": "error",
                               "rubric_version": R.RUBRIC_VERSION}},
            "tool": {"name": "faketool", "version": "0.1"},
            "summary": {}, "cases": cases}


def test_the_tier_b_sample_is_deterministic_and_covers_every_class():
    cases = []
    for i in range(30):
        case = case_doc(cls="syntax.punct" if i < 25 else "syntax.braces")
        case["case"] = f"C{i:02d}"
        cases.append(case)
    doc = make_run_doc(cases)
    R.regrade(doc)
    first = R.tier_b_sample(doc["cases"])
    assert first == R.tier_b_sample(doc["cases"])
    classes = {c["class"] for c in cases if c["case"] in set(first)}
    assert classes == {"syntax.punct", "syntax.braces"}
    # ceil(10% of 25) = 3, and the 5-case class takes the floor of 3 too.
    assert len(first) == 3 + 3


def test_the_sample_always_includes_the_cases_a_proxy_cannot_settle():
    good = dict(case_doc(cause=["assign"]), case="GOOD", cls="a.b")
    odd = dict(case_doc("something else", cause=["assign"]), case="ODD",
               cls="a.b")
    filler = [dict(case_doc(cause=["assign"]), case=f"F{i}", cls="a.b")
              for i in range(20)]
    doc = make_run_doc([good, odd] + filler)
    R.regrade(doc)
    assert "ODD" in R.tier_b_sample(doc["cases"])


def test_tier_b_scores_override_the_proxy_and_mark_the_case():
    doc = case_doc(cause=["assign"])
    block = R.score_case(doc, override={"d1": 1, "notes": {"d1": "too vague"}},
                         rater="mb")
    assert block["d1"] == 1 and block["tier"] == "B" and block["rater"] == "mb"
    assert block["notes"]["d1"] == "too vague"
    assert block["d2"] == 3     # untouched dimensions keep the proxy score


def test_the_cache_key_changes_with_the_message_and_the_rubric(monkeypatch):
    a = case_doc("one")
    b = case_doc("two")
    assert R.fingerprint(a, "0.1") == R.fingerprint(case_doc("one"), "0.1")
    assert R.fingerprint(a, "0.1") != R.fingerprint(b, "0.1")
    assert R.fingerprint(a, "0.1") != R.fingerprint(a, "0.2")
    # A changed anchor invalidates a human score as surely as a changed
    # message does, so the rubric version is part of the key.
    before = R.fingerprint(a, "0.1")
    monkeypatch.setattr(R, "RUBRIC_VERSION", "99")
    assert R.fingerprint(a, "0.1") != before


def test_a_cached_human_score_survives_a_regrade(tmp_path):
    case = dict(case_doc(cause=["assign"]), case="A")
    doc = make_run_doc([case])
    R.regrade(doc)
    assert doc["cases"][0]["rubric"]["tier"] == "A"

    cache = R.RubricCache(tmp_path / "c.json")
    cache.put(R.fingerprint(case, "0.1"), {"d1": 1, "rater": "mb"})
    cache.save()

    R.regrade(doc, cache=R.RubricCache(tmp_path / "c.json"))
    block = doc["cases"][0]["rubric"]
    assert block["tier"] == "B" and block["d1"] == 1 and block["rater"] == "mb"


def test_a_cache_from_a_future_schema_is_ignored_rather_than_crashed_on(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"schema": "pss-errsuite/rubric-cache/99",
                                "entries": {"x": {"d1": 0}}}))
    assert R.RubricCache(path).entries == {}
    path.write_text("not json at all")
    assert R.RubricCache(path).entries == {}


def test_regrade_is_idempotent():
    doc = make_run_doc([dict(case_doc(cause=["assign"]), case="A"),
                        dict(case_doc(status="missed"), case="B")])
    once = json.dumps(R.regrade(doc), sort_keys=True)
    twice = json.dumps(R.regrade(json.loads(once)), sort_keys=True)
    assert once == twice
    assert "rubric" not in json.loads(once)["cases"][1]


# -- fix-it verification, end to end --------------------------------------

FIXIT_HEADER = """\
//! case:    {cid}
//! class:   fixture.fixit
//! title:   {title}
//! expect:  error
//! detect:  recommended
//! at:      9:1
//! count:   1
//! fix:     9: // repaired
{directive}
struct s {{ bit[8] a = "x"; }}
"""

# The fake tool's behaviour is dictated by the `//FAKE:` line, so a fix-it
# that "repairs" the file is one that edits that line out -- which is exactly
# the shape of a real repair, and means the re-run is a genuine second
# invocation with genuinely different input.
GOOD_FIX = ('//FAKE: emit 9:1 error "missing \';\' after \'a\'" '
            'end=8 suggestion="// fixed:"')
BAD_FIX = ('//FAKE: emit 9:1 error "missing \';\' after \'a\'" '
           'end=1 suggestion=" "')


@pytest.mark.parametrize("cid,directive,expected", [
    ("FX-FIXIT-OK", GOOD_FIX, R.FIXIT_VERIFIED),
    ("FX-FIXIT-BAD", BAD_FIX, R.FIXIT_INVALID),
])
def test_the_runner_applies_a_fixit_and_re_runs_the_tool(
        cid, directive, expected, write_case, faketool_json_descriptor):
    """Design §5.3's strongest signal: the only check that tests a message's
    *claim* rather than its shape.  `BAD_FIX` offers a suggestion that leaves
    the defect in place -- the tool proposed a fix that does not fix."""
    from pss_errsuite.adapters import make_adapter
    from pss_errsuite.runner import Runner

    case = write_case(f"{cid.lower()}.pss",
                      FIXIT_HEADER.format(cid=cid, title="fix-it",
                                          directive=directive))
    desc = faketool_json_descriptor
    runner = Runner(make_adapter(desc), desc, tool_pss="3.0")
    try:
        run = runner.run_case(case)
    finally:
        runner.cleanup()

    assert run.status == "detected"
    assert run.observations.fixit == expected
    assert run.control_status == "clean"


def test_a_verified_fixit_is_the_only_route_to_d4_three(
        write_case, faketool_json_descriptor):
    from pss_errsuite import report
    from pss_errsuite.adapters import make_adapter
    from pss_errsuite.runner import Runner

    desc = faketool_json_descriptor
    blocks = {}
    for cid, directive in (("FX-FIXIT-OK", GOOD_FIX),
                           ("FX-FIXIT-BAD", BAD_FIX)):
        case = write_case(f"{cid.lower()}.pss",
                          FIXIT_HEADER.format(cid=cid, title="fix-it",
                                              directive=directive))
        runner = Runner(make_adapter(desc), desc, tool_pss="3.0")
        try:
            run = runner.run_case(case)
        finally:
            runner.cleanup()
        blocks[cid] = report.case_document(run)["rubric"]

    assert blocks["FX-FIXIT-OK"]["d4"] == 3
    assert blocks["FX-FIXIT-BAD"]["d4"] == 1
    assert R.F_FIXIT_INVALID in blocks["FX-FIXIT-BAD"]["flags"]


def test_fixit_verification_can_be_turned_off(write_case,
                                              faketool_json_descriptor):
    """It costs one extra invocation per fix-it offered, which is worth
    declining on a slow tool."""
    from pss_errsuite.adapters import make_adapter
    from pss_errsuite.runner import Runner

    case = write_case("off.pss",
                      FIXIT_HEADER.format(cid="FX-FIXIT-OFF", title="t",
                                          directive=GOOD_FIX))
    desc = faketool_json_descriptor
    runner = Runner(make_adapter(desc), desc, tool_pss="3.0",
                    verify_fixit=False)
    try:
        run = runner.run_case(case)
    finally:
        runner.cleanup()
    assert run.observations.fixit is None
