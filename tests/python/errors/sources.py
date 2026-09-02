"""Known-good PSS sources for the E-7 mutation sweep (test_mutation_sweep.py).

Two providers, both optional and both skip cleanly when empty -- mirroring
how tests/python/corpus/test_pss_corpus.py treats an absent corpus:

``spec_examples``
    The inline snippets passed to ``assert_parse_ok`` /
    ``assert_parse_ok_with_warning`` in
    tests/python/spec_examples/test_curated_examples.py, harvested with
    :mod:`ast` rather than imported, since they are string literals inside
    test bodies and not otherwise reachable as data.

``corpus``
    Whatever tests/python/corpus/test_pss_corpus.py would sweep (the
    ``pss-corpus`` package's ``curated/`` tree), found the same way that
    module finds it. Duplicated rather than imported -- see that module's
    own ``_find_corpus`` docstring for why a shared package isn't worth it
    for twenty lines that rarely change.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import List, NamedTuple

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SPEC_EXAMPLES_FILE = (
    REPO_ROOT / "tests" / "python" / "spec_examples" / "test_curated_examples.py"
)

_ASSERT_CALLS = {"assert_parse_ok", "assert_parse_ok_with_warning"}


class Source(NamedTuple):
    name: str
    code: str


def spec_example_sources() -> List[Source]:
    if not SPEC_EXAMPLES_FILE.is_file():
        return []
    tree = ast.parse(SPEC_EXAMPLES_FILE.read_text(), filename=str(SPEC_EXAMPLES_FILE))
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _ASSERT_CALLS):
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        code = node.args[0].value
        if not isinstance(code, str) or not code.strip():
            continue
        out.append(Source(f"spec_examples:{node.lineno}", code))
    return out


def _find_corpus_root() -> Path | None:
    override = os.environ.get("PSS_CORPUS")
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates += [
        REPO_ROOT / "packages" / "pss-corpus",
        REPO_ROOT.parent / "pss-corpus",
    ]
    for path in candidates:
        if not path.is_dir():
            continue
        root = path / "curated" if (path / "curated").is_dir() else path
        if any(root.rglob("*.pss")):
            return root
    return None


def corpus_sources(limit: int = 40) -> List[Source]:
    root = _find_corpus_root()
    if root is None:
        return []
    files = sorted(root.rglob("*.pss"))[:limit]
    out = []
    for f in files:
        try:
            code = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        out.append(Source(f"corpus:{f.relative_to(root)}", code))
    return out


def all_sources() -> List[Source]:
    return spec_example_sources() + corpus_sources()
