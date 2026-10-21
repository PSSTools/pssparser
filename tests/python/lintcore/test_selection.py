"""Selection in the core (lint-core-plan.md C7.1): profiles, selectors and
precedence, ported from :mod:`pssparser.checkers.selectors`, which is the
oracle here. The same answers, and the same messages, word for word."""
import random

import pytest

from pssparser.checkers import MarkerDef
from pssparser.checkers.selectors import RuleSet, SelectorError
from pssparser.lint.selection import host_marker, with_core


def _rule(id, tier, *, name="", family="", since="", default_enabled=True, **kw):
    return MarkerDef(id=id, severity="", summary=id, tier=tier, name=name, family=family,
                     since=since, default_enabled=default_enabled,
                     detail="Severity: tier default.", **kw)


#: test_selectors.py's catalogue, plus teams, an alias and a retired code.
RULES = [
    MarkerDef(id="PSS001", severity="error", summary="syntax"),
    MarkerDef(id="PSSP000", severity="error", summary="tool", tier="tool"),
    MarkerDef(id="PSS053", severity="warning", summary="old", status="retired",
              replaced_by=("LINT601",)),
    _rule("LINT101", "correctness", name="corr-rule", family="constraint"),
    _rule("LINT102", "suspicious", name="susp-rule", family="constraint"),
    _rule("LINT203", "portability", name="port-rule", family="activity"),
    _rule("LINT204", "simplify", name="simp-rule", family="activity"),
    _rule("LINT301", "style", name="style-rule", family="exec"),
    _rule("LINT302", "pedantic", name="ped-rule", family="exec"),
    _rule("LINT401", "restriction", name="restr-rule", family="decl"),
    _rule("LINT402", "nursery", name="nurs-rule", family="decl", since="2026.1"),
    _rule("LINT501", "suspicious", name="new-rule", family="register", since="2027.1"),
    _rule("LINT502", "suspicious", name="opt-in-rule", family="register",
          default_enabled=False),
    _rule("LINT601", "style", name="minimal-style", family="evolution"),
    _rule("ACME001", "style", name="acme-suffix", family="naming", aliases=("ACME900",)),
    _rule("ACME100", "suspicious", name="acme-claim"),
    _rule("ACME-NET001", "correctness", name="net-one"),
    _rule("ACME-NET100", "style", name="net-hundred"),
    _rule("ACME-DMA001", "pedantic", name="dma-one", since="2026.2"),
]

MINIMAL = ("LINT601",)


def merged_minimal(mdefs, minimal):
    """`minimal` for the host's entries; the core's own for the rest."""
    from pssparser.lint.catalog import MINIMAL_IDS
    host = {md.id for md in mdefs}
    return tuple(minimal) + tuple(i for i in MINIMAL_IDS if i not in host)


#: What the engine holds after the `engine` fixture's set_host_markers(): the
#: core's markers too (C7.3).
ALL = with_core(RULES)
ALL_MINIMAL = merged_minimal(RULES, MINIMAL)
#: The core's `minimal` rules that RULES does not replace: always there.
CORE_MIN = set(ALL_MINIMAL) - set(MINIMAL)


def _aliases(mdefs):
    out = {}
    for md in mdefs:
        for a in md.aliases:
            out[a] = md.id
    for md in mdefs:
        if md.status == "retired" and md.replaced_by:
            out.setdefault(md.id, md.replaced_by[0])
    return out


def _oracle(mdefs=ALL, minimal=ALL_MINIMAL, pin=""):
    rs = RuleSet(mdefs, rules_version=pin, minimal=minimal)
    rs.aliases = _aliases(mdefs)
    return rs


@pytest.fixture
def engine(factory):
    e = factory.mkLintEngine()
    assert e.set_host_markers([host_marker(md, md.id in MINIMAL) for md in RULES]) == []
    return e


