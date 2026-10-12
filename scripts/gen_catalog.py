#!/usr/bin/env python3
"""Generate the core's marker catalogue from the Python ``MarkerDef``s.

lint-core-plan.md C7.3.  Python stays the source of truth: the ``PSS``,
``PSSP`` and core-emitted ``LINT`` definitions (``CoreChecker.marker_defs``),
the taxonomy (``checkers/taxonomy.py``) and the message patterns that give a
core marker its code (``cli/commands.py``'s ``_build_core_patterns``, in its
order).  The output, ``src/lint/catalog/catalog.json``, is checked in, so a
review sees what changed, and embedded in the core at build time
(``src/lint/catalog/mk_catalog.py``).  Never edit it by hand.

Usage::

    PYTHONPATH=python python3 scripts/gen_catalog.py          # rewrite it
    PYTHONPATH=python python3 scripts/gen_catalog.py --check  # exit 1 if stale

``tests/python/lintcore/test_catalog.py`` fails when the file is stale.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "lint" / "catalog" / "catalog.json"

SCHEMA = "pssparser-catalog/1"


def marker(md, minimal: bool) -> dict:
    return {
        "id": md.id,
        "name": md.name,
        "tier": md.tier,
        "family": md.family,
        "since": md.since,
        "status": md.status,
        "severity": md.severity,
        "aliases": list(md.aliases),
        "replaced_by": list(md.replaced_by),
        "default_enabled": bool(md.default_enabled),
        "minimal": minimal,
        "summary": md.summary,
        "detail": md.detail,
        "lrm": list(md.lrm),
    }


def catalogue() -> dict:
    from pssparser.checkers import taxonomy
    from pssparser.checkers.core_checker import CoreChecker
    from pssparser.cli.commands import _build_core_patterns
    from pssparser.lint.catalog import MINIMAL_IDS

    mins = set(MINIMAL_IDS)
    return {
        "schema": SCHEMA,
        "generated_by": "scripts/gen_catalog.py",
        "taxonomy": {
            "tiers": [[t, s] for t, s in taxonomy.TIER_SEVERITY.items()],
            "families": list(taxonomy.FAMILIES),
            "profiles": list(taxonomy.PROFILES),
            "default_profile": taxonomy.DEFAULT_PROFILE,
            "profile_tiers": {p: list(t) for p, t in taxonomy.PROFILE_TIERS.items()},
            "doc_url": taxonomy.RULE_DOC_URL,
        },
        "markers": [marker(md, md.id in mins) for md in CoreChecker.marker_defs],
        # First match wins.  Python compiles them with re.IGNORECASE.
        "patterns": [["(?i)" + rx.pattern, code] for rx, code in _build_core_patterns()],
    }


def render() -> str:
    return json.dumps(catalogue(), indent=1, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when the checked-in file is stale")
    args = ap.parse_args(argv)
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.stderr.write(f"{OUT.relative_to(ROOT)} is stale; run scripts/gen_catalog.py\n")
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
