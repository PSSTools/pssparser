"""Per-rule parse-tree counts (ParseProfileInfo.get_rule_invocations).

The grammar-coverage measure behind scripts/grammar_cov.py. It exists because
decision invocation counts cannot answer "was this rule used": an LL(1)
decision never reaches the profiling simulator and always reports zero.
"""
from io import StringIO

import pssparser.ast as zsp_ast
import pssparser.core as zspp


def _rule_counts(text):
    f = zspp.Factory.inst()
    builder = f.mkAstBuilder(f.mkMarkerCollector())
    builder.setEnableProfile(True)
    builder.build(zsp_ast.Factory.inst().mkGlobalScope(0), StringIO(text))
    return builder.getProfileInfo().get_rule_invocations()


def test_every_rule_is_listed_and_used_ones_are_counted():
    counts = _rule_counts("component c1 { } component c2 { action a { } }")
    assert counts["compilation_unit"] == 1
    assert counts["component_declaration"] == 2
    assert counts["action_declaration"] == 1
    # Zeros are included: the unused rules are the point.
    assert counts["covergroup_declaration"] == 0
    assert len(counts) > 300


def test_counts_are_per_file():
    assert _rule_counts("component c1 { }")["component_declaration"] == 1
    assert _rule_counts("component c1 { }")["component_declaration"] == 1