def _resolve(engine, profile=None, select=(), ignore=(), cli_select=(), cli_ignore=(),
             pin="", rule=None, overrides=None, **more):
    lint = {"select": list(select), "ignore": list(ignore)}
    if rule is not None:
        lint["rule"] = rule
    if overrides is not None:
        lint["overrides"] = overrides
    if profile is not None:
        lint["profile"] = profile
    if pin:
        lint["rules-version"] = pin
    req = {"lint": lint, "command_line": {"select": list(cli_select),
                                          "ignore": list(cli_ignore)}}
    req.update(more)
    r = engine.resolve_selection(req)
    assert r["ok"], r
    return r


def _enabled(engine, *a, **kw):
    r = _resolve(engine, *a, **kw)
    assert r["errors"] == [], r["errors"]
    return set(r["groups"][0]["enabled"])


# -- the oracle's own cases ------------------------------------------------

@pytest.mark.parametrize("profile", ["none", "minimal", "recommended", "library", "strict",
                                     "all"])
def test_profiles(engine, profile):
    assert _enabled(engine, profile) == _oracle().resolve(profile)


def test_the_default_profile_is_minimal(engine):
    assert _enabled(engine) == {"LINT601"} | CORE_MIN


@pytest.mark.parametrize("profile,select,ignore", [
    ("recommended", ["LINT102"], ["suspicious"]),
    ("recommended", ["LINT10"], ["family:constraint"]),
    ("none", ["family:activity"], ["portability"]),
    ("none", ["LINT1"], ["LINT"]),
    ("none", ["LINT"], ["LINT10"]),
    ("none", ["LINT101"], ["corr-rule"]),              # a tie goes to ignore
    ("none", ["recommended", "pedantic"], ["LINT203"]),
    ("all", [], []),
    ("all", ["opt-in-rule"], []),
    ("none", ["ACME"], ["ACME-NET"]),
    ("none", ["ACME-NET"], ["ACME"]),
    ("none", ["ACME-NET1"], []),
    ("none", ["PSS053"], []),                           # a retired code: its replacement
    ("none", ["ACME900"], []),                          # an alias
    ("none", ["  LINT101 "], []),                       # trimmed
])
def test_precedence(engine, profile, select, ignore):
    assert _enabled(engine, profile, select, ignore) == \
        _oracle().resolve(profile, select, ignore)


def test_the_pin(engine):
    rs = _oracle(pin="2026.1")
    r = _resolve(engine, "strict", pin="2026.1")
    assert set(r["groups"][0]["enabled"]) == rs.resolve("strict")
    # LINT409-LINT411 are core-emitted, but since 2026.2: a pin holds
    # them back like any other rule.
    assert r["groups"][0]["held_back"] == rs.held_back("strict") == [
        "ACME-DMA001", "LINT409", "LINT410", "LINT411", "LINT501"]
    # An explicit select beats the pin.
    assert "LINT501" in _enabled(engine, "recommended", ["new-rule"], pin="2026.1")


def test_the_command_line_is_a_layer(engine):
    rs = _oracle()
    want = rs.overlay(rs.resolve("recommended", ["ACME"], ["LINT204"]),
                      ["LINT204", "style"], ["ACME-NET"])
    assert _enabled(engine, "recommended", ["ACME"], ["LINT204"],
                    cli_select=["LINT204", "style"], cli_ignore=["ACME-NET"]) == want


@pytest.mark.parametrize("text", ["cor-rule", "family:constrain", "ACME-OPS", "ACME-TEAM1",
                                  "LINT9", "pedntic", "", "family:"])
def test_unknown_selectors_say_what_the_oracle_says(engine, text):
    with pytest.raises(SelectorError) as exc:
        _oracle().parse(text)
    r = _resolve(engine, select=[text])
    assert [e["message"] for e in r["errors"]] == [f"'lint.select' names an {exc.value}"]
    assert r["errors"][0]["key"] == "lint.select"


