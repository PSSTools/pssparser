"""Locations (lint-core-plan.md C6.9; rule-authoring-requests-2026-10-10.md B9).

`file_of(node)` -> `FileInfo{path, dir, name, stem, ext}`: the host's name for
the node's file, normalized and, under a base directory (the CLI: the
configuration's), relative to it. `decls_in(FileInfo)`: the file's top-level
declarations, in source order.

The engine has no file names of its own: the host sends them in the lint
request (`files`, `base_dir`). Every host does -- the CLI, the examples
runner, the TypeScript `Parser.runLint()` -- and the test hook reads the same
two keys from its document.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from isolation import _parent_package_root  # noqa: E402


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


_DMA = ("import std_pkg::*;\n"
        "package dma_pkg { struct desc_s { } }\n"
        "component dma_c { }\n"
        "component extra_c { }\n"
        "typedef bit[8] byte_t;\n")
_TOP = "component pss_top { dma_c d; }\n"


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("/w/proj/ip/dma/dma_c.pss", _DMA), ("/w/proj/tests/top.pss", _TOP)])
    root = p.link()
    return root, p.user_units(), p.file_map


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    if v["type"] == "struct":
        return {k: _py(x) for k, x in v["value"].items() if k != "struct"}
    return v.get("value")


def _ev(hooks, model, expr, base="/w/proj", files=None, unit=0):
    root, units, names = model
    doc = {"expr": expr,
           "files": {str(k): v for k, v in names.items()} if files is None else files}
    if base is not None:
        doc["base_dir"] = base
    r = hooks.cel_check_node(doc, units[unit], model=root)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def test_file_of(hooks, model):
    assert _ev(hooks, model, "file_of(node)") == {
        "path": "ip/dma/dma_c.pss", "dir": "ip/dma", "name": "dma_c.pss",
        "stem": "dma_c", "ext": ".pss"}


def test_without_a_base_directory_the_path_is_as_given(hooks, model):
    assert _ev(hooks, model, "file_of(node).path", base=None) == "/w/proj/ip/dma/dma_c.pss"


def test_a_file_outside_the_base_directory(hooks, model):
    assert _ev(hooks, model, "file_of(node).path", base="/w/proj/tests") == \
        "../ip/dma/dma_c.pss"


def test_a_file_in_the_base_directory_itself(hooks, model):
    assert _ev(hooks, model, "[file_of(node).path, file_of(node).dir]",
               base="/w/proj/ip/dma") == ["dma_c.pss", ""]


@pytest.mark.parametrize("given,base,want", [
    ("C:\\proj\\ip\\a.pss", "C:\\proj", "ip/a.pss"),     # Windows separators
    ("/w/./ip//x/../a.pss", "/w", "ip/a.pss"),           # '.', '//', '..'
    ("ip/a.pss", "/w", "ip/a.pss"),                      # relative vs absolute: as given
    ("./ip/../ip/a.pss", "", "ip/a.pss"),
    ("../up/a.pss", "", "../up/a.pss"),                  # '..' above a relative start
])
def test_normalization(hooks, model, given, base, want):
    assert _ev(hooks, model, "file_of(node).path", base=base,
               files={"1": given}) == want


@pytest.mark.parametrize("name,stem,ext", [
    ("a.pss", "a", ".pss"),
    ("a.tar.gz", "a.tar", ".gz"),
    ("Makefile", "Makefile", ""),
    (".hidden", ".hidden", ""),
])
def test_name_stem_ext_as_pathlib(hooks, model, name, stem, ext):
    assert _ev(hooks, model, "[file_of(node).name, file_of(node).stem, file_of(node).ext]",
               base=None, files={"1": "/d/" + name}) == [name, stem, ext]


def test_null_cases(hooks, model):
    assert _ev(hooks, model, "file_of(null) == null") is True
    # A file the host did not name.
    assert _ev(hooks, model, "file_of(node) == null", files={}) is True
    # A specialization is in no file (C6.8).
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("/w/t.pss", "struct S<int W = 4> { }\ncomponent pss_top { S<8> s; }\n")])
    root = p.link()
    m = (root, p.user_units(), p.file_map)
    assert _ev(hooks, m, "descendants(node).filter(d, type(d) == Field)"
               ".map(f, file_of(type_decl(f.type).value()) == null)", base="/w") == [True]


def test_records_compare_member_by_member(hooks, model):
    assert _ev(hooks, model, "descendants(node).filter(d, d.isa(Component))"
               ".all(c, file_of(c) == file_of(node))") is True
    assert _ev(hooks, model, "file_of(node) == file_of(node.children[0])") is True


def test_decls_in(hooks, model):
    # Source order; the package is one declaration; the import is none.
    assert _ev(hooks, model, "decls_in(file_of(node)).map(d, decl_path(d))") == [
        "dma_pkg", "dma_c", "extra_c", "byte_t"]


def test_decls_in_another_file(hooks, model):
    # From the second file's node, the first file's declarations by its path.
    assert _ev(hooks, model, "decls_in(file_of(node)).map(d, decl_path(d))",
               unit=1) == ["pss_top"]


def test_decls_in_an_unnamed_file(hooks, model):
    # file_of gives null for a file the host did not name; decls_in(null) is [].
    assert _ev(hooks, model, "decls_in(file_of(node))", files={}) == []


def test_the_engine_takes_files_from_the_request(factory, model):
    root, units, names = model
    e = factory.mkLintEngine()
    e.load_rules("r.yaml", (
        "pss-rules:\n"
        "  rules:\n"
        "    - id: ACME001\n"
        "      name: component-file-name\n"
        "      tier: style\n"
        "      summary: s\n"
        "      message: \"'${node.name.id}' is in ${file_of(node).path}\"\n"
        "      match: { kind: Component }\n"
        "      where: file_of(node).stem != node.name.id\n"))
    req = {"enabled": ["ACME001"], "base_dir": "/w/proj",
           "files": {str(k): v for k, v in names.items()}}
    r = e.run(units, req, model=root)
    assert r["problems"] == []
    assert sorted(m["message"] for m in r["markers"]) == [
        "'extra_c' is in ip/dma/dma_c.pss", "'pss_top' is in tests/top.pss"]


def test_a_bad_files_entry_is_a_request_problem(factory, model):
    root, units, _ = model
    e = factory.mkLintEngine()
    r = e.run(units, {"enabled": [], "files": {"x": "a.pss"}, "base_dir": 3}, model=root)
    assert r["problems"] == ["files: 'x' is not a fileid with a path",
                             "base_dir: not a string"]


_RULE = """\
pss-rules:
  rules:
    - id: ACME001
      name: where-is-it
      tier: suspicious
      summary: s
      message: "${file_of(node).path}"
      match: { kind: Component }
