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
    sev_w = max(
        len(m["status"] if m.get("status") in ("retired", "reserved")
            else m["severity"])
        for m in markers
    )
    checker_w = max(len(m["checker"]) for m in markers)
    id_w = max(id_w, 2)
    sev_w = max(sev_w, 3)
    checker_w = max(checker_w, 7)
    header = f"{'ID':<{id_w}}  {'SEV':<{sev_w}}  {'CHECKER':<{checker_w}}  SUMMARY"
    out.write(header + "\n")
    out.write("-" * len(header) + "\n")
    for m in markers:
        # A retired or reserved code is listed -- it is still a valid thing
        # to look up -- but its column says it is never reported.
        sev = m["severity"]
        if m.get("status") in ("retired", "reserved"):
            sev = m["status"]
        out.write(
            f"{m['id']:<{id_w}}  {sev:<{sev_w}}  "
            f"{m['checker']:<{checker_w}}  {m['summary']}\n"
        )
    return 0


def cmd_list_extensions(
    manager: CheckerManager,
    stdout: TextIO | None = None,
) -> int:
    """Print installed checker extensions and return exit code 0."""
    out = stdout or sys.stdout
    extensions = manager.list_extensions()
    if not extensions:
        out.write(
            "No checker extensions installed.\n"
            "Install one from PyPI to add rules; see 'Shipping a collection' "
            "in the checker plug-in guide to write your own.\n"
        )
        return 0

    out.write(f"Installed extensions ({len(extensions)}):\n")
    for info in extensions:
        version = f" {info['version']}" if info["version"] else ""
        # The distribution is what the user would `pip uninstall`, so it is
        # worth showing whenever it differs from the extension name.
        dist = ""
        if info["dist"] and info["dist"] != info["name"]:
            dist = f" [{info['dist']}]"
        legacy = " (single-checker entry point)" if info["legacy"] else ""
        if info.get("bundled"):
            legacy = " (bundled with pssparser)"
        out.write(f"  {info['name']}{version}{dist}{legacy}\n")
        out.write(f"    {info['description']}\n")
        names = ", ".join(info["checkers"]) if info["checkers"] else "(none)"
        out.write(f"    checkers: {names}\n")
    return 0


