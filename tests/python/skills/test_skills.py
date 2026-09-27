"""Tests for the agent skills in ``skills/`` (docs/design/agent-skills.md §6).

The skills are instructions an agent follows literally, so a wrong flag or an
example that no longer links is a defect, not a typo.  These tests hold the
skill text to the tool:

* T1  frontmatter of every ``skills/*/SKILL.md``;
* T2  the ``agent.skills`` entry points, and that discovering them does not
      load the native libraries;
* T3  every ``pssparser`` flag and every ``PSS`` marker ID the text names;
* T4  every fenced ``pss`` / ``python`` block runs, and the extension
      template installs;
* T5  an installed wheel carries exactly the shipped skills;
* T6  size limits.

A fenced block opts out of T4 with a ``no-check`` tag: ```` ```pss no-check ````.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap

import pytest

from ..isolation import _parent_package_root

_REPO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_SKILLS = os.path.join(_REPO, "skills")

#: Every skill in the repository, shipped or not.
ALL_SKILLS = sorted(
    d for d in os.listdir(_SKILLS)
    if os.path.isfile(os.path.join(_SKILLS, d, "SKILL.md")))

#: Kept in step with pssparser.skills.SHIPPED by test_shipped_matches_module.
SHIPPED = ("pssparser", "pssparser-checkers", "pssparser-api")


def _md_files(skill=None):
    """Every Markdown file of *skill* (or of all skills), as absolute paths."""
    roots = [os.path.join(_SKILLS, skill)] if skill else [_SKILLS]
    out = []
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x != "assets"]
            out.extend(os.path.join(d, f) for f in files if f.endswith(".md"))
    return sorted(out)


def _rel(path):
    return os.path.relpath(path, _REPO)


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{_rel(path)}: no YAML frontmatter"
    fields = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        assert sep, f"{_rel(path)}: frontmatter line is not 'key: value': {line!r}"
        fields[key.strip()] = value.strip()
    return fields


_FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```\s*$", re.S | re.M)


def _blocks(lang):
    """(file, line, tags, body) for every fenced *lang* block in every skill."""
    out = []
    for path in _md_files():
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in _FENCE.finditer(text):
            info = m.group(1).split()
            if not info or info[0] != lang:
                continue
            line = text.count("\n", 0, m.start()) + 1
            out.append((path, line, set(info[1:]), m.group(2)))
    return out


def _run_python(code, cwd, env_extra=None):
    """Run *code* in a child that imports the parent's ``pssparser``."""
    env = dict(os.environ)
    env["PYTHONPATH"] = _parent_package_root()
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, env=env, cwd=cwd, timeout=300)


# ---------------------------------------------------------------------------
# T1 -- frontmatter
# ---------------------------------------------------------------------------

def test_expected_skills_exist():
    assert set(SHIPPED) | {"pssparser-dev"} == set(ALL_SKILLS)


def test_shipped_matches_module():
    from pssparser import skills
    assert tuple(skills.SHIPPED) == SHIPPED


@pytest.mark.parametrize("name", ALL_SKILLS)
def test_frontmatter(name):
    fm = _frontmatter(os.path.join(_SKILLS, name, "SKILL.md"))
    assert fm.get("name") == name
    desc = fm.get("description", "")
    assert desc, f"{name}: empty description"
    assert len(desc) <= 1024, f"{name}: description is {len(desc)} chars"
    # A YAML plain scalar cannot contain ': ' -- it would not parse as YAML.
    assert ": " not in desc, f"{name}: description contains ': '"


@pytest.mark.parametrize("name", ALL_SKILLS)
def test_references_are_linked(name):
    """C2: an agent reads a reference only if SKILL.md points to it."""
    with open(os.path.join(_SKILLS, name, "SKILL.md"), encoding="utf-8") as f:
        skill = f.read()
    refs = os.path.join(_SKILLS, name, "references")
    for f in sorted(os.listdir(refs)) if os.path.isdir(refs) else []:
        assert f"references/{f}" in skill, \
            f"{name}/SKILL.md never mentions references/{f}"


# ---------------------------------------------------------------------------
# T2 -- entry points
# ---------------------------------------------------------------------------

