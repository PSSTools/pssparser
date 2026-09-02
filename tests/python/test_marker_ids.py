"""
Pins the core marker-ID catalogue and the message-to-ID mapping.

Core markers originate in C++ and carry no ID on the marker object; the ID is
recovered in Python by matching the message text against the ``patterns``
declared on each ``MarkerDef``.  That makes the C++ message strings part of the
contract, with nothing in the build to enforce it -- hence this file.

Two kinds of coverage here:

1. **Mapping** -- representative message text for each ID maps to that ID, and
   nothing shadows anything else. A new pattern added in the wrong place will
   fail here rather than silently mis-labelling diagnostics.
2. **Discoverability** -- every declared ID is reachable through
   ``--list-markers`` and ``--describe``, which is the acceptance criterion for
   the PSS 3.1 marker allocation (plan item P0-T2).
"""
import io
import re

import pytest

from pssparser.checkers.core_checker import CoreChecker
from pssparser.cli.commands import _assign_core_code


# Representative message text for each core ID. For PSS100+ these are the
# messages the not-yet-written C++ code is *required* to emit -- keeping them
# here means the ID mapping is settled before the emitting code is written.
REPRESENTATIVE_MESSAGES = [
    ("PSS001", "expected ';' before '}'"),
    ("PSS001", "unexpected end of input; possible missing closing '}'"),
    ("PSS001", "unknown exec-block kind 'wibble'"),
    ("PSS001",
     "unexpected low bound '1' in an integer width; only '0' is permitted, "
     "as in 'bit[7:0]'"),
    ("PSS002", "unknown type 'Foo'"),
    ("PSS002", "unknown type 'Nope' in 'p::q'"),
    ("PSS002", "unknown identifier 'bar'"),
    ("PSS002", "unknown method 'baz' on built-in type"),
    ("PSS003", "duplicate declaration of 'a'"),
    ("PSS003", "duplicate symbol declaration"),
    ("PSS003", "duplicate parameter name 'p'"),
    ("PSS003", "duplicate variable declaration x, previously declared"),
    ("PSS004", "failed to resolve ref-path a.b.c"),
    ("PSS004", "root ref-path element x is not a composite scope"),
    ("PSS005", "cannot extend unknown type 'Foo'"),
    ("PSS005", "cannot extend unknown enum 'MyEnum'"),
    ("PSS006", "call to 'g' expects 1 argument, got 3"),
    ("PSS006", "call to 'g' expects 1 to 2 arguments, got 0"),
    ("PSS006", "call to 'g' expects at least 1 argument, got 0"),
    ("PSS006", "no overload of 'g' accepts 3 arguments"),
    # PSS006 covers the whole "call does not match the callee's parameters"
    # family -- count, argument type, and calling something that is not a
    # function. Both message spellings reach it: checkCallArity's for an
    # ordinary call, TaskCheckCallArgs's for a built-in method signature.
    ("PSS006", "too few arguments to 'f': expected 2, got 1"),
    ("PSS006", "too many arguments to 'f': expected at most 2, got 3"),
    ("PSS006", "argument 1 of 'g' is a string, but parameter 'a' is numeric"),
    ("PSS006", "'f' is not a function"),
    ("PSS007", "'f' returns void, so 'return' cannot take a value"),
    ("PSS008", "'f' is declared pure, so it cannot return void"),
    ("PSS009", "declarations of 'f' disagree about the return type"),
    ("PSS010", "no field 'chan_en' in register value type 'csr_s'"),
    ("PSS011", "invalid digit 'G' in based literal"),
    ("PSS100", "annotation is not attached to a model element"),
    ("PSS101", "unknown annotation type 'desc_s'; annotation disregarded"),
    ("PSS102", "annotation initializer for 'owner' is not a constant expression"),
    ("PSS104", "'compile if' branch without enclosing braces is deprecated"),
    ("PSS105", "illegal 'mutable' qualifier: not permitted on a rand field"),
    ("PSS106", "exec block tag is not permitted on 'body' exec blocks"),
    ("PSS107", "member selection is not permitted on a slice of 'arr'"),
    # PSS108/PSS109 -- the exact text emitted for the `{{` collision (D3.3).
    # The hint is a *suffix* on both, which keeps each pattern anchored on its
    # distinguishing prefix rather than on the shared tail.
    ("PSS108",
     "unterminated mustache expression; if '{{' was intended as literal text, "
     "separate the braces ('{ {') -- triple-quoted strings have no escape mechanism"),
    ("PSS109",
     "malformed mustache expression: unexpected ','; if '{{' was intended as "
     "literal text, separate the braces ('{ {')"),
    ("PSS110", "unterminated template directive"),
    ("PSS110", "unterminated template comment"),
    ("PSS110", "unclosed template block at end of string"),
    ("PSS110", "malformed template directive: expected ';' after assignment"),
    ("PSS111", "template block close with no open block"),
    ("PSS111", "'else' with no preceding 'if'"),
    ("PSS112",
     "template assignment target 'a' is not declared within this template string"),
    ("PSS113", "template expression is not of scalar type"),
    ("PSS114", "call to non-pure function 'f' in a template string"),
    ("PSS115",
     "template string with non-constant elements is not a constant expression"),
]


