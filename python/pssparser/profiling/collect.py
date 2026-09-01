"""Collection: drive the parser over files and snapshot the profile.

Two things here are easy to get wrong and are therefore done explicitly.

**One file per ``build()``.**  ``AstBuilderInt::build`` resets its profile on
entry, so ``get_profile_info()`` reports the *last* file only.  Handing a
92-file list to ``Parser.parses()`` and reading the profile afterwards yields
data for file 92 and silently discards the rest.  The driver below reads the
profile after every single file.

**The builder is driven directly, not through ``Parser``.**  ``Parser.parse()``
raises on the first syntax error, which makes it unusable for the
``parses = false`` bucket -- the half of the corpus whose prediction behaviour
is least understood.  Using one path for both buckets also keeps DFA warmth
identical between them, which a mixed approach would not.
"""
from __future__ import annotations

import time
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .model import DecisionSample, Event, FileProfile


class ProfileCollector:
    """Parses files in one process, accumulating nothing between them.

    One collector is one process's worth of DFA warmth.  Construct it once and
    sweep for **warm** numbers; construct one per file (in its own process) for
    **cold** ones.
    """

    def __init__(self, grammar_lines: Optional[Dict[str, int]] = None,
                 load_stdlib: bool = True):
        import pssparser.core as zspp
        import pssparser.ast as zsp_ast

        self._core = zspp
        self._ast_f = zsp_ast.Factory.inst()
        self._parser_f = zspp.Factory.inst()
        self._grammar_lines = grammar_lines or {}
        self._n_scopes = 0

        self._marker_l = self._parser_f.mkMarkerCollector()
        self._builder = self._parser_f.mkAstBuilder(self._marker_l)
        self._builder.setEnableProfile(True)

        #: The standard library is parsed by every real consumer before any
        #: user file, and parsing it warms a substantial part of the DFA.  It
        #: is loaded here for the same reason, so that "cold" means what a
        #: consumer's first file actually experiences.  Its own profile is
        #: discarded -- callers wanting it should collect it as a file.
        if load_stdlib:
            stdlib = self._ast_f.mkGlobalScope(self._n_scopes)
            self._n_scopes += 1
            self._parser_f.loadStandardLibrary(self._builder, stdlib)

    def collect_text(self, name: str, text: str, bucket: str = "<inline>",
                     mode: str = "warm") -> FileProfile:
        marker_l = self._parser_f.mkMarkerCollector()
        self._builder.setMarkerListener(marker_l)

        scope = self._ast_f.mkGlobalScope(self._n_scopes)
        self._n_scopes += 1

        start = time.perf_counter_ns()
        self._builder.build(scope, StringIO(text))
        wall = time.perf_counter_ns() - start

        errors = self._count_errors(marker_l)
        profile = self._builder.getProfileInfo()

        return FileProfile(
            path=name,
            bucket=bucket,
            mode=mode,
            lines=text.count("\n") + 1,
            tokens=profile.token_count if profile else 0,
            parse_wall_ns=wall,
            dfa_size=profile.dfa_size if profile else 0,
            syntax_errors=errors,
            parsed=(errors == 0),
            decisions=self._samples(profile))

    def collect_file(self, path: Path, bucket: str = "", mode: str = "warm") -> FileProfile:
        text = path.read_text(encoding="utf-8", errors="replace")
        ret = self.collect_text(str(path), text, bucket=bucket, mode=mode)
        return ret

    def _count_errors(self, marker_l) -> int:
        err = int(self._core.MarkerSeverityE.Error)
        n = 0
        for i in range(marker_l.numMarkers()):
            if int(marker_l.getMarker(i).severity()) == err:
                n += 1
        return n

    def _samples(self, profile) -> List[DecisionSample]:
        """Convert the C++ profile into model objects.

        Decisions never invoked are dropped.  The grammar has 347 and a 57-line
        file touches a couple of dozen; carrying the other 320 zeros per file
        would make a corpus profile roughly thirty times larger than the corpus
        and tell the reader nothing.
        """
        if profile is None:
            return []
        ret = []
        for d in profile.get_decision_info():
            if not d.invocations:
                continue
            rule = d.rule_name
            ret.append(DecisionSample(
                decision=d.decision,
                rule=rule,
                rule_index=d.rule_index,
                grammar_line=self._grammar_lines.get(rule, 0),
                invocations=d.invocations,
                sll_look=d.sll_lookahead_ops,
                sll_min_look=d.sll_min_lookahead,
                sll_max_look=d.sll_max_lookahead,
                ll_look=d.ll_lookahead_ops,
                ll_min_look=d.ll_min_lookahead,
                ll_max_look=d.ll_max_lookahead,
                sll_atn_transitions=d.sll_atn_transitions,
                ll_atn_transitions=d.ll_atn_transitions,
                ll_fallback=d.ll_fallback,
                ambiguities=d.ambiguity_count,
                context_sensitivities=d.context_sensitivity_count,
                errors=d.error_count,
                predicate_evals=d.predicate_eval_count,
                time_ns=d.time_in_prediction,
                events=[
                    Event(
                        kind=e.kind,
                        start_line=e.start_line,
                        start_column=e.start_column,
                        stop_line=e.stop_line,
                        stop_column=e.stop_column,
                        token_count=e.token_count,
                        text=e.text)
                    for e in d.get_events()
                ]))
        return ret


def collect_warm(
        files: Iterable[Tuple[Path, str, bool]],
        grammar_lines: Optional[Dict[str, int]] = None,
        repeat: int = 1) -> List[FileProfile]:
    """Sweep the whole corpus in one process, snapshotting each file.

    Steady-state numbers: the DFA is warm from the second file onward, which is
    the state a language server or a formatter actually runs in.

    ``repeat`` re-parses the whole corpus N times in the same process.  Counters
    scale linearly with it, so the caller must divide; its purpose is to give
    *timing* enough signal to be worth reading on a 5000-line corpus.  The
    result is marked synthetic and must not be used as a baseline.
    """
    collector = ProfileCollector(grammar_lines)
    ret: List[FileProfile] = []
    for _ in range(max(1, repeat)):
        for path, bucket, _parses in files:
            ret.append(collector.collect_file(path, bucket=bucket, mode="warm"))
    return ret
