"""Configuration-file discovery, parsing, validation, and precedence.

A pssparser configuration lives either in a dedicated ``.pssparser.toml`` or
in a ``[tool.pssparser]`` table inside ``pyproject.toml``.  Both spellings
carry the same tree; the dedicated file simply omits the ``[tool.pssparser]``
prefix.

Two rules shape everything in this module:

**Nothing is silently ignored.**  An unrecognised key is an error with a
did-you-mean, not a shrug.  A table that is quietly dropped is a rule the
user believes is configured and is not -- which is the exact failure this
whole feature exists to prevent.

**Every resolved value remembers where it came from.**  With as many as four
layers able to set ``select``, the only supportable answer to "why did this
rule run?" is :func:`format_show_config`, and that needs provenance recorded
at the moment a value is chosen rather than reconstructed afterwards.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ``tomllib`` is stdlib from 3.11; ``setup.py`` declares a 3.10 floor, so the
# shim is required.  ``tomli`` is the upstream of ``tomllib`` itself, so the
# parse behaviour is identical on both branches -- this is the only import
# site, and ``tests/python/cli/test_config.py`` pins that.
try:  # pragma: no cover - exercised on exactly one branch per interpreter
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        # Declared in install_requires, so this is only reachable in a
        # hand-assembled 3.10 environment.  Degrade to "no TOML parser"
        # rather than breaking `import pssparser.cli.app` outright: a user
        # who never writes a config file should not be stopped by a
        # dependency they do not use.  _no_parser() turns the first actual
        # parse into an actionable message instead of an ImportError
        # traceback from somewhere in argparse setup.
        tomllib = None  # type: ignore[assignment]

from .suggestion import suggest

#: Name of the dedicated configuration file looked for by the upward search.
CONFIG_FILENAME = ".pssparser.toml"

#: The table ``pyproject.toml`` carries a pssparser configuration under.
PYPROJECT_FILENAME = "pyproject.toml"
PYPROJECT_TABLE = ("tool", "pssparser")

#: Severities a ``[severity]`` entry may name.  ``"off"`` is config-only --
#: it is not a severity a diagnostic can carry, it means "drop it".
VALID_SEVERITIES = ("error", "warning", "info", "hint", "off")

#: The current configuration schema version.  Present so that a future
#: incompatible change has somewhere to announce itself; adding this later is
#: impossible to do cleanly, which is the whole reason it is here now.
SCHEMA_VERSION = 1


class ConfigError(Exception):
    """A configuration file is missing, unparseable, or invalid.

    Always a usage error (exit 2).  The message is user-facing and names the
    file and the offending key.
    """


_NO_TOML_PARSER = (
    "no TOML parser available: this interpreter predates 'tomllib' (3.11) "
    "and 'tomli' is not installed. Run 'pip install tomli', or pass "
    "--no-config to run without a configuration file"
)

#: ``TOMLDecodeError`` subclasses ``ValueError``, so this is a safe catch
#: target even on the branch where no parser could be imported at all.
_TOMLDecodeError = (
    tomllib.TOMLDecodeError if tomllib is not None else ValueError
)


def _toml_load(stream) -> Dict[str, Any]:
    if tomllib is None:
        raise ConfigError(_NO_TOML_PARSER)
    return tomllib.load(stream)


# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------
#
# Declared as data so that validation, the did-you-mean candidate set, and
# --show-config all read from one table.  A key added here is automatically
# accepted, suggested, and displayed.

#: Root keys and their expected TOML type, as (python type, description).
_ROOT_SCHEMA: Dict[str, Tuple[type, str]] = {
    "version": (int, "configuration schema version"),
    "select": (list, "array of checker names"),
    "disable": (list, "array of checker names"),
    "load": (list, "array of 'module:Class' specs"),
    "severity": (dict, "table of marker ID to severity"),
    "warnings": (dict, "warning-policy table"),
    "checker": (dict, "table of per-checker option tables"),
    "extensions": (dict, "table of per-extension tables"),
}

_WARNINGS_SCHEMA: Dict[str, Tuple[tuple, str]] = {
    "error": ((bool, list), "true for -Werror, or an array of IDs"),
    "no-error": ((list,), "array of IDs exempt from -Werror"),
    "none": ((bool,), "true for --no-warnings"),
}

_EXTENSION_SCHEMA: Dict[str, Tuple[tuple, str]] = {
    "enabled": ((bool,), "false to skip this extension's checkers"),
}

#: Plural spellings users reach for first.  TOML forbids a key from being
#: both an array and a table, so ``checkers = [...]`` and
#: ``[checkers.naming-convention]`` cannot coexist in one document -- which
#: is exactly why the list keys and the per-checker table have different
#: names.  That asymmetry is invisible until you trip over it, so these get a
#: dedicated explanation rather than a bare did-you-mean.
_PLURAL_TRAPS = {
    "checkers": (
        "use 'select'/'disable'/'load' for lists of checker names, and the "
        "singular '[checker.<name>]' table for one checker's options.\n"
        "  TOML forbids a key from being both an array and a table, so "
        "'checkers = [...]' and '[checkers.<name>]' cannot coexist in one "
        "file; the two names are what keep both spellings available."
    ),
    "extension": (
        "per-extension settings live under the plural '[extensions.<name>]'."
    ),
    "severities": ("use the singular '[severity]' table."),
    "warning": ("use the plural '[warnings]' table."),
}


# ----------------------------------------------------------------------
# Resolved configuration
# ----------------------------------------------------------------------


@dataclass
class ResolvedConfig:
    """A fully resolved configuration, with provenance for every value.

    Instances are built by :func:`resolve` and are read-only by convention.
    ``provenance`` maps a dotted display key (``"select"``,
    ``"severity.PSS114"``, ``"checker.naming-convention.style"``) to a human
    string naming where the winning value came from.
    """

    select: Optional[List[str]] = None
    disable: List[str] = field(default_factory=list)
    load: List[str] = field(default_factory=list)
    severity: Dict[str, str] = field(default_factory=dict)
    checker_options: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    extensions_enabled: Dict[str, bool] = field(default_factory=dict)

    warnings_error_all: bool = False
    warnings_error_codes: List[str] = field(default_factory=list)
    warnings_no_error_codes: List[str] = field(default_factory=list)
    no_warnings: bool = False

    #: Files that contributed, lowest-precedence first, as display paths.
    sources: List[str] = field(default_factory=list)
    provenance: Dict[str, str] = field(default_factory=dict)

    #: Keys a config file set that a CLI flag then overrode -- the PSS034
    #: population.  Display keys, sorted.
    overridden: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when no file contributed anything (the no-config case)."""
        return not self.sources


