"""Reporting: three tiers, because they answer three different questions.

1. Which *decisions* cost the most.
2. Which *rules* they belong to -- what you would actually restructure.
3. *Where in the corpus* the cost shows up, quoted, so the finding can be
   reproduced and understood without re-running anything.

The header states prediction time as a fraction of parse time.  If that is 3%,
the reader should stop after the header, and the report says so rather than
letting them work through a ranking that cannot matter.
"""
from __future__ import annotations

from typing import List, Optional

from .aggregate import RuleRollup, Totals, merge_decisions, rank, rollup_by_rule, totals
from .model import CorpusProfile, DecisionSample


def _ns(v: int) -> str:
    if v < 1_000:
        return "%d ns" % v
    if v < 1_000_000:
        return "%.1f us" % (v / 1_000)
    if v < 1_000_000_000:
        return "%.1f ms" % (v / 1_000_000)
    return "%.2f s" % (v / 1_000_000_000)


def _n(v: int) -> str:
    return "{:,}".format(v)


def header(profile: CorpusProfile, t: Totals) -> List[str]:
    out = [
        "PSS grammar profile -- %s mode" % profile.mode,
        "=" * 72,
        "grammar      src/PSSParser.g4 @ %s" % profile.grammar_sha,
        "corpus       %s @ %s" % (profile.corpus_root or "?", profile.corpus_rev),
        "files        %d (%s lines, %s tokens); %d with syntax errors"
            % (profile.file_count or t.files, _n(t.lines), _n(t.tokens),
               profile.error_file_count or t.files_with_errors),
    ]
    if profile.repeat > 1:
        out.append(
            "repeat       %dx -- SYNTHETIC. Counters below are divided by %d; "
            "not valid as a baseline." % (profile.repeat, profile.repeat))
    out += [
        "",
        "parse wall   %s   prediction %s (%.1f%% of parse, upper bound*)"
            % (_ns(t.parse_wall_ns), _ns(t.prediction_ns),
               100.0 * t.prediction_fraction),
        "lookahead    %s SLL / %s LL tokens over %s predictions"
            % (_n(t.sll_look), _n(t.ll_look), _n(t.invocations)),
        "ATN          %s SLL / %s LL transitions (DFA misses only; %s DFA states)"
            % (_n(t.sll_atn_transitions), _n(t.ll_atn_transitions), _n(t.dfa_size)),
        "signals      %s LL fallbacks, %s ambiguities, %s context sensitivities"
            % (_n(t.ll_fallback), _n(t.ambiguities), _n(t.context_sensitivities)),
        "",
        "* measured under profiling, which adds a clock read per prediction.",
    ]
    if t.prediction_fraction < 0.05 and t.parse_wall_ns:
        out.append(
            "  Prediction is under 5%% of parse time: grammar restructuring "
            "cannot win much here.")
    return out


def decision_table(decisions: List[DecisionSample], top: int) -> List[str]:
    out = [
        "",
        "Top %d decisions by SLL lookahead" % top,
        "-" * 72,
        "%4s  %-28s %9s %7s %10s %8s %6s %5s %4s"
            % ("rank", "rule", "g4:line", "invoc", "look", "look/inv",
               "maxLA", "LLfb", "amb"),
    ]
    for i, d in enumerate(rank(decisions)[:top], start=1):
        out.append("%4d  %-28s %9s %7s %10s %8.1f %6d %5d %4d" % (
            i, d.rule[:28],
            (str(d.grammar_line) if d.grammar_line else "-"),
            _n(d.invocations), _n(d.sll_look), d.look_per_invocation,
            max(d.sll_max_look, d.ll_max_look), d.ll_fallback, d.ambiguities))
    out.append("")
    out.append("look/inv is the structural signal: high invocations with "
               "look/inv near 1 is a decision doing its job.")
    return out


def rule_table(rules: List[RuleRollup], total_look: int, top: int) -> List[str]:
    out = [
        "",
        "Top %d rules by SLL lookahead" % top,
        "-" * 72,
        "%4s  %-28s %9s %6s %7s %10s %6s %5s %4s"
            % ("rank", "rule", "g4:line", "decs", "invoc", "look", "share",
               "LLfb", "amb"),
    ]
    for i, r in enumerate(rules[:top], start=1):
        share = (100.0 * r.sll_look / total_look) if total_look else 0.0
        out.append("%4d  %-28s %9s %6d %7s %10s %5.1f%% %5d %4d" % (
            i, r.rule[:28],
            (str(r.grammar_line) if r.grammar_line else "-"),
            r.decisions, _n(r.invocations), _n(r.sll_look), share,
            r.ll_fallback, r.ambiguities))
    return out


def evidence(decisions: List[DecisionSample], top: int) -> List[str]:
    """Tier 3: the source that provoked each hotspot.

    This is the tier that makes the report a work order.  Events are capped in
    the C++ layer, so a decision with 40 ambiguities shows a handful of
    examples -- the counts in the tables above are the exact figures.
    """
    out = [
        "",
        "Evidence -- source spans behind the top %d decisions" % top,
        "-" * 72,
    ]
    shown = 0
    for d in rank(decisions)[:top]:
        if not d.events:
            continue
        shown += 1
        out.append("")
        out.append("decision %d  %s  (src/PSSParser.g4:%s)"
                   % (d.decision, d.rule, d.grammar_line or "?"))
        for e in d.events:
            out.append("    %-20s %d:%d  %d tokens"
                       % (e.kind, e.start_line, e.start_column, e.token_count))
            if e.text:
                out.append("        %s" % e.text.replace("\n", " ")[:100])
    if not shown:
        out.append("")
        out.append("(no events recorded -- nothing ambiguous, context-sensitive")
        out.append(" or maximally deep in the top decisions)")
    return out


def ambiguity_report(decisions: List[DecisionSample]) -> List[str]:
    """Ambiguities, called out separately because they are not a cost signal.

    ANTLR resolves an ambiguity by silently taking the lowest-numbered
    alternative.  That makes every entry here a place where the grammar says
    two things and the parser picks one without telling anybody -- a
    correctness question that merely happens to surface in the profiler.
    """
    amb = [d for d in decisions if d.ambiguities]
    if not amb:
        return ["", "Ambiguities: none.", ]
    out = [
        "",
        "Ambiguous decisions (%d) -- grammar defects, not merely costs" % len(amb),
        "-" * 72,
    ]
    for d in sorted(amb, key=lambda d: d.ambiguities, reverse=True):
        out.append("  decision %-5d %-28s g4:%-6s %d occurrences"
                   % (d.decision, d.rule[:28], d.grammar_line or "?",
                      d.ambiguities))
        for e in d.events:
            if e.kind == "ambiguity" and e.text:
                out.append("      %d:%d  %s"
                           % (e.start_line, e.start_column,
                              e.text.replace("\n", " ")[:80]))
                break
    return out


def text_report(profile: CorpusProfile, top: int = 25) -> str:
    t = totals(profile.files)
    decisions = merge_decisions(profile.files)
    if profile.repeat > 1:
        from .aggregate import scale
        decisions = scale(decisions, profile.repeat)
    rules = rollup_by_rule(decisions)

    out: List[str] = []
    out += header(profile, t)
    out += decision_table(decisions, top)
    out += rule_table(rules, t.sll_look, top)
    out += ambiguity_report(decisions)
    out += evidence(decisions, top)
    out.append("")
    return "\n".join(out)


def markdown_report(profile: CorpusProfile, top: int = 25) -> str:
    """The same content as a markdown document, for checking in or pasting."""
    t = totals(profile.files)
    decisions = merge_decisions(profile.files)
    if profile.repeat > 1:
        from .aggregate import scale
        decisions = scale(decisions, profile.repeat)
    rules = rollup_by_rule(decisions)

    out = [
        "# PSS grammar profile (%s)" % profile.mode,
        "",
        "| | |",
        "| --- | --- |",
        "| grammar | `src/PSSParser.g4` @ `%s` |" % profile.grammar_sha,
        "| corpus | `%s` @ `%s` |" % (profile.corpus_root, profile.corpus_rev),
        "| files | %d (%s lines, %s tokens) |" % (t.files, _n(t.lines), _n(t.tokens)),
        "| parse wall | %s |" % _ns(t.parse_wall_ns),
        "| prediction | %s (%.1f%% of parse) |"
            % (_ns(t.prediction_ns), 100.0 * t.prediction_fraction),
        "| lookahead | %s SLL / %s LL |" % (_n(t.sll_look), _n(t.ll_look)),
        "| signals | %s LL fallbacks, %s ambiguities |"
            % (_n(t.ll_fallback), _n(t.ambiguities)),
        "",
        "## Top %d decisions" % top,
        "",
        "| rank | rule | g4 | invocations | look | look/inv | maxLA | LLfb | amb |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for i, d in enumerate(rank(decisions)[:top], start=1):
        out.append("| %d | `%s` | %s | %s | %s | %.1f | %d | %d | %d |" % (
            i, d.rule, d.grammar_line or "-", _n(d.invocations), _n(d.sll_look),
            d.look_per_invocation, max(d.sll_max_look, d.ll_max_look),
            d.ll_fallback, d.ambiguities))

    out += ["", "## Top %d rules" % top, "",
            "| rank | rule | g4 | decisions | look | share |",
            "| ---: | --- | ---: | ---: | ---: | ---: |"]
    for i, r in enumerate(rules[:top], start=1):
        share = (100.0 * r.sll_look / t.sll_look) if t.sll_look else 0.0
        out.append("| %d | `%s` | %s | %d | %s | %.1f%% |" % (
            i, r.rule, r.grammar_line or "-", r.decisions, _n(r.sll_look), share))

    out += ["", "## Evidence", "", "```"]
    out += evidence(decisions, top)[3:]
    out += ["```", ""]
    return "\n".join(out)
