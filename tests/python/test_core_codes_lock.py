"""The core code lockfile: a published code is never lost or reused.

``tests/data/core-codes.lock`` lists every code the core has ever shipped,
with its lifecycle state (marker-id-namespaces §2.5).  A code may move from
``active`` to ``deprecated`` to ``retired`` and from ``reserved`` to
``active``; it may never disappear from ``CoreChecker.marker_defs``, and a
retired code may never become active again.  A new code is appended to the
lockfile in the change that adds it.
"""
from __future__ import annotations

import sys
from pathlib import Path

from pssparser.checkers.core_checker import CoreChecker

LOCKFILE = Path(__file__).resolve().parents[1] / "data" / "core-codes.lock"

#: Allowed transitions, old state -> new states.
_ALLOWED = {
    "reserved": {"reserved", "active", "retired"},
    "active": {"active", "deprecated", "retired"},
    "deprecated": {"deprecated", "retired"},
    "retired": {"retired"},
}


def _read_lock() -> dict:
    states = {}
    for line in LOCKFILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        code, state = line.split()
        states[code] = state
    return states


def test_no_locked_code_disappears():
    declared = {m.id for m in CoreChecker.marker_defs}
    missing = sorted(set(_read_lock()) - declared)
    assert missing == [], (
        "codes in core-codes.lock no longer declared; retire them instead: "
        f"{missing}")


def test_lifecycle_only_moves_forward():
    locked = _read_lock()
    bad = [
        (m.id, locked[m.id], m.status) for m in CoreChecker.marker_defs
        if m.id in locked and m.status not in _ALLOWED[locked[m.id]]
    ]
    assert bad == [], f"illegal lifecycle transitions: {bad}"


def test_every_declared_code_is_locked():
    unlocked = sorted({m.id for m in CoreChecker.marker_defs} - set(_read_lock()))
    assert unlocked == [], (
        f"new core codes not yet in core-codes.lock: {unlocked}; append them")


def test_every_code_has_a_valid_status():
    from pssparser.checkers.taxonomy import STATUSES
    assert all(m.status in STATUSES for m in CoreChecker.marker_defs)


if __name__ == "__main__" and "--write" in sys.argv:
    locked = _read_lock()
    header = [l for l in LOCKFILE.read_text().splitlines() if l.startswith("#")]
    rows = [f"{m.id} {m.status}" for m in CoreChecker.marker_defs]
    # keep any locked code that vanished, so the test still reports it
    declared = {m.id for m in CoreChecker.marker_defs}
    rows += [f"{c} {s}" for c, s in locked.items() if c not in declared]
    LOCKFILE.write_text("\n".join(header + rows) + "\n")