# ----------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------


def _display_path(path: Path) -> str:
    """Render *path* relative to CWD so output is machine-independent."""
    try:
        rel = os.path.relpath(path, Path.cwd())
    except ValueError:
        # Different drive on Windows; an absolute path is the honest answer.
        return str(path)
    # Do not let a relative path climb more than a couple of levels before
    # an absolute one becomes the more readable rendering.
    if rel.startswith(".." + os.sep + ".." + os.sep):
        return str(path)
    return rel


def _pyproject_has_section(path: Path) -> bool:
    """True when *path* parses and carries a ``[tool.pssparser]`` table.

    A ``pyproject.toml`` that does not mention pssparser must not stop the
    upward search -- almost every Python project has one, and stopping there
    would make a repo-root config unreachable from a subdirectory.  A
    ``pyproject.toml`` that does not parse must not stop it either, and must
    not raise: it belongs to some other tool, and pssparser is not entitled
    to fail a run over it.  ``--config`` is the path where a parse error is
    the user's problem and is reported.
    """
    try:
        with path.open("rb") as f:
            data = _toml_load(f)
    except (OSError, _TOMLDecodeError, ConfigError):
        return False
    node: Any = data
    for part in PYPROJECT_TABLE:
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return isinstance(node, dict)


def discover_config_files(start: Optional[Path] = None) -> List[Path]:
    """Search upward from *start* (default CWD) for configuration files.

    Returns the files found in the first directory that carries a pssparser
    configuration, ordered lowest-precedence first -- so ``pyproject.toml``
    before ``.pssparser.toml`` when a directory has both.  Returns ``[]``
    when nothing is found.

    The walk stops at the first directory that carries a configuration, at a
    directory containing ``.git``, or at the filesystem root.  It starts at
    the working directory rather than at the first source file's directory,
    which is what every other linter does and what stops
    ``pssparser a/x.pss b/y.pss`` from silently resolving two configs.
    """
    here = (start or Path.cwd()).resolve()
    for directory in [here, *here.parents]:
        found: List[Path] = []
        pyproject = directory / PYPROJECT_FILENAME
        if pyproject.is_file() and _pyproject_has_section(pyproject):
            found.append(pyproject)
        dedicated = directory / CONFIG_FILENAME
        if dedicated.is_file():
            found.append(dedicated)
        if found:
            return found
        if (directory / ".git").exists():
            # A repository boundary: a config above it belongs to some other
            # project that happens to be an ancestor on disk.
            break
    return []


