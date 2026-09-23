"""CheckerManager: discovery, filtering, loading, and invocation of checkers."""
from __future__ import annotations

import importlib
import inspect
import os
from typing import Dict, List, Optional, Type

from pssparser.cli.suggestion import suggest

from .base import CheckerBase
from .extension import (
    API_VERSION,
    NO_FILE,
    ExtensionError,
    ExtensionInfo,
    ExtensionIssue,
    ExtensionRegistry,
    make_registry,
)

#: Entry-point group for an extension contributing a *collection* of checkers.
EXTENSION_GROUP = "pssparser.extensions"

#: Legacy entry-point group: one entry point per checker class.  Still
#: supported; adapted into a synthetic single-checker extension on load.
CHECKER_GROUP = "pssparser.checkers"

#: Environment escape hatch, equivalent to ``--no-extensions``.  Set it to
#: make a run reproducible, or to find out whether an installed extension is
#: responsible for a behaviour you did not expect.
NO_EXTENSIONS_ENV = "PSSPARSER_NO_EXTENSIONS"


def _entry_points(group: str) -> list:
    """Return entry points in *group*, or ``[]`` if they cannot be read.

    Entry-point enumeration touches installed metadata on disk, which can be
    malformed in ways that have nothing to do with pssparser.  A broken
    environment must degrade to "no extensions", never to a traceback.
    """
    try:
        from importlib.metadata import entry_points
        return list(entry_points(group=group))
    except Exception:
        return []


def _ep_dist(ep) -> Optional[str]:
    """Best-effort distribution name for *ep*, or ``None``.

    ``EntryPoint.dist`` is populated when the entry point came from installed
    metadata and absent when it was synthesized (notably in tests), so every
    access is defensive.
    """
    try:
        dist = getattr(ep, "dist", None)
        if dist is None:
            return None
        name = getattr(dist, "name", None)
        return name if isinstance(name, str) else None
    except Exception:
        return None


def _ep_version(ep) -> str:
    """Best-effort distribution version for *ep*, or ``""``."""
    try:
        dist = getattr(ep, "dist", None)
        if dist is None:
            return ""
        version = getattr(dist, "version", None)
        return version if isinstance(version, str) else ""
    except Exception:
        return ""


def _origin(ext_name: str, dist: Optional[str]) -> str:
    """Render ``name`` or ``name (from dist)`` for a diagnostic message."""
    return f"{ext_name!r} (from {dist})" if dist else f"{ext_name!r}"


#: ``options_schema`` type names and the Python types they accept.
OPTION_TYPES = {
    "string": (str,),
    "int": (int,),
    "bool": (bool,),
    "string-list": (list,),
}


def _type_ok(value, type_name: str) -> bool:
    accepted = OPTION_TYPES.get(type_name)
    if accepted is None:
        return True  # unknown declared type -- reported separately
    # ``bool`` is a subclass of ``int``, so an int slot would otherwise
    # silently accept ``true``.
    if type_name == "int" and isinstance(value, bool):
        return False
    if not isinstance(value, accepted):
        return False
    if type_name == "string-list":
        return all(isinstance(v, str) for v in value)
    return True


