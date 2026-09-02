#!/usr/bin/env python3
"""Generate docs/markers.rst from CoreChecker.marker_defs.

Run after any change to python/pssparser/checkers/core_checker.py::marker_defs
so the reference page cannot drift from the catalogue that --list-markers and
--describe read. tests/python/cli/test_marker_docs.py checks the committed
file is up to date with this script's output.

Only CoreChecker's built-in IDs are documented here, not third-party plugin
checkers discovered at runtime (CheckerManager.discover() picks those up from
installed packages, which varies by environment -- a doc generator that read
them would produce a different docs/markers.rst on every machine). Plugin
authors document their own IDs; see docs/checker_plugin_guide.rst.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "python"))

from pssparser.checkers.core_checker import CoreChecker  # noqa: E402

OUTPUT_PATH = _ROOT / "docs" / "markers.rst"

_HEADER = """\
Marker Reference
================

Every diagnostic the built-in core checker can emit, generated from
``CoreChecker.marker_defs`` by ``scripts/gen_marker_docs.py`` -- do not edit
this file by hand, it will be overwritten.

``PSS001``-``PSS099`` is the general band, ``PSS020``-``PSS028`` its syntax
sub-band, and ``PSS100``-``PSS199`` is the PSS 3.1 language-rule band.
``PSS023`` and ``PSS027`` are reserved within the syntax sub-band and
deliberately have no entry below -- see ``PSS022``'s detail and
``core_checker.py``'s syntax-band comment (U-9) respectively for why. Query
the same information from the command line with ``--list-markers`` and
``--describe <ID>``.

"""


def render() -> str:
    lines = [_HEADER]
    for mdef in CoreChecker.marker_defs:
        lines.append(f"{mdef.id}\n{'-' * len(mdef.id)}\n\n")
        lines.append(f"**Severity:** {mdef.severity}\n\n")
        lines.append(f"{mdef.summary}\n\n")
        if mdef.detail:
            lines.append(f"{mdef.detail}\n\n")
    return "".join(lines)


def main() -> int:
    text = render()
    OUTPUT_PATH.write_text(text)
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
