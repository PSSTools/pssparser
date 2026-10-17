"""Source waivers in the core (lint-core-plan.md C7.2): collection and
application ported from :mod:`pssparser.waivers`, which is the oracle here.
The same waivers, spans, diagnostics kept and waived, and hygiene markers,
word for word."""
import random

import pytest

from pssparser import Parser
from pssparser import waivers as W
from pssparser.checkers import MarkerDef
from pssparser.checkers.selectors import RuleSet, _is_core_error
from pssparser.lint.selection import tell_engine, with_core


def _same(a, b):
    """Waivers compared field by field (ids and used included)."""
    def key(w):
        return (w.form, w.file, w.line, w.col, w.selectors, w.reason, tuple(w.start),
                tuple(w.end), sorted(w.ids), w.used)
    assert [key(w) for w in a] == [key(w) for w in b]


# -- pragmas --------------------------------------------------------------

PRAGMAS = [
    "struct s {}  // pssparser waive LINT402: why\n",
    "// pssparser waive LINT402, LINT401: why\n\n// other\nstruct s {}\n",
    "// pssparser waive LINT402\nstruct s {}\n",
    "/* // pssparser waive LINT402: x */ struct s {}\n",
    'const string s = "// pssparser waive LINT402: x";\n',
    "// pssparser waiver LINT402: x\nstruct s {}\n",
    "//pssparser waive LINT402: tight\nstruct s {}\n",
    "//   pssparser \t waive   LINT402 ,, LINT401 :  a: b : c  \r\nstruct s {}\r\n",
    "// pssparser waive: no ids\nstruct s {}\n",
    "// pssparser waive , : commas only\nstruct s {}\n",
    "// pssparserwaive LINT402: no space\nstruct s {}\n",
    "// pssparser waive_ LINT402: word after\nstruct s {}\n",
    "// pssparser waiveé LINT402: unicode word\nstruct s {}\n",
    "// pssparser waive LINT402: ümläut reason ☃\nstruct s {}\n",
    "struct s {}\n// pssparser waive LINT402: at the end, no code after\n",
    "// pssparser waive LINT402: last line, no newline",
    "/* block */ // pssparser waive LINT402: only trivia before\nstruct s {}\n",
    "struct s { /* multi\n line */ } // pssparser waive LINT402: after ML\n",
    "  \t// pssparser waive LINT402: indented\n\n\n   struct s {}\n",
    "﻿// pssparser waive LINT402: after a BOM\nstruct s {}\n",
    "struct s {} \x01 // pssparser waive LINT402: after an error char\n",
    "// pssparser waive LINT402: one\n// pssparser waive LINT401: two\nstruct s {}\n",
    "component C {\n  int a; // pssparser waive LINT402: x\n  // pssparser waive "
    "LINT401: y\n  int b;\n}\n",
]


@pytest.mark.parametrize("src", PRAGMAS)
def test_pragmas(factory, src):
    e = factory.mkLintEngine()
    got = [W.Waiver.from_engine(w) for w in e.collect_waivers([], {"m.pss": src})["waivers"]]
    _same(got, W.collect_pragmas("m.pss", src))


def test_pragmas_in_several_files_are_sorted_by_file(factory):
    texts = {"b.pss": PRAGMAS[0], "a.pss": PRAGMAS[1] + PRAGMAS[0]}
    e = factory.mkLintEngine()
    got = [W.Waiver.from_engine(w) for w in e.collect_waivers([], texts)["waivers"]]
    _same(got, W.collect(None, list(texts), read=texts.__getitem__))
    assert [w.file for w in got] == ["a.pss", "a.pss", "b.pss"]


# -- annotations ----------------------------------------------------------

ANN = '@lint_pkg::waive {.id = "LINT402", .reason = "r"}'

ANNOTATED = [
    "component C {\n  %s\n  int a;\n  int b;\n}\n" % ANN,
    "component C {\n  %s\n  function void f() {\n    int a;\n  }\n}\n" % ANN,
    "component C { action A {} action B {\n  activity {\n    %s\n"
    "    do A;\n    do A;\n  } } }\n" % ANN,
    "package p {\n  struct t {}\n  %s;\n  struct u {}\n}\nstruct v {}\n" % ANN,
    "%s;\nstruct v {}\n" % ANN,
    "package q { annotation waive { string id; string reason; } }\n"
    'component C { @q::waive {.id = "LINT402", .reason = "r"} int a; }\n',
    '@lint_pkg::waive {.id = " LINT402 , LINT401 ,", .reason = "  spaced  "}\n'
    "component C { }\n",
    '@lint_pkg::waive {.id = "LINT402"}\ncomponent C { }\n',
    '@lint_pkg::waive {.reason = "no id"}\ncomponent C { }\n',
    '@lint_pkg::waive\ncomponent C { }\n',
    "component C {\n  %s\n  %s\n  int a;\n}\n" % (ANN, ANN.replace("LINT402", "LINT401")),
    "component C {\n  exec run_start {\n    %s\n    int x = 1;\n  }\n}\n" % ANN,
    "struct s {\n  %s\n  rand int a;\n  constraint {\n    %s\n    a > 1;\n  }\n}\n"
    % (ANN, ANN),
    # An annotation on a top-level package fails link() (known-issues LE-4):
    # parse only, below.
    "%s\npackage p {\n  %s;\n}\n" % (ANN, ANN),
    "component C { %s int a; } // pssparser waive LINT401: both forms\n" % ANN,
]


