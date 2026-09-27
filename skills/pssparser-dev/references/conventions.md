# Project conventions

Where each kind of note belongs. Getting this wrong loses information: a status
update in a reviewed design doc rots it, and a deferred defect recorded only in
a phase plan becomes unfindable once the phase scrolls past.

## Design doc + plan tracker

A project in `docs/design/` normally has two files:

- `<topic>.md`: the design. Reviewed prose; decisions and rationale. Keep it
  stable. Record review decisions in its decisions section, not as edits
  scattered through the text.
- `<topic>-plan.md`: the tracker. Steps, status checkboxes, "Landed" notes
  with commit hashes, and corrections the implementation made to the design
  (typically a §0 "survey corrections" that supersede parts of the design).

When you land a step: tick the box and add a dated note *in the plan*. When the
code contradicts the design, record the correction in the plan and follow it;
do not rewrite the design to match.

Some projects also keep a `-resume.md` handoff (where work stopped, how to pick
it up). Update it when you stop mid-project.

Read the plan before the design when resuming work: the plan says what is true
now.

## Known issues (`docs/design/known-issues.md`)

The register of known, understood, deliberately unfixed defects, organized by
area. Each entry: what is wrong, how it shows up, why it was left, what closing
it would take.

- When you defer a finding, add it here *and* cross-reference it from the
  plan. The plan alone is not enough.
- Remove an entry (or mark it closed) when it is **fixed**, not when it is
  worked around. Keep a closed entry when its limits are the useful fact.
- Closing an entry often uncovers more defects than it fixes. Write those up
  here too, and give a new ID to any decision the fix forces but does not
  settle.
- IDs carry the prefix of where the issue was found (for example `P3-`, `CL-`,
  `SR-`), not where it was introduced.

## Cross-repository follow-ups (`docs/design/cross-repo-followups.md`)

Anything pssparser work makes necessary *outside* this repository: a pssfmt
xfail that a fix turns into an XPASS, a downstream test to tighten, a corpus
addition, a spec comment to submit. Add an `X-n` entry in the same change,
with the repository, the cause, what to do, the order constraint, and a
checkbox. Tick entries when the other side lands; do not delete them.

When you retire a corpus defect ID, check pssfmt's
`tests/corpus/test_round_trip.py` and `tests/corpus/test_parser_gaps.py`, which
mirror pssparser's known-unparseable list.

Never perform an outward-facing step (submitting spec comments, pushing to
another repository) without being asked. Record it here instead.

## CHANGELOG.md

User-visible changes get an entry under `## Unreleased`, headed
`### Added|Fixed|Changed — <what>` with the plan item and LRM clause in
parentheses. Name any new marker codes. Version numbers are
`<PSS major>.<PSS minor>.<patch>`: the first two follow the LRM revision the
parser targets, so a feature release within one LRM revision bumps only the
patch.

Releases are cut by pushing a `v*` tag; the tag is the version. The source
carries `0.0.0` in `python/pssparser/__version__.py` and is not edited to
release.

## The LRM

- Cite clauses and syntax numbers (`LRM 17.2.6b`, `Syntax 85`, `B.1`) in
  comments, tests, messages' detail text, and CHANGELOG entries.
- Read the spec from the PDF with `pdftotext -layout`. Markdown conversions of
  the drafts corrupt Annex B and Table 3.
- Where the LRM contradicts itself (Annex B against a clause's syntax box, an
  example against normative text), record it in `known-issues.md` and follow
  the normative text. Spec comments go through `cross-repo-followups.md`.
- LRM examples are fragments; complete them before using them as test models
  (see `testing.md`).

## Language facts that affect every test

- No core-library package is implicitly visible. A model uses `print`,
  `message`, `format`, `urandom`, `sizeof_s`, `packed_s`, `@doc`, `@code_doc`,
  and so on only after `import std_pkg::*;`.
- An import is not a re-export.
- A bare `action` at package scope is a syntax error; it belongs in a
  `component`.

## Commits

Keep a change and its regenerated baselines, goldens, generated bindings,
docs (`docs/markers.rst`) and tracker updates in the same commit, so any commit
passes the suite and each regression is bisectable. Land risky refactors
separately from features for the same reason.
