"""Tool descriptors: a tool is onboarded by TOML, no Python (design §2.2).

Unknown keys are rejected rather than ignored, for the same reason unknown case
directives are: a typo that silently disables a capability declaration shows up
later as a mysterious pile of `skipped` cases.
"""
from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .adapters.base import Capabilities

_SCHEMA: dict[str, set[str]] = {
    "tool": {"name", "version_cmd", "version_re", "version", "pss", "adapter"},
    "invoke": {"argv", "file_argv", "cwd", "timeout_s", "env",
               "max_errors_argv"},
    "output": {"kind", "stream", "pattern", "continuation", "fields"},
    "capabilities": {"multifile", "max_errors", "json_output",
                     "exit_code_on_error"},
}

ADAPTERS = ("subprocess", "pssparser-inprocess")
OUTPUT_KINDS = ("regex", "json", "none")
STREAMS = ("stdout", "stderr", "both")


class DescriptorError(Exception):
    pass


@dataclass
class Descriptor:
    path: Path
    name: str
    adapter: str = "subprocess"
    version_cmd: list[str] = field(default_factory=list)
    version_re: str | None = None
    version: str | None = None
    #: Language version the tool *claims* to implement.  Honour system: nothing
    #: verifies it, so reports print it next to every headline number.
    pss: str | None = None

    argv: list[str] = field(default_factory=list)
    #: How *one* input file is spelled on the command line.  Substituted for
    #: the standalone ``{files}`` element of `argv`, once per input file, with
    #: ``{file}`` replaced by the path -- so a tool wanting a flag before each
    #: file (`-pss a.pss -pss b.pss`) writes ``file_argv = ["-pss", "{file}"]``.
    #: The default reproduces a bare list of paths.
    file_argv: list[str] = field(default_factory=lambda: ["{file}"])
    cwd: str = "case"
    timeout_s: float = 30.0
    env: dict[str, str] = field(default_factory=dict)
    max_errors_argv: list[str] = field(default_factory=list)

    kind: str = "regex"
    stream: str = "both"
    pattern: str | None = None
    continuation: str | None = None
    fields: dict[str, str] = field(default_factory=dict)

    capabilities: Capabilities = field(default_factory=Capabilities)

    #: True when the descriptor declared no `pss`, in which case the runner
    #: assumes the newest version the corpus contains and warns -- failing
    #: loudly in the tool's disfavour rather than silently inflating its score.
    pss_assumed: bool = False


def _expand(value: str, *, suite_root: Path) -> str:
    """Expand the descriptor placeholders that are not per-case.

    ``{files}`` and ``{maxerrors}`` are *not* expanded here -- they are
    per-invocation and belong to the adapter.
    """
    return (value
            .replace("{python}", sys.executable)
            .replace("{suite_root}", str(suite_root))
            .replace("{repo_root}", str(suite_root.parent)))


