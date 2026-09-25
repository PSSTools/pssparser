"""The completeness gate: no reference may survive linking unbound in silence.

`TaskCheckRefsResolved` runs after resolution and checks every reference in the
user units -- type identifiers, names and paths, the `role: ref` fields of the
schema (symbol-resolution plan 3.5, INV-3). A name left unbound with nothing
said about it is reported: PSS002 when nothing in the model declares it, PSS042
(a pssparser defect) when something does. It exists because the front end's
silent-drop defects all had one shape -- a resolution path that fails, writes
nothing to the marker listener, and leaves a null target behind:

  - `TaskResolveRefs::visitDataTypeUserDefined`'s failure branch was a
    commented-out marker, so an unresolvable field type produced no diagnostic,
    no count and no exit status;
  - the same null reached `TaskIsPyRef`, which printed `Error:` to stderr via
    DEBUG_ERROR -- uncounted, so a run could print 104 `Error:` lines and then
    report `0 errors in 0 files` and exit 0.

Half these tests assert the check *fires*; the other half assert it stays
quiet. Both halves are needed and they fail to different changes: a rejection
suite cannot see a check that fires too widely, and a clean control cannot see
one that has stopped firing.

Run the parser out of process where the assertion is about what reached a
*stream* -- an in-process test cannot see what the C++ layer writes to fd 2.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect  # noqa: E402


def _run(tmp_path, sources):
    """Run the pssparser CLI over `sources` ({name: text}); return CompletedProcess."""
    paths = []
    for name, text in sources.items():
        p = tmp_path / f"{name}.pss"
        p.write_text(text)
        paths.append(str(p))
    return subprocess.run(
        [sys.executable, "-m", "pssparser", *paths],
        capture_output=True, text=True)


def _out(res):
    """Both streams. Diagnostics go to stderr and the summary with them; which
    stream carries what is not the subject of these tests."""
    return res.stdout + res.stderr


# --------------------------------------------------------------------------
# it fires

def test_a_qualified_type_that_does_not_exist_is_reported(tmp_path):
    """The reference this check was first written for.

    `p::nosuch_s` used to link clean, exit 0, and hand every consumer a field
    with no type. The resolver reports it itself now; the gate stays quiet.
    """
    res = _run(tmp_path, {"m": """
        package p { struct s { rand bit[8] v; } }
        component c { p::nosuch_s f; }
        component pss_top { c c0; }
    """})

    assert res.returncode == 1
    assert "unknown type 'nosuch_s' in 'p'" in _out(res)
    assert "1 error in 1 file" in _out(res)


def _errors(src):
    _root, markers = parse_collect(src)
    return [(m["line"], m.get("code"), m["message"])
            for m in markers if m["severity"] == "error"]


def test_a_name_the_resolver_skips_is_reported():
    """`resolveStaticRootedLeaf` has no built-in method handling, so the
    qualified spelling of an unknown string method was accepted silently.
    Nothing declares `nosuchmeth`, so it is PSS002."""
    assert _errors("""
package p { function string f(); }
function void g() { int v; v = p::f().nosuchmeth(); }
""") == [(3, "PSS002", "'f' has no member named 'nosuchmeth'")]


def test_the_body_of_an_extension_of_an_unknown_type_is_not_reported():
    """Its names were never looked up; the target is the one report."""
    assert [c for _, c, _ in _errors("""
component pss_top {
    extend component nosuch_c {
        action a_a { activity { do nosuch_a; } }
    }
}
""")] == ["PSS002"]


@pytest.mark.parametrize("src", [
    # A template local assigned in `{% %}`: bound, where it used to be found
    # and dropped.
    'component pss_top { action A { exec body C = """{% int i = 0; %}'
    '{% i = 1; %}"""; } }',
    # Annotations on activity and procedural statements (Example 323): they
    # used to be skipped by the resolver entirely.
    "import std_pkg::*;\n"
    "component pss_top { action A { }\n"
    "  action B { activity { @code_doc {.text=\"x\"} do A; } }\n"
    "  function void f() { repeat (i : 2) { @code_doc {.text=\"y\"} } } }",
    # A qualified array dimension: every element of the path is bound, not
    # only the last.
    "package sizes { const int N = 4; }\n"
    "component pss_top { static const int K = 2;\n"
    "  bit[8] a[sizes::N]; bit[8] b[pss_top::K]; }",
])
def test_legal_references_the_gate_found_unbound(src):
    """Each of these was left unbound by the resolver on legal input; the
    gate reported them as PSS042 until the resolver was fixed."""
    assert _errors(src) == []