def resolve_options(checker: CheckerBase, user_options: Optional[dict]):
    """Validate *user_options* against *checker*'s schema and fill defaults.

    Returns the complete option table to hand to ``configure()``, or
    ``None`` when the checker declares no options and the user supplied
    none -- in which case ``configure()`` is not called at all, so a checker
    written before options existed behaves exactly as it did.

    Validation runs at startup, before any source file is read, so a typo in
    a config file fails immediately rather than after a long parse.

    Raises
    ------
    ValueError
        Unknown option, wrong type, value outside ``choices``, or options
        supplied to a checker that declares none.
    """
    schema = getattr(type(checker), "options_schema", None) or {}
    user = user_options or {}

    if not schema:
        if user:
            raise ValueError(
                f"checker {checker.name!r} accepts no options, but "
                f"[checker.{checker.name}] sets "
                f"{', '.join(repr(k) for k in sorted(user))}"
            )
        return None

    for key, value in user.items():
        if key not in schema:
            hint = suggest(key, sorted(schema))
            detail = (
                f"did you mean '{hint}'?" if hint
                else "known options: " + ", ".join(sorted(schema))
            )
            raise ValueError(
                f"checker {checker.name!r} has no option {key!r}; {detail}"
            )
        spec = schema[key] or {}
        type_name = spec.get("type", "string")
        if not _type_ok(value, type_name):
            raise ValueError(
                f"checker {checker.name!r}: option {key!r} must be of type "
                f"{type_name}, got {type(value).__name__}"
            )
        choices = spec.get("choices")
        if choices and value not in choices:
            raise ValueError(
                f"checker {checker.name!r}: option {key!r} must be one of "
                f"{', '.join(repr(c) for c in choices)}; got {value!r}"
            )

    resolved = {}
    for key, spec in schema.items():
        spec = spec or {}
        if key in user:
            resolved[key] = user[key]
        else:
            default = spec.get("default")
            # Copy mutable defaults so one checker instance cannot mutate
            # the class-level schema and leak into the next run.
            resolved[key] = list(default) if isinstance(default, list) else default
    return resolved


