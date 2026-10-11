#!/usr/bin/env python3
"""Generate docs/_static/pss-rules.schema.json, the JSON Schema of a
declarative rule file (pss-rules-format.md §6.4; lint-core-plan.md C4.4).

The schema is written by the C++ rule loader from the field table it
validates against (``src/lint/rules/RuleSchema.cpp``), and lists the AST node
kinds from the reflection tables; this script reads it through the built
module, so build first.  Run after any change to the loader's fields or to
``ast/*.yaml``.  ``tests/python/lintcore/test_rules_schema.py`` fails when
the committed file is stale.

Sphinx copies ``docs/_static`` into the built site, so the schema is
published with the docs; a rule file can name it in a
``# yaml-language-server: $schema=...`` comment for editor completion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "python"))

OUTPUT_PATH = _ROOT / "docs" / "_static" / "pss-rules.schema.json"


def schema() -> dict:
    from pssparser.core import Factory
    return Factory.inst()._lintTestHooks().rules_schema()


def render(doc=None) -> str:
    if doc is None:
        doc = schema()
    return json.dumps(doc, indent=2) + "\n"


def main() -> int:
    OUTPUT_PATH.write_text(render())
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