def test_an_unknown_annotation_parameter_in_an_activity_is_reported():
    """Reachable only now that annotations in activities are resolved: an
    ActivityDecl holds its statement's annotation, and a MonitorActivityDecl
    its statements as symbol-scope children. Once each: the gate does not
    repeat the resolver's report."""
    assert _errors("""
annotation ann_t { int v; }
component pss_top { action A { }
  action B { activity { @ann_t {.nosuch = 1} do A; } }
  monitor M { activity { @ann_t {.nosuch2 = 1} A a; } } }
""") == [
        (4, "PSS002", "unknown identifier 'nosuch' in annotation type 'ann_t'"),
        (5, "PSS002", "unknown identifier 'nosuch2' in annotation type 'ann_t'"),
    ]


def test_an_unresolved_reference_makes_the_run_exit_nonzero(tmp_path):
    """The half of the contract that CI depends on. D1's complaint was not that
    the message was poor -- it was that the run said `0 errors` and exited 0."""
    res = _run(tmp_path, {"m": """
        package p { struct s { rand bit[8] v; } }
        component c { p::nosuch_s f; }
        component pss_top { c c0; }
    """})

    assert res.returncode != 0
    assert "0 errors in 0 files" not in _out(res)


# --------------------------------------------------------------------------
# it stays quiet

def test_a_clean_model_prints_no_error_line_anywhere(tmp_path):
    """No stream may carry a line beginning `Error:` on a run reporting 0 errors.

    This is the assertion whose absence let 104 uncounted `Error:` lines coexist
    with `0 errors in 0 files` and exit 0 for months. It is deliberately about
    the raw streams rather than the marker list, because the messages in
    question never reached the marker list -- that was the defect.
    """
    res = _run(tmp_path, {"m": """
        component leaf_c { int n; }
        component pss_top { leaf_c u; }
    """})

    assert res.returncode == 0
    for stream in (res.stdout, res.stderr):
        offenders = [ln for ln in stream.splitlines()
                     if ln.startswith("Error:")]
        assert offenders == [], offenders


def test_the_shape_that_printed_104_error_lines_prints_none(tmp_path):
    """The same assertion as above, on input that actually reaches the branch.

    A two-component model is too small: the uncounted `Error:` lines came from
    TaskIsPyRef walking into a *not-yet-resolved unit*, which needs a cross-file
    forward reference into a package declaring a register group that holds a
    register. That is D3's shape, and the file order below is the failing one
    (the reference first). It produced one `Error:` line per unresolved field --
    104 on the 22-file model -- while reporting `0 errors in 0 files`, exit 0.

    Written as an ordered dict so the use-before-declaration order is the one
    that reaches the parser; reversing it makes the test vacuous.
    """
    res = _run(tmp_path, {
        "a_use": """
            import addr_reg_pkg::*;
            component d_c {
                function void f(addr_handle_t b) {
                    addr_handle_t h;
                    h = make_handle_from_handle(b, r_pkg::OFF);
                }
            }
        """,
        "b_decl": """
            package r_pkg {
                import std_pkg::*;
                import addr_reg_pkg::*;
                const bit[64] OFF = 0x20;
                struct r_s : packed_s<> { rand bit[32] a; }
                pure component r_c : reg_c<r_s, READWRITE, 32> {}
                pure component grp_c : reg_group_c {
                    r_c r0;
                    function bit[64] get_offset_of_instance(string name) { return 0; }
                    function bit[64] get_offset_of_instance_array(string n, int i) { return -1; }
                }
            }
        """,
    })

    assert res.returncode == 0, _out(res)
    offenders = [ln for ln in (res.stdout + res.stderr).splitlines()
                 if ln.startswith("Error:")]
    assert offenders == [], offenders