def test_each_layer_names_its_key(engine):
    r = _resolve(engine, select=["x1"], ignore=["x2"], cli_select=["x3"], cli_ignore=["x4"],
                 severity={"x5": "error"}, warnings={"error": ["x6"], "no-error": ["x7"]})
    assert [(e["key"], e["text"]) for e in r["errors"]] == [
        ("severity.x5", "x5"), ("warnings.error", "x6"), ("warnings.no-error", "x7"),
        ("lint.select", "x1"), ("lint.ignore", "x2"), ("--select", "x3"), ("--ignore", "x4")]
    assert r["errors"][0]["message"].startswith("'[severity]' names an unknown")
    assert r["errors"][5]["message"].startswith("'--select' names an unknown")


def test_severity_keys_expand(engine):
    keys = {"suspicious": "error", "LINT102": "info", "PSS": "warning", "family:exec": "off",
            "ACME": "hint"}
    r = _resolve(engine, severity=keys)
    want = _oracle().expand(keys)
    assert {i: s["key"] for i, s in r["severity"].items()} == {i: t for i, (t, _) in want.items()}
    assert {i: s["severity"] for i, s in r["severity"].items()} == {
        i: keys[t] for i, (t, _) in want.items()}
    assert "PSS001" not in r["severity"]        # a group never reaches a core error


def test_werror_groups_expand_in_registry_order(engine):
    r = _resolve(engine, warnings={"error": ["info", "ACME", "LINT101", "pedantic"],
                                   "no-error": ["ACME-NET"]})
    rs = _oracle()
    want, spelling = [], {}
    for text in ("ACME", "LINT101", "pedantic"):
        for mid in rs.expand([text]):
            if mid not in want:
                want.append(mid)
                spelling.setdefault(mid, text)
    assert r["warnings"]["error"] == want
    assert r["warnings"]["spelling"] == spelling
    assert r["warnings"]["error_info"] is True
    assert r["warnings"]["no_error"] == list(rs.expand(["ACME-NET"]))


def test_rule_options_name_a_lint_rule(engine):
    r = _resolve(engine, rule={"corr-rul": {"x": 1}, "LINT101": {"y": 2}, "PSS001": {}})
    assert [(e["key"], e["message"]) for e in r["errors"]] == [
        ("lint.rule.corr-rul",
         "'[lint.rule.corr-rul]' configures an unknown lint rule; did you mean 'corr-rule'?"),
        ("lint.rule.PSS001",
         "'[lint.rule.PSS001]' configures an unknown lint rule; run --list-markers to see "
         "the rule names")]
    assert r["groups"][0]["options"] == {"LINT101": {"y": 2}}


def test_bad_shapes_are_request_errors(engine):
    r = engine.resolve_selection({"lint": {"select": "LINT101", "profile": "most",
                                           "oops": 1}, "zzz": 1})
    assert sorted(e["message"] for e in r["errors"] if e["key"] == "request") == [
        "lint.profile: not a profile name", "lint.select: not a list of strings",
        "lint: unknown key 'oops'", "unknown key 'zzz'"]
    assert engine.resolve_selection("x")["ok"] is False


# -- explicit selection (E3(a)) --------------------------------------------

@pytest.mark.parametrize("select,cli,explicit", [
    (["LINT301"], [], {"LINT301"}),
    (["style-rule"], [], {"LINT301"}),
    (["LINT3"], [], {"LINT301", "LINT302"}),
    (["ACME"], [], {"ACME001", "ACME100", "ACME-NET001", "ACME-NET100", "ACME-DMA001"}),
    (["style"], [], set()),
    (["family:exec"], [], set()),
    (["all"], [], set()),
    (["LINT301"], ["style"], set()),                    # a later layer decides it again
    (["style"], ["LINT301"], {"LINT301"}),
])
def test_explicit(engine, select, cli, explicit):
    r = _resolve(engine, "none", select, cli_select=cli)
    assert set(r["groups"][0]["explicit"]) == explicit
    assert explicit <= set(r["groups"][0]["enabled"])


# -- random differential ---------------------------------------------------

_SELECTORS = sorted({md.id for md in RULES} | {md.name for md in RULES if md.name} | {
    "LINT", "LINT1", "LINT10", "LINT3", "LINT50", "ACME", "ACME-NET", "ACME-NET1", "ACME-DMA",
    "ACME0", "PSS", "PSSP", "PSS053", "ACME900", "family:constraint", "family:activity",
    "family:exec", "family:register", "family:naming", "correctness", "suspicious",
    "portability", "simplify", "style", "pedantic", "restriction", "nursery", "minimal",
    "recommended", "strict", "all", "none", "library"})


