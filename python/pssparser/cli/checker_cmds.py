"""Output helpers for checker query commands."""
from __future__ import annotations

import sys
from typing import TextIO

from pssparser.checkers import CheckerManager


def cmd_list_checkers(
    manager: CheckerManager,
    stdout: TextIO | None = None,
) -> int:
    """Print all registered checkers and return exit code 0."""
    out = stdout or sys.stdout
    checkers = manager.list_checkers()
    out.write(f"Registered checkers ({len(checkers)}):\n")
    for info in checkers:
        builtin_tag = " [built-in]" if info["is_builtin"] else ""
        ids_str = " ".join(info["marker_ids"]) if info["marker_ids"] else "(none)"
        out.write(f"  {info['name']:<20} {info['description']}{builtin_tag}\n")
        out.write(f"    markers: {ids_str}\n")
    return 0


def cmd_list_markers(
    manager: CheckerManager,
    stdout: TextIO | None = None,
) -> int:
    """Print all declared marker IDs and return exit code 0."""
    out = stdout or sys.stdout
    markers = manager.list_all_markers()
    if not markers:
        out.write("(no markers registered)\n")
        return 0
    # Column widths
    id_w = max(len(m["id"]) for m in markers)
    sev_w = max(len(m["severity"]) for m in markers)
    checker_w = max(len(m["checker"]) for m in markers)
    id_w = max(id_w, 2)
    sev_w = max(sev_w, 3)
    checker_w = max(checker_w, 7)
    header = f"{'ID':<{id_w}}  {'SEV':<{sev_w}}  {'CHECKER':<{checker_w}}  SUMMARY"
    out.write(header + "\n")
    out.write("-" * len(header) + "\n")
    for m in markers:
        out.write(
            f"{m['id']:<{id_w}}  {m['severity']:<{sev_w}}  "
            f"{m['checker']:<{checker_w}}  {m['summary']}\n"
        )
    return 0


def cmd_describe(
    manager: CheckerManager,
    marker_id: str,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Print the full definition for *marker_id* and return exit code."""
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    info = manager.describe_marker(marker_id)
    if info is None:
        err.write(
            f"error: unknown marker ID {marker_id!r}; "
            "use --list-markers to see available IDs\n"
        )
        return 2
    out.write(f"{info['id']}  [{info['severity']}]  checker: {info['checker']}\n")
    out.write(f"{info['summary']}\n")
    if info.get("detail"):
        out.write(f"\n{info['detail']}\n")
    return 0