@pytest.mark.parametrize("expected_id,message", REPRESENTATIVE_MESSAGES)
def test_message_maps_to_expected_id(expected_id, message):
    assigned = _assign_core_code({"message": message})
    assert assigned.get("code") == expected_id, \
        "message %r mapped to %r, expected %r" % (
            message, assigned.get("code"), expected_id)


def test_unmatched_message_gets_no_code():
    """A message no pattern claims must stay uncoded, not fall through to one."""
    assigned = _assign_core_code({"message": "some entirely novel diagnostic"})
    assert "code" not in assigned


def test_existing_code_is_not_overwritten():
    """Checker-produced markers already carry a code; leave it alone."""
    assigned = _assign_core_code({"message": "unknown type 'Foo'", "code": "PSC001"})
    assert assigned["code"] == "PSC001"


# -- catalogue integrity ----------------------------------------------------

def test_marker_ids_are_unique():
    ids = [m.id for m in CoreChecker.marker_defs]
    assert len(ids) == len(set(ids))


def test_marker_ids_are_in_ascending_order():
    """Patterns are tried in declaration order, so keep that order legible."""
    ids = [m.id for m in CoreChecker.marker_defs]
    assert ids == sorted(ids)


#: PSS020-PSS029: syntax-classification sub-band, plus PSS029 (the
#: --max-errors cutoff marker, MarkerCollector::marker in C++). These IDs
#: arrive on the marker directly from C++, not via message-pattern matching,
#: so `patterns` is deliberately empty and there is nothing to add to
#: REPRESENTATIVE_MESSAGES for them -- see SYNTAX_BAND_SAMPLES and
#: test_syntax_band_ids_are_reachable below instead.
#: PSS023 and PSS027 are reserved, not assigned (see core_checker.py).
_SYNTAX_BAND = {"PSS0%02d" % n for n in range(20, 30)}


def test_every_core_marker_declares_patterns():
    """A core marker with no pattern can never be assigned to a diagnostic."""
    missing = [
        m.id for m in CoreChecker.marker_defs
        if not m.patterns and m.id not in _SYNTAX_BAND
    ]
    assert not missing, "core markers with no message patterns: %s" % missing


def test_every_marker_has_a_representative_message():
    """Every declared ID must be exercised by the mapping test above."""
    covered = {mid for mid, _ in REPRESENTATIVE_MESSAGES} | _SYNTAX_BAND
    declared = {m.id for m in CoreChecker.marker_defs}
    assert declared - covered == set(), \
        "IDs with no representative message: %s" % sorted(declared - covered)


def test_syntax_band_markers_declare_no_patterns():
    """The inverse of test_every_core_marker_declares_patterns: a syntax-band
    marker's code comes from C++, so a pattern here would be dead weight that
    could silently shadow a real (checker-produced) diagnostic."""
    offenders = [
        m.id for m in CoreChecker.marker_defs
        if m.id in _SYNTAX_BAND and m.patterns
    ]
    assert not offenders, "syntax-band markers with unnecessary patterns: %s" % offenders


def test_assign_core_code_never_fires_for_the_syntax_band():
    """_assign_core_code only fills in a missing code; a syntax-band marker
    must always already carry one by the time Python sees it."""
    for marker_id in sorted(_SYNTAX_BAND - {"PSS023", "PSS027"}):
        assigned = _assign_core_code({"message": "some entirely novel diagnostic"})
        assert assigned.get("code") != marker_id


#: One real snippet per reachable syntax-band ID, parsed through the actual
#: C++ parser (not the message-pattern table above -- there is none for these
#: IDs). PSS023 and PSS027 are reserved/unreachable (see core_checker.py) and
#: are deliberately absent here. The third element is the --max-errors value
#: to apply before parsing (None = library default, unlimited) -- only
#: PSS029 needs one, since it is the cap-cutoff marker itself.
SYNTAX_BAND_SAMPLES = [
    ("PSS020", "struct S { int x }", None),
    ("PSS021", "struct S { int x; ", None),
    ("PSS022", "struct S { int ; }", None),
    ("PSS024", "class C { }", None),
    ("PSS025", "struct S { int x; * }", None),
    ("PSS026", "enum E { struct };", None),
    ("PSS028", "struct S { 123 x; }", None),
    (
        "PSS029",
        "\n".join("struct S%d { int ; }" % i for i in range(5)),
        2,
    ),
]


