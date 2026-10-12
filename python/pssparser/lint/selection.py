"""Rule selection in the core engine (lint-core-plan C7.1).

The core resolves profiles, ``select``/``ignore``, ``[[lint.overrides]]``,
the command line's layer, ``[severity]`` keys and ``-W`` groups
(:meth:`pssparser.core.LintEngine.resolve_selection`), so the CLI and the
WASM build select the same rules.  This module is the Python host's side:
it tells the engine about the markers it has no record of (the LRM, tool
and core lint markers, and Python checkers' rules), builds the request from
a :class:`~pssparser.cli.config.ResolvedConfig`, and reads the answer.

:mod:`pssparser.checkers.selectors` stays as the test oracle (the C++ is a
port of it), and for :func:`pssparser.waivers.apply` without an engine.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set


def host_marker(md, minimal: bool = False) -> dict:
    """One ``MarkerDef`` as the engine's host-marker dict."""
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
    }


def with_core(mdefs: Iterable) -> list:
    """The markers an engine holds after :func:`tell_engine` with *mdefs*
    (lint-core-plan C7.3): the core's own (``CoreChecker.marker_defs``, which
    the engine has built in) in order, each replaced by the entry of *mdefs*
    with its ID, then the rest of *mdefs*.  For the registry, which starts
    with the core, that is the registry itself."""
    from pssparser.checkers.core_checker import CoreChecker
    mdefs = list(mdefs)
    by_id = {md.id: md for md in mdefs}
    core = [by_id.get(md.id, md) for md in CoreChecker.marker_defs]
    core_ids = {md.id for md in core}
    return core + [md for md in mdefs if md.id not in core_ids]


def tell_engine(engine, mdefs: Iterable, refused: Iterable[str] = (),
                minimal: Optional[Sequence[str]] = None) -> None:
    """Give *engine* every registry entry it did not load itself.

    *mdefs* is the whole registry (``CheckerManager.all_marker_defs``),
    loaded rules included: the engine keeps the registry's order, which
    ``-Werror`` group expansion follows.  The engine already holds the core's
    markers; an entry with a core ID replaces that one (:func:`with_core`).  *minimal* defaults to the
    core-emitted lint (:data:`pssparser.lint.catalog.MINIMAL_IDS`).
    """
    if minimal is None:
        from pssparser.lint.catalog import MINIMAL_IDS
        minimal = MINIMAL_IDS
    mins = set(minimal)
    problems = engine.set_host_markers(
        [host_marker(md, md.id in mins) for md in mdefs], sorted(set(refused)))
    if problems:  # pragma: no cover - the dicts are built above
        raise ValueError("; ".join(problems))


@dataclass
class Group:
    """The effective rule set of the files one combination of overrides
    matches; group 0 is the files no override matches."""

    overrides: List[int]
    profile: str
    enabled: Set[str]
    explicit: Set[str]
    held_back: List[str]
    options: Dict[str, Dict[str, object]]


@dataclass
class Resolution:
    """What :meth:`LintEngine.resolve_selection` answered."""

    errors: List[dict]
    lint_ids: Set[str]
    groups: List[Group]
    #: Each requested path's group, by the path as given.
    path_group: Dict[str, int]
    #: Each requested path as the globs saw it (relative to the base).
    path_rel: Dict[str, str]
    severity: Dict[str, dict]
    warnings: dict
    #: The real path of each requested path, for :meth:`group_of`.
    _real: Dict[str, int] = field(default_factory=dict, repr=False)

    @classmethod
    def from_json(cls, r: dict) -> "Resolution":
        groups = [Group(g["overrides"], g["profile"], set(g["enabled"]), set(g["explicit"]),
                        list(g["held_back"]), dict(g["options"])) for g in r["groups"]]
        res = cls(errors=list(r["errors"]), lint_ids=set(r["lint_ids"]), groups=groups,
                  path_group={p["path"]: p["group"] for p in r["paths"]},
                  path_rel={p["path"]: p["rel"] for p in r["paths"]},
                  severity=dict(r["severity"]), warnings=dict(r["warnings"]))
        res._real = {os.path.realpath(p): g for p, g in res.path_group.items()}
        return res

    def group_of(self, path: str) -> Group:
        """The group of *path*: one of the requested paths (by real path), or
        group 0 for any other."""
        g = self.path_group.get(path)
        if g is None:
            g = self._real.get(os.path.realpath(path), 0)
        return self.groups[g]

    def rel_of(self, path: str) -> str:
        """*path* as the globs saw it: relative to the base directory."""
        rel = self.path_rel.get(path)
        if rel is None:
            real = os.path.realpath(path)
            rel = next((r for p, r in self.path_rel.items()
                        if os.path.realpath(p) == real), path)
        return rel

    def union(self, paths: Iterable[str]) -> Set[str]:
        """Rules enabled for any of *paths* (group 0 when there are none)."""
        out: Set[str] = set()
        seen = False
        for p in paths:
            out |= self.group_of(p).enabled
            seen = True
        return out if seen else set(self.groups[0].enabled)


