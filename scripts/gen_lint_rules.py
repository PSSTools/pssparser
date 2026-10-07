#!/usr/bin/env python3
"""Generate docs/lint-rules.rst from the LINT rule catalogue.

Run after any change to ``python/pssparser/lint/catalog.py`` or to a bundled
lint rule.  ``tests/python/lint/test_lint_rules_doc.py`` fails when the
committed file is stale.

Only the rules shipped with pssparser are documented: the bundled extension
is in-tree, so the output is the same on every machine.  Third-party rules are
documented by their own packages (see docs/checker_plugin_guide.rst).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "python"))

from pssparser.checkers import taxonomy  # noqa: E402
from pssparser.lint.catalog import ALL  # noqa: E402

OUTPUT_PATH = _ROOT / "docs" / "lint-rules.rst"

_FAMILY_TITLES = {
    "constraint": "Constraints",
    "activity": "Activities",
    "exec": "Exec blocks and functions",
    "decl": "Declarations",
    "import": "Imports and packages",
    "register": "Registers",
    "evolution": "Deprecated forms",
    "naming": "Naming",
    "metric": "Metrics",
}

_HEADER = """\
Lint Rule Reference
===================

Every ``LINT`` rule shipped with pssparser, generated from
``pssparser.lint.catalog`` by ``scripts/gen_lint_rules.py`` -- do not edit
this file by hand, it will be overwritten.  ``pssparser --explain <ID or
name>`` prints the same entry at the command line; :doc:`lint` explains
profiles, selection and configuration.

Each rule has a **tier**, which sets its default severity and the profiles
that enable it:

.. list-table::
   :header-rows: 1

   * - Tier
     - Default severity
     - Profiles
{tier_rows}

Every profile except ``none`` also includes the ``minimal`` rules: the
warnings pssparser reported before lint existed.

"""


def _tier_rows() -> str:
    rows = []
    for tier in taxonomy.LINT_TIERS:
        profiles = [p for p, tiers in taxonomy.PROFILE_TIERS.items() if tier in tiers]
        rows.append(
            f"   * - ``{tier}``\n"
            f"     - {taxonomy.TIER_SEVERITY[tier]}\n"
            f"     - {', '.join(f'``{p}``' for p in profiles) or '(none; select explicitly)'}"
        )
    return "\n".join(rows)


def _indent(text: str, n: int = 3) -> str:
    pad = " " * n
    return "\n".join(pad + line if line.strip() else "" for line in text.splitlines())


def _entry(md) -> str:
    title = f"{md.id}: ``{md.name}``" if md.name else md.id
    out = [f".. _{md.id.lower()}:\n\n{title}\n{'~' * len(title)}\n\n"]
    facts = [f"**Tier:** {md.tier}", f"**Default severity:** {md.severity}"]
    if md.since:
        facts.append(f"**Since:** {md.since}")
    if md.aliases:
        facts.append("**Formerly:** " + ", ".join(f"``{a}``" for a in md.aliases))
    if md.fix != "none":
        facts.append(f"**Fix:** {md.fix}")
    if md.lrm:
        facts.append("**LRM:** " + ", ".join(md.lrm))
    out.append("; ".join(facts) + "\n\n")
    out.append(f"{md.summary}\n\n")
    if md.detail:
        out.append(f"{md.detail}\n\n")
    for ex in md.examples:
        label = "Flagged" if ex.expect else "Not flagged"
        if ex.note:
            label += f" ({ex.note})"
        out.append(f"{label}:\n\n.. code-block:: pss\n\n{_indent(ex.code)}\n\n")
        if ex.fixed:
            out.append(f"After the fix:\n\n.. code-block:: pss\n\n{_indent(ex.fixed)}\n\n")
    return "".join(out)


def render() -> str:
    parts = [_HEADER.format(tier_rows=_tier_rows())]
    rules = sorted((md for md in ALL if md.emittable), key=lambda m: m.id)
    for family in taxonomy.FAMILIES:
        members = [md for md in rules if md.family == family]
        if not members:
            continue
        title = _FAMILY_TITLES.get(family, family)
        parts.append(f"{title}\n{'-' * len(title)}\n\n")
        parts.extend(_entry(md) for md in members)
    return "".join(parts)


def main() -> int:
    OUTPUT_PATH.write_text(render())
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