@pytest.mark.parametrize("seed", range(60))
def test_random_differential(engine, seed):
    rnd = random.Random(seed)
    pick = lambda: rnd.sample(_SELECTORS, rnd.randint(0, 4))  # noqa: E731
    profile = rnd.choice(["minimal", "recommended", "library", "strict", "all", "none"])
    pin = rnd.choice(["", "2026.1", "2026.2", "2027.1"])
    sel, ign, csel, cign = pick(), pick(), pick(), pick()
    rs = _oracle(pin=pin)
    want = rs.overlay(rs.resolve(profile, sel, ign), csel, cign)
    r = _resolve(engine, profile, sel, ign, csel, cign, pin=pin)
    assert r["errors"] == []
    assert set(r["groups"][0]["enabled"]) == want
    assert r["groups"][0]["held_back"] == rs.held_back(profile)
    keys = {k: "warning" for k in pick()}
    got = _resolve(engine, severity=keys, pin=pin)["severity"]
    assert {i: s["key"] for i, s in got.items()} == {
        i: t for i, (t, _) in rs.expand(keys).items()}


# -- the real registry -----------------------------------------------------

def test_the_real_registry(factory):
    """Every marker the CLI knows, through the engine and through the
    oracle, for each profile and a mix of selectors."""
    from pssparser.checkers.manager import CheckerManager
    from pssparser.lint.selection import tell_engine

    manager = CheckerManager()
    manager.discover(load_extensions=False)
    mdefs = manager.all_marker_defs()
    e = factory.mkLintEngine()
    tell_engine(e, mdefs)
    rs = RuleSet(mdefs)
    rs.aliases = manager.alias_map()
    one = sorted(md.id for md in rs.lint)[0]
    for profile in ("minimal", "recommended", "strict", "all", "none"):
        for sel, ign in (([], []), (["LINT"], [one]), (["family:decl"], ["minimal"])):
            r = _resolve(e, profile, sel, ign)
            assert r["errors"] == []
            assert set(r["groups"][0]["enabled"]) == rs.resolve(profile, sel, ign), (
                profile, sel, ign)
    assert set(_resolve(e)["lint_ids"]) == {md.id for md in rs.lint}
    # A moved code is still accepted, as its current ID.
    for old, new in manager.alias_map().items():
        if new in rs.by_id:
            assert set(_resolve(e, "none", [old])["groups"][0]["enabled"]) == (
                {new} if rs.by_id[new].is_lint else set())


# -- per-path overrides (F2.5) ---------------------------------------------

def _groups(engine, paths, overrides, base="/w", **kw):
    r = _resolve(engine, overrides=overrides, base_dir=base, paths=paths, **kw)
    assert r["errors"] == [], r["errors"]
    return {p["path"]: set(r["groups"][p["group"]]["enabled"]) for p in r["paths"]}, r


def test_an_override_turns_a_rule_off_in_one_directory(engine):
    got, r = _groups(engine, ["/w/ip/a.pss", "/w/tests/t.pss", "/w/tests/sub/u.pss"],
                     [{"files": ["tests/**"], "ignore": ["LINT601"]}])
    assert got == {"/w/ip/a.pss": {"LINT601"} | CORE_MIN, "/w/tests/t.pss": CORE_MIN,
                   "/w/tests/sub/u.pss": CORE_MIN}
    assert [g["overrides"] for g in r["groups"]] == [[], [0]]


