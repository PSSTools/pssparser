"""Tests for ``pssparser.cli.stats`` -- declaration counting (S1) and the
diagnostic histogram (S4).

Rendering and the CLI flags are covered by ``test_stats_output.py``.
"""
import pytest

from pssparser.cli.commands import _collect_stats, _user_global_scopes
from pssparser.cli.diagnostics import Diagnostic, DiagnosticCollection
from pssparser.cli.stats import (
    DECL_KEYS,
    UNCODED,
    collect_decls,
    diagnostics_by_code,
)
from pssparser.parser import Parser


# 1 package, 1 component, 2 actions, 1 struct, 1 buffer, 1 stream,
# 1 resource, 1 state, 1 import, 1 function, 2 constraint blocks,
# 1 exec block, and 7 fields (addr, w, id, v, a, b, x).
CENSUS_SRC = """package p {
    buffer   B { rand bit[32] addr; constraint c { addr < 100; } }
    stream   St { int w; }
    resource R { int id; }
    state    Stt { int v; }
    struct   S { int a; }
    function void f(int a);
}
component C {
    import p::*;
    B b;
    action A {
        rand int x;
        constraint c1 { x > 0; }
        exec body { x = 1; }
    }
    action A2 { }
}
"""

CENSUS = {
    "packages": 1,
    "components": 1,
    "actions": 2,
    "structs": 1,
    "buffers": 1,
    "streams": 1,
    "states": 1,
    "resources": 1,
    "fields": 7,
    "constraints": 2,
    "exec_blocks": 1,
    "functions": 1,
    "imports": 1,
}


def _counts(tmp_path, sources, *, syntax_only=False):
    """Parse *sources* (a name -> text mapping) and return decl counts."""
    files = []
    for name, text in sources.items():
        p = tmp_path / name
        p.write_text(text)
        files.append(str(p))

    parser = Parser()
    parser.parse(files)
    if not syntax_only:
        parser.link()
    scopes, _ = _user_global_scopes(parser, files)
    return collect_decls(scopes)


class TestDeclarationCounts:
    def test_known_census(self, tmp_path):
        counts = _counts(tmp_path, {"m.pss": CENSUS_SRC})
        assert counts == CENSUS

    def test_no_standard_library_leakage(self, tmp_path):
        """The stdlib unit must contribute nothing.

        ``Parser.parse`` prepends a synthesised standard-library unit; a walk
        that forgets to filter it reports the same ~200 phantom types for
        every model, so a file declaring one struct must count exactly one.
        """
        counts = _counts(tmp_path, {"m.pss": "package p { struct S { int a; } }\n"})
        assert counts["structs"] == 1
        assert counts["packages"] == 1
        assert counts["components"] == 0
        assert counts["actions"] == 0
        assert counts["functions"] == 0

    def test_synthesized_members_are_not_counted(self, tmp_path):
        """The linker grafts implicit members onto the user's own types.

        Every action gets a ``set_executor`` prototype with a negative
        ``fileid``.  It lives inside the user's global scope, so unit-level
        filtering does not remove it -- only the synthesised-location check
        does.
        """
        counts = _counts(tmp_path, {"m.pss": "component C { action A { } }\n"})
        assert counts["functions"] == 0
        assert counts["actions"] == 1

    def test_exec_block_is_not_a_function(self, tmp_path):
        counts = _counts(
            tmp_path,
            {"m.pss": "component C { action A { exec body { } } }\n"},
        )
        assert counts["exec_blocks"] == 1
        assert counts["functions"] == 0

    @pytest.mark.parametrize("body", [
        "function void f(int a);",           # prototype only
        "function void f(int a) { }",        # definition
        "import target function void f(int a);",  # imported
    ])
    def test_every_function_form_counts_once(self, tmp_path, body):
        """A definition and an import each *contain* a prototype node.

        Counting FunctionDefinition/FunctionImport as well as the prototype
        would report two functions for one declaration.
        """
        counts = _counts(tmp_path, {"m.pss": "package p { %s }\n" % body})
        assert counts["functions"] == 1

    def test_struct_kinds_are_bucketed_separately(self, tmp_path):
        counts = _counts(tmp_path, {"m.pss": """package p {
            struct S1 { int a; } struct S2 { int a; }
            buffer B { int a; } stream St { int a; }
            state Stt { int a; } resource R { int a; }
        }
        """})
        assert counts["structs"] == 2
        assert counts["buffers"] == 1
        assert counts["streams"] == 1
        assert counts["states"] == 1
        assert counts["resources"] == 1

    def test_multi_file_aggregation(self, tmp_path):
        counts = _counts(tmp_path, {
            "a.pss": "package p { struct S { int a; } }\n",
            "b.pss": "package q { import p::*; struct T { int b; } }\n",
        })
        assert counts["packages"] == 2
        assert counts["structs"] == 2
        assert counts["fields"] == 2
        # One import statement, counted once.
        assert counts["imports"] == 1

    def test_empty_but_valid_file_is_all_zeros(self, tmp_path):
        counts = _counts(tmp_path, {"empty.pss": "\n"})
        assert set(counts) == set(DECL_KEYS)
        assert all(v == 0 for v in counts.values())

    def test_syntax_only_matches_linked(self, tmp_path):
        """``--syntax-only`` never links, so it takes the fallback path.

        The two paths must agree, or the same model reports different sizes
        depending on an unrelated flag.
        """
        linked = _counts(tmp_path, {"m.pss": CENSUS_SRC})
        unlinked = _counts(tmp_path, {"m.pss": CENSUS_SRC}, syntax_only=True)
        assert unlinked == linked


