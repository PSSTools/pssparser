/*
 * Runner.h
 *
 * Copyright 2026 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License.
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Rule evaluation and findings (lint-core-plan.md C5.2; pss-rules-format.md
 * §3.1, §3.4).
 *
 * For each (rule, node) match the walk offers (Walker.h):
 * - `node` and each `options.<name>` are bound; the `let:` bindings are
 *   evaluated in order, each seeing the ones before it; then `where:`, then
 *   `report:` (omitted: `[node]`).
 * - Each reported node is one finding, bound as `finding` while the message
 *   is rendered. A rule reports a node at most once in a run, so two matches
 *   reporting the same node give one finding.
 * - An unset element in `report:` (null) is skipped.
 *
 * Failures (C5.3; lint-rule-expressions.md §5). Each rule has a budget of
 * evaluation steps per file (per root run), shared by all its expressions.
 * An error result of `where:`, `report:` or a message interpolation, or
 * running out of budget anywhere, is one RuleFailure (PSSP220, PSSP221)
 * naming the rule and the node, and the rule is skipped for the rest of
 * that file; the other rules continue. A finding whose message failed is
 * kept, with `?` for the failed part. An erroring `let:` fails only through
 * what uses it.
 *
 * A finding's location is the reported node's own; most expressions have
 * none, so then the first located node under it (pre-order: where the
 * expression starts), else its nearest located ancestor.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include "pssp/IMarker.h"
#include "pssp/ast/Location.h"
#include "../cel/CelAst.h"
#include "../cel/CelValue.h"
#include "Walker.h"

namespace pssp {
namespace lint {
namespace run {

struct Finding {
    const rules::Rule   *rule = nullptr;
    rf::Node            node;
    std::string         message;
    MarkerSeverityE     severity = MarkerSeverityE::Warn;
    ast::Location       loc;            // lineno -1: no location found
};

/** A rule that failed in a file: PSSP220 (an error) or PSSP221 (budget). */
struct RuleFailure {
    const rules::Rule   *rule = nullptr;
    const char          *code = "";         // "PSSP220", "PSSP221"
    std::string         in;                 // "let", "where", "report", "message"
    std::string         error;              // the error value's message
    rf::Node            node;               // the match being evaluated
    ast::Location       loc;
    std::string         message;            // the marker's text
};

/** What one rule did in a run: counts, steps, time, and its first error. */
struct RuleStats {
    uint64_t            matches = 0;        // evaluated (not counting skipped)
    uint64_t            findings = 0;
    uint64_t            steps = 0;          // across files
    uint64_t            ns = 0;             // evaluation time, across files
    uint64_t            errors = 0;         // failures: at most one per file
    // The first failure: where it arose ("let", "where", "report", "message") and
    // the error value's message, at node `errorNode`.
    std::string         errorIn;
    std::string         error;
    rf::Node            errorNode;
};

struct RunOptions {
    // Evaluation steps per rule per file. Q-E5: the real number comes from C8.
    uint64_t            maxSteps = 1000000;
    // Option values the host set (`[lint.rule.<name>]`), by rule; an option
    // not listed takes its `default:`.
    std::unordered_map<const rules::Rule *,
        std::vector<std::pair<std::string, cel::Value>>>    options;
};

/** The severity a rule's findings get: its `severity:`, else its tier's. */
MarkerSeverityE ruleSeverity(const rules::Rule &r);

class Runner {
public:
    /**
     * `rules` are the enabled rules, in load order; they must outlive the
     * runner. A rule not given is never evaluated.
     */
    explicit Runner(const std::vector<const rules::Rule *> &rules,
        const RunOptions &opts=RunOptions());
    ~Runner();

    /**
     * Walks and evaluates the tree under `root`. Call once per owned root:
     * each is a file, with its own budget per rule.
     */
    void run(const rf::Node &root);

    /** The rule failures so far, at most one per rule per file. */
    const std::vector<RuleFailure> &failures() const { return m_failures; }

    /** The findings so far: walk order, then rule order, then report order. */
    const std::vector<Finding> &findings() const { return m_findings; }

    /** Per rule, in the order the rules were given. */
    const std::vector<RuleStats> &stats() const { return m_stats; }

    const Walker &walker() const { return m_walker; }

    /** A finding as a marker, with the rule's ID. The caller owns it. */
    static IMarker *toMarker(const Finding &f);

    /** A failure as a PSSP220/PSSP221 marker at the node. The caller owns it. */
    static IMarker *toMarker(const RuleFailure &f);

    /**
     * The gate (design L8.1): lint runs only when parse, link and the
     * semantic checks reported no error. With `nErrors` > 0 the caller does
     * not run the rules, and reports this PSSP230 info marker instead
     * ("lint skipped: N errors"). The caller owns it.
     */
    static IMarker *skippedMarker(uint32_t nErrors);

    /**
     * A node as a message shows it (format §3.4). Until decl_path (C6.2): a
     * declaration's name, an identifier's or literal's text, else
     * "Kind at L:C".
     */
    std::string renderNode(const rf::Node &n);

    /** A node in a failure message: "Action 'A'", else renderNode()'s "Kind at L:C". */
    std::string describeNode(const rf::Node &n);

private:
    using Vars = std::vector<std::pair<std::string, cel::Value>>;

    // A rule's state in the file being run.
    struct FileState {
        uint64_t        steps = 0;
        bool            failed = false;
    };

    void match(const rules::Rule &r, const rf::Node &n);
    void evaluate(size_t idx, const rules::Rule &r, const rf::Node &n);
    cel::Value eval(const cel::Expr *e, const Vars &vars, size_t idx, bool &overrun);
    std::string renderMessage(size_t idx, const rules::Rule &r, const rf::Node &finding,
        Vars &vars);
    void fail(size_t idx, const rules::Rule &r, const char *in, const cel::Value &v,
        bool overrun, const rf::Node &n);
    ast::Location locate(const rf::Node &n);
    const ast::Location &firstLocated(const rf::Node &n);

private:
    RunOptions                                          m_opts;
    Dispatch                                            m_dispatch;
    Walker                                              m_walker;
    std::unordered_map<const rules::Rule *, size_t>     m_index;
    std::vector<RuleStats>                              m_stats;
    std::vector<FileState>                              m_file;      // per rule
    std::vector<Finding>                                m_findings;
    std::vector<RuleFailure>                            m_failures;
    std::set<std::pair<const void *, const void *>>     m_reported;  // (rule, node)
    std::unordered_map<const void *, ast::Location>     m_located;   // firstLocated() memo
};

}
}
}
