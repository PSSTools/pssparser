"""Generic subprocess adapter: run argv, parse whatever comes back.

Two things here are less obvious than they look:

*Process groups.*  A tool that forks a licence daemon or a helper process
outlives a `Popen.kill()` on the leader.  Every invocation therefore gets its
own session and the whole group is signalled on timeout -- otherwise a hang
leaks processes for the rest of the run and the machine slowly dies instead of
the suite reporting `timeout` and moving on.

*Crash vs. error vs. could-not-run.*  These are three different findings and
the status vocabulary keeps them apart (design §4.1).  A non-zero exit is
normal for a tool that found an error; a negative exit (signal) or an exit at
or above 64 is a crash; an exit code outside the declared set with nothing
parsed from either stream is a failed invocation.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from ..descriptor import Descriptor
from .base import CaseOpts, ToolResult
from . import json_cli, regex_out

#: stdout/stderr are kept so a surprising classification can be audited without
#: a re-run, but a tool that dumps its whole input back at us must not blow up
#: the run file.
CAPTURE_LIMIT = 16 * 1024

_CRASH_MARKERS = (
    "Traceback (most recent call last)",
    "Internal error",
    "INTERNAL ERROR",
    "Assertion failed",
    "Segmentation fault",
)


def _truncate(text: str) -> str:
    if len(text) <= CAPTURE_LIMIT:
        return text
    return text[:CAPTURE_LIMIT] + f"\n…[truncated, {len(text)} bytes total]"


def build_argv(desc: Descriptor, files: list[Path],
               opts: CaseOpts) -> list[str]:
    argv: list[str] = []
    for arg in desc.argv:
        if arg == "{files}":
            # `file_argv` defaults to ["{file}"], so the common case is still
            # a bare list of paths; a tool that wants a flag before each file
            # sets it to e.g. ["-pss", "{file}"] and gets the group repeated.
            for f in files:
                argv.extend(a.replace("{file}", str(f))
                            for a in desc.file_argv)
        elif "{files}" in arg:
            if len(files) != 1:
                raise ValueError(
                    f"{desc.path}: argv element {arg!r} embeds {{files}} but "
                    f"the case has {len(files)} files; use a standalone "
                    f"'{{files}}' element for multi-file cases")
            argv.append(arg.replace("{files}", str(files[0])))
        else:
            argv.append(arg)
    if opts.max_errors is not None and desc.max_errors_argv:
        argv.extend(a.replace("{maxerrors}", str(opts.max_errors))
                    for a in desc.max_errors_argv)
    return argv


class SubprocessAdapter:
    def __init__(self, desc: Descriptor):
        self.desc = desc
        self.name = desc.name
        self.version = desc.version or "unknown"

    # -- version ----------------------------------------------------------

    def probe_version(self) -> str:
        """Capture the version once per run, from the tool itself."""
        if self.desc.version:
            self.version = self.desc.version
            return self.version
        if not self.desc.version_cmd:
            self.version = "unknown"
            return self.version
        try:
            proc = subprocess.run(self.desc.version_cmd, capture_output=True,
                                  text=True, timeout=30,
                                  env=self._env())
        except (OSError, subprocess.SubprocessError) as e:
            self.version = f"unknown ({e})"
            return self.version
        text = (proc.stdout + proc.stderr).strip()
        if self.desc.version_re:
            import re
            m = re.search(self.desc.version_re, text)
            text = m.group(1) if m and m.groups() else (m.group(0) if m else text)
        self.version = text.splitlines()[0].strip() if text else "unknown"
        return self.version

    # -- run --------------------------------------------------------------

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(self.desc.env)
        return env

    def _cwd(self, files: list[Path]) -> str:
        if self.desc.cwd == "case":
            return str(files[0].parent)
        return self.desc.cwd

    def run(self, files: list[Path], opts: CaseOpts) -> ToolResult:
        argv = build_argv(self.desc, files, opts)
        timeout = opts.timeout_s or self.desc.timeout_s
        t0 = time.perf_counter()
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=self._cwd(files), env=self._env(),
                start_new_session=True,
            )
        except OSError as e:
            return ToolResult(
                exit_code=None, duration_s=time.perf_counter() - t0,
                invocation_error=f"could not run {argv[0]!r}: {e}",
                parse_confidence="none")

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            stdout, stderr = proc.communicate()
            timed_out = True
        duration = time.perf_counter() - t0

        stdout, stderr = stdout or "", stderr or ""
        rc = proc.returncode
        diagnostics, confidence = self._parse(stdout, stderr)

        crashed = False
        invocation_error = None
        if not timed_out:
            declared = {0, self.desc.capabilities.exit_code_on_error}
            if rc is not None and rc < 0:
                crashed = True
            elif rc is not None and rc >= 64:
                crashed = True
            elif rc not in declared and not diagnostics:
                invocation_error = (
                    f"exit {rc} is outside the declared set {sorted(declared)} "
                    f"and nothing was parsed from the output")
            if any(m in stderr or m in stdout for m in _CRASH_MARKERS):
                crashed = True

        return ToolResult(
            exit_code=None if timed_out else rc,
            diagnostics=tuple(diagnostics),
            stdout=_truncate(stdout), stderr=_truncate(stderr),
            duration_s=duration, timed_out=timed_out, crashed=crashed,
            invocation_error=invocation_error,
            parse_confidence="none" if timed_out else confidence,
        )

    def _parse(self, stdout: str, stderr: str):
        desc = self.desc
        if desc.kind == "none":
            return [], "none"
        if desc.kind == "json":
            return json_cli.parse(stdout, stderr, desc)
        return regex_out.parse(stdout, stderr, desc)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass
