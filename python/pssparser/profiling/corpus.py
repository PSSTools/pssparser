"""Corpus discovery and bucket policy.

The discovery order is deliberately identical to
``tests/python/corpus/test_pss_corpus.py``, and duplicated rather than shared,
for the reason given there: it is twenty lines, and a package to hold them
would add a build, a release cadence and a version-skew failure mode to a
repository whose entire value is having none of those.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


#: Bucket policy used when there is no ``manifest.toml`` to read.  Pinned to
#: the manifest by ``test_pss_corpus.test_the_manifest_agrees_with_the_fallback``.
FALLBACK_BROKEN_BUCKETS = ("pathological",)


def _sweep_root(path: Path) -> Path:
    """The subtree to sweep.

    ``curated/`` and ``breadth/`` carry different promises -- recorded
    provenance versus bulk input of unknown validity -- so a consumer selects
    between them with a path, and breadth cannot leak in merely by arriving.
    """
    curated = path / "curated"
    return curated if curated.is_dir() else path


def find_corpus(explicit: Optional[str] = None) -> Tuple[Optional[Path], Optional[Path], str]:
    """Locate the corpus.

    Returns ``(sweep_root, repo_root, source)``.  ``repo_root`` is where
    ``manifest.toml`` lives and is ``None`` for a bare directory of ``.pss``
    files; ``source`` names which candidate won, for diagnostics.
    """
    repo_root = Path(__file__).resolve().parents[3]

    candidates: List[Tuple[str, Path]] = []
    if explicit:
        candidates.append(("--corpus", Path(explicit)))
    override = os.environ.get("PSS_CORPUS")
    if override:
        candidates.append(("PSS_CORPUS", Path(override)))
    candidates += [
        ("ivpm", repo_root / "packages" / "pss-corpus"),
        ("sibling", repo_root.parent / "pss-corpus"),
    ]

    for name, path in candidates:
        if not path.is_dir():
            continue
        root = _sweep_root(path)
        if any(root.rglob("*.pss")):
            repo = path if (path / "manifest.toml").is_file() else None
            return root, repo, "%s (%s)" % (name, root)
    return None, None, "none"


def _toml():
    """A TOML reader, or ``None``.  ``tomllib`` is stdlib only from 3.11."""
    try:
        import tomllib
        return tomllib
    except ModuleNotFoundError:
        try:
            import tomli
            return tomli
        except ModuleNotFoundError:
            return None


def bucket_policy(repo_root: Optional[Path]) -> Dict[str, bool]:
    """``bucket name -> parses``, read from the corpus's own manifest.

    Read from the corpus rather than hardcoded, so a new bucket arrives with
    its policy attached instead of needing a matching commit here.
    """
    if repo_root is not None:
        toml = _toml()
        if toml is not None:
            data = toml.loads((repo_root / "manifest.toml").read_text(encoding="utf-8"))
            return {
                name: bool(spec.get("parses", True))
                for name, spec in data.get("bucket", {}).items()
            }
    return {name: False for name in FALLBACK_BROKEN_BUCKETS}


def bucket_of(path: Path, sweep_root: Path) -> str:
    """The bucket a file belongs to: its first directory under the sweep root."""
    try:
        rel = path.relative_to(sweep_root)
    except ValueError:
        return "<outside>"
    return rel.parts[0] if len(rel.parts) > 1 else "<root>"


def corpus_files(
        sweep_root: Path,
        policy: Dict[str, bool],
        want: str = "all") -> List[Tuple[Path, str, bool]]:
    """``(path, bucket, expected_to_parse)`` for each file, in a fixed order.

    Sorted, and the sort is load-bearing rather than cosmetic: in warm mode the
    first file parsed pays nearly all the DFA-construction cost, so an unstable
    order would move that cost between files and make runs incomparable.
    """
    ret = []
    for path in sorted(sweep_root.rglob("*.pss")):
        bucket = bucket_of(path, sweep_root)
        parses = policy.get(bucket, True)
        if want == "good" and not parses:
            continue
        if want == "bad" and parses:
            continue
        ret.append((path, bucket, parses))
    return ret


def corpus_rev(repo_root: Optional[Path]) -> str:
    """The corpus's git revision, or ``"unknown"``.

    Recorded so a baseline comparison across two different corpora can be
    refused rather than silently reported as a grammar regression.
    """
    if repo_root is None:
        return "unknown"
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() if out.returncode == 0 else "unknown"
