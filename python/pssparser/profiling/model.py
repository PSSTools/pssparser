"""The profile data model -- plain values, JSON in and out.

Deliberately free of any dependency on the parser extension.  Aggregation and
reporting are the parts most likely to be wrong, and keeping them testable
against synthetic samples means the tests for them do not need a built
extension, a corpus, or a working grammar.

Everything here is a snapshot of one *file's* parse.  Corpus-level totals are
computed in :mod:`.aggregate`, never stored: a stored total cannot be
re-attributed once you decide you wanted the breakdown after all.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


#: Bumped when a field is removed or its meaning changes -- not when one is
#: added.  A reader refuses a profile whose schema it does not know, which is
#: what keeps a stale ``baseline.json`` from being silently mis-read.
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Event:
    """A profiler event, already resolved to a source location by the C++ side.

    ``kind`` is one of ``ambiguity``, ``context-sensitivity``, ``error``,
    ``predicate-eval``, ``sll-max-look``, ``ll-max-look``.
    """
    kind: str
    start_line: int
    start_column: int
    stop_line: int
    stop_column: int
    token_count: int
    text: str


@dataclass
class DecisionSample:
    """One ATN decision's profile within one file.

    The ranking key is :attr:`sll_look`.  It counts tokens of lookahead on
    *every* invocation, DFA hit or miss, so it is exact, deterministic, and
    independent of how warm the cache was -- which none of the ATN-transition
    or timing fields are.
    """
    decision: int
    rule: str
    rule_index: int = 0
    grammar_line: int = 0
    invocations: int = 0
    sll_look: int = 0
    sll_min_look: int = 0
    sll_max_look: int = 0
    ll_look: int = 0
    ll_min_look: int = 0
    ll_max_look: int = 0
    sll_atn_transitions: int = 0
    ll_atn_transitions: int = 0
    ll_fallback: int = 0
    ambiguities: int = 0
    context_sensitivities: int = 0
    errors: int = 0
    predicate_evals: int = 0
    time_ns: int = 0
    events: List[Event] = field(default_factory=list)

    @property
    def look_per_invocation(self) -> float:
        """Mean SLL lookahead per invocation.

        The column that separates a decision which is merely *hot* from one
        that is structurally expensive.  40 000 invocations at 1.1 tokens each
        is a decision doing its job; 200 invocations at 38 tokens each is a
        grammar that cannot tell its alternatives apart.
        """
        return (self.sll_look / self.invocations) if self.invocations else 0.0

    def merge(self, other: "DecisionSample") -> None:
        """Fold *other* into this sample, in place.

        Sums the counters; takes the extreme of the min/max pair rather than
        summing it; concatenates events up to a cap.  ``min`` skips zeros:
        a decision not invoked in one file reports ``sll_min_look == 0``, and
        letting that win would claim every decision has a free path.
        """
        assert self.decision == other.decision, "cannot merge unlike decisions"
        self.invocations += other.invocations
        self.sll_look += other.sll_look
        self.ll_look += other.ll_look
        self.sll_atn_transitions += other.sll_atn_transitions
        self.ll_atn_transitions += other.ll_atn_transitions
        self.ll_fallback += other.ll_fallback
        self.ambiguities += other.ambiguities
        self.context_sensitivities += other.context_sensitivities
        self.errors += other.errors
        self.predicate_evals += other.predicate_evals
        self.time_ns += other.time_ns

        self.sll_max_look = max(self.sll_max_look, other.sll_max_look)
        self.ll_max_look = max(self.ll_max_look, other.ll_max_look)
        self.sll_min_look = _merge_min(self.sll_min_look, other.sll_min_look)
        self.ll_min_look = _merge_min(self.ll_min_look, other.ll_min_look)

        self.events = _merge_events(self.events, other.events)


#: Events retained per decision after merging across files.  Triage reads a
#: handful of examples; a corpus sweep would otherwise accumulate one per file.
_MAX_MERGED_EVENTS = 8

#: Event kinds in decreasing order of what they tell a grammar author.  The
#: ordering is load-bearing, not cosmetic: a first-come-first-served cap lets
#: the max-lookahead events of the first few files fill every slot, so a
#: decision that is ambiguous in file 40 reports its ambiguity *count* with no
#: example to go with it -- which is exactly the case this ordering fixes.
_EVENT_PRIORITY = {
    "ambiguity": 0,
    "context-sensitivity": 1,
    "sll-max-look": 2,
    "ll-max-look": 3,
    "error": 4,
    "predicate-eval": 5,
}


def _merge_events(existing: List[Event], incoming: List[Event]) -> List[Event]:
    """Combine two event lists, keeping the most informative under the cap.

    Stable within a kind, so the first example of an ambiguity stays the one
    reported however many files follow.
    """
    combined = list(existing) + list(incoming)
    if len(combined) <= _MAX_MERGED_EVENTS:
        return combined
    ordered = sorted(
        enumerate(combined),
        key=lambda pair: (_EVENT_PRIORITY.get(pair[1].kind, 99), pair[0]))
    keep = sorted(ordered[:_MAX_MERGED_EVENTS], key=lambda pair: pair[0])
    return [ev for _, ev in keep]


def _merge_min(a: int, b: int) -> int:
    """``min`` over values where 0 means "not observed", not "observed zero"."""
    if not a:
        return b
    if not b:
        return a
    return min(a, b)


@dataclass
class FileProfile:
    """One file, parsed once."""
    path: str
    bucket: str
    mode: str                       # "cold" | "warm"
    lines: int = 0
    tokens: int = 0
    parse_wall_ns: int = 0
    dfa_size: int = 0               # process-cumulative; see IParseProfileInfo.h
    syntax_errors: int = 0
    parsed: bool = True
    decisions: List[DecisionSample] = field(default_factory=list)

    @property
    def active_decisions(self) -> List[DecisionSample]:
        """Decisions actually invoked. The grammar has 347; a file uses a few."""
        return [d for d in self.decisions if d.invocations]

    @property
    def total_sll_look(self) -> int:
        return sum(d.sll_look for d in self.decisions)

    @property
    def total_prediction_ns(self) -> int:
        return sum(d.time_ns for d in self.decisions)


@dataclass
class CorpusProfile:
    """A whole run.

    :attr:`grammar_sha` and :attr:`corpus_rev` exist so a stored profile can
    never be silently compared against a different grammar or a different
    corpus.  A differing ``grammar_sha`` is the *point* of a comparison; a
    differing ``corpus_rev`` invalidates it, and the reporter says so rather
    than quietly producing a diff of two unrelated things.
    """
    mode: str
    schema: int = SCHEMA_VERSION
    grammar_sha: str = ""
    corpus_rev: str = ""
    corpus_root: str = ""
    repeat: int = 1
    synthetic: bool = False
    #: Real file counts, carried separately so that a :meth:`compacted`
    #: profile -- which has collapsed its per-file rows -- can still report
    #: honestly how many files it covered.  Zero means "derive from
    #: :attr:`files`".
    file_count: int = 0
    error_file_count: int = 0
    files: List[FileProfile] = field(default_factory=list)

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(dataclasses.asdict(self), indent=indent)

    def compacted(self) -> "CorpusProfile":
        """The same profile with per-file rows merged into one, events dropped.

        For the checked-in baseline.  Kept in full, a 92-file sweep is ~1.5 MB
        of JSON, five-sixths of it per-file breakdown and event text that the
        gate never reads -- and every regeneration commits the whole of it
        again.  Merged, it is the ~300 decision rows the comparison actually
        uses.

        Attribution is not lost so much as not *stored*: when the gate fires,
        re-running the profiler gives a far better answer than a months-old
        per-file breakdown would.
        """
        from .aggregate import merge_decisions, totals  # circular at module level

        t = totals(self.files)
        merged = merge_decisions(self.files)
        for d in merged:
            d.events = []

        return CorpusProfile(
            mode=self.mode,
            schema=self.schema,
            grammar_sha=self.grammar_sha,
            corpus_rev=self.corpus_rev,
            corpus_root=self.corpus_root,
            repeat=self.repeat,
            synthetic=self.synthetic,
            file_count=t.files,
            error_file_count=t.files_with_errors,
            files=[FileProfile(
                path="<merged>",
                bucket="<merged>",
                mode=self.mode,
                lines=t.lines,
                tokens=t.tokens,
                parse_wall_ns=t.parse_wall_ns,
                dfa_size=t.dfa_size,
                syntax_errors=0,
                parsed=True,
                decisions=merged)])

    @staticmethod
    def from_json(text: str) -> "CorpusProfile":
        data = json.loads(text)
        schema = data.get("schema")
        if schema != SCHEMA_VERSION:
            raise ValueError(
                "profile schema %r is not the %r this build reads; "
                "regenerate it rather than comparing across schemas"
                % (schema, SCHEMA_VERSION))
        return _corpus_from_dict(data)


def _corpus_from_dict(data: Dict[str, Any]) -> CorpusProfile:
    files = []
    for f in data.pop("files", []):
        decisions = []
        for d in f.pop("decisions", []):
            events = [Event(**e) for e in d.pop("events", [])]
            decisions.append(DecisionSample(events=events, **d))
        files.append(FileProfile(decisions=decisions, **f))
    return CorpusProfile(files=files, **data)