def test_overrides_apply_in_order(engine):
    ovs = [{"files": ["ip/**"], "select": ["LINT301"]},
           {"files": ["ip/legacy/**"], "ignore": ["style"]},
           {"files": ["ip/legacy/keep.pss"], "select": ["style-rule"]}]
    got, _ = _groups(engine, ["/w/ip/a.pss", "/w/ip/legacy/b.pss", "/w/ip/legacy/keep.pss"], ovs)
    # The core's minimal rules are portability, so "style" leaves them on.
    assert got["/w/ip/a.pss"] == {"LINT601", "LINT301"} | CORE_MIN
    assert got["/w/ip/legacy/b.pss"] == CORE_MIN
    assert got["/w/ip/legacy/keep.pss"] == {"LINT301"} | CORE_MIN


def test_an_override_profile_replaces_the_base_profile(engine):
    # The project's select and ignore still apply under it.
    got, r = _groups(engine, ["/w/lib/x.pss", "/w/a.pss"],
                     [{"files": ["lib/"], "profile": "library"}],
                     profile="minimal", select=["ACME-NET001"], ignore=["LINT102"])
    rs = _oracle()
    assert got["/w/lib/x.pss"] == rs.resolve("library", ["ACME-NET001"], ["LINT102"])
    assert got["/w/a.pss"] == rs.resolve("minimal", ["ACME-NET001"], ["LINT102"])
    assert r["groups"][1]["profile"] == "library"


def test_the_command_line_beats_an_override(engine):
    got, _ = _groups(engine, ["/w/tests/t.pss"],
                     [{"files": ["tests"], "ignore": ["LINT601", "LINT301"]}],
                     cli_select=["LINT301"])
    assert got["/w/tests/t.pss"] == {"LINT301"} | CORE_MIN


def test_override_options_merge(engine):
    _, r = _groups(engine, ["/w/a.pss", "/w/x/b.pss"],
                   [{"files": ["x/*.pss"], "rule": {"corr-rule": {"b": 3, "c": [1]}}}],
                   rule={"LINT101": {"a": 1, "b": 2}})
    assert r["groups"][0]["options"] == {"LINT101": {"a": 1, "b": 2}}
    assert r["groups"][1]["options"] == {"LINT101": {"a": 1, "b": 3, "c": [1]}}


def test_override_errors_name_the_override(engine):
    # Nothing near enough to suggest (`LINT999` would be "did you mean LINT409").
    r = _resolve(engine, overrides=[{"files": ["x"], "select": ["XYZ999"]},
                                    {"select": ["LINT101"]},
                                    {"files": ["y"], "rule": {"nope": {}}, "severity": {}}])
    assert [(e["key"], e["message"]) for e in r["errors"]] == [
        ("lint.overrides[0].select", "'lint.overrides[0].select' names an unknown marker or "
         "selector 'XYZ999'; run --list-markers to see the declared IDs and names"),
        ("request", "lint.overrides[1]: 'files' must list at least one pattern"),
        ("request", "lint.overrides[2]: unknown key 'severity'"),
        ("lint.overrides[2].rule.nope", "'lint.overrides[2].rule.nope' configures an unknown "
         "lint rule; run --list-markers to see the rule names")]


@pytest.mark.parametrize("pattern,path,hit", [
    ("tests/**", "tests/a.pss", True),
    ("tests/**", "tests/x/y/a.pss", True),
    ("tests/**", "src/tests/a.pss", False),         # anchored at the base
    ("tests", "src/tests/a.pss", True),             # no '/': any depth
    ("tests/", "tests/a.pss", True),
    ("/tests/*.pss", "tests/a.pss", True),
    ("*.pss", "deep/down/a.pss", True),
    ("*_test.pss", "ip/dma_test.pss", True),
    ("*_test.pss", "ip/dma.pss", False),
    ("ip/*/a.pss", "ip/dma/a.pss", True),
    ("ip/*/a.pss", "ip/dma/sub/a.pss", False),      # '*' does not cross '/'
    ("ip/**/a.pss", "ip/a.pss", True),              # '**/' may be no directory
    ("ip/**/a.pss", "ip/x/y/a.pss", True),
    ("ip/d?a/*", "ip/dma/a.pss", True),
    ("ip/[a-d]ma/*", "ip/dma/a.pss", True),
    ("ip/[!d]ma/*", "ip/dma/a.pss", False),
    ("IP/**", "ip/a.pss", False),                   # case-sensitive
    ("vendor", "vendor/x/y.pss", True),
    ("ip/**", "../ip/a.pss", False),                # outside the base
    ("*.pss", "../ip/a.pss", True),
])
def test_globs(engine, pattern, path, hit):
    r = _resolve(engine, overrides=[{"files": [pattern], "ignore": ["LINT601"]}],
                 base_dir="/w/proj", paths=["/w/proj/" + path])
    assert r["errors"] == []
    assert (r["paths"][0]["group"] == 1) is hit, r["paths"]