def request(cfg, paths: Sequence[str] = ()) -> dict:
    """The engine's selection dict for *cfg* (a ``ResolvedConfig``), placing
    *paths*.  With a base directory, paths are made absolute, as the base is."""
    base = getattr(cfg, "base_dir", None)
    lint: dict = {}
    if cfg.lint_profile is not None:
        lint["profile"] = cfg.lint_profile
    if cfg.lint_select:
        lint["select"] = list(cfg.lint_select)
    if cfg.lint_ignore:
        lint["ignore"] = list(cfg.lint_ignore)
    if cfg.rules_version:
        lint["rules-version"] = cfg.rules_version
    if cfg.lint_rule_options:
        lint["rule"] = cfg.lint_rule_options
    overrides = getattr(cfg, "lint_overrides", None)
    if overrides:
        lint["overrides"] = overrides
    out: dict = {"lint": lint}
    cli = {}
    if cfg.cli_lint_select:
        cli["select"] = list(cfg.cli_lint_select)
    if cfg.cli_lint_ignore:
        cli["ignore"] = list(cfg.cli_lint_ignore)
    if cli:
        out["command_line"] = cli
    if cfg.severity:
        out["severity"] = dict(cfg.severity)
    warnings = {}
    if cfg.warnings_error_codes:
        warnings["error"] = list(cfg.warnings_error_codes)
    if cfg.warnings_no_error_codes:
        warnings["no-error"] = list(cfg.warnings_no_error_codes)
    if warnings:
        out["warnings"] = warnings
    if base:
        out["base_dir"] = base
    out["paths"] = [os.path.abspath(p) if base else p for p in paths]
    return out


class RunSelection:
    """A run's lint selection, per file: what reporting and the checkers'
    short-circuit read.

    With a configuration the engine resolved it for the run's files
    (:attr:`request` is what the declarative rules' run sends); without one
    every file has the default profile's rules.
    """

    def __init__(self, lint_ids: Set[str], enabled: Set[str],
                 resolution: Optional[Resolution] = None,
                 request: Optional[dict] = None, files: Sequence[str] = ()) -> None:
        self.lint_ids = set(lint_ids)
        self._enabled = set(enabled)
        self.resolution = resolution
        #: The engine's ``selection`` dict, without paths; ``None`` without
        #: a configuration.
        self.request = request
        #: Rules enabled for any of the run's files: the ones that run.
        self.union = resolution.union(files) if resolution is not None else set(enabled)

    def enabled_for(self, file: str) -> Set[str]:
        if self.resolution is None:
            return self._enabled
        return self.resolution.group_of(file).enabled

    def explicit(self, code: str, file: str) -> bool:
        """Whether *code* is selected by name for *file* (E3(a))."""
        if self.resolution is None:
            return False
        return code in self.resolution.group_of(file).explicit


def for_run(config, files: Sequence[str]) -> Optional[RunSelection]:
    """The run's selection from *config*'s engine, or ``None`` when the
    configuration was not resolved against a registry."""
    engine = getattr(config, "lint_engine", None)
    if engine is None:
        return None
    res = Resolution.from_json(engine.resolve_selection(request(config, files)))
    sel = request(config)
    del sel["paths"]
    return RunSelection(res.lint_ids, res.groups[0].enabled, res, sel, files)