def test_a_generic_that_is_never_instantiated_is_not_reported(tmp_path):
    """`T` names a template parameter, not a missing type, and a generic
    nothing instantiates never binds it. Reporting it would reject valid PSS."""
    res = _run(tmp_path, {"m": """
        component MyComponent {
            struct BaseStruct { }
            struct MyStruct<int SIZE, struct T : BaseStruct> {
                bit[SIZE] data;
                T item;
            }
        }
    """})

    assert res.returncode == 0, _out(res)


def test_a_template_parameter_default_is_not_reported(tmp_path):
    """`<type T = BaseStruct>` binds its default at specialization time. An
    uninstantiated generic has none, which is legal."""
    res = _run(tmp_path, {"m": """
        component MyComponent {
            struct BaseStruct { }
            struct MyContainer<type T = BaseStruct> { T data; }
        }
    """})

    assert res.returncode == 0, _out(res)


def test_an_instance_qualified_action_reference_is_not_reported(tmp_path):
    """`tx::send_pkt` in an activity, where `tx` is a component *instance*.

    Legal PSS, and this node never receives a target because the path is
    resolved by instance rather than by scope. The first version of this check
    reported it and broke five working models -- the failure mode that gets a
    check switched off. Kept as a test rather than a comment because the
    exemption is generous (any qualified name whose last element names a
    declared type) and something has to hold it to that shape.
    """
    res = _run(tmp_path, {"m": """
        buffer packet_s { rand bit[8] v; }
        component tx_c { action send_pkt { output packet_s pkt; } }
        component pss_top {
            tx_c tx;
            pool packet_s pkt_pool;
            bind pkt_pool *;
            action do_transfer { activity { tx::send_pkt s; } }
        }
    """})

    assert res.returncode == 0, _out(res)


@pytest.mark.parametrize("order", ["decl-first", "use-first"], ids=str)
def test_a_cross_file_forward_reference_is_not_reported(tmp_path, order):
    """PSS 3.1 18.2: order of presentation is not part of the language. The
    check measures the state *after* resolution for exactly this reason -- a
    reference into a not-yet-walked unit is unresolved in the middle of the
    pass, and reporting that would make the diagnostics order-dependent."""
    decl = "package a_pkg { struct cfg_s { rand bit[8] mode; } }"
    use = "import a_pkg::*;\ncomponent user_c { cfg_s cfg; }\ncomponent pss_top { user_c u; }"

    sources = {"a_decl": decl, "b_use": use}
    if order == "use-first":
        sources = {"a_use": use, "b_decl": decl}

    res = _run(tmp_path, sources)

    assert res.returncode == 0, _out(res)


# --------------------------------------------------------------------------
# one mistake, one message

def test_an_unknown_bare_type_is_reported_once(tmp_path):
    """`unknown_t` is already diagnosed, better, as `unknown type 'unknown_t'`.

    The gate must not add a second error for the same position: two
    diagnostics for one mistake is the cascade pssparser-issues.md 5.3
    objects to. What is asserted is the *count*, since the first message is
    the one the user should see.
    """
    res = _run(tmp_path, {"m": """
        component c { unknown_t regs; }
        component pss_top { c c0; }
    """})

    assert res.returncode == 1
    assert "1 error in 1 file" in _out(res)
    assert "unknown type 'unknown_t'" in _out(res)


def test_an_unknown_annotation_parameter_on_a_function_is_reported():
    """A function's own annotations were never resolved: the enclosing
    scope's collector stops at the function's symbol scope."""
    assert _errors("""
import std_pkg::*;
@code_doc {.nosuch = "x"}
function void h();
""") == [(3, "PSS002",
          "unknown identifier 'nosuch' in annotation type 'code_doc'")]