def test_paths_are_relative_to_the_base(engine):
    r = _resolve(engine, base_dir="/w/proj", paths=["/w/proj/ip/../ip/./a.pss", "/w/other/b.pss",
                                                     "C:\\w\\c.pss"])
    assert [p["rel"] for p in r["paths"]] == ["ip/a.pss", "../other/b.pss", "C:/w/c.pss"]


# -- a run with a selection ------------------------------------------------

_RULES = """\
pss-rules:
  rules:
    - id: ACME001
      name: comp
      tier: style
      summary: s
      message: "component ${node.name.id}"
      match: { kind: Component }
    - id: ACME002
      name: act
      tier: suspicious
      summary: s
      message: "action ${node.name.id} ${options.tag}"
      options:
        tag: { type: string, default: "d" }
      match: { kind: Action }
    - id: ACME003
      name: field-type
      tier: suspicious
      summary: s
      message: "field type ${decl_path(finding)}"
      match: { kind: Field }
      report: "[type_decl(node.type).value()]"
"""


@pytest.fixture(scope="module")
def two_files():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("/w/ip/a.pss", "component a_c { action A { } }\n"),
              ("/w/tests/t.pss", "component t_c { action T { } a_c sub; }\n"),
              ("/w/top.pss", "component top_c { t_c t; }\n")])
    root = p.link()
    return root, p.user_units(), p.file_map


def _run(factory, model, selection, **req):
    root, units, names = model
    e = factory.mkLintEngine()
    assert e.load_rules("r.yaml", _RULES)
    req = dict(req, selection=selection, files={str(k): v for k, v in names.items()})
    return e.run(units, req, model=root)


def test_a_run_reports_per_file(factory, two_files):
    # ACME003 matches a field in one file and reports the field's type,
    # declared in another: the finding is dropped where the rule is off.
    sel = {"lint": {"profile": "none", "select": ["ACME"],
                    "overrides": [{"files": ["tests/**"], "ignore": ["ACME001"],
                                   "rule": {"act": {"tag": "T"}}},
                                  {"files": ["ip"], "ignore": ["ACME003"]}]},
           "base_dir": "/w"}
    r = _run(factory, two_files, sel)
    assert r["problems"] == []
    got = sorted((m["code"], m["message"]) for m in r["markers"])
    assert got == [("ACME001", "component a_c"), ("ACME001", "component top_c"),
                   ("ACME002", "action A d"), ("ACME002", "action T T"),
                   ("ACME003", "field type t_c")]


def test_a_rule_off_everywhere_is_not_run(factory, two_files):
    sel = {"lint": {"profile": "none", "select": ["ACME002"]}}
    r = _run(factory, two_files, sel)
    assert [s["id"] for s in r["stats"]] == ["ACME002"]


def test_the_request_base_dir_is_the_default(factory, two_files):
    sel = {"lint": {"profile": "none", "select": ["ACME001"],
                    "overrides": [{"files": ["ip"], "ignore": ["ACME001"]}]}}
    r = _run(factory, two_files, sel, base_dir="/w")
    assert sorted(m["message"] for m in r["markers"]) == ["component t_c", "component top_c"]


def test_selection_errors_are_problems(factory, two_files):
    r = _run(factory, two_files, {"lint": {"select": ["ACME01"]}}, enabled=["ACME001"])
    assert r["problems"] == [
        "selection: given with enabled or options; those are ignored",
        "selection: 'lint.select' names an unknown marker or selector 'ACME01'; "
        "did you mean 'ACME001'?"]
