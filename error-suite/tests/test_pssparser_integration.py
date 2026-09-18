"""The one place the suite touches pssparser.

Marked `needs_pssparser` and skipped cleanly without a build.  Its job is to
catch *descriptor drift*: if the CLI renames a flag or changes its JSON shape,
every case silently becomes `missed` and the run file reads like a
catastrophically bad tool rather than a stale descriptor.
"""
from __future__ import annotations

import pytest

from pss_errsuite.adapters import make_adapter
from pss_errsuite.adapters.base import CaseOpts
from pss_errsuite.case import collect_cases, load_case
from pss_errsuite.descriptor import load_descriptor
from pss_errsuite.runner import Runner

pytestmark = pytest.mark.needs_pssparser


@pytest.fixture
def descriptor(suite_root):
    return load_descriptor(suite_root / "tools" / "pssparser-py.toml",
                           suite_root)


def test_the_descriptor_still_matches_the_cli(require_pssparser, descriptor,
                                              corpus, tmp_path):
    """Structured output, a real version string, and at least one diagnostic
    we could actually read."""
    adapter = make_adapter(descriptor)
    version = adapter.probe_version()
    assert version and "unknown" not in version

    case = load_case(corpus / "syntax" / "punct" / "missing_semicolon_01.pss",
                     corpus)
    work = tmp_path / case.path.name
    work.write_text(case.source)
    result = adapter.run([work], CaseOpts(timeout_s=30))
    assert result.parse_confidence == "structured"
    assert result.exit_code == 1
    assert result.diagnostics and result.diagnostics[0].code


def test_a_full_corpus_run_has_no_control_failures(require_pssparser,
                                                   descriptor, corpus):
    """A control failure means the *repaired* case does not parse, which is a
    corpus defect, not a tool finding -- so it is a gate here even though the
    detection numbers are not."""
    runner = Runner(make_adapter(descriptor), descriptor, jobs=4,
                    tool_pss=descriptor.pss)
    try:
        runs = runner.run_all(collect_cases(corpus))
    finally:
        runner.cleanup()
    failed = [r.case.case_id for r in runs if r.status == "control_failed"]
    assert failed == [], f"controls do not parse clean: {failed}"
    crashed = [r.case.case_id for r in runs
               if r.status in ("crash", "timeout", "tool_error")]
    assert crashed == [], f"pssparser died on: {crashed}"


def test_the_two_descriptors_diverge_only_where_we_can_explain_it(
        require_pssparser, suite_root, corpus, tmp_path):
    """X-3's exit criterion, made mechanical.

    The CLI path and the in-process path are different tools on purpose (plan
    §0.3), and every way they differ today is understood: the in-process
    descriptor declares no `max_errors`, so the `syntax.volume` cap cases skip;
    without the cap it reports all fifty defects where the CLI stops at twenty;
    and one case neither path diagnoses (ES-D1).  Anything *else* -- in
    particular a `we_miss` -- is news, and should fail here rather than be
    noticed in a report nobody reads.
    """
    import json

    from pss_errsuite import compare as C
    from pss_errsuite import report

    paths = []
    for name in ("pssparser-py", "pssparser-inproc"):
        desc = load_descriptor(suite_root / "tools" / f"{name}.toml", suite_root)
        adapter = make_adapter(desc)
        runner = Runner(adapter, desc, jobs=1, tool_pss=desc.pss)
        try:
            runs = runner.run_all(collect_cases(corpus))
        finally:
            runner.cleanup()
        doc = report.build_document(
            runs, desc=desc, adapter=adapter, tolerance=runner.tolerance,
            severity_floor="error", suite_root=suite_root,
            started=report._utc_now(), duration_s=0.0)
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(doc))
        paths.append(path)

    document = C.compare(paths)
    tags = {t for t, n in
            document["summary"]["by_tag"]["pssparser-inproc"].items() if n}
    assert tags <= {C.AGREE, C.BOTH_MISS, C.THEY_NOISIER, C.INCOMPARABLE}, (
        f"an unexplained divergence appeared: {sorted(tags)}")

    for case in C.cases_tagged(document, C.INCOMPARABLE, C.THEY_NOISIER):
        assert case["class"] == "syntax.volume", (
            f"{case['case']} diverges for a reason the max_errors capability "
            f"does not explain")


def test_the_inprocess_adapter_agrees_on_single_file_syntax_cases(
        require_pssparser, suite_root, corpus):
    """The two pssparser descriptors are different tools by design (plan §0.3)
    -- but on a single-file syntax case with no checker involvement they must
    agree, or one of the two paths is wrong."""
    cli = load_descriptor(suite_root / "tools" / "pssparser-py.toml",
                          suite_root)
    inproc = load_descriptor(suite_root / "tools" / "pssparser-inproc.toml",
                             suite_root)
    case = load_case(corpus / "syntax" / "punct" / "missing_semicolon_01.pss",
                     corpus)

    out = {}
    for name, desc in (("cli", cli), ("inproc", inproc)):
        runner = Runner(make_adapter(desc), desc, tool_pss="3.1")
        try:
            out[name] = runner.run_case(case)
        finally:
            runner.cleanup()
    assert out["cli"].status == out["inproc"].status
    assert ([(d.line, d.col, d.message)
             for d in out["cli"].result.diagnostics]
            == [(d.line, d.col, d.message)
                for d in out["inproc"].result.diagnostics])