class CheckerManager:
    """Manages discovery, filtering, and invocation of checker plug-ins.

    Typical usage::

        manager = CheckerManager()
        manager.discover()                        # load entry_points
        manager.load("mypkg.rules:MyChecker")     # optional: ad-hoc load
        checkers = manager.active(select=None, exclude=["some-checker"])

    Discovery never raises.  Anything that goes wrong while loading a
    third-party extension is recorded as an issue (see
    :attr:`load_diagnostics`) and the remaining extensions still load; the
    caller decides how to surface it.  That asymmetry with :meth:`load` is
    deliberate: ``--load-checker`` is something the user typed and should fail
    fast, while an installed extension is code the user did not write and
    cannot easily debug.
    """

    def __init__(self) -> None:
        self._registered: Dict[str, Type[CheckerBase]] = {}
        #: extension name -> ExtensionInfo, for successfully-loaded extensions
        self._extensions: Dict[str, ExtensionInfo] = {}
        #: checker name -> extension name that contributed it
        self._provenance: Dict[str, str] = {}
        #: marker ID -> human-readable owner, for duplicate reporting
        self._marker_owner: Dict[str, str] = {}
        #: problems found during discovery
        self._issues: List[ExtensionIssue] = []

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self, load_extensions: bool = True) -> None:
        """Register ``CoreChecker``, then every installed extension.

        Extensions load in sorted order by extension name -- not in
        ``importlib.metadata`` order, which varies by machine -- so duplicate
        reports and ``--list-*`` output are reproducible.

        Parameters
        ----------
        load_extensions:
            ``False`` registers ``CoreChecker`` and nothing else, the
            ``--no-extensions`` behaviour.  The ``PSSPARSER_NO_EXTENSIONS``
            environment variable forces this too.

        Idempotent with respect to ``CoreChecker``; calling it twice will not
        re-register an extension already present.
        """
        from .core_checker import CoreChecker

        if "core" not in self._registered:
            self._registered["core"] = CoreChecker
            self._provenance["core"] = "(built-in)"
            for md in CoreChecker.marker_defs:
                self._marker_owner.setdefault(md.id, "checker 'core'")

        if not load_extensions or os.environ.get(NO_EXTENSIONS_ENV):
            return

        eps = [(ep.name, ep, False) for ep in _entry_points(EXTENSION_GROUP)]
        eps += [(ep.name, ep, True) for ep in _entry_points(CHECKER_GROUP)]
        # Sort by entry-point name so the load order -- and therefore which
        # side of a duplicate-ID collision is reported as the loser -- does not
        # depend on filesystem or metadata ordering.
        eps.sort(key=lambda item: item[0])

        for ep_name, ep, is_legacy in eps:
            if ep_name in self._extensions:
                continue
            if is_legacy:
                self._load_legacy_checker_ep(ep_name, ep)
            else:
                self._load_extension_ep(ep_name, ep)

    # -- extension loading ---------------------------------------------

    def _load_extension_ep(self, ep_name: str, ep) -> None:
        """Load one ``pssparser.extensions`` entry point."""
        dist = _ep_dist(ep)
        try:
            obj = ep.load()
        except Exception as exc:
            self._issue(
                "PSS030",
                "warning",
                f"extension {_origin(ep_name, dist)} failed to import: "
                f"{type(exc).__name__}: {exc}",
            )
            return

        register, module = self._resolve_register(obj)
        if register is None:
            self._issue(
                "PSS030",
                "warning",
                f"extension {_origin(ep_name, dist)} exposes neither a "
                f"register(registry) function nor a CHECKERS list; one of the "
                f"two is required",
            )
            return

        # A module-level REQUIRES_API lets an extension refuse *before* its
        # register() runs, which is the only point at which refusing is free
        # of side effects.
        module_requires = getattr(module, "REQUIRES_API", None)
        if isinstance(module_requires, int) and module_requires > API_VERSION:
            self._report_api_mismatch(ep_name, dist, module_requires)
            return

        reg = make_registry(ep_name, dist=dist, version=_ep_version(ep))
        try:
            register(reg)
        except ExtensionError as exc:
            self._issue(
                "PSS030",
                "warning",
                f"extension {_origin(ep_name, dist)} misused the checker API: {exc}",
            )
            return
        except Exception as exc:
            self._issue(
                "PSS030",
                "warning",
                f"extension {_origin(ep_name, dist)} raised during register(): "
                f"{type(exc).__name__}: {exc}",
            )
            return

        if reg.requires_api > API_VERSION:
            self._report_api_mismatch(ep_name, dist, reg.requires_api)
            return

        self._accept_extension(ep_name, reg, dist, legacy=False)

    def _resolve_register(self, obj):
        """Return ``(register_callable, module)`` for a loaded entry point.

        Accepts three shapes: a module exposing ``register``, a module
        exposing the declarative ``CHECKERS`` shorthand (which is synthesized
        into a ``register()``), or a callable named directly by the entry
        point's ``module:attr`` form.
        """
        if callable(obj) and not inspect.ismodule(obj):
            return obj, inspect.getmodule(obj)

        module = obj if inspect.ismodule(obj) else None
        if module is None:
            return None, None

        register = getattr(module, "register", None)
        if callable(register):
            return register, module

        checkers = getattr(module, "CHECKERS", None)
        if isinstance(checkers, (list, tuple)):
            def _synthesized(reg, _classes=tuple(checkers)) -> None:
                for cls in _classes:
                    reg.add_checker(cls)
            desc = (getattr(module, "__doc__", "") or "").strip().splitlines()
            _synthesized.__doc__ = desc[0] if desc else ""
            return _synthesized, module

        return None, module

    def _load_legacy_checker_ep(self, ep_name: str, ep) -> None:
        """Adapt one legacy ``pssparser.checkers`` entry point.

        The class -- not the entry-point key -- is the authority on the
        checker's name (CK-X1).  A disagreement is reported as ``PSS031``
        rather than silently resolved, because the two spellings select
        different things on the command line.
        """
        dist = _ep_dist(ep)
        try:
            cls = ep.load()
        except Exception as exc:
            self._issue(
                "PSS030",
                "warning",
                f"checker entry point {_origin(ep_name, dist)} failed to import: "
                f"{type(exc).__name__}: {exc}",
            )
            return

        reg = make_registry(ep_name, dist=dist, version=_ep_version(ep))
        try:
            reg.add_checker(cls)
        except ExtensionError as exc:
            self._issue(
                "PSS030",
                "warning",
                f"checker entry point {_origin(ep_name, dist)} is not usable: {exc}",
            )
            return

        declared = getattr(cls, "name", "")
        if declared != ep_name:
            self._issue(
                "PSS031",
                "warning",
                f"entry point {ep_name!r} declares checker name {declared!r}; "
                f"the class is authoritative, so it is registered as "
                f"{declared!r}. Rename the entry-point key to match"
                + (f" (distribution {dist})" if dist else ""),
            )

        self._accept_extension(ep_name, reg, dist, legacy=True)

    def _accept_extension(
        self,
        ep_name: str,
        reg: ExtensionRegistry,
        dist: Optional[str],
        *,
        legacy: bool,
    ) -> None:
        """Fold a populated registry into this manager."""
        accepted: List[str] = []
        for cls in reg.checkers:
            if self._accept_checker(cls, ep_name, dist):
                accepted.append(cls.name)

        self._extensions[ep_name] = ExtensionInfo(
            name=ep_name,
            version=reg.version,
            description=reg.description,
            dist=dist,
            checkers=accepted,
            legacy=legacy,
        )

    def _accept_checker(
        self,
        cls: Type[CheckerBase],
        ext_name: str,
        dist: Optional[str],
    ) -> bool:
        """Register one checker class unless its marker IDs already exist.

        Uniqueness is checked *before* registration, so a collision costs the
        colliding checker and nothing else: the rest of its extension, and
        every other extension, still load.
        """
        checker_name = cls.name
        owner = f"checker {checker_name!r} from extension {ext_name!r}"

        try:
            marker_ids = [md.id for md in cls().marker_defs]
        except Exception as exc:
            self._issue(
                "PSS030",
                "warning",
                f"{owner} could not be instantiated: {type(exc).__name__}: {exc}",
            )
            return False

        clashes = [mid for mid in marker_ids if mid in self._marker_owner]
        if clashes:
            first = clashes[0]
            self._issue(
                "PSS033",
                "error",
                f"duplicate marker ID {first!r}: declared by both "
                f"{self._marker_owner[first]} and {owner}. "
                f"{checker_name!r} was not registered; "
                f"run with --no-extensions to confirm which extension is "
                f"responsible",
            )
            return False

        if checker_name in self._registered:
            self._issue(
                "PSS030",
                "warning",
                f"checker name {checker_name!r} is already registered by "
                f"{self._provenance.get(checker_name, 'an earlier extension')!r}; "
                f"the copy from extension {ext_name!r} was ignored",
            )
            return False

        self._registered[checker_name] = cls
        self._provenance[checker_name] = ext_name
        for mid in marker_ids:
            self._marker_owner[mid] = owner
        return True

    def _report_api_mismatch(self, ep_name: str, dist: Optional[str], needs: int) -> None:
        self._issue(
            "PSS032",
            "warning",
            f"extension {_origin(ep_name, dist)} requires checker API version "
            f"{needs}, but this pssparser provides {API_VERSION}; the extension "
            f"was not loaded. Upgrade pssparser, or install a build of the "
            f"extension for API {API_VERSION}",
        )

    def _issue(self, code: str, severity: str, message: str) -> None:
        self._issues.append(ExtensionIssue(code=code, severity=severity, message=message))

    # ------------------------------------------------------------------
    # Load reporting
    # ------------------------------------------------------------------

    @property
    def load_diagnostics(self) -> List[dict]:
        """Discovery problems as marker dicts, ready for ``Diagnostic``.

        These carry the :data:`~pssparser.checkers.extension.NO_FILE`
        pseudo-path because they belong to the tool, not to any source file.
        They are ordinary diagnostics in every other respect: they appear in
        ``--json``, they are counted, and ``-Werror`` promotes the warnings
        among them.
        """
        return [
            {
                "severity": issue.severity,
                "message": f"[{issue.code}] {issue.message}",
                "file": NO_FILE,
                "line": 0,
                "col": 0,
                "code": issue.code,
                "extent": 0,
                "related": [],
            }
            for issue in self._issues
        ]

    def extension_of(self, checker_name: str) -> Optional[str]:
        """Return the extension that contributed *checker_name*, if known."""
        return self._provenance.get(checker_name)

    def validate_options(self, options: Optional[Dict[str, dict]]) -> None:
        """Validate a whole ``{checker: {option: value}}`` table.

        Called once at startup, before any source file is read, so that a
        mistyped option fails immediately instead of after a long parse.
        :meth:`active` re-runs the same resolution to build the tables it
        passes to ``configure()``; doing it twice is cheap and keeps the
        error at the point where the user can act on it.

        Raises ``ValueError`` with a message naming the checker.
        """
        for name, table in (options or {}).items():
            cls = self._registered.get(name)
            if cls is None:
                # Whether the checker exists at all is config's business
                # (it has the file and line to blame); skip quietly here.
                continue
            resolve_options(cls(), table)

    @property
    def registered(self) -> Dict[str, Type[CheckerBase]]:
        """The registry, keyed by ``CheckerBase.name``.

        A read-only view for callers that need to know what is installed --
        config validation, principally.  Mutating the returned dict does not
        affect the manager.
        """
        return dict(self._registered)

    def disable_extension(self, ext_name: str) -> List[str]:
        """Unregister every checker contributed by *ext_name*.

        Backs ``[extensions.<name>] enabled = false``.  Removing the checkers
        rather than filtering them at selection time is what makes the
        setting visible to ``--list-checkers`` and to ``select``
        validation: a disabled extension's checker is genuinely not
        available, and asking for it by name should fail the same way asking
        for an uninstalled one does.

        Returns the checker names removed.
        """
        removed = [
            name for name, ext in self._provenance.items() if ext == ext_name
        ]
        for name in removed:
            cls = self._registered.pop(name, None)
            self._provenance.pop(name, None)
            if cls is None:
                continue
            # Release the marker IDs too, so a later extension may legally
            # claim them.  Leaving them owned would make a disabled
            # extension keep reserving IDs it no longer contributes.
            for md in cls().marker_defs:
                if self._marker_owner.get(md.id, "").endswith(
                    f"from extension {ext_name!r}"
                ):
                    self._marker_owner.pop(md.id, None)
        info = self._extensions.get(ext_name)
        if info is not None:
            info.checkers = [c for c in info.checkers if c not in removed]
        return removed

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_unique_ids(self) -> None:
        """Raise ``ValueError`` if any ``MarkerDef.id`` is declared by two checkers."""
        seen: Dict[str, str] = {}  # marker_id -> checker_name
        for name, cls in self._registered.items():
            for md in cls().marker_defs:
                if md.id in seen:
                    raise ValueError(
                        f"Duplicate MarkerDef ID {md.id!r}: "
                        f"declared by both {seen[md.id]!r} and {name!r}"
                    )
                seen[md.id] = name

    # ------------------------------------------------------------------
    # Ad-hoc loading
    # ------------------------------------------------------------------

    def load(self, spec: str) -> None:
        """Load a checker from a ``'module.path:ClassName'`` spec string.

        Unlike :meth:`discover`, this raises: the spec came from a
        ``--load-checker`` flag the user typed, and a typo there should stop
        the run rather than quietly change which rules execute.

        Parameters
        ----------
        spec:
            A string of the form ``"module.path:ClassName"``.

        Raises
        ------
        ValueError
            On malformed spec, missing module/class, empty checker name, or
            duplicate marker IDs.
        """
        module_path, sep, class_name = spec.rpartition(":")
        if not sep or not module_path or not class_name:
            raise ValueError(
                f"Invalid checker spec {spec!r}; expected 'module.path:ClassName'"
            )
        try:
            mod = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            raise ValueError(
                f"Cannot load checker spec {spec!r}: module not found — {exc}"
            ) from exc
        try:
            cls = getattr(mod, class_name)
        except AttributeError as exc:
            raise ValueError(
                f"Cannot load checker spec {spec!r}: attribute not found — {exc}"
            ) from exc

        instance = cls()
        if not instance.name:
            raise ValueError(
                f"Checker {cls.__name__!r} loaded from {spec!r} has an empty 'name' attribute"
            )
        # Re-loading a class that discovery already registered is a no-op
        # rather than a duplicate-ID failure: before CK-X1 was fixed the two
        # paths keyed the registry differently, so the same class could land
        # twice and then trip _check_unique_ids on its own IDs.
        if self._registered.get(instance.name) is cls:
            return
        self._registered[instance.name] = cls
        self._provenance.setdefault(instance.name, "(--load-checker)")
        try:
            self._check_unique_ids()
        except ValueError:
            del self._registered[instance.name]
            self._provenance.pop(instance.name, None)
            raise
        for md in instance.marker_defs:
            self._marker_owner.setdefault(md.id, f"checker {instance.name!r}")

    # ------------------------------------------------------------------
    # Active-checker selection
    # ------------------------------------------------------------------

    def active(
        self,
        select: Optional[List[str]],
        exclude: Optional[List[str]],
        options: Optional[Dict[str, dict]] = None,
    ) -> List[CheckerBase]:
        """Return instantiated active checkers after applying filters.

        ``is_builtin`` checkers are never included (they are metadata-only).

        Parameters
        ----------
        select:
            If non-empty, keep *only* these checker names.  Unknown names
            raise ``ValueError`` (fail-fast).
        exclude:
            If ``select`` is ``None``/empty and this is non-empty, remove
            these checker names from the active set.  Unknown names are
            silently ignored.
        options:
            ``{checker_name: {option: value}}`` from the configuration.
            Validated against each checker's ``options_schema`` and passed
            to its ``configure()``.

        Raises
        ------
        ValueError
            When *select* contains names not in the registry, or when an
            option is unknown, mistyped, or aimed at a checker that declares
            no options.
        """
        non_builtin = [
            n for n, cls in self._registered.items()
            if not getattr(cls, "is_builtin", False)
        ]

        if select:
            unknown = [n for n in select if n not in self._registered]
            if unknown:
                raise ValueError(f"Unknown checker(s): {', '.join(unknown)}")
            names = [n for n in select if n in self._registered]
        elif exclude:
            names = [n for n in non_builtin if n not in exclude]
        else:
            names = non_builtin

        instances = []
        for n in names:
            inst = self._registered[n]()
            resolved = resolve_options(inst, (options or {}).get(n))
            if resolved is not None:
                inst.configure(resolved)
            instances.append(inst)
        return instances

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_checkers(self) -> List[dict]:
        """Return info dicts for ``--list-checkers`` display."""
        result = []
        for name, cls in self._registered.items():
            inst = cls()
            result.append({
                "name": name,
                "description": inst.description or "(no description)",
                "marker_ids": [md.id for md in inst.marker_defs],
                "is_builtin": getattr(inst, "is_builtin", False),
                "extension": self._provenance.get(name),
            })
        return result

    def list_extensions(self) -> List[dict]:
        """Return info dicts for ``--list-extensions`` display, sorted by name."""
        return [
            {
                "name": info.name,
                "version": info.version,
                "description": info.description or "(no description)",
                "dist": info.dist,
                "checkers": list(info.checkers),
                "legacy": info.legacy,
            }
            for info in sorted(self._extensions.values(), key=lambda i: i.name)
        ]

    def list_all_markers(self) -> List[dict]:
        """Return every ``MarkerDef`` across all registered checkers."""
        result = []
        for name, cls in self._registered.items():
            for md in cls().marker_defs:
                result.append({
                    "id": md.id,
                    "severity": md.severity,
                    "checker": name,
                    "summary": md.summary,
                })
        return result

    def describe_marker(self, marker_id: str) -> Optional[dict]:
        """Return a full description dict for *marker_id*, or ``None``."""
        for name, cls in self._registered.items():
            for md in cls().marker_defs:
                if md.id == marker_id:
                    return {
                        "id": md.id,
                        "severity": md.severity,
                        "checker": name,
                        "summary": md.summary,
                        "detail": md.detail,
                    }
        return None

    def build_marker_index(self, active_checkers: List[CheckerBase]) -> dict:
        """Build a ``{marker_id: MarkerDef}`` index for the given checkers.

        Always includes ``CoreChecker`` marker defs so that built-in codes
        can be looked up even though ``CoreChecker`` is not in
        *active_checkers*.
        """
        from .core_checker import CoreChecker

        index: dict = {}
        for md in CoreChecker().marker_defs:
            index[md.id] = md
        for checker in active_checkers:
            for md in checker.marker_defs:
                index[md.id] = md
        return index