def _collect_both(e, srcs, link=True):
    p = Parser()
    p.parses(list(srcs.items()))
    if link:
        p.link()
    read = srcs.__getitem__
    return W.collect(p, list(srcs), read=read), W.collect_in(e, p, list(srcs), read=read)


@pytest.mark.parametrize("src", ANNOTATED)
@pytest.mark.parametrize("link", [True, False], ids=["linked", "parsed"])
def test_annotations(factory, src, link):
    if link and "\npackage p {\n  @" in src:
        pytest.skip("known-issues LE-4: an annotation on a package does not link")
    oracle, core = _collect_both(factory.mkLintEngine(), {"m.pss": src}, link)
    _same(core, oracle)


def test_annotations_without_an_ast_are_not_collected(factory):
    src = ANNOTATED[0] + "// pssparser waive LINT401: x\nstruct t {}\n"
    e = factory.mkLintEngine()
    got = W.collect_in(e, None, ["m.pss"], read=lambda f: src)
    assert [w.form for w in got] == ["pragma"]


#: Where an element or standalone waiver may go, in models of each kind of
#: scope; the random tests put one or more at some of these places.
TEMPLATE = """\
package p {{
{0}  struct t {{
{1}    rand int a;
{2}    constraint {{
{3}      a > 1;
{4}      if (a > 2) {{ a < 10; }}
    }}
  }}
{5}  enum e {{ A, B }}
}}
component C {{
{6}  int f;
{7}  action A {{
{8}    rand bit[8] x;
{9}    exec body {{
{10}      int y = 1;
{11}      if (y > 0) {{ y = 2; }}
    }}
  }}
{12}  action B {{
    activity {{
{13}      do A;
{14}      repeat (2) {{ do A; }}
    }}
  }}
{15}  function void g() {{
{16}    int z;
  }}
}}
"""


def _random_model(rng):
    slots = []
    for i in range(17):
        text = ""
        for _ in range(rng.choice((0, 0, 0, 1, 1, 2))):
            ids = rng.choice(("LINT402", "LINT401, LINT402", "style", "LINT4", "nosuch"))
            reason = rng.choice(("", ", .reason = \"r\""))
            ann = '@lint_pkg::waive {.id = "%s"%s}' % (ids, reason)
            # An element annotation on the enum does not link (LE-4).
            if rng.random() < 0.3 or i == 5:
                ann += ";"
            text += "  " + ann + ("\n" if rng.random() < 0.7 else " ")
            if rng.random() < 0.2:
                text += "// pssparser waive %s: p\n" % ids
        slots.append(text)
    return TEMPLATE.format(*slots)


@pytest.mark.parametrize("seed", range(40))
def test_random_annotations(factory, seed):
    rng = random.Random(seed)
    srcs = {"a.pss": _random_model(rng), "b.pss": _random_model(rng).replace("p {", "p2 {")
            .replace("component C", "component C2")}
    oracle, core = _collect_both(factory.mkLintEngine(), srcs, link=rng.random() < 0.7)
    _same(core, oracle)


# -- application ----------------------------------------------------------

def _rule(id, tier, *, name="", family="", **kw):
    return MarkerDef(id=id, severity="", summary=id, tier=tier, name=name, family=family,
                     detail="Severity: tier default.", **kw)


