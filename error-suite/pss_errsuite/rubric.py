"""Tier-A message grading (design §5).

§4 answers *did the tool react to the defect*; this answers *was what it said
any good*.  Scored only on `detected` / `detected_mislocated` cases: there is
no message to grade on a `missed`, and the correct message on an `accept` case
is silence.

Everything here reads a **case document from a run file**, not a `Case` and a
`ToolResult`.  That is what lets `grade` re-score a finished run with a newer
rubric and no tool invocation at all -- the run file already carries the
source, the expectation and the verbatim diagnostics, and design §6 requires it
to stay that way.

Three rules hold the whole thing together:

* **An unmeasurable dimension is `null`, never 0.**  Only ~10% of the corpus
  declares `cause:` today, and a 0 for "the author never wrote down what the
  right answer was" would be a finding about our metadata masquerading as a
  finding about a tool's messages.  `null` propagates: the composite averages
  what was measured and records how many dimensions that was.
* **The accuracy gate is the one rule not to lose.**  D1 = 0 zeroes the
  composite outright (design §5.1): a precisely-located, fix-it-carrying,
  beautifully-worded message about the *wrong thing* spends the user's trust in
  the wrong place.  It lives in `apply_accuracy_gate` with its own test because
  it is the rule most likely to be refactored away by someone tidying up the
  arithmetic.  An *unmeasured* D1 never gates -- silence is not a zero.
* **Tier A has a ceiling below 3 on some dimensions, and says so.**  D5 = 3
  requires reading the message out of context and D3 = 3 requires judging
  whether it names "both sides and the relationship"; neither is mechanically
  decidable, so Tier A stops at 2 and attaches a note saying why.  A Tier-A
  composite of 1.0 is therefore not reachable, which is the honest outcome: a
  corpus graded entirely by proxy measures conformance to the proxies.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from .classify import DETECTED, DETECTED_MISLOCATED
from . import lint

#: Bumped whenever an anchor or a proxy changes.  Scores from different
#: versions are never averaged or compared (design §5.6), which `compare`
#: enforces by refusing the join.
RUBRIC_VERSION = "1"

DIMENSIONS = ("d1", "d2", "d3", "d4", "d5", "d6")

DIMENSION_NAMES = {
    "d1": "accuracy", "d2": "location", "d3": "specificity",
    "d4": "actionability", "d5": "clarity", "d6": "economy",
}

#: Statuses that have a message worth grading.
GRADEABLE = (DETECTED, DETECTED_MISLOCATED)

# Flags -- stable strings, they end up in run files and in `triage` output.
F_D1_UNMEASURED = "d1_unmeasured"
F_D1_DISAGREES = "d1_disagrees_with_status"
F_FIXIT_INVALID = "fixit_invalid"
F_GATED = "accuracy_gate_applied"

#: Fix-it verification outcomes, recorded by the runner in `observations`.
FIXIT_VERIFIED = "verified"
FIXIT_INVALID = "invalid"

_HEDGES = ("possibly", "perhaps", "may be missing", "might be", "near ",
           "somewhere")

#: Messages that assert invalidity without ever saying what valid looks like.
_BARE_INVALID = re.compile(
    r"^\W*(syntax\s+error|parse\s+error|invalid|illegal|bad\s+syntax|error)"
    r"\W*$", re.I)

_FIX_WORDS = ("expected", "expecting", "did you mean", "try ", "use ",
              "must be", "should be", "declare", "add ", "remove ",
              "insert", "missing")

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

#: Enough PSS (and English) to stop "struct" or "the" counting as the user's
#: own vocabulary in the D3 fallback.  Deliberately not the full keyword set:
#: a word wrongly *absent* here only makes D3 more generous, and D3's job is to
#: find messages with nothing of the program in them at all.
_KEYWORDS = frozenset("""
action activity component struct buffer stream state resource pool exec body
constraint import package extend pure abstract static const rand bit int
string bool chandle enum inherit ref input output lock share array list map
set if else foreach forall repeat while do select schedule parallel sequence
symbol function target solve file type void return default super this null
true false new inside dist with bins coverpoint covergroup cross instance
declared declaration expression statement identifier value expected found
here the a an of to in for is not and or but be been was were at by on
error warning note file line column token character
""".split())


# -- term matching -------------------------------------------------------
#
# `cause:` terms are matched against the lemma, not the exact string (design
# §5.4).  With no lemmatizer available and stdlib-only as a constraint, the
# approximation is a suffix set: `assign` matches "assigns", "assigned",
# "assignment".  It over-matches occasionally and that is the right direction
# -- a false *match* costs a point of strictness, a false miss reports a good
# message as inaccurate.

_SUFFIX = r"(?:s|es|ed|d|ing|ment|ments)?"
_HAS_LETTER = re.compile(r"[A-Za-z]")


def term_matches(term: str, message: str) -> bool:
    """Is *term* present in *message*, case-insensitively and lemma-ishly?

    Punctuation terms (`;`, `}`) are matched as substrings, because word
    boundaries are meaningless for them and a missing-semicolon case declares
    `cause: ;`.
    """
    term = term.strip()
    if not term:
        return False
    low = message.lower()
    if not _HAS_LETTER.search(term):
        return term.lower() in low
    words = [w for w in re.split(r"\s+", term.lower().strip()) if w]
    pattern = r"\s+".join(re.escape(w) + _SUFFIX for w in words)
    return re.search(r"(?<![A-Za-z0-9_])" + pattern + r"(?![A-Za-z0-9_])",
                     low) is not None


def _any_term(terms, message: str) -> list[str]:
    return [t for t in terms if term_matches(t, message)]


# -- reading a case document ---------------------------------------------


def primary_diagnostic(doc: dict) -> dict | None:
    """The diagnostic the classifier called "the one about this defect".

    Reuses the recorded `primary_index` rather than re-deriving it, so a
    re-grade can never disagree with the status about *which message* it is
    talking about.
    """
    diags = (doc.get("result") or {}).get("diagnostics") or []
    index = (doc.get("observations") or {}).get("primary_index")
    if index is None or not diags:
        return None
    if 0 <= index < len(diags):
        return diags[index]
    return None


def body_identifiers(source: str) -> set[str]:
    """Identifiers the user wrote, excluding the `//!` header.

    Keywords are *not* filtered here, because the caller needs both readings:
    a one-letter field called `a` is indistinguishable from the article "a"
    when it appears bare in a message, but perfectly identifiable as `'a'`.
    """
    lines = source.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith("//!"):
        i += 1
    body = "".join(lines[i:])
    return {m.group(0) for m in _IDENT_RE.finditer(body)}


_QUOTED_RE = re.compile(r"'([^']+)'|\"([^\"]+)\"")


def quoted_lexemes(message: str) -> list[str]:
    return [a or b for a, b in _QUOTED_RE.findall(message)]


def _word_present(word: str, message: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(word)
                     + r"(?![A-Za-z0-9_])", message) is not None


def _has_span(diag: dict) -> bool:
    return diag.get("end_col") is not None or diag.get("end_line") is not None


def _file_matches(doc: dict, diag: dict) -> bool:
    want = (doc.get("expect", {}).get("at", {}) or {}).get("file")
    if not want:
        # A case with no `at:` still has a file it is about.  `files[0]` is a
        # bad guess for it -- with `files:` the case body can be second -- so
        # prefer the recorded case file and keep the old fallback only for run
        # documents written before it existed.
        want = doc.get("case_file")
    if not want:
        files = doc.get("files") or []
        want = files[0].rsplit("/", 1)[-1] if files else None
    got = diag.get("file")
    if got is None:
        return False
    return want is None or got.rsplit("/", 1)[-1] == want


# -- the six proxies -----------------------------------------------------
#
# Each returns `(score, note)`.  The note is mandatory below 3 -- design §6
# requires `rubric.notes` to be actionable, and "D4: 1" on its own is not.


def d1_accuracy(doc: dict, primary: dict | None) -> tuple[int | None, str | None]:
    if primary is None:
        return 0, "no diagnostic to read"
    message = primary.get("message", "")
    expect = doc.get("expect", {})
    cause = expect.get("cause") or []
    not_cause = expect.get("not_cause") or []

    wrong = _any_term(not_cause, message)
    if wrong:
        hit = _any_term(cause, message) if cause else []
        if hit:
            return 1, (f"names the declared misdiagnosis ({wrong[0]!r}) "
                       f"alongside the cause ({hit[0]!r})")
        return 0, f"reports {wrong[0]!r}, the misdiagnosis this case declares"

    if not cause:
        return None, ("no `cause:` in the case header, so accuracy is not "
                      "mechanically decidable")

    hit = _any_term(cause, message)
    if len(hit) == len(cause):
        return 3, None
    if hit:
        missing = [t for t in cause if t not in hit]
        return 2, (f"mentions {hit[0]!r} but not {', '.join(repr(m) for m in missing)}; "
                   f"the diagnosis may be at the wrong granularity")
    if _BARE_INVALID.match(message.strip()):
        return 1, "generic: excludes nothing about this defect"
    return 1, (f"none of the declared cause terms "
               f"({', '.join(repr(c) for c in cause)}) appear")


def d2_location(doc: dict, primary: dict | None) -> tuple[int | None, str | None]:
    status = doc.get("status")
    if primary is None or primary.get("line") is None:
        return 0, "no location"
    if not _file_matches(doc, primary):
        return 0, f"points at {primary.get('file')!r}, not the case file"
    if status == DETECTED_MISLOCATED:
        return 1, (f"right file, but line {primary.get('line')} is outside the "
                   f"run's tolerance of the declared defect")

    at = (doc.get("expect", {}) or {}).get("at") or {}
    exact = (primary.get("line") == at.get("line")
             and primary.get("col") == at.get("col"))
    if not exact or not _has_span(primary):
        why = ("a point, not a span" if not _has_span(primary)
               else "the span does not start on the declared position")
        return 2, f"within tolerance but {why}"
    if at.get("end_col") is not None and (
            primary.get("end_col") != at.get("end_col")
            or primary.get("end_line") != (at.get("end_line") or at.get("line"))):
        return 2, "span start is exact but its end is not the declared one"
    if doc.get("expect", {}).get("also") and not (
            doc.get("observations", {}).get("has_related")):
        return 2, ("exact span, but the case declares a second site (`also:`) "
                   "and no `related` location matches it")
    return 3, None


def d3_specificity(doc: dict, primary: dict | None) -> tuple[int | None, str | None]:
    if primary is None:
        return 0, "no diagnostic to read"
    if doc.get("expect", {}).get("about") == "tool":
        # The case is about the tool's own reporting -- an error cap firing --
        # so there is no declaration for the message to name and no answer to
        # the question D3 asks.  `null`, not 0: the rubric's first rule.
        return None, ("`about: tool` -- the diagnostic is about the tool's "
                      "reporting, not about a construct in the program")
    message = primary.get("message", "")
    lints = lint.lint_message(message, has_location=True, has_code=True)
    if lint.G3_JARGON in lints or lint.L_BARE_TOKEN in lints:
        return 0, "grammar or implementation vocabulary, not the user's"

    names = doc.get("expect", {}).get("names") or []
    if names:
        present = [n for n in names if _word_present(n, message)]
        if not present:
            quoted = quoted_lexemes(message)
            if quoted:
                return 1, (f"quotes {quoted[0]!r} but names none of the "
                           f"declared entities ({', '.join(names)})")
            return 0, f"names none of {', '.join(names)} and quotes nothing"
        if len(present) < len(names):
            missing = [n for n in names if n not in present]
            return 2, (f"names {', '.join(present)} but not "
                       f"{', '.join(missing)}")
        if len(names) >= 2:
            return 3, None
        return 2, ("names the entity, but this case declares only one side; "
                   "Tier A cannot tell whether the relationship is stated")

    # No `names:` to check against.  The 2/3 boundary is out of reach, but the
    # bottom of the scale is not: whether the message contains any of the
    # user's own vocabulary at all is decidable from the source.
    source = doc.get("source") or ""
    unmeasured = "no `names:` in the case header"
    if not source:
        return None, unmeasured
    idents = body_identifiers(source)
    quoted = quoted_lexemes(message)
    if any(q in idents for q in quoted):
        return None, unmeasured
    # Unquoted, only identifiers long enough not to collide with ordinary
    # English count -- a field called `a` is not evidence when the message
    # says "a string".
    if any(len(i) >= 3 and i.lower() not in _KEYWORDS
           and _word_present(i, message) for i in idents):
        return None, unmeasured
    if quoted:
        return 1, "quotes a lexeme but no entity from the user's program"
    return 0, "contains no element of the user's program"


def d4_actionability(doc: dict, primary: dict | None
                     ) -> tuple[int | None, str | None]:
    if primary is None:
        return 0, "no diagnostic to read"
    message = primary.get("message", "")
    fixit = (doc.get("observations") or {}).get("fixit")

    if fixit == FIXIT_VERIFIED:
        return 3, None
    if fixit == FIXIT_INVALID:
        return 1, ("the offered fix does not produce a file the tool accepts; "
                   "a fix-it that does not fix is worse than none (design §5.3)")
    if primary.get("suggestion"):
        if not _has_span(primary):
            return 2, ("the suggestion carries replacement text but no span, "
                       "so it is not machine-applicable")
        return 2, ("the fix-it was not verified; `run` applies it and re-runs "
                   "the tool to earn the 3")
    if primary.get("code"):
        return 2, ("a diagnostic code, but no fix: say what would be valid, "
                   "or offer a span and a replacement")
    low = message.lower()
    if any(w in low for w in _FIX_WORDS):
        return 2, "says what was expected, but offers no applicable fix"
    if _BARE_INVALID.match(message.strip()):
        return 0, "asserts invalidity without saying what valid looks like"
    return 1, "no code, no suggestion, and no statement of what would be valid"


def d5_clarity(doc: dict, primary: dict | None) -> tuple[int | None, str | None]:
    if primary is None:
        return 0, "no diagnostic to read"
    message = primary.get("message", "")
    lints = lint.lint_message(message, has_location=True, has_code=True)
    if lint.G3_JARGON in lints:
        return 0, "implementation vocabulary leaks into the message"
    if lint.G7_NEWLINE in lints:
        return 0, "multi-line message"
    if lint.L_BARE_TOKEN in lints:
        return 0, "the message is a bare token"
    if lint.G7_LENGTH in lints:
        return 1, f"{len(message)} characters; the limit is {lint.MAX_LENGTH}"
    low = message.lower()
    hedge = next((h for h in _HEDGES if h in low), None)
    if hedge:
        return 1, f"hedged ({hedge.strip()!r})"
    if len(re.findall(r"[.!?]\s+[A-Z]", message)) >= 1:
        return 1, "more than one sentence"
    return 2, ("Tier A stops at 2: reading the message out of context, the "
               "D5 = 3 test, needs a human")


def d6_economy(doc: dict, primary: dict | None) -> tuple[int | None, str | None]:
    obs = doc.get("observations") or {}
    n = obs.get("error_count") or 0
    k = doc.get("expect", {}).get("count") or 1
    index = obs.get("primary_index")
    first = index == 0

    if n > 3 * k and not first:
        return 0, (f"{n} errors for {k} declared defect(s), and the one about "
                   f"this defect is not first")
    if n > 3 * k:
        return 1, f"{n} errors for {k} declared defect(s)"
    if n > k + 1:
        return 1, f"{n} errors where {k} was declared"
    if not first and n > k:
        return 1, (f"the diagnostic about this defect is #{(index or 0) + 1} "
                   f"of {n}")
    if n == k and first and obs.get("has_related"):
        return 3, None
    if n == k and first:
        return 2, ("exact count and ordering; attach secondary information as "
                   "`related` rather than as separate errors to reach 3")
    return 2, f"{n} errors against a declared {k}, within tolerance"


_PROXIES = {
    "d1": d1_accuracy, "d2": d2_location, "d3": d3_specificity,
    "d4": d4_actionability, "d5": d5_clarity, "d6": d6_economy,
}


# -- composite and gate --------------------------------------------------


def composite(scores: dict) -> float | None:
    """Mean of the *measured* dimensions, normalized to 0..1.

    Design §5.2 writes this as `sum / 18`, which assumes all six are scored.
    With `null` dimensions the denominator has to shrink, or a case with no
    `cause:` would be reported as a third less good than an identical case
    that has one.  The count is carried alongside as `measured` so a reader
    can see how much of the score is actually evidence.
    """
    measured = [s for s in (scores.get(d) for d in DIMENSIONS)
                if s is not None]
    if not measured:
        return None
    return round(sum(measured) / (3 * len(measured)), 4)


def apply_accuracy_gate(d1: int | None, value: float | None) -> float | None:
    """D1 = 0 ⇒ composite 0, regardless of the other five (design §5.1).

    A confidently-worded, precisely-located, fix-it-carrying message about the
    wrong thing is worse than a crude message about the right thing.  An
    *unmeasured* D1 does not gate: we do not know that it is wrong, and
    treating "the author wrote no `cause:`" as a wrong diagnosis would zero a
    third of the corpus for a metadata gap.
    """
    if d1 == 0:
        return 0.0
    return value


# -- scoring one case ----------------------------------------------------


def score_case(doc: dict, *, override: dict | None = None,
               rater: str = "auto") -> dict | None:
    """The `rubric` block for one case document, or `None` if not gradeable.

    *override* supplies Tier-B scores (`{"d1": 2, ...}`, any subset); they win
    over the proxy for the dimensions they name and mark the case tier B.
    """
    if doc.get("status") not in GRADEABLE:
        return None

    primary = primary_diagnostic(doc)
    scores: dict = {}
    notes: dict = {}
    for key, proxy in _PROXIES.items():
        score, note = proxy(doc, primary)
        scores[key] = score
        if note:
            notes[key] = note

    flags = []
    if (doc.get("observations") or {}).get("fixit") == FIXIT_INVALID:
        flags.append(F_FIXIT_INVALID)

    tier = "A"
    if override:
        for key in DIMENSIONS:
            if key in override and override[key] is not None:
                scores[key] = int(override[key])
                notes.pop(key, None)
        tier = "B"
        for key, value in (override.get("notes") or {}).items():
            notes[key] = value

    if scores["d1"] is None:
        flags.append(F_D1_UNMEASURED)
    elif scores["d1"] <= 1 and doc.get("status") == DETECTED:
        # Design §5.3's Tier-B sample trigger: the status says the tool found
        # the defect, the accuracy proxy says the message is about something
        # else.  One of the two is wrong and only a human can say which.
        flags.append(F_D1_DISAGREES)

    raw = composite(scores)
    gated = apply_accuracy_gate(scores["d1"], raw)
    if gated != raw:
        flags.append(F_GATED)

    block = {
        "version": RUBRIC_VERSION,
        "tier": tier,
        "rater": rater if tier == "B" else "auto",
        "composite": gated,
        "measured": sum(1 for d in DIMENSIONS if scores[d] is not None),
    }
    for key in DIMENSIONS:
        block[key] = scores[key]
    if notes:
        block["notes"] = {k: notes[k] for k in DIMENSIONS if k in notes}
    if flags:
        block["flags"] = flags
    return block


# -- fix-it application --------------------------------------------------


def apply_fixit(source: str, diag) -> str | None:
    """Apply a diagnostic's repair.

    Returns `None` when the diagnostic offers nothing applicable -- no
    replacement text, or no span to put it over.

    A tool that reports its own edit span (`fix`) is taken at its word. That
    span is often *not* the diagnostic's: "expected ';' after 'a'" underlines
    a column so the caret has something to point at, while the edit inserts a
    character and replaces nothing. Falling back to the diagnostic's span for
    such a tool deletes whatever sits under the caret and records a
    `fixit_invalid` the tool did not earn -- which is what ES-S2 was, and why
    pssparser used to cap at D4 = 2. A tool that reports only `suggestion`
    still gets the old behaviour, and still carries that cap.
    """
    get = diag.get if isinstance(diag, dict) else lambda k: getattr(diag, k, None)
    fix = get("fix")
    if fix is not None:
        fget = (fix.get if isinstance(fix, dict)
                else lambda k: getattr(fix, k, None))
        replacement = fget("replacement")
        line, col = fget("line"), fget("col")
        end_line, end_col = fget("end_line"), fget("end_col")
        if end_line is None:
            end_line = line
        if end_col is None:
            end_col = col
    else:
        replacement = get("suggestion")
        line, col = get("line"), get("col")
        end_line, end_col = get("end_line"), get("end_col")
    if replacement is None or line is None or col is None:
        return None
    if end_col is None:
        return None
    if end_line is None:
        end_line = line

    lines = source.splitlines(keepends=True)
    if not (1 <= line <= len(lines) and 1 <= end_line <= len(lines)):
        return None
    if end_line < line or (end_line == line and end_col < col):
        return None

    head = lines[line - 1][:col - 1]
    tail_line = lines[end_line - 1]
    tail = tail_line[end_col - 1:]
    out = lines[:line - 1] + [head + replacement + tail] + lines[end_line:]
    return "".join(out)


# -- rollups -------------------------------------------------------------


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def rollup(cases: list[dict]) -> dict:
    """The run-level rubric summary.

    Never a single headline number (design §5.2): a scalar "message quality:
    0.71" invites the scoreboard use §2 rules out and hides the only
    interesting structure, which is *which class* is bad.  So: per class, and
    per dimension, with the metadata coverage that says how much of it is
    evidence.
    """
    graded = [c for c in cases if c.get("rubric")]
    by_class: dict[str, dict] = {}
    for case in graded:
        bucket = by_class.setdefault(case["class"], {"scores": []})
        bucket["scores"].append(case["rubric"]["composite"])
    classes = {}
    for cls, bucket in sorted(by_class.items()):
        scores = [s for s in bucket["scores"] if s is not None]
        classes[cls] = {
            "n": len(bucket["scores"]),
            "mean": _mean(scores),
            "min": min(scores) if scores else None,
        }

    dimensions = {}
    for key in DIMENSIONS:
        values = [c["rubric"][key] for c in graded]
        measured = [v for v in values if v is not None]
        dimensions[key] = {
            "name": DIMENSION_NAMES[key],
            "mean": _mean(measured),
            "measured": len(measured),
            "unmeasured": len(values) - len(measured),
        }

    flags: dict[str, int] = {}
    for case in graded:
        for flag in case["rubric"].get("flags", ()):
            flags[flag] = flags.get(flag, 0) + 1

    gradeable = [c for c in cases if c.get("status") in GRADEABLE]
    return {
        "version": RUBRIC_VERSION,
        "graded": len(graded),
        "gradeable": len(gradeable),
        "tier": {
            "A": sum(1 for c in graded if c["rubric"]["tier"] == "A"),
            "B": sum(1 for c in graded if c["rubric"]["tier"] == "B"),
        },
        "by_class": classes,
        "dimensions": dimensions,
        "flags": flags,
        "coverage": metadata_coverage(cases),
    }


def metadata_coverage(cases: list[dict]) -> dict:
    """How much of the corpus can Tier A actually speak about?

    D1 reads `cause:`/`not_cause:` and D3 reads `names:`.  Where they are
    absent the dimension is `null`, so this block is the backfill work queue:
    it is the difference between "our messages are unmeasured" and "our
    messages are bad", and those are very different reports.
    """
    scored = [c for c in cases if c.get("status") in GRADEABLE]
    out = {"gradeable": len(scored)}
    for key in ("cause", "not_cause", "names"):
        out[key] = sum(1 for c in scored if (c.get("expect") or {}).get(key))
    return out


def cases_missing_metadata(cases: list[dict], key: str = "cause") -> list[str]:
    """Gradeable case ids with no *key* declared, in corpus order."""
    return [c["case"] for c in cases
            if c.get("status") in GRADEABLE
            and not (c.get("expect") or {}).get(key)]


# -- Tier B: which cases are worth a human's time ------------------------


def tier_b_sample(cases: list[dict], fraction: float = 0.1,
                  per_class_floor: int = 3) -> list[str]:
    """Design §5.3's sample, in corpus order and fully deterministic.

    Three populations, unioned: a stratified slice of every class (so no class
    is graded entirely by proxy), every case where the D1 proxy and the status
    disagree (the tool "found" the defect but the message is about something
    else -- only a human can say which of the two is wrong), and every case
    scoring below 0.4 (the work queue, which deserves a real read before it
    becomes a bug report).

    No randomness: two people asking for the sample get the same sample, and
    re-grading after a corpus edit does not reshuffle what has already been
    scored by hand.
    """
    graded = [c for c in cases if c.get("rubric")]
    chosen: set[str] = set()

    by_class: dict[str, list[dict]] = {}
    for case in graded:
        by_class.setdefault(case["class"], []).append(case)
    for members in by_class.values():
        want = min(len(members),
                   max(per_class_floor, math.ceil(len(members) * fraction)))
        for case in members[:want]:
            chosen.add(case["case"])

    for case in graded:
        block = case["rubric"]
        if F_D1_DISAGREES in block.get("flags", ()):
            chosen.add(case["case"])
        if block["composite"] is not None and block["composite"] < 0.4:
            chosen.add(case["case"])

    return [c["case"] for c in graded if c["case"] in chosen]


def fingerprint(doc: dict, tool_version: str) -> str:
    """Cache key: this case, this tool version, these messages, this rubric.

    A message that has not changed is not re-graded (design §5.3), so human
    effort is spent once per distinct message rather than once per run.  The
    rubric version is in the key because a changed anchor invalidates a human
    score exactly as surely as a changed message does.
    """
    diags = (doc.get("result") or {}).get("diagnostics") or []
    parts = [doc.get("case", ""), tool_version or "", RUBRIC_VERSION]
    parts += [f"{d.get('severity')}:{d.get('line')}:{d.get('col')}:"
              f"{d.get('message')}" for d in diags]
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


CACHE_SCHEMA = "pss-errsuite/rubric-cache/1"


class RubricCache:
    """Tier-B scores on disk, keyed by :func:`fingerprint`.

    Gitignored: it is human judgement about a named tool's messages, which is
    comparison output like any other (design §2).
    """

    def __init__(self, path):
        self.path = Path(path)
        self.entries: dict[str, dict] = {}
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            if data.get("schema") == CACHE_SCHEMA:
                self.entries = data.get("entries") or {}

    def get(self, key: str) -> dict | None:
        return self.entries.get(key)

    def put(self, key: str, entry: dict) -> None:
        self.entries[key] = entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"schema": CACHE_SCHEMA, "entries": self.entries},
                       indent=2) + "\n", encoding="utf-8")


def regrade(document: dict, *, cache: RubricCache | None = None) -> dict:
    """Re-score every gradeable case of a run document, in place.

    Deterministic: the case documents carry everything the proxies read, so
    grading twice changes nothing.  Tier-B scores in *cache* override the
    proxies for the dimensions they name.
    """
    version = (document.get("tool") or {}).get("version") or ""
    for case in document.get("cases") or []:
        override = None
        rater = "auto"
        if cache is not None:
            entry = cache.get(fingerprint(case, version))
            if entry:
                override = entry
                rater = entry.get("rater") or "human"
        block = score_case(case, override=override, rater=rater)
        if block is None:
            case.pop("rubric", None)
        else:
            case["rubric"] = block
    document.setdefault("summary", {})["rubric"] = rollup(
        document.get("cases") or [])
    document.setdefault("run", {}).setdefault("policy", {})[
        "rubric_version"] = RUBRIC_VERSION
    return document