"""


def _cli(cwd, *args):
    env = dict(os.environ)
    env["PYTHONPATH"] = _parent_package_root()
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    env.pop("PSSPARSER_NO_LINT", None)      # set for every test by conftest
    r = subprocess.run([sys.executable, "-m", "pssparser", "--format", "json", *args],
                       capture_output=True, text=True, env=env, cwd=str(cwd), timeout=300)
    # The message, without its "[ACME001] " prefix.
    return [d["message"].split("] ", 1)[1] for d in json.loads(r.stdout)["diagnostics"]
            if d.get("code") == "ACME001"]


def test_cli_paths_are_relative_to_the_config(tmp_path):
    # The configuration is in the project root; pssparser runs from a
    # subdirectory and names the file relative to it.
    (tmp_path / "ip").mkdir()
    (tmp_path / "ip" / "a.pss").write_text("component a_c { }\n")
    (tmp_path / "rules.yaml").write_text(_RULE)
    (tmp_path / ".pssparser.toml").write_text(
        '[lint]\nrules = ["rules.yaml"]\nselect = ["ACME001"]\n')
    assert _cli(tmp_path / "ip", "a.pss") == ["ip/a.pss"]
    assert _cli(tmp_path, "ip/a.pss") == ["ip/a.pss"]


def test_cli_without_a_config_the_path_is_as_given(tmp_path):
    (tmp_path / "ip").mkdir()
    (tmp_path / "ip" / "a.pss").write_text("component a_c { }\n")
    (tmp_path / "rules.yaml").write_text(_RULE)
    assert _cli(tmp_path, "--no-config", "--rules", "rules.yaml", "--select", "ACME001",
                "ip/a.pss") == ["ip/a.pss"]


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    for fid, cost in (("file_of_node", "constant"), ("decls_in_FileInfo", "custom")):
        f = fns[fid]
        assert (f["group"], f["level"], f["scope"], f["cost"]) == (
            "Locations", "L0", "file", cost), f
    assert "FileInfo" in [r["name"] for r in hooks.cel_functions()["records"]]
