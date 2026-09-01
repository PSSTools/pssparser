"""Cold collection: one subprocess per file.

The DFA lives in the generated parser's *static* data and is shared by every
``PSSParser`` instance in the process, so it is warm from the second file
onward and there is no exposed way to clear it.  A fresh process is the only
way to ask "what does this construct cost to learn?", and the answer is what
explains first-parse latency for a short-lived consumer such as a pre-commit
hook or a CLI invocation.

The subprocess also makes the sweep crash-safe, which is not incidental: the
``parses = false`` bucket exists to hold input that has crashed the parser
before, and an in-process sweep that dies takes the other ninety-one files'
results with it.
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .model import FileProfile, _corpus_from_dict  # noqa: F401  (shared decoding)
from .model import CorpusProfile


#: This repository's importable ``pssparser``.  Matches the convention in
#: ``tests/python/isolation.py``: a subprocess must load the checkout under
#: test, never whatever happens to be installed.
_REPO_PYTHON = str(Path(__file__).resolve().parents[2])


def _child_source() -> str:
    """The program the child runs: parse one file, write one JSON profile.

    The result goes to a *file*, not to stdout.  The parser's error listener
    writes diagnostics to stdout from C++, so a file with a syntax error
    prepends "Error: ..." to whatever the child prints -- and the JSON no
    longer parses.  That failure mode is invisible and precisely inverted: it
    drops the files with errors, which are the ones whose prediction behaviour
    is least understood.
    """
    return (
        "import json, sys, dataclasses\n"
        "from pathlib import Path\n"
        "from pssparser.profiling.collect import ProfileCollector\n"
        "from pssparser.profiling.grammar_map import find_grammar, rule_lines\n"
        "path, bucket, out = sys.argv[1], sys.argv[2], sys.argv[3]\n"
        "lines = rule_lines(find_grammar())\n"
        "c = ProfileCollector(lines)\n"
        "p = c.collect_file(Path(path), bucket=bucket, mode='cold')\n"
        "Path(out).write_text(json.dumps(dataclasses.asdict(p)))\n"
    )


def collect_cold_file(
        path: Path,
        bucket: str,
        timeout: float = 120.0) -> Optional[FileProfile]:
    """Profile one file in a fresh process.

    Returns ``None`` if the child crashed or produced nothing parseable.  A
    crash is reported by the caller rather than raised: one pathological file
    must not end the sweep.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [_REPO_PYTHON] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

    with tempfile.TemporaryDirectory(prefix="pss-profile-") as tmp:
        result_path = Path(tmp) / "profile.json"
        try:
            out = subprocess.run(
                [sys.executable, "-c", _child_source(),
                 str(path), bucket, str(result_path)],
                capture_output=True, text=True, env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None

        # A crash leaves no result file: the child is killed by a signal
        # before it writes.  That is the case this whole module exists for.
        if out.returncode != 0 or not result_path.is_file():
            return None
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return _file_from_dict(data)


def _file_from_dict(data: dict) -> FileProfile:
    from .model import DecisionSample, Event
    decisions = []
    for d in data.pop("decisions", []):
        events = [Event(**e) for e in d.pop("events", [])]
        decisions.append(DecisionSample(events=events, **d))
    return FileProfile(decisions=decisions, **data)


def collect_cold(
        files: Iterable[Tuple[Path, str, bool]],
        progress=None) -> Tuple[List[FileProfile], List[Path]]:
    """Profile every file in its own process.

    Returns ``(profiles, crashed)``.  ``crashed`` is reported rather than
    silently dropped -- a file that cannot be profiled is a finding, and a
    sweep that quietly covers 88 of 92 files reads as though it covered all 92.
    """
    profiles: List[FileProfile] = []
    crashed: List[Path] = []
    for path, bucket, _parses in files:
        if progress:
            progress(path)
        got = collect_cold_file(path, bucket)
        if got is None:
            crashed.append(path)
        else:
            profiles.append(got)
    return profiles, crashed