def cmd_describe_checker(
    manager: CheckerManager,
    name: str,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Print everything known about checker *name* and return exit code.

    The answer to "what can I configure here?" -- the options table with
    types, defaults, and choices -- has no other home: ``--list-checkers``
    is a one-line-per-checker summary and would be ruined by it.
    """
    from pssparser.checkers.manager import OPTION_TYPES  # noqa: F401
    from .suggestion import suggest

    out = stdout or sys.stdout
    err = stderr or sys.stderr

    cls = manager.registered.get(name)
    if cls is None:
        hint = suggest(name, sorted(manager.registered))
        detail = (
            f"did you mean '{hint}'?" if hint
            else "use --list-checkers to see what is installed"
        )
        err.write(f"error: unknown checker {name!r}; {detail}\n")
        return 2

    inst = cls()
    out.write(f"{name}\n")
    out.write(f"  {inst.description or '(no description)'}\n")

    ext = manager.extension_of(name)
    if ext:
        version = ""
        for info in manager.list_extensions():
            if info["name"] == ext:
                version = f" {info['version']}" if info["version"] else ""
                break
        out.write(f"\nProvided by: {ext}{version}\n")

    out.write("\nMarkers:\n")
    if inst.marker_defs:
        for md in inst.marker_defs:
            out.write(f"  {md.id:<10} [{md.severity}]  {md.summary}\n")
    else:
        out.write("  (none)\n")

    schema = getattr(cls, "options_schema", None) or {}
    out.write("\nOptions:\n")
    if not schema:
        out.write("  (none -- this checker takes no configuration)\n")
    else:
        for key in sorted(schema):
            spec = schema[key] or {}
            type_name = spec.get("type", "string")
            default = spec.get("default")
            rendered = _render_default(default)
            out.write(f"  {key:<16} {type_name:<12} default: {rendered}\n")
            if spec.get("help"):
                out.write(f"    {spec['help']}\n")
            if spec.get("choices"):
                choices = ", ".join(str(c) for c in spec["choices"])
                out.write(f"    one of: {choices}\n")
        out.write(
            f"\nSet these under [checker.{name}] in .pssparser.toml "
            f"(or [tool.pssparser.checker.{name}] in pyproject.toml).\n"
        )
    return 0


def _render_default(value) -> str:
    if value is None:
        return "(unset)"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[]" if not value else ", ".join(str(v) for v in value)
    return repr(value) if isinstance(value, str) else str(value)


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
    if info.get("status") in ("retired", "reserved"):
        state = info["status"]
        if info.get("replaced_by"):
            state += " -> " + ", ".join(info["replaced_by"])
        out.write(f"{info['id']}  [{state}]  checker: {info['checker']}\n")
    else:
        out.write(
            f"{info['id']}  [{info['severity']}]  checker: {info['checker']}\n"
        )
    out.write(f"{info['summary']}\n")
    facts = []
    if info.get("name"):
        facts.append(f"name: {info['name']}")
    if info.get("tier"):
        facts.append(f"tier: {info['tier']}")
    if info.get("family"):
        facts.append(f"family: {info['family']}")
    if info.get("aliases"):
        facts.append("formerly: " + ", ".join(info["aliases"]))
    if facts:
        out.write("  ".join(facts) + "\n")
    if info.get("detail"):
        out.write(f"\n{info['detail']}\n")
    return 0


def cmd_explain(
    manager: CheckerManager,
    selector: str,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Explain one rule, by ID, old ID or name (``--explain``).

    Where ``--describe`` prints the catalogue entry, this is written for the
    person deciding what to do about a finding: what the rule is for, where
    it sits (tier, family, default severity), the LRM clauses, the bad and
    good examples, its options, and whether it can fix the code.
    """
    from pssparser.checkers import taxonomy
    from .suggestion import suggest

    out = stdout or sys.stdout
    err = stderr or sys.stderr

    aliases = manager.alias_map()
    wanted = aliases.get(selector, selector)
    md = None
    for cand in manager.all_marker_defs():
        if cand.emittable and (cand.id == wanted or (cand.name and cand.name == wanted)):
            md = cand
            break
    if md is None:
        names = sorted(
            {c.id for c in manager.all_marker_defs() if c.emittable}
            | {c.name for c in manager.all_marker_defs() if c.name})
        hint = suggest(selector, names)
        detail = (f"did you mean '{hint}'?" if hint
                  else "use --list-markers to see the declared IDs")
        err.write(f"error: unknown rule {selector!r}; {detail}\n")
        return 2

    title = f"{md.id} {md.name}".rstrip()
    out.write(f"{title}\n{md.summary}\n\n")
    rows = []
    if md.tier:
        rows.append(("tier", md.tier))
    if md.family:
        rows.append(("family", md.family))
    if md.level:
        rows.append(("analysis level", md.level))
    rows.append(("default severity", md.severity))
    if md.since:
        rows.append(("since", md.since))
    if md.aliases:
        rows.append(("formerly", ", ".join(md.aliases)))
    if md.lrm:
        rows.append(("LRM", ", ".join(md.lrm)))
    rows.append(("fix", md.fix if md.fix != "none" else "none available"))
    if taxonomy.namespace_of(md.id) == "LINT":
        rows.append(("docs", taxonomy.doc_url(md.id)))
    for key, value in rows:
        out.write(f"  {key + ':':<18} {value}\n")
    if selector != md.id and selector in aliases:
        out.write(f"\n{selector} is the old ID of {md.id}; write {md.id}.\n")
    if md.detail:
        out.write(f"\n{md.detail}\n")
    for ex in md.examples:
        label = "Flagged" if ex.expect else "Not flagged"
        if ex.note:
            label += f" ({ex.note})"
        out.write(f"\n{label}:\n\n")
        out.write("".join(f"    {line}\n" for line in ex.code.splitlines()))
        if ex.fixed:
            out.write("\nAfter the fix:\n\n")
            out.write("".join(f"    {line}\n" for line in ex.fixed.splitlines()))
    if md.options_schema:
        out.write("\nOptions:\n")
        for key in sorted(md.options_schema):
            spec = md.options_schema[key] or {}
            out.write(f"  {key:<16} {spec.get('type', 'string'):<12} "
                      f"default: {_render_default(spec.get('default'))}\n")
            if spec.get("help"):
                out.write(f"    {spec['help']}\n")
        name = md.name or md.id
        out.write(f"\nSet these under [lint.rule.{name}].\n")
    return 0