_T2 = r"""
import json, sys
import importlib.metadata as md
import pssparser.skills as s
loaded = sorted(m for m in ("pssparser.core", "pssparser.ast", "pssparser.parser")
                if m in sys.modules)
dist = md.distribution("pssparser")
eps = {ep.name: ep.value for ep in dist.entry_points if ep.group == "agent.skills"}
dirs = {}
for name, value in eps.items():
    mod, _, attr = value.partition(":")
    dirs[name] = getattr(__import__(mod, fromlist=[attr]), attr)()
print(json.dumps({"loaded": loaded, "eps": eps, "dirs": dirs,
                  "meta": str(getattr(dist, "_path", "")),
                  "pkg": s.__file__}))
"""


@pytest.fixture(scope="module")
def entry_points(tmp_path_factory):
    r = _run_python(_T2, str(tmp_path_factory.mktemp("t2")))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_skill_discovery_does_not_load_native_code(entry_points):
    assert entry_points["loaded"] == []


def test_entry_points(entry_points):
    if not entry_points["eps"] and entry_points["meta"].startswith(_REPO):
        pytest.skip(
            "the in-tree %s predates the agent.skills entry points; "
            "refresh it with `python setup.py egg_info`" % entry_points["meta"])
    assert sorted(entry_points["eps"]) == sorted(SHIPPED)
    for name, path in entry_points["dirs"].items():
        assert os.path.isabs(path), path
        skill_md = os.path.join(path, "SKILL.md")
        assert os.path.isfile(skill_md), f"{name}: {path} has no SKILL.md"
        assert os.path.basename(path) == name
        assert _frontmatter(skill_md)["name"] == name


def test_source_tree_fallback_is_the_repo_skill():
    """C6: the fallback must be the directory IVPM's auto-probe finds."""
    from pssparser import skills
    pkg = os.path.dirname(os.path.abspath(skills.__file__))
    if os.path.isdir(os.path.join(pkg, "share", "skills")):
        pytest.skip("testing an installed pssparser")
    for name in SHIPPED:
        assert os.path.realpath(skills._skill_dir(name)) == \
            os.path.realpath(os.path.join(_SKILLS, name))


# ---------------------------------------------------------------------------
# T3 -- flags and marker IDs
# ---------------------------------------------------------------------------

def _cli_options():
    from pssparser.cli.app import _build_parser
    opts = set()
    for action in _build_parser()._actions:
        opts.update(action.option_strings)
    # main() answers these before argparse runs, so they are not in it.
    opts.update(("--version", "-V"))
    return opts


_INLINE = re.compile(r"`([^`\n]+)`")
_FLAG = re.compile(r"(?<![\w-])(--?[A-Za-z][\w-]*)")


def _pssparser_commands(text):
    """Command lines that invoke pssparser, from fences and inline code."""
    cmds = []
    for m in _FENCE.finditer(text):
        info = m.group(1).split()
        if info and info[0] in ("bash", "sh", "shell", "console", "text"):
            for line in m.group(2).splitlines():
                line = line.strip().lstrip("$ ").strip()
                if re.match(r"(python -m )?pssparser(\s|$)", line):
                    cmds.append(line)
    prose = _FENCE.sub("", text)
    for span in _INLINE.findall(prose):
        span = span.strip()
        if re.match(r"(python -m )?pssparser(\s|$)", span) \
                or re.fullmatch(r"--?[A-Za-z][\w-]*(=\S*)?( \S+)?", span):
            cmds.append(span)
    return cmds


@pytest.mark.parametrize("path", _md_files(), ids=_rel)
def test_flags_exist(path):
    known = _cli_options()
    with open(path, encoding="utf-8") as f:
        text = f.read()
    bad = []
    for cmd in _pssparser_commands(text):
        # Stop at a shell operator: `pssparser a.pss | jq ...`.
        cmd = re.split(r"\s(?:\||&&|;|>|2>)", cmd)[0]
        for flag in _FLAG.findall(cmd):
            flag = flag.split("=")[0]
            if flag.startswith("-W") and flag != "-W":
                flag = "-W"
            if flag not in known:
                bad.append((flag, cmd))
    assert not bad, f"{_rel(path)}: unknown pssparser flags: {bad}"


@pytest.fixture(scope="module")
def marker_ids():
    from pssparser.checkers import CheckerManager
    m = CheckerManager()
    m.discover(load_extensions=False)
    return {d["id"] for d in m.list_all_markers()}


