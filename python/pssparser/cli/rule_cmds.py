"""Rule files on the command line: ``[lint] rules``, ``--rules`` and
``--check-rules`` (lint-core-plan C4.3; pss-rules-format §6.2-§6.3)."""
from __future__ import annotations

import sys
from typing import List, Optional, Sequence, TextIO

from pssparser.lint import rulefiles
from pssparser.lint.rulefiles import RuleLoad, RulePath

from .diagnostics import Diagnostic, DiagnosticCollection


def configured_paths(cfg) -> List[RulePath]:
    """``[lint] rules`` then ``--rules``, in order."""
    return [RulePath(path, origin) for path, origin in getattr(cfg, "lint_rules", [])]


def named_paths(paths: Sequence[str]) -> List[RulePath]:
    """The PATHs of ``--check-rules PATH...``, which replace the configured
    rule paths."""
    return [RulePath(p, "--check-rules") for p in paths]


def load_rules(entries: Sequence[RulePath], manager) -> RuleLoad:
    """The built-in rules, then *entries*, checked against *manager*'s
    registry.  Raises :class:`~pssparser.lint.rulefiles.RulePathError`."""
    return rulefiles.load(entries, manager.all_marker_defs(), manager.owner_of)


def report_problems(load: RuleLoad, stream: TextIO) -> None:
    """Rule-file diagnostics as plain lines, for the query flags
    (``--describe``, ``--explain``, ...), which build no diagnostic
    collection: a rule that failed to load is missing from their answer,
    and this says why."""
    for d in load.diagnostics:
        stream.write(f"{d['file']}:{d['line']}:{d['col']}: {d['severity']}: "
                     f"{d['message']}\n")


def report_skipped(load: RuleLoad, stream: TextIO) -> None:
    """The ``--verbose`` listing of directory entries that were not rule
    files, so a misspelt ``pss-rules`` key can be found."""
    for path, reason in load.skipped:
        stream.write(f"pssparser: skipped {path}: {reason}\n")


def example_markers(load: RuleLoad) -> List[dict]:
    """``PSSP222`` markers for the failing examples of the rules in
    *load*'s files: one per problem, at the example."""
    from pssparser.lint.examples import run_examples

    out = []
    for r in run_examples(load.engine, files=load.files, skip=load.refused):
        for p in r.problems:
            out.append({
                "severity": "error",
                "message": f"[PSSP222] example '{r.name}' of {r.rule}: {p}",
                "file": r.file,
                "line": r.line,
                "col": r.col,
                "code": "PSSP222",
                "extent": 0,
                "related": [],
            })
    return out


def cmd_check_rules(
    paths: Sequence[str],
    *,
    cfg,
    manager,
    output_format: str = "text",
    quiet: bool = False,
    color: Optional[bool] = None,
    verbose: bool = False,
    stderr: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
    load: Optional[RuleLoad] = None,
) -> int:
    """Load and validate rule files, and report their diagnostics.

    *paths* are checked when given; otherwise the configured ones
    (``[lint] rules`` and ``--rules``).  The built-in rules are always
    loaded first, so a site rule that takes a built-in rule's name is
    found.  Returns 0 when no rule file has an error, 1 when one does, and
    2 for a usage problem: nothing to check, or a path that does not exist.
    *load* is the rule files already loaded from those paths, when the
    caller has loaded them (the command line does, before checking its
    configuration against the registry).

    Each rule's ``examples:`` then run (lint-core-plan C5.5), for the
    rules in the files checked (not the built-in ones): a failing example
    is a ``PSSP222`` error at the example.
    """
    from .output import HumanOutput, JsonOutput
    from .source_context import SourceCache

    _stderr = stderr or sys.stderr
    _stdout = stdout or sys.stdout
    if paths:
        entries = named_paths(paths)
    else:
        entries = configured_paths(cfg)
    if not entries:
        _stderr.write(
            "error: --check-rules has no rule files to check: name files or "
            "directories, or set [lint] rules in the configuration\n")
        return 2
    if load is None:
        try:
            load = load_rules(entries, manager)
        except rulefiles.RulePathError as exc:
            _stderr.write(f"error: {exc}\n")
            return 2

    if verbose:
        report_skipped(load, _stderr)

    coll = DiagnosticCollection()
    coll.set_processed_files(load.files)
    for marker in load.diagnostics:
        coll.add(Diagnostic.from_marker(marker))
    for marker in example_markers(load):
        coll.add(Diagnostic.from_marker(marker))

    catalog = {md.id: md for md in manager.all_marker_defs()}
    if output_format == "json":
        driver = JsonOutput(stream=_stdout, catalog=catalog)
    elif output_format == "sarif":
        from .sarif import SarifOutput
        driver = SarifOutput(stream=_stdout, catalog=catalog, enabled_rules=[])
    elif output_format == "github":
        from .github import GithubOutput
        driver = GithubOutput(stream=_stdout)
    else:
        driver = HumanOutput(SourceCache(), stream=_stderr, color=color,
                             catalog=catalog)
    if not quiet:
        for diag in coll.diagnostics:
            driver.emit(diag)
    driver.finish(coll, quiet, None)
    if output_format == "text" and not quiet:
        mine = set(load.files)
        n = sum(1 for r in load.engine.rules()
                if r["file"] in mine and r["id"] not in load.refused)
        _stderr.write(f"pssparser: {n} rule{'s' if n != 1 else ''} loaded from "
                      f"{len(load.files)} file{'s' if len(load.files) != 1 else ''}\n")
    return 1 if coll.has_errors else 0


