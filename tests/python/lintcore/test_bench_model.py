"""The lint benchmark's generated model (lint-core-plan.md C8).

``scripts/bench_lint.py`` times lint on a model it generates; a model with an
error would gate lint off and time nothing, so it must stay clean.
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location(
        "bench_lint", os.path.join(ROOT, "scripts", "bench_lint.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_model_links_cleanly_and_the_rules_run(bench, tmp_path, factory):
    from pssparser.parser import Parser
    paths = bench.generate(str(tmp_path), 3)
    assert len(paths) == 4
    p = Parser()
    p.parses([(f, open(f).read()) for f in paths])
    root = p.link()     # raises on an error
    assert [m for m in p.markers if m["severity"] in ("error", "warning")] == []

    e = factory.mkLintEngine()
    for r in bench.default_rules():
        assert e.load_rules(r, open(r).read()), r
    res = e.run(p.user_units(), {}, model=root)
    assert res["ok"] and res["index_ns"] > 0
    assert sum(s["matches"] for s in res["stats"]) > 0
    assert not [m for m in res["markers"] if m["code"] in ("PSSP220", "PSSP221")]