# ----------------------------------------------------------------------
# Parsing and validation
# ----------------------------------------------------------------------


def _type_name(t: Any) -> str:
    names = {
        bool: "a boolean", int: "an integer", str: "a string",
        list: "an array", dict: "a table", float: "a float",
    }
    if isinstance(t, tuple):
        return " or ".join(names.get(x, x.__name__) for x in t)
    return names.get(t, getattr(t, "__name__", str(t)))


def _describe(value: Any) -> str:
    return _type_name(type(value))


def _unknown_key(where: str, key: str, candidates, source: str) -> ConfigError:
    """Build the error for an unrecognised key, with a did-you-mean."""
    trap = _PLURAL_TRAPS.get(key)
    if trap:
        return ConfigError(f"{source}: unknown key '{key}' in {where}; {trap}")
    hint = suggest(key, list(candidates))
    detail = f"did you mean '{hint}'?" if hint else (
        "known keys: " + ", ".join(sorted(candidates))
    )
    return ConfigError(f"{source}: unknown key '{key}' in {where}; {detail}")


def _require_str_list(value: Any, key: str, source: str) -> List[str]:
    if not isinstance(value, list):
        raise ConfigError(
            f"{source}: '{key}' must be an array of strings, "
            f"got {_describe(value)}"
        )
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(
                f"{source}: every entry in '{key}' must be a string, "
                f"got {_describe(item)}"
            )
    return list(value)


