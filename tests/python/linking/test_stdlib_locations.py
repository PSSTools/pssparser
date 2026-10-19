"""Locations in the compiled-in core library.

The core library is one source unit, fileid 0. Its five files used to be
built one at a time, each starting again at line 1, so a fileid-0 location
could not say which file it was in: diagnostics showed ``<unknown>``. Every
line was also one too high, because the generated source began with a newline.

Now the files are built back to back, each in its own band of fileid-0 lines,
and ``Parser.resolve_location`` maps a location back to
``<stdlib>/<file>.pss`` and the line within that file.
"""
import re

import pytest

import pssparser
from pssparser import refs
from pssparser.parser import (
    STDLIB_PREFIX, core_library_location, core_library_sources)

from ..isolation import run_isolated


def _first_decl(text):
    """(name, line, col) of the first struct/enum/component declared in a
    core-library file's text, or None. The column is the keyword's, where a
    duplicate's "first declared here" points."""
    for n, line in enumerate(text.split("\n"), 1):
        m = re.match(r"(\s*)(struct|enum|component)\s+(\w+)", line)
        if m:
            return m.group(3), n, len(m.group(1)) + 1
    return None


def _pkg_of(text, line):
    """The package a file's `line` is inside: the last one opened before it."""
    pkg = None
    for n, l in enumerate(text.split("\n"), 1):
        if n > line:
            break
        m = re.match(r"\s*package\s+(\w+)", l)
        if m:
            pkg = m.group(1)
    return pkg


def _decl_cases():
    out = []
    for name, _, _, text in core_library_sources():
        d = _first_decl(text)
        if d is not None:
            out.append(pytest.param(name, _pkg_of(text, d[1]), *d, id=name))
    return out


def test_the_bands_are_contiguous_and_cover_each_file():
    srcs = core_library_sources()
    assert [s[0] for s in srcs] == sorted(s[0] for s in srcs)
    first = 1
    for name, start, num, text in srcs:
        assert start == first, name
        assert num == text.count("\n"), name
        first += num


def test_the_embedded_text_is_the_library_source():
    import os
    on_disk = {os.path.basename(f): open(f).read()
               for f in pssparser.get_stdlib_files()}
    if not on_disk:
        pytest.skip("no core-library sources on disk")
    assert {s[0]: s[3] for s in core_library_sources()} == on_disk


def test_a_line_maps_to_its_file_and_local_line():
    for name, start, num, _ in core_library_sources():
        assert core_library_location(start) == (STDLIB_PREFIX + name, 1)
        assert core_library_location(start + num - 1) == (STDLIB_PREFIX + name, num)
    assert core_library_location(0) is None


@pytest.mark.parametrize("name,pkg,decl,line,col", _decl_cases())
def test_a_duplicate_of_a_library_declaration_points_into_its_file(
        name, pkg, decl, line, col):
    p = pssparser.Parser()
    p.parses([("t.pss", "package %s { struct %s {} }\n" % (pkg, decl))])
    with pytest.raises(pssparser.ParseException):
        p.link()
    dups = [m for m in p.markers if m.get("code") == "PSS003"]
    assert len(dups) == 1, p.markers
    rel = dups[0]["related"]
    assert [(r["file"], r["line"], r["col"]) for r in rel] == [
        (STDLIB_PREFIX + name, line, col)], rel


def test_the_cli_names_the_library_file():
    res = run_isolated([("t.pss", "package addr_reg_pkg { struct addr_trait_s {} }\n")])
    assert res.rc == 1, res.describe()
    assert "--> <stdlib>/addr_reg_pkg.pss:12:5" in res.output, res.describe()
    assert "<unknown>" not in res.output, res.describe()


def test_the_cli_json_names_the_library_file():
    import json
    res = run_isolated([("t.pss", "package addr_reg_pkg { struct addr_trait_s {} }\n")],
                       args=["--json"])
    diags = json.loads(res.stdout)["diagnostics"]
    assert [(r["file"], r["line"], r["col"]) for r in diags[0]["related"]] == [
        ("<stdlib>/addr_reg_pkg.pss", 12, 5)], res.describe()


def test_a_library_reference_maps_to_its_declaration_in_std_pkg():
    p = pssparser.Parser()
    p.parses([("t.pss", """
import std_pkg::*;
component pss_top { exec init_down { message(LOW, "x"); } }
""")])
    p.link()
    occ = [o for o in refs.occurrences(p) if o.text == "message"]
    assert len(occ) == 1 and occ[0].resolution == refs.Resolution.LIBRARY, occ
    path, line = refs.library_location(occ[0].decl_location)
    assert path == "<stdlib>/std_pkg.pss"
    text = dict((s[0], s[3]) for s in core_library_sources())["std_pkg.pss"]
    assert re.search(r"\bmessage\s*\(", text.split("\n")[line - 1]), line
    assert p.resolve_location(0, occ[0].decl_location.line) == (path, line)


def test_a_user_location_is_unchanged():
    p = pssparser.Parser()
    p.parses([("t.pss", "struct s {}\n")])
    p.link()
    assert p.resolve_location(1, 7) == ("t.pss", 7)