def load_descriptor(path: Path, suite_root: Path | None = None) -> Descriptor:
    path = Path(path)
    suite_root = Path(suite_root) if suite_root else path.parent.parent
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise DescriptorError(f"{path}: {e}") from None

    for section, keys in raw.items():
        if section not in _SCHEMA:
            raise DescriptorError(
                f"{path}: unknown section [{section}]; expected one of "
                f"{sorted(_SCHEMA)}")
        unknown = set(keys) - _SCHEMA[section]
        if unknown:
            raise DescriptorError(
                f"{path}: unknown key(s) {sorted(unknown)} in [{section}]")

    tool = raw.get("tool", {})
    if "name" not in tool:
        raise DescriptorError(f"{path}: [tool] name is required")
    invoke = raw.get("invoke", {})
    output = raw.get("output", {})
    caps = raw.get("capabilities", {})

    d = Descriptor(path=path, name=tool["name"])
    d.adapter = tool.get("adapter", "subprocess")
    if d.adapter not in ADAPTERS:
        raise DescriptorError(
            f"{path}: [tool] adapter must be one of {list(ADAPTERS)}")
    d.version_cmd = [_expand(a, suite_root=suite_root)
                     for a in tool.get("version_cmd", [])]
    d.version_re = tool.get("version_re")
    d.version = tool.get("version")
    d.pss = tool.get("pss")
    d.pss_assumed = d.pss is None

    d.argv = [_expand(a, suite_root=suite_root) for a in invoke.get("argv", [])]
    if d.adapter == "subprocess" and not d.argv:
        raise DescriptorError(f"{path}: [invoke] argv is required")
    if d.argv and not any("{files}" in a for a in d.argv):
        raise DescriptorError(
            f"{path}: [invoke] argv must contain '{{files}}' somewhere")
    if "file_argv" in invoke:
        d.file_argv = [_expand(a, suite_root=suite_root)
                       for a in invoke["file_argv"]]
        # The plural check runs first: '{files}' does not *contain* '{file}'
        # (the 's' intervenes), so the typo would otherwise be reported as the
        # far less helpful "must contain '{file}'".
        if any("{files}" in a for a in d.file_argv):
            raise DescriptorError(
                f"{path}: [invoke] file_argv uses '{{files}}'; it describes a "
                f"single file, so the placeholder is '{{file}}'")
        if not any("{file}" in a for a in d.file_argv):
            raise DescriptorError(
                f"{path}: [invoke] file_argv must contain '{{file}}' somewhere "
                f"-- otherwise the input path is never passed to the tool")
        # `argv` positions the file group; `file_argv` spells one member of it.
        # `{file}` in argv would be expanded by neither, and silently reach the
        # tool as a literal.
        if any("{file}" in a and "{files}" not in a for a in d.argv):
            raise DescriptorError(
                f"{path}: [invoke] argv uses '{{file}}'; argv takes '{{files}}' "
                f"and [invoke] file_argv takes '{{file}}'")
        if not any(a == "{files}" for a in d.argv):
            raise DescriptorError(
                f"{path}: [invoke] file_argv needs a standalone '{{files}}' "
                f"element in argv to expand at; argv embeds it in {
                    next(a for a in d.argv if '{files}' in a)!r}")
    d.cwd = invoke.get("cwd", "case")
    d.timeout_s = float(invoke.get("timeout_s", 30.0))
    d.env = {k: _expand(str(v), suite_root=suite_root)
             for k, v in invoke.get("env", {}).items()}
    d.max_errors_argv = [_expand(a, suite_root=suite_root)
                         for a in invoke.get("max_errors_argv", [])]

    if d.adapter == "subprocess" and not output:
        # Defaulting here would be silent ruin: with no way to read the tool's
        # diagnostics every case comes back empty, which classifies as `missed`
        # and reads like a catastrophically bad tool rather than a bad
        # descriptor.
        raise DescriptorError(
            f"{path}: an [output] section is required -- the suite has no way "
            f"to read this tool's diagnostics without one")
    d.kind = output.get("kind", "json" if d.adapter != "subprocess" else "regex")
    if d.kind not in OUTPUT_KINDS:
        raise DescriptorError(
            f"{path}: [output] kind must be one of {list(OUTPUT_KINDS)}")
    d.stream = output.get("stream", "both")
    if d.stream not in STREAMS:
        raise DescriptorError(
            f"{path}: [output] stream must be one of {list(STREAMS)}")
    d.pattern = output.get("pattern")
    d.continuation = output.get("continuation")
    d.fields = dict(output.get("fields", {}))
    if d.kind == "regex":
        if not d.pattern:
            raise DescriptorError(
                f"{path}: [output] kind='regex' requires a pattern")
        try:
            compiled = re.compile(d.pattern)
        except re.error as e:
            raise DescriptorError(f"{path}: [output] pattern: {e}") from None
        if "message" not in compiled.groupindex:
            raise DescriptorError(
                f"{path}: [output] pattern needs a (?P<message>…) group")

    d.capabilities = Capabilities(
        multifile=bool(caps.get("multifile", True)),
        max_errors=bool(caps.get("max_errors", False)),
        json_output=bool(caps.get("json_output", d.kind == "json")),
        exit_code_on_error=int(caps.get("exit_code_on_error", 1)),
    )
    if (d.adapter == "subprocess" and d.capabilities.max_errors
            and not d.max_errors_argv):
        raise DescriptorError(
            f"{path}: [capabilities] max_errors is true but [invoke] "
            f"max_errors_argv is empty -- the runner would have no way to set "
            f"the cap")
    return d