def rule_sources(load: RuleLoad) -> List[tuple]:
    """Every loaded rule file as ``(path, origin, rules)``, in load order:
    the built-in ones, then ``[lint] rules`` and ``--rules`` (B12)."""
    counts: dict = {}
    order: List[str] = []
    for r in load.engine.rules():
        if r["id"] in load.refused:
            continue
        if r["file"] not in counts:
            order.append(r["file"])
        counts[r["file"]] = counts.get(r["file"], 0) + 1
    for f in load.files:
        if f not in counts:
            order.append(f)
    out = []
    for f in order:
        origin = ("built-in" if f.startswith("pssparser:")
                  else load.origins.get(f, ""))
        out.append((f, origin, counts.get(f, 0)))
    return out


#: The ``--rules-for --format json`` schema name (B14 versions it).
RULES_FOR_SCHEMA = "pssparser-rules/1"


def _effective_severity(md, cfg) -> str:
    sev = (getattr(cfg, "severity", None) or {}).get(md.id)
    return sev or md.severity


def _rule_entry(md, cfg, options: dict, manager, detail: bool) -> dict:
    entry = {
        "id": md.id,
        "name": md.name,
        "severity": _effective_severity(md, cfg),
        "tier": md.tier,
        "family": md.family,
        "summary": md.summary,
        "source": md.source or manager.owner_of(md.id),
        "match": list(md.match),
    }
    if detail:
        entry["doc"] = md.detail
        values = {name: spec.get("default") for name, spec in (md.options_schema or {}).items()}
        values.update(options.get(md.id, {}))
        entry["options"] = values
        entry["examples"] = [{"code": ex.code, "fires": bool(ex.expect), "note": ex.note}
                             for ex in md.examples]
    return entry


def cmd_rules_for(paths: Sequence[str], *, cfg, manager, output_format: str = "text",
                  stdout: Optional[TextIO] = None) -> int:
    """``--rules-for FILE...`` (B12): the lint rules that would run on each
    FILE, after the configuration, its overrides and the command line.

    Selection depends on the path only, so no model is parsed and a FILE
    need not exist yet: an agent can ask before it writes one.  Text gives
    one line per rule; ``--format json`` adds each rule's doc, effective
    options and examples.
    """
    import json

    from pssparser.lint.selection import Resolution, request

    _stdout = stdout or sys.stdout
    res = Resolution.from_json(cfg.lint_engine.resolve_selection(request(cfg, paths)))
    by_id = {md.id: md for md in manager.all_marker_defs()}
    detail = output_format == "json"
    files = []
    for p in paths:
        g = res.group_of(p)
        options = {rid: dict(o) for rid, o in g.options.items()}
        # A Python checker's options come from the project table only.
        for name, opts in (cfg.lint_rule_options or {}).items():
            md = by_id.get(name) or next(
                (m for m in by_id.values() if m.name == name), None)
            if md is not None:
                options.setdefault(md.id, dict(opts))
        rules = [_rule_entry(by_id[i], cfg, options, manager, detail)
                 for i in sorted(g.enabled) if i in by_id
                 and (getattr(cfg, "severity", None) or {}).get(i) != "off"]
        files.append({"path": p, "rel": res.rel_of(p), "profile": g.profile,
                      "overrides": list(g.overrides), "rules": rules})
    if detail:
        _stdout.write(json.dumps({"schema": RULES_FOR_SCHEMA, "files": files}, indent=2)
                      + "\n")
        return 0
    for f in files:
        ovs = ", ".join(f"lint.overrides[{i}]" for i in f["overrides"]) or "no override"
        _stdout.write(f"{f['path']}: profile {f['profile']}, {ovs}, "
                      f"{len(f['rules'])} rule{'s' if len(f['rules']) != 1 else ''}\n")
        for r in f["rules"]:
            name = f" {r['name']}" if r["name"] else ""
            _stdout.write(f"  {r['id']}{name} [{r['severity']}] {r['summary']}"
                          f"  ({r['source']})\n")
    return 0