# -- S4: diagnostics_by_code -----------------------------------------------

def _diag(code, severity="error"):
    return Diagnostic(file="f.pss", line=1, col=1, severity=severity,
                      message="m", code=code)


class TestDiagnosticsByCode:
    def test_known_mix(self):
        hist = diagnostics_by_code([
            _diag("PSS022"), _diag("PSS022"), _diag("PSS029"),
            _diag("PSS104", severity="warning"),
        ])
        assert hist == {"PSS022": 2, "PSS029": 1, "PSS104": 1}

    def test_uncoded_markers_are_bucketed_not_dropped(self):
        """A message the pattern table does not recognise still gets counted.

        A non-zero ``<uncoded>`` count is the signal that the C++ messages
        have drifted from ``_assign_core_code``'s regex table -- dropping
        those markers would hide exactly the thing worth watching.
        """
        hist = diagnostics_by_code([_diag(None), _diag(None), _diag("PSS001")])
        assert hist == {UNCODED: 2, "PSS001": 1}

    def test_empty_is_empty(self):
        assert diagnostics_by_code([]) == {}

    def test_keys_are_sorted(self):
        hist = diagnostics_by_code([_diag("PSS104"), _diag("PSS001")])
        assert list(hist) == ["PSS001", "PSS104"]


class TestCollectStats:
    def test_timings_absent_when_not_requested(self, tmp_path):
        p = tmp_path / "m.pss"
        p.write_text(CENSUS_SRC)
        parser = Parser()
        parser.parse([str(p)])
        parser.link()

        coll = DiagnosticCollection()
        run = _collect_stats(parser, [str(p)], coll, timings=None)
        assert run.timings_ns == {}
        assert run.files == 1
        assert run.decls == CENSUS

    def test_timings_include_parser_and_caller_phases(self, tmp_path):
        p = tmp_path / "m.pss"
        p.write_text(CENSUS_SRC)
        parser = Parser()
        parser.parse([str(p)])
        parser.link()

        coll = DiagnosticCollection()
        run = _collect_stats(parser, [str(p)], coll, timings={"link": 5})
        # The standard-library load is reported on its own row rather than
        # folded into the user's parse time.
        assert "stdlib" in run.timings_ns
        assert "parse (incl. read)" in run.timings_ns
        assert run.timings_ns["link"] == 5
        assert all(v >= 0 for v in run.timings_ns.values())
