"""Orchestration: scratch dirs, parallelism, timeouts, skips, controls.

Cases are **never** run in `cases/` itself.  Tools drop artifacts next to their
input, and a corpus that mutates when you measure it is not a corpus.  Every
case gets a fresh directory under the scratch root, and the control gets its
own directory using the *same filename* as the case so that file attribution
and line numbers line up between the two runs.
"""
from __future__ import annotations

import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .adapters.base import CaseOpts, ToolResult
from .case import TOOL_KEYS, Case, CaseFormatError
from .classify import (CLEAN, DETECTED, DETECTED_MISLOCATED, Observations,
                       SKIPPED, SKIPPED_VERSION, control_is_clean, classify)
from .descriptor import Descriptor
from .lint import lint_diagnostic
from .locate import Tolerance
from .rubric import FIXIT_INVALID, FIXIT_VERIFIED, apply_fixit


@dataclass
class CaseRun:
    case: Case
    status: str
    observations: Observations
    result: ToolResult | None = None
    control_status: str | None = None
    control_error_count: int = 0
    skip_reason: str | None = None
    notes: list[str] = field(default_factory=list)


def version_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in v.split("."))
    except ValueError:
        return (0,)


class Runner:
    def __init__(self, adapter, desc: Descriptor, *,
                 tolerance: Tolerance | None = None,
                 severity_floor: str = "error",
                 jobs: int = 1,
                 scratch_root: Path | None = None,
                 timeout_s: float | None = None,
                 tool_pss: str | None = None,
                 verify_fixit: bool = True):
        self.adapter = adapter
        self.desc = desc
        self.tolerance = tolerance or Tolerance()
        self.severity_floor = severity_floor
        self.jobs = max(1, jobs)
        self.timeout_s = timeout_s or desc.timeout_s
        self.tool_pss = tool_pss or desc.pss
        self.verify_fixit = verify_fixit
        self._scratch_root = scratch_root
        self._owned_scratch: str | None = None

    # -- scratch ----------------------------------------------------------

    @property
    def scratch_root(self) -> Path:
        if self._scratch_root is None:
            self._owned_scratch = tempfile.mkdtemp(prefix="pss-errsuite-")
            self._scratch_root = Path(self._owned_scratch)
        return self._scratch_root

    def cleanup(self) -> None:
        if self._owned_scratch:
            shutil.rmtree(self._owned_scratch, ignore_errors=True)
            self._owned_scratch = None
            self._scratch_root = None

    def _materialize(self, case: Case, subdir: str,
                     override: dict[str, str] | None = None) -> list[Path]:
        dest_dir = self.scratch_root / subdir / case.case_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = []
        for src in case.input_files():
            dest = dest_dir / src.name
            text = (override or {}).get(src.name)
            if text is None:
                if not src.is_file():
                    raise FileNotFoundError(
                        f"{case.path}: 'files:' names {src.name!r}, which does "
                        f"not exist beside the case")
                shutil.copyfile(src, dest)
            else:
                dest.write_text(text, encoding="utf-8")
            out.append(dest)
        return out

    # -- skips ------------------------------------------------------------

    def _skip_reason(self, case: Case) -> tuple[str, str] | None:
        caps = self.desc.capabilities
        for req in case.requires:
            if not caps.has(req):
                return SKIPPED, f"tool does not declare capability {req!r}"
        if len(case.input_files()) > 1 and not caps.multifile:
            return SKIPPED, "tool does not accept multiple files"
        if self.tool_pss and version_tuple(case.pss) > version_tuple(self.tool_pss):
            return (SKIPPED_VERSION,
                    f"case targets PSS {case.pss}; tool declares "
                    f"{self.tool_pss}")
        return None

    # -- one case ---------------------------------------------------------

    def run_case(self, case: Case) -> CaseRun:
        skip = self._skip_reason(case)
        if skip is not None:
            status, reason = skip
            return CaseRun(case=case, status=status,
                           observations=Observations(), skip_reason=reason)

        opts = CaseOpts(
            max_errors=self._max_errors_for(case),
            timeout_s=self.timeout_s,
        )
        files = self._materialize(case, "case")
        result = self.adapter.run(files, opts)

        control_result = None
        control_status = None
        control_errors = 0
        if case.expect != "accept":
            control_overrides = case.control_overrides()
            if control_overrides is not None:
                control_files = self._materialize(
                    case, "control", control_overrides)
                control_result = self.adapter.run(control_files, opts)
                control_errors = len(control_result.errors())
                control_status = (
                    CLEAN if control_is_clean(control_result,
                                               self.severity_floor)
                    else "failed")

        status, obs = classify(case, result, control_result, self.tolerance,
                               self.severity_floor)
        obs.lints = sorted({lint for d in result.diagnostics
                            for lint in lint_diagnostic(d)})
        if self.verify_fixit and status in (DETECTED, DETECTED_MISLOCATED):
            obs.fixit = self._verify_fixit(case, result, obs, opts)
        run = CaseRun(case=case, status=status, observations=obs,
                      result=result, control_status=control_status,
                      control_error_count=control_errors)
        if case.expect != "accept" and control_status is None:
            run.notes.append(
                "no control (no .ok.pss sibling and no fix:); "
                "the result is not cross-tool comparable")
        return run

    # -- fix-it verification ----------------------------------------------
    #
    # Design §5.3: apply the tool's own fix and re-run it.  If the result is
    # clean the suggestion is real and earns D4 = 3; if it isn't, the tool
    # proposed a fix that does not fix, which is flagged rather than credited.
    # This is the only check in the rubric that tests a message's *claim*
    # rather than its shape, and it costs one extra invocation on exactly the
    # cases that offer a machine-applicable fix.

    def _verify_fixit(self, case: Case, result: ToolResult,
                      obs: Observations, opts: CaseOpts) -> str | None:
        if obs.primary_index is None:
            return None
        # "Re-run and see that it is clean" can only answer the question on a
        # file with one defect in it. A thirty-defect volume case still has
        # twenty-nine after a perfect fix, and recording that as
        # `fixit_invalid` scores the tool *below* offering no fix at all --
        # for a fix that was right. Where the check cannot decide, it says so
        # by not running, and D4 stays at 2.
        if (case.count or 1) != 1 or len(result.diagnostics) != 1:
            return None
        diag = result.diagnostics[obs.primary_index]
        if diag.file is not None and (
                diag.file.rsplit("/", 1)[-1] != case.path.name):
            # The fix belongs to a companion file whose source we would have
            # to re-read and re-index; out of scope rather than wrong.
            return None
        patched = apply_fixit(case.source, diag)
        if patched is None:
            return None
        files = self._materialize(case, "fixit", {case.path.name: patched})
        after = self.adapter.run(files, opts)
        return (FIXIT_VERIFIED if control_is_clean(after, self.severity_floor)
                else FIXIT_INVALID)

    def _max_errors_for(self, case: Case) -> int | None:
        opts = case.tool_opts.get(self.desc.name, {})
        # These directives were addressed to the tool now running, so "I do not
        # understand this one" is an error here even though it is only a
        # warning in `validate`, which does not know whose namespace it is.
        unknown = sorted(set(opts) - TOOL_KEYS)
        if unknown:
            raise CaseFormatError(
                f"{case.path}: {self.desc.name}.{unknown[0]}: no reader "
                f"consumes {unknown[0]!r} (known: "
                f"{', '.join(sorted(TOOL_KEYS))})")
        raw = opts.get("max_errors")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            # Silently falling back to the default cap is how this whole class
            # of defect hides: the case declares a cap, the run measures the
            # default, and nothing says so.
            raise CaseFormatError(
                f"{case.path}: {self.desc.name}.max_errors: expected an "
                f"integer, got {raw!r}") from None

    # -- all cases --------------------------------------------------------

    def run_all(self, cases: list[Case], progress=None) -> list[CaseRun]:
        if self.jobs == 1:
            runs = []
            for case in cases:
                runs.append(self.run_case(case))
                if progress:
                    progress(runs[-1])
            return runs
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            futures = [pool.submit(self.run_case, c) for c in cases]
            runs = []
            for fut in futures:
                runs.append(fut.result())
                if progress:
                    progress(runs[-1])
            return runs