@pytest.mark.parametrize("expected_id,source,max_errors", SYNTAX_BAND_SAMPLES)
def test_syntax_band_ids_are_reachable(expected_id, source, max_errors):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent))
    from test_helpers import parse_collect

    try:
        _root, markers = parse_collect(source, max_errors=max_errors)
    except Exception as exc:
        markers = getattr(exc, "markers", [])
    codes = [m.get("code") for m in markers]
    assert expected_id in codes, \
        "parsing %r produced codes %r, expected %r among them" % (
            source, codes, expected_id)


def test_syntax_band_samples_cover_every_reachable_id():
    covered = {mid for mid, _, _ in SYNTAX_BAND_SAMPLES}
    reachable = _SYNTAX_BAND - {"PSS023", "PSS027"}
    assert reachable - covered == set(), \
        "reachable syntax-band IDs with no sample: %s" % sorted(reachable - covered)


def test_every_reachable_syntax_band_id_has_a_corpus_case():
    """Exit criterion for E-3: every PSS020-PSS028 ID that can actually be
    emitted (excludes the reserved PSS023/PSS027) has >= 1 corpus case under
    tests/python/errors/data/, queried the same way test_corpus.py does."""
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent / "errors"))
    from corpus_loader import collect_cases

    ids_with_cases = {c.id for c in collect_cases() if c.id in _SYNTAX_BAND}
    reachable = _SYNTAX_BAND - {"PSS023", "PSS027"}
    assert reachable - ids_with_cases == set(), \
        "reachable syntax-band IDs with no corpus case: %s" % sorted(
            reachable - ids_with_cases)


def test_all_patterns_compile():
    for mdef in CoreChecker.marker_defs:
        for pat in mdef.patterns:
            re.compile(pat, re.IGNORECASE)


def test_severities_are_valid():
    valid = {"error", "warning", "info", "hint"}
    for mdef in CoreChecker.marker_defs:
        assert mdef.severity in valid, \
            "%s has invalid severity %r" % (mdef.id, mdef.severity)


def test_pss31_band_is_reserved_for_31_diagnostics():
    """PSS100-PSS199 is the PSS 3.1 band; PSS001-PSS099 the general one."""
    pss31 = [m.id for m in CoreChecker.marker_defs
             if 100 <= int(m.id[3:]) <= 199]
    # PSS103 is retired (see core_checker.py): §7.13b is enforced by the
    # grammar, so no linker check can emit it. The gap is deliberate -- the ID
    # must not be reused.
    assert pss31 == ["PSS100", "PSS101", "PSS102",
                     "PSS104", "PSS105", "PSS106", "PSS107",
                     "PSS108", "PSS109", "PSS110", "PSS111", "PSS112",
                     "PSS113", "PSS114", "PSS115"]


# -- CLI discoverability (P0-T2 acceptance criterion) ------------------------

def _manager():
    from pssparser.checkers import CheckerManager
    manager = CheckerManager()
    manager.discover()
    return manager


def test_list_markers_shows_every_core_id():
    from pssparser.cli.checker_cmds import cmd_list_markers

    out = io.StringIO()
    assert cmd_list_markers(_manager(), stdout=out) == 0
    text = out.getvalue()

    for mdef in CoreChecker.marker_defs:
        assert mdef.id in text, "%s missing from --list-markers" % mdef.id


@pytest.mark.parametrize("marker_id", [m.id for m in CoreChecker.marker_defs])
def test_describe_returns_detail_for_every_core_id(marker_id):
    from pssparser.cli.checker_cmds import cmd_describe

    out = io.StringIO()
    err = io.StringIO()
    assert cmd_describe(_manager(), marker_id, stdout=out, stderr=err) == 0, \
        err.getvalue()
    text = out.getvalue()
    assert marker_id in text
    assert len(text.strip()) > len(marker_id) + 20, \
        "--describe %s produced no substantive text" % marker_id


def test_describe_rejects_unknown_id():
    from pssparser.cli.checker_cmds import cmd_describe

    out = io.StringIO()
    err = io.StringIO()
    assert cmd_describe(_manager(), "PSS999", stdout=out, stderr=err) == 2
    assert "unknown marker" in err.getvalue()
