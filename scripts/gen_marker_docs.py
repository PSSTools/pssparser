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

Every diagnostic the built-in core can emit, generated from
``CoreChecker.marker_defs`` by ``scripts/gen_marker_docs.py`` -- do not edit
this file by hand, it will be overwritten.  Query the same information from
the command line with ``--list-markers`` and ``--describe <ID>``.

Namespaces
----------

``PSS``
   Normative PSS: the model violates the language reference manual.
   ``PSS001``-``PSS099`` is the general band, ``PSS020``-``PSS028`` its
   syntax sub-band, and ``PSS100``-``PSS199`` the PSS 3.1 language-rule band.
``LINT``
   Lint: legal PSS that is probably not what the author meant.  The rules
   listed here are raised by the core linker; the full rule reference,
   grouped by family, is :doc:`lint-rules`.
``PSSP``
   pssparser itself: an extension failed to load, a construct is accepted
   but not represented in the AST, an old ID was used in a configuration.

Several warnings that used to carry ``PSS`` IDs moved to ``LINT`` or
``PSSP``.  Their old IDs are listed under *Retired and reserved codes*; they
are still accepted wherever an ID is typed (configuration, ``-W``,
``--describe``) and are never reused.

Severities
----------

``error``
   The model is invalid, or a finding was promoted with ``-Werror``.  Sets
   exit status 1.
``warning``
   Probably wrong; fix or waive it.  Exit status 0 unless ``-Werror``.
``info``
   Worth knowing, no action required.  Counted as a *note*; not promoted by
   a bare ``-Werror`` (use ``-Werror=info`` or ``-Werror=ID``).
``hint``
   An editor nudge.  Hidden at the command line unless ``--show-hints``;
   always present in machine-readable output.

"""


def _entry(mdef) -> str:
    out = [f"{mdef.id}\n{'~' * len(mdef.id)}\n\n"]
    if mdef.status in ("retired", "reserved"):
        state = mdef.status.capitalize()
        if mdef.replaced_by:
            state += ": replaced by " + ", ".join(
                f"``{r}``" for r in mdef.replaced_by)
        out.append(f"**{state}**\n\n")
    else:
        out.append(f"**Severity:** {mdef.severity}\n\n")
        facts = []
        if mdef.name:
            facts.append(f"**Name:** ``{mdef.name}``")
        if mdef.tier:
            facts.append(f"**Tier:** {mdef.tier}")
        if mdef.family:
            facts.append(f"**Family:** {mdef.family}")
        if mdef.aliases:
            facts.append("**Formerly:** " + ", ".join(
                f"``{a}``" for a in mdef.aliases))
        if facts:
            out.append("; ".join(facts))
            out.append("\n\n")
    out.append(f"{mdef.summary}\n\n")
    if mdef.detail:
        out.append(f"{mdef.detail}\n\n")
    return "".join(out)


def _section(title: str, defs) -> str:
    if not defs:
        return ""
    head = f"{title}\n{'-' * len(title)}\n\n"
    return head + "".join(_entry(m) for m in defs)


def render() -> str:
    defs = CoreChecker.marker_defs
    active = [m for m in defs if m.emittable]
    inactive = [m for m in defs if not m.emittable]
    return "".join([
        _HEADER,
        _section("PSS: LRM violations",
                 [m for m in active if not m.id.startswith(("PSSP", "LINT"))]),
        _section("LINT: core-emitted lint",
                 [m for m in active if m.id.startswith("LINT")]),
        _section("PSSP: the tool's own diagnostics",
                 [m for m in active if m.id.startswith("PSSP")]),
        _section("Retired and reserved codes", inactive),
    ])


def main() -> int:
    text = render()
    OUTPUT_PATH.write_text(text)
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