#: A small catalogue: core errors, a tool error, the hygiene markers, a
#: retired code, lint rules in families and tiers, and a team's rules.
RULES = [
    MarkerDef(id="PSS001", severity="error", summary="syntax"),
    MarkerDef(id="PSS002", severity="error", summary="unresolved"),
    MarkerDef(id="PSS010", severity="warning", summary="an LRM warning"),
    MarkerDef(id="PSSP000", severity="error", summary="tool", tier="tool"),
    MarkerDef(id="PSSP202", severity="warning", summary="unused", tier="tool"),
    MarkerDef(id="PSSP203", severity="warning", summary="unknown", tier="tool"),
    MarkerDef(id="PSSP204", severity="warning", summary="on error", tier="tool"),
    MarkerDef(id="PSSP205", severity="warning", summary="no reason", tier="tool"),
    MarkerDef(id="PSSP004", severity="info", summary="alias", tier="tool"),
    MarkerDef(id="PSS053", severity="warning", summary="old", status="retired",
              replaced_by=("LINT402",)),
    MarkerDef(id="LINT099", severity="warning", summary="old too", status="retired",
              replaced_by=("PSS002",)),
    _rule("LINT401", "suspicious", name="import-shadow", family="import"),
    _rule("LINT402", "style", name="import-after-declaration", family="import"),
    _rule("LINT403", "correctness", name="unknown-annotation", family="decl"),
    _rule("ACME001", "style", name="acme-suffix", family="naming", aliases=("ACME900",)),
    _rule("ACME002", "pedantic", name="acme-case", family="naming"),
]

CODES = [md.id for md in RULES] + ["", "XYZ999", None]

#: What the engine holds after tell_engine(RULES): the core's markers too,
#: RULES' replacing theirs (C7.3). The oracle resolves against the same.
ALL = with_core(RULES)

SELECTORS = ["LINT402", "LINT401", "import-after-declaration", "family:import", "LINT4",
             "LINT", "style", "ACME", "acme-suffix", "ACME900", "PSS053", "LINT099", "PSS002",
             "PSS", "PSSP", "PSSP202", "PSS010", "error", "nosuch", "LINT40X", "family:nope",
             "recommended", "all", "tool"]


@pytest.fixture
def engine(factory):
    # As the CLI tells it: `minimal` is MINIMAL_IDS, as RuleSet's default.
    e = factory.mkLintEngine()
    tell_engine(e, RULES)
    return e


def _aliases(mdefs):
    """manager.alias_map(): every rule's aliases, then retired codes."""
    out = {a: md.id for md in mdefs for a in md.aliases}
    for md in mdefs:
        if md.status == "retired" and md.replaced_by:
            out.setdefault(md.id, md.replaced_by[0])
    return out


def _oracle_apply(diags, waivers, ran):
    catalog = {md.id: md for md in ALL}
    aliases = _aliases(ALL)
    return W.apply(diags, waivers, rules=RuleSet(ALL),
                   is_core_error=lambda c: c in catalog and _is_core_error(catalog[c]),
                   ran=ran, aliases=aliases)


def _waiver(rng, file):
    form = rng.choice(("pragma", "annotation"))
    sels = rng.sample(SELECTORS, rng.choice((0, 1, 1, 1, 2, 3)))
    line = rng.randint(1, 20)
    end = rng.choice(((line, W._EOL), (line + rng.randint(0, 5), rng.randint(1, 30)),
                      (W._EOL, W._EOL)))
    return W.Waiver(form=form, file=file, line=line, col=rng.randint(1, 20), selectors=sels,
                    reason=rng.choice(("", "why")), start=(line, rng.randint(1, 10)), end=end)


def _diag(rng, files):
    return {"code": rng.choice(CODES), "file": rng.choice(files),
            "line": rng.randint(0, 25), "col": rng.randint(0, 40), "message": "m"}


def _check(engine, diags, mk_waivers, ran):
    oracle_w, core_w = mk_waivers(), mk_waivers()
    want = _oracle_apply(diags, oracle_w, ran)
    got = W.apply_in(engine, diags, core_w, ran=ran)
    assert [id(d) for d in got.kept] == [id(d) for d in want.kept]
    def at(ws, w):
        return next(i for i, x in enumerate(ws) if x is w)
    assert [(id(d), at(core_w, w)) for d, w in got.waived] == [
        (id(d), at(oracle_w, w)) for d, w in want.waived]
    assert got.markers == want.markers
    _same(core_w, oracle_w)


@pytest.mark.parametrize("seed", range(80))
def test_random_application(engine, seed, tmp_path, monkeypatch):
    # Two spellings of one file: the waivers match by real path.
    monkeypatch.chdir(tmp_path)
    rng = random.Random(seed)
    files = ["a.pss", "./a.pss", "b.pss"]
    diags = [_diag(rng, files) for _ in range(rng.randint(0, 25))]
    specs = [(rng.getstate(), rng.choice(("a.pss", "b.pss")))
             for _ in range(rng.randint(0, 6))]
    for _ in range(len(specs)):
        rng.random()

    def mk():
        out = []
        for state, file in specs:
            r = random.Random()
            r.setstate(state)
            out.append(_waiver(r, file))
        return out

    ran = None
    if rng.random() < 0.7:
        ran = set(rng.sample([md.id for md in RULES], rng.randint(0, len(RULES))))
    _check(engine, diags, mk, ran)