@pytest.mark.parametrize("path", _md_files(), ids=_rel)
def test_marker_ids_exist(path, marker_ids):
    with open(path, encoding="utf-8") as f:
        ids = set(re.findall(r"\bPSS\d{3}\b", f.read()))
    assert ids <= marker_ids, f"{_rel(path)}: unknown IDs {sorted(ids - marker_ids)}"


# ---------------------------------------------------------------------------
# T4 -- examples
# ---------------------------------------------------------------------------

_PSS = [b for b in _blocks("pss") if "no-check" not in b[2]]
_PY = [b for b in _blocks("python") if "no-check" not in b[2]]


def _block_id(b):
    return f"{_rel(b[0])}:{b[1]}"


@pytest.mark.parametrize("block", _PSS, ids=_block_id)
def test_pss_example_links_clean(block):
    from pssparser import Parser, ParseException
    path, line, _, body = block
    p = Parser()
    try:
        p.parses([(f"{_rel(path)}:{line}.pss", body)])
        p.link()
    except ParseException:
        pass
    errors = [m for m in p.markers if m["severity"] == "error"]
    assert not errors, f"{_block_id(block)}:\n" + "\n".join(
        f'{m["line"]}:{m["col"]}: [{m.get("code")}] {m["message"]}'
        for m in errors)


@pytest.mark.parametrize("block", _PY, ids=_block_id)
def test_python_example_runs(block, tmp_path):
    r = _run_python(textwrap.dedent(block[3]), str(tmp_path))
    assert r.returncode == 0, \
        f"{_block_id(block)}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"


def test_python_blocks_are_checked():
    """Guard the guard: an empty parametrization would pass vacuously."""
    assert _PSS and _PY


_TEMPLATE = os.path.join(_SKILLS, "pssparser-checkers", "assets",
                         "extension-template")


@pytest.mark.needs_install
def test_extension_template_installs(tmp_path):
    if not os.path.isdir(_TEMPLATE):
        pytest.skip("no extension template yet")
    src = tmp_path / "src"
    # Copy first: building in place would leave egg-info in skills/, and
    # the whole skill directory is copied into the wheel.
    shutil.copytree(_TEMPLATE, src)
    target = tmp_path / "target"
    uv = shutil.which("uv")
    cmd = ([uv, "pip", "install", "--python", sys.executable] if uv
           else [sys.executable, "-m", "pip", "install"])
    r = subprocess.run(cmd + ["--quiet", "--no-deps", "--target", str(target),
                              str(src)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([_parent_package_root(), str(target)])
    env.pop("PSSPARSER_NO_EXTENSIONS", None)
    r = subprocess.run(
        [sys.executable, "-m", "pssparser", "--list-extensions"],
        capture_output=True, text=True, env=env, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "my-pss-rules" in r.stdout, r.stdout
    # And its own tests pass against this pssparser.
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "-c", os.devnull, "--rootdir", str(src), str(src / "tests")],
        capture_output=True, text=True, env=env, cwd=str(src))
    assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# T5 -- the installed wheel
# ---------------------------------------------------------------------------

def test_installed_wheel_ships_exactly_the_shipped_skills():
    import pssparser
    pkg = os.path.dirname(os.path.abspath(pssparser.__file__))
    if os.path.realpath(pkg).startswith(os.path.realpath(_REPO) + os.sep):
        pytest.skip("pssparser is imported from the source tree, not a wheel")
    share = os.path.join(pkg, "share", "skills")
    assert os.path.isdir(share), f"the installed pssparser has no {share}"
    assert sorted(os.listdir(share)) == sorted(SHIPPED)
    # The installed copy is the repository's, file for file.
    for name in SHIPPED:
        for d, dirs, files in os.walk(os.path.join(_SKILLS, name)):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                rel = os.path.relpath(os.path.join(d, f), _SKILLS)
                with open(os.path.join(_SKILLS, rel), "rb") as a, \
                        open(os.path.join(share, rel), "rb") as b:
                    assert a.read() == b.read(), f"installed {rel} differs"


# ---------------------------------------------------------------------------
# T6 -- size
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", _md_files(), ids=_rel)
def test_size(path):
    with open(path, encoding="utf-8") as f:
        n = sum(1 for _ in f)
    limit = 200 if os.path.basename(path) == "SKILL.md" else 400
    assert n <= limit, f"{_rel(path)}: {n} lines, limit {limit}"
