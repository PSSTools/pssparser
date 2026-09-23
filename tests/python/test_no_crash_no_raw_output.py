"""INV-1 and INV-2, runtime half: no input crashes pssparser or makes it print.

Every model below goes through the CLI (``--json``) in its own process, so
that a crash is observed rather than suffered. For each one:

* **INV-1, no crash.** The exit status is 0, 1 or 3 -- never a signal (a
  segfault from runaway recursion) or an abort (an uncaught C++ exception).
  An internal failure must surface as a ``PSS000`` marker instead, and
  ``PSS000`` itself is allowed only for inputs listed in ``PSS000_XFAIL``.
* **INV-2, no raw output.** stdout is exactly one JSON document and stderr is
  empty. The dmgr ``DEBUG_ERROR`` macro used to print ``Error: ...`` lines to
  stdout, ahead of the JSON, with nothing counted.

The inputs are every file the project has for exercising the front end: the
error suite and the pss-corpus (both tracked), plus -- when present in the
working tree -- the semantic-checks review probes and the symbol-resolution
repros under docs/design/. See docs/design/symbol-resolution-plan.md §2.

The source half of INV-2 is ``test_no_raw_output_src.py``.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: (label, root, required). A required root that is missing is a failure; the
#: docs/design inputs are working-tree material and may be absent.
INPUT_ROOTS = [
    ("error-suite", ROOT / "error-suite" / "cases", True),
    ("pss-corpus", ROOT / "packages" / "pss-corpus" / "curated", False),
    ("review-probes", ROOT / "docs" / "design" / "semantic-checks" / "probes", False),
    ("resolution-repros", ROOT / "docs" / "design" / "symbol-resolution" / "repros", False),
]

#: Inputs, relative to ROOT, that are known to produce PSS000. Each entry is
#: a defect to fix; keep the reason next to it. Empty since R0 (2026-09-23).
PSS000_XFAIL: dict = {}

#: Exit statuses the CLI may return: clean, errors reported, internal error.
_OK_RC = {0, 1, 3}


def _run(path: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "python") + os.pathsep + env.get("PYTHONPATH", "")
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    p = subprocess.run(
        [sys.executable, "-m", "pssparser", "--json", str(path)],
        capture_output=True, text=True, env=env, timeout=300)
    res = {
        "file": str(path.relative_to(ROOT)),
        "rc": p.returncode,
        "stderr": p.stderr,
        "json_ok": True,
        "codes": [],
        "stdout_head": "",
    }
    try:
        doc = json.loads(p.stdout)
        res["codes"] = [d.get("code") for d in doc.get("diagnostics", [])]
    except ValueError:
        res["json_ok"] = False
        res["stdout_head"] = p.stdout[:200]
    return res


@pytest.mark.parametrize("label,root,required", INPUT_ROOTS,
                         ids=[r[0] for r in INPUT_ROOTS])
def test_no_crash_and_no_raw_output(label, root, required):
    if not root.is_dir():
        if required:
            pytest.fail("input root %s is missing" % root)
        pytest.skip("%s not present in this checkout" % root)

    files = sorted(root.rglob("*.pss"))
    assert files, "no .pss files under %s" % root

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        results = list(ex.map(_run, files))

    crashed, raw, internal, unexpected_ok = [], [], [], []
    for r in results:
        if r["rc"] not in _OK_RC:
            crashed.append("%s: rc=%d" % (r["file"], r["rc"]))
        if not r["json_ok"] or r["stderr"]:
            raw.append("%s: %r" % (
                r["file"], (r["stderr"] or r["stdout_head"])[:160]))
        has_pss000 = "PSS000" in r["codes"]
        if has_pss000 and r["file"] not in PSS000_XFAIL:
            internal.append(r["file"])
        if not has_pss000 and r["file"] in PSS000_XFAIL:
            unexpected_ok.append(r["file"])

    problems = []
    if crashed:
        problems.append("crashed (INV-1):\n  " + "\n  ".join(crashed))
    if internal:
        problems.append("internal error PSS000 (INV-1):\n  " + "\n  ".join(internal))
    if raw:
        problems.append("raw output / unparseable --json (INV-2):\n  " + "\n  ".join(raw))
    if unexpected_ok:
        problems.append("in PSS000_XFAIL but now clean -- remove the entry:\n  "
                        + "\n  ".join(unexpected_ok))
    assert not problems, "%s: %d files\n%s" % (label, len(files), "\n".join(problems))
