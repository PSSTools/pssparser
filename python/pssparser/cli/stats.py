"""Run statistics for ``--stats``.

Three independent pieces, deliberately kept separable so a caller can ask
for one without paying for the others:

* :class:`StatsVisitor` -- an AST walk producing declaration counts.
* :func:`diagnostics_by_code` -- a histogram over the reported diagnostics.
* :class:`RunStats` -- the container the CLI renders, which also holds the
  phase timings gathered in ``commands.py``.

**Scope discipline.** The walk must only ever be handed the *user's* global
scopes.  ``Parser.parse`` prepends a synthesised standard-library unit, so a
walk rooted at the linked tree reports the same ~200 phantom types for every
model on earth.  ``commands._user_global_scopes`` does the filtering; this
module never reaches for the parser itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .diagnostics import Diagnostic

# Declaration counters, in render order.  Every key is always present, even
# at zero: the JSON consumer contract is that ``.stats.decls.actions`` never
# needs a missing-key branch.  (Human rendering drops the zero rows; that
# asymmetry is intentional.)
DECL_KEYS: tuple = (
    "packages",
    "components",
    "actions",
    "structs",
    "buffers",
    "streams",
    "states",
    "resources",
    "fields",
    "constraints",
    "exec_blocks",
    "functions",
    "imports",
)

# Human-readable singular/plural labels for each counter.
DECL_LABELS: Dict[str, tuple] = {
    "packages": ("package", "packages"),
    "components": ("component", "components"),
    "actions": ("action", "actions"),
    "structs": ("struct", "structs"),
    "buffers": ("buffer", "buffers"),
    "streams": ("stream", "streams"),
    "states": ("state", "states"),
    "resources": ("resource", "resources"),
    "fields": ("field", "fields"),
    "constraints": ("constraint block", "constraint blocks"),
    "exec_blocks": ("exec block", "exec blocks"),
    "functions": ("function", "functions"),
    "imports": ("import", "imports"),
}

# StructKind enum value -> counter key.  Resolved lazily so importing this
# module does not require the compiled extension (the CLI imports it before
# deciding whether a parse is even going to happen).
_STRUCT_KIND_KEYS = {
    "Buffer": "buffers",
    "Stream": "streams",
    "State": "states",
    "Resource": "resources",
    "Struct": "structs",
}


def _struct_kind_map() -> Dict[int, str]:
    from pssparser import ast as pss_ast

    return {
        int(getattr(pss_ast.StructKind, name)): key
        for name, key in _STRUCT_KIND_KEYS.items()
        if hasattr(pss_ast.StructKind, name)
    }


def new_decl_counts() -> Dict[str, int]:
    return {k: 0 for k in DECL_KEYS}


@dataclass
class RunStats:
    """Everything ``--stats`` reports about one run."""

    files: int = 0
    decls: Dict[str, int] = field(default_factory=new_decl_counts)
    # Phase name -> nanoseconds.  Empty under ``--stats-no-timing``.
    timings_ns: Dict[str, int] = field(default_factory=dict)
    # Marker ID -> count.  Uncoded markers bucket under ``<uncoded>``.
    diagnostics_by_code: Dict[str, int] = field(default_factory=dict)


def make_visitor():
    """Build a fresh ``StatsVisitor``.

    A factory rather than a plain import so that ``pssparser.ast`` -- a
    compiled extension -- is only loaded when stats are actually wanted.
    """
    from pssparser import ast as pss_ast

    kind_map = _struct_kind_map()

    class StatsVisitor(pss_ast.VisitorBase):
        """Counts declarations across one or more user global scopes."""

        def __init__(self) -> None:
            super().__init__()
            self.counts = new_decl_counts()

        def _bump(self, key: str, node=None) -> None:
            if node is not None and self._is_synthesized(node):
                return
            self.counts[key] += 1

        @staticmethod
        def _is_synthesized(node) -> bool:
            """True for a declaration the tool invented rather than read.

            Filtering out the standard-library *unit* is not enough: the
            linker also grafts implicit members onto the user's own types --
            every action gets a ``set_executor`` prototype, for instance --
            and those live inside the user's global scope.  They are marked
            by a negative ``fileid``, the same convention that keeps them
            from being reported as a diagnostic location.
            """
            try:
                name = node.getName()
                if name is None:
                    return False
                loc = name.getLocation()
            except AttributeError:
                return False
            return loc is not None and loc.fileid < 0

        def visitPackageScope(self, i):
            self._bump("packages", i)
            super().visitPackageScope(i)

        def visitComponent(self, i):
            self._bump("components", i)
            super().visitComponent(i)

        def visitAction(self, i):
            self._bump("actions", i)
            super().visitAction(i)

        def visitStruct(self, i):
            # A `struct` and a `buffer` are the same node type distinguished
            # only by kind; reporting them as one number would hide the
            # thing a PSS reader most wants to know about a model.
            self._bump(kind_map.get(int(i.getKind()), "structs"), i)
            super().visitStruct(i)

        def visitField(self, i):
            self._bump("fields", i)
            super().visitField(i)

        def visitConstraintBlock(self, i):
            self._bump("constraints", i)
            super().visitConstraintBlock(i)

        def visitExecBlock(self, i):
            self._bump("exec_blocks", i)
            super().visitExecBlock(i)

        def visitFunctionPrototype(self, i):
            # Every function declaration owns exactly one prototype node --
            # a bare declaration, a definition with a body, and an imported
            # function alike. Counting FunctionDefinition/FunctionImport as
            # well would double-count the latter two, since the visitor
            # descends from those into the prototype they contain.
            self._bump("functions", i)
            super().visitFunctionPrototype(i)

        def visitPackageImportStmt(self, i):
            self._bump("imports", i)
            super().visitPackageImportStmt(i)

    return StatsVisitor()


def collect_decls(global_scopes: Iterable) -> Dict[str, int]:
    """Walk *global_scopes* and return declaration counts.

    *global_scopes* must already be filtered to the user's files -- see the
    module docstring.
    """
    visitor = make_visitor()
    for gs in global_scopes:
        gs.accept(visitor)
    return visitor.counts


UNCODED = "<uncoded>"


def diagnostics_by_code(diags: Iterable[Diagnostic]) -> Dict[str, int]:
    """Histogram of diagnostics keyed by marker ID.

    Core markers acquire their ID from a message-pattern table
    (``commands._assign_core_code``), so a C++ message that matches no
    pattern arrives with no code at all.  Those bucket under ``<uncoded>``
    rather than being dropped: a non-zero ``<uncoded>`` count is the signal
    that the pattern table has drifted from the C++ message text.
    """
    hist: Dict[str, int] = {}
    for d in diags:
        key = d.code or UNCODED
        hist[key] = hist.get(key, 0) + 1
    return dict(sorted(hist.items()))


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _fmt_ns(ns: int) -> str:
    ms = ns / 1_000_000.0
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms:.1f}ms"


def render_human(stats: RunStats) -> str:
    """Render *stats* as the human-readable block written to stderr."""
    lines: List[str] = []
    lines.append(
        "stats: " + _plural(stats.files, "file", "files") + " processed"
    )

    # Drop all-zero rows: a model with no streams should not have to read a
    # line telling it so.  (JSON does the opposite -- see DECL_KEYS.)
    shown = [(k, stats.decls.get(k, 0)) for k in DECL_KEYS
             if stats.decls.get(k, 0)]
    if shown:
        items = [_plural(n, *DECL_LABELS[k]) for k, n in shown]
        lines.append("  declarations: " + ", ".join(items))
    else:
        lines.append("  declarations: none")

    if stats.diagnostics_by_code:
        items = [f"{code} x{n}" for code, n in stats.diagnostics_by_code.items()]
        lines.append("  diagnostics:  " + ", ".join(items))

    if stats.timings_ns:
        items = [f"{name} {_fmt_ns(ns)}" for name, ns in stats.timings_ns.items()]
        lines.append("  timing:       " + ", ".join(items))

    return "\n".join(lines) + "\n"


def to_json(stats: RunStats) -> dict:
    """Render *stats* as the ``"stats"`` value of the JSON document."""
    doc: dict = {
        "files": stats.files,
        # Every key, always -- even at zero.
        "decls": {k: stats.decls.get(k, 0) for k in DECL_KEYS},
        "diagnostics_by_code": dict(stats.diagnostics_by_code),
    }
    if stats.timings_ns:
        doc["timing_ms"] = {
            name: round(ns / 1_000_000.0, 3)
            for name, ns in stats.timings_ns.items()
        }
    return doc