def test_application_cases(engine):
    def mk():
        return [
            W.Waiver("annotation", "m.pss", 3, 3, ["LINT402"], "r", (3, 3), (10, 2)),
            W.Waiver("pragma", "m.pss", 4, 19, ["PSS053"], "", (4, 1), (4, W._EOL)),
            W.Waiver("annotation", "m.pss", 12, 1, ["PSS002", "LINT401"], "r",
                     (12, 1), (W._EOL, W._EOL)),
            W.Waiver("annotation", "m.pss", 13, 1, ["PSS"], "r", (13, 1), (14, 1)),
            W.Waiver("pragma", "m.pss", 15, 1, [], "r", (16, 1), (16, W._EOL)),
            W.Waiver("pragma", "m.pss", 17, 1, ["LINT40X"], "r", (18, 1), (18, W._EOL)),
            W.Waiver("annotation", "m.pss", 19, 1, ["ACME"], "r", (19, 1), (20, 1)),
        ]
    diags = [
        {"code": "LINT402", "file": "m.pss", "line": 5, "col": 3},     # waived
        {"code": "LINT402", "file": "m.pss", "line": 10, "col": 2},    # end is exclusive
        {"code": "LINT402", "file": "m.pss", "line": 4, "col": 7},     # by the old ID
        {"code": "PSS002", "file": "m.pss", "line": 12, "col": 5},     # an error: kept
        {"code": "LINT401", "file": "m.pss", "line": 30, "col": 1},    # to the file's end
        {"code": "PSSP205", "file": "m.pss", "line": 13, "col": 1},    # hygiene: kept
        {"code": "PSS010", "file": "m.pss", "line": 13, "col": 9},     # PSS's warning
    ]
    _check(engine, diags, mk, {"LINT402", "LINT401", "ACME001", "ACME002"})
    got = W.apply_in(engine, diags, mk(), ran={"ACME001"})
    assert [m["code"] for m in got.markers] == [
        "PSSP004", "PSSP205", "PSSP204", "PSSP203", "PSSP203", "PSSP202"]


def test_empty_requests(engine):
    assert engine.apply_waivers([], [], None) == {
        "ok": True, "kept": [], "waived": [], "waivers": [], "markers": []}
    assert engine.collect_waivers([], {}) == {"ok": True, "waivers": []}


# -- the real registry ----------------------------------------------------

def test_the_real_registry(factory, tmp_path, monkeypatch):
    """Every selector a waiver may name, against the CLI's markers."""
    from pssparser.checkers.manager import CheckerManager
    from pssparser.lint.selection import tell_engine

    monkeypatch.chdir(tmp_path)
    manager = CheckerManager()
    manager.discover(load_extensions=False)
    mdefs = list(manager.all_marker_defs())
    e = factory.mkLintEngine()
    tell_engine(e, mdefs)
    catalog = {md.id: md for md in mdefs}
    aliases = manager.alias_map()
    sels = ([md.id for md in mdefs] + [md.name for md in mdefs if md.name]
            + ["LINT", "PSS", "PSSP", "style", "recommended", "family:decl", "nosuch"])
    rng = random.Random(7)

    def mk():
        return [W.Waiver("pragma", "m.pss", i + 1, 1, [s], "r", (i + 1, 1), (i + 1, W._EOL))
                for i, s in enumerate(sels)]
    diags = [{"code": rng.choice(list(catalog)), "file": "m.pss",
              "line": rng.randint(1, len(sels)), "col": 1} for _ in range(400)]
    ran = set(catalog)
    oracle_w, core_w = mk(), mk()
    want = W.apply(diags, oracle_w, rules=RuleSet(mdefs),
                   is_core_error=lambda c: c in catalog and _is_core_error(catalog[c]),
                   ran=ran, aliases=aliases)
    got = W.apply_in(e, diags, core_w, ran=ran)
    assert [id(d) for d in got.kept] == [id(d) for d in want.kept]
    assert got.markers == want.markers
    _same(core_w, oracle_w)


def test_a_rules_alias_is_an_old_id(engine):
    """A rule's alias works in a waiver, with the PSSP004 note, as a retired
    code does (the oracle took only retired codes until C7.2)."""
    w = [W.Waiver("pragma", "m.pss", 1, 1, ["ACME900"], "r", (2, 1), (2, W._EOL))]
    d = [{"code": "ACME001", "file": "m.pss", "line": 2, "col": 5}]
    got = W.apply_in(engine, d, w, ran={"ACME001"})
    assert got.kept == [] and len(got.waived) == 1
    assert [(m["code"], m["severity"], m["message"]) for m in got.markers] == [
        ("PSSP004", "info", "'ACME900' is the old ID of ACME001; write 'ACME001' in the waiver")]