def _validate_table(data: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Validate one pssparser table and return it normalised.

    Raises :class:`ConfigError` on any unknown key or type mismatch.  The
    values are *not* checked against the checker registry here -- an unknown
    marker ID or checker name needs a populated ``CheckerManager``, which is
    :func:`validate_against_registry`'s job.
    """
    if not isinstance(data, dict):
        raise ConfigError(
            f"{source}: the pssparser configuration must be a table, "
            f"got {_describe(data)}"
        )

    for key, value in data.items():
        if key not in _ROOT_SCHEMA:
            raise _unknown_key(
                "the pssparser configuration", key, _ROOT_SCHEMA, source
            )
        expected, _ = _ROOT_SCHEMA[key]
        # bool is a subclass of int, so an `int` slot would silently accept
        # `version = true`.
        if expected is int and isinstance(value, bool):
            raise ConfigError(
                f"{source}: '{key}' must be {_type_name(expected)}, "
                f"got {_describe(value)}"
            )
        if not isinstance(value, expected):
            raise ConfigError(
                f"{source}: '{key}' must be {_type_name(expected)}, "
                f"got {_describe(value)}"
            )

    version = data.get("version")
    if version is not None and version > SCHEMA_VERSION:
        raise ConfigError(
            f"{source}: configuration declares version {version}, but this "
            f"pssparser understands version {SCHEMA_VERSION}; "
            "upgrade pssparser or lower the 'version' key"
        )

    for key in ("select", "disable", "load"):
        if key in data:
            _require_str_list(data[key], key, source)

    _validate_severity(data.get("severity"), source)
    _validate_warnings(data.get("warnings"), source)
    _validate_checker(data.get("checker"), source)
    _validate_extensions(data.get("extensions"), source)

    return data


def _validate_severity(table: Any, source: str) -> None:
    if table is None:
        return
    for code, sev in table.items():
        if isinstance(sev, dict):
            raise ConfigError(
                f"{source}: '[severity.{code}]' is a table; severity entries "
                f"are plain values, e.g. {code} = \"warning\""
            )
        if not isinstance(sev, str) or sev not in VALID_SEVERITIES:
            raise ConfigError(
                f"{source}: severity for '{code}' must be one of "
                f"{', '.join(VALID_SEVERITIES)}; got {sev!r}"
            )


def _validate_warnings(table: Any, source: str) -> None:
    if table is None:
        return
    for key, value in table.items():
        if key not in _WARNINGS_SCHEMA:
            raise _unknown_key(
                "[warnings]", key, _WARNINGS_SCHEMA, source
            )
        expected, _ = _WARNINGS_SCHEMA[key]
        if not isinstance(value, expected):
            raise ConfigError(
                f"{source}: 'warnings.{key}' must be "
                f"{_type_name(expected)}, got {_describe(value)}"
            )
    if isinstance(table.get("error"), list):
        _require_str_list(table["error"], "warnings.error", source)
    if "no-error" in table:
        _require_str_list(table["no-error"], "warnings.no-error", source)


def _validate_checker(table: Any, source: str) -> None:
    if table is None:
        return
    for name, options in table.items():
        if not isinstance(options, dict):
            raise ConfigError(
                f"{source}: '[checker.{name}]' must be a table of options, "
                f"got {_describe(options)}"
            )


def _validate_extensions(table: Any, source: str) -> None:
    if table is None:
        return
    for name, settings in table.items():
        if not isinstance(settings, dict):
            raise ConfigError(
                f"{source}: '[extensions.{name}]' must be a table, "
                f"got {_describe(settings)}"
            )
        for key, value in settings.items():
            if key not in _EXTENSION_SCHEMA:
                raise _unknown_key(
                    f"[extensions.{name}]", key, _EXTENSION_SCHEMA, source
                )
            expected, _ = _EXTENSION_SCHEMA[key]
            if not isinstance(value, expected):
                raise ConfigError(
                    f"{source}: 'extensions.{name}.{key}' must be "
                    f"{_type_name(expected)}, got {_describe(value)}"
                )


def load_config_file(path: Path, *, required: bool = False) -> Tuple[Dict[str, Any], str]:
    """Read and validate one configuration file.

    Returns ``(table, display_path)``.  For ``pyproject.toml`` the table is
    the contents of ``[tool.pssparser]``; for a dedicated file it is the
    whole document.

    ``required`` marks a path the user named explicitly (``--config``), for
    which a missing file or a TOML syntax error is an error rather than a
    reason to move on.
    """
    display = _display_path(path)
    is_pyproject = path.name == PYPROJECT_FILENAME

    try:
        with path.open("rb") as f:
            data = _toml_load(f)
    except FileNotFoundError:
        if required:
            raise ConfigError(f"config file not found: {display}") from None
        return {}, display
    except OSError as exc:
        raise ConfigError(f"{display}: cannot read config file: {exc}") from None
    except _TOMLDecodeError as exc:
        if required or not is_pyproject:
            raise ConfigError(f"{display}: invalid TOML: {exc}") from None
        return {}, display

    if is_pyproject:
        node: Any = data
        for part in PYPROJECT_TABLE:
            if not isinstance(node, dict) or part not in node:
                if required:
                    raise ConfigError(
                        f"{display}: no [tool.pssparser] table "
                        "(use a .pssparser.toml, or add the table)"
                    )
                return {}, display
            node = node[part]
        data = node
        display = f"{display} [tool.pssparser]"

    return _validate_table(data, display), display


# ----------------------------------------------------------------------
# Precedence
# ----------------------------------------------------------------------


def _merge(cfg: ResolvedConfig, table: Dict[str, Any], source: str) -> None:
    """Fold one file's table into *cfg*, overwriting lower layers.

    Scalars and arrays replace wholesale -- an array that merged would give
    no way to *shrink* a list set by a lower layer.  Tables merge per entry,
    so a narrow ``[severity]`` override does not discard the rest.
    """
    if "select" in table:
        cfg.select = list(table["select"])
        cfg.provenance["select"] = source
    for key, attr in (("disable", "disable"), ("load", "load")):
        if key in table:
            setattr(cfg, attr, list(table[key]))
            cfg.provenance[key] = source

    for code, sev in (table.get("severity") or {}).items():
        cfg.severity[code] = sev
        cfg.provenance[f"severity.{code}"] = source

    warnings = table.get("warnings") or {}
    if "error" in warnings:
        err = warnings["error"]
        if isinstance(err, bool):
            cfg.warnings_error_all = err
            cfg.warnings_error_codes = []
        else:
            cfg.warnings_error_all = False
            cfg.warnings_error_codes = list(err)
        cfg.provenance["warnings.error"] = source
    if "no-error" in warnings:
        cfg.warnings_no_error_codes = list(warnings["no-error"])
        cfg.provenance["warnings.no-error"] = source
    if "none" in warnings:
        cfg.no_warnings = warnings["none"]
        cfg.provenance["warnings.none"] = source

    for name, options in (table.get("checker") or {}).items():
        bucket = cfg.checker_options.setdefault(name, {})
        for opt, value in options.items():
            bucket[opt] = value
            cfg.provenance[f"checker.{name}.{opt}"] = source

    for name, settings in (table.get("extensions") or {}).items():
        if "enabled" in settings:
            cfg.extensions_enabled[name] = settings["enabled"]
            cfg.provenance[f"extensions.{name}.enabled"] = source

    if source not in cfg.sources:
        cfg.sources.append(source)


def resolve(
    args,
    *,
    start: Optional[Path] = None,
) -> ResolvedConfig:
    """Build the fully resolved configuration for this run.

    Precedence, lowest first: ``pyproject.toml``, ``.pssparser.toml``,
    ``--config PATH``, command-line flags.  ``--config`` *replaces*
    discovery rather than layering on top of it: a named config file is the
    authoritative answer to "which rules run", and having a stray
    ``.pssparser.toml`` two directories up still contribute would defeat the
    point of naming one.

    Raises :class:`ConfigError` for anything the user must fix.
    """
    cfg = ResolvedConfig()

    if not getattr(args, "no_config", False):
        explicit = getattr(args, "config", None)
        if explicit:
            table, display = load_config_file(Path(explicit), required=True)
            _merge(cfg, table, display)
        else:
            for path in discover_config_files(start):
                table, display = load_config_file(path)
                if table:
                    _merge(cfg, table, display)

    _apply_cli_overrides(cfg, args)
    return cfg


def _apply_cli_overrides(cfg: ResolvedConfig, args) -> None:
    """Let command-line flags win, recording what they displaced.

    A flag that was not given must not overwrite a configured value with its
    argparse default -- which is why every overridable flag defaults to
    ``None``/``False`` and is tested for presence rather than for truth.
    """
    overridden: List[str] = []

    def take(key: str, value, attr: str) -> None:
        if value is None:
            return
        if key in cfg.provenance:
            overridden.append(key)
        setattr(cfg, attr, value)
        cfg.provenance[key] = "command line"

    take("select", getattr(args, "checkers", None), "select")
    take("disable", getattr(args, "no_checkers", None), "disable")
    take("load", getattr(args, "load_checkers", None), "load")

    policy = getattr(args, "warning_policy", None)
    if policy is not None:
        if policy.error_all or policy.error_codes:
            if "warnings.error" in cfg.provenance:
                overridden.append("warnings.error")
            cfg.warnings_error_all = policy.error_all
            cfg.warnings_error_codes = sorted(policy.error_codes)
            cfg.provenance["warnings.error"] = "command line"
        if policy.no_error_codes:
            if "warnings.no-error" in cfg.provenance:
                overridden.append("warnings.no-error")
            cfg.warnings_no_error_codes = sorted(policy.no_error_codes)
            cfg.provenance["warnings.no-error"] = "command line"

    if getattr(args, "no_warnings", False):
        if "warnings.none" in cfg.provenance:
            overridden.append("warnings.none")
        cfg.no_warnings = True
        cfg.provenance["warnings.none"] = "command line"

    if getattr(args, "no_extensions", False):
        # --no-extensions is not an override of any single key; it turns the
        # whole extension layer off upstream, in discover().  Recording it
        # here keeps --show-config honest about why an [extensions.x] entry
        # had no effect.
        for name in cfg.extensions_enabled:
            overridden.append(f"extensions.{name}.enabled")

    cfg.overridden = sorted(set(overridden))


def to_warning_policy(cfg: ResolvedConfig, policy) -> None:
    """Write *cfg*'s warning settings onto an existing ``WarningPolicy``.

    The policy object is built by argparse's ``-W`` action, so it already
    holds the command-line values; this fills in whatever the config layer
    resolved, which -- because ``_apply_cli_overrides`` already ran -- is the
    winning value either way.
    """
    policy.error_all = cfg.warnings_error_all
    policy.error_codes = set(cfg.warnings_error_codes)
    policy.no_error_codes = set(cfg.warnings_no_error_codes)
    policy.no_warnings = cfg.no_warnings


# ----------------------------------------------------------------------
# Registry-dependent validation
# ----------------------------------------------------------------------


def validate_against_registry(cfg: ResolvedConfig, manager) -> None:
    """Check names in *cfg* against the checkers and markers actually loaded.

    Split from :func:`_validate_table` because it needs a populated
    ``CheckerManager``, which does not exist until extensions have been
    discovered.  Everything here is fail-fast: a config naming a checker that
    is not installed stops the run.  The cost is real -- a config listing a
    locally-installed extension fails in a CI job that lacks it -- and it is
    deliberate.  A rule silently not running is the failure mode this feature
    exists to prevent, and a hard stop names the missing checker where a
    warning gets lost in the diagnostic stream.
    """
    known_checkers = set(manager.registered)
    all_markers = manager.list_all_markers()
    known_markers = {md["id"] for md in all_markers}
    core_errors = {
        md["id"] for md in all_markers
        if md["checker"] == "core" and md["severity"] == "error"
    }

    for name in cfg.select or []:
        if name not in known_checkers:
            source = cfg.provenance.get("select", "configuration")
            hint = suggest(name, sorted(known_checkers))
            detail = f"did you mean '{hint}'?" if hint else (
                "run --list-checkers to see what is installed"
            )
            raise ConfigError(
                f"{source}: 'select' names checker '{name}', which is not "
                f"installed; {detail}"
            )

    for name in cfg.checker_options:
        if name not in known_checkers:
            source = cfg.provenance.get(
                f"checker.{name}." + next(iter(cfg.checker_options[name]), ""),
                "configuration",
            )
            hint = suggest(name, sorted(known_checkers))
            detail = f"did you mean '{hint}'?" if hint else (
                "run --list-checkers to see what is installed"
            )
            raise ConfigError(
                f"{source}: '[checker.{name}]' configures a checker that is "
                f"not installed; {detail}"
            )

    known_extensions = {info["name"] for info in manager.list_extensions()}
    for name, enabled in cfg.extensions_enabled.items():
        if name in known_extensions:
            continue
        # `enabled = false` on an absent extension is already satisfied --
        # nothing it contributes is running.  `enabled = true` is a request
        # for rules that will not run, which is precisely what fail-fast is
        # for.  The asymmetry is deliberate: it lets one config file serve a
        # developer machine that has an optional extension and a CI image
        # that does not.
        if not enabled:
            continue
        source = cfg.provenance.get(f"extensions.{name}.enabled", "configuration")
        hint = suggest(name, sorted(known_extensions))
        detail = f"did you mean '{hint}'?" if hint else (
            "run --list-extensions to see what is installed"
        )
        raise ConfigError(
            f"{source}: '[extensions.{name}]' enables an extension that is "
            f"not installed; {detail}"
        )

    for code in cfg.severity:
        if code not in known_markers:
            source = cfg.provenance.get(f"severity.{code}", "configuration")
            hint = suggest(code, sorted(known_markers))
            detail = f"did you mean '{hint}'?" if hint else (
                "run --list-markers to see the declared IDs"
            )
            raise ConfigError(
                f"{source}: '[severity]' names unknown marker '{code}'; "
                f"{detail}"
            )

    # A core error is a statement that the model could not be built.  The
    # parse- and link-failure paths return a forced exit code of 1 with no
    # linked AST; letting a config file downgrade those diagnostics would
    # produce a run that reports success while having compiled nothing.  The
    # restriction is what keeps that forced exit code honest, so it is
    # checked here -- at config-load time, where the message can name the
    # key -- rather than ignored later at diagnostic time.
    for code, sev in cfg.severity.items():
        if code in core_errors and sev != "error":
            source = cfg.provenance.get(f"severity.{code}", "configuration")
            raise ConfigError(
                f"{source}: '{code}' is a core error and cannot be set to "
                f"'{sev}'. A core error means the model could not be built, "
                f"so silencing it would report success for a run that "
                f"produced nothing. Use --no-warnings or a narrower "
                f"'select' if the goal is a quieter report"
            )


# ----------------------------------------------------------------------
# --show-config
# ----------------------------------------------------------------------


def format_show_config(cfg: ResolvedConfig) -> str:
    """Render the resolved configuration with per-value provenance.

    Every value that is in effect appears here with the layer that set it,
    including values nothing set -- ``(default)`` is an answer to "why did
    this rule run?" just as much as a file path is.
    """
    lines: List[str] = []

    if cfg.sources:
        lines.append("Configuration files (lowest precedence first):")
        for src in cfg.sources:
            lines.append(f"  {src}")
    else:
        lines.append("Configuration files: none found")
    lines.append("")

    def prov(key: str) -> str:
        return cfg.provenance.get(key, "(default)")

    def row(key: str, value: str) -> None:
        lines.append(f"  {key:<34} {value:<24} {prov(key)}")

    lines.append("Resolved values:")
    lines.append(f"  {'key':<34} {'value':<24} source")
    row("select", "(all)" if cfg.select is None else ", ".join(cfg.select) or "(none)")
    row("disable", ", ".join(cfg.disable) or "(none)")
    row("load", ", ".join(cfg.load) or "(none)")

    if cfg.warnings_error_codes:
        row("warnings.error", ", ".join(cfg.warnings_error_codes))
    else:
        row("warnings.error", "true" if cfg.warnings_error_all else "false")
    row("warnings.no-error", ", ".join(cfg.warnings_no_error_codes) or "(none)")
    row("warnings.none", "true" if cfg.no_warnings else "false")

    if cfg.severity:
        lines.append("")
        lines.append("Severity overrides:")
        for code in sorted(cfg.severity):
            row(f"severity.{code}", cfg.severity[code])

    if cfg.checker_options:
        lines.append("")
        lines.append("Checker options:")
        for name in sorted(cfg.checker_options):
            for opt in sorted(cfg.checker_options[name]):
                key = f"checker.{name}.{opt}"
                row(key, _render(cfg.checker_options[name][opt]))

    if cfg.extensions_enabled:
        lines.append("")
        lines.append("Extensions:")
        for name in sorted(cfg.extensions_enabled):
            key = f"extensions.{name}.enabled"
            row(key, "true" if cfg.extensions_enabled[name] else "false")

    if cfg.overridden:
        lines.append("")
        lines.append("Overridden by command-line flags:")
        for key in cfg.overridden:
            lines.append(f"  {key}")

    return "\n".join(lines) + "\n"


def _render(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "(none)"
    return str(value)
