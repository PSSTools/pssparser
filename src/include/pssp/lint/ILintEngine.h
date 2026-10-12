/*
 * ILintEngine.h
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
 * The C++ lint engine (lint-core-plan.md): loads pss-rules files and runs
 * them over a linked model. One engine per host session; it owns the rule
 * sets loaded into it.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include "pssp/lint/IRuleSet.h"
#include "pssp/lint/LintRequest.h"
#include "pssp/lint/RuleDiagnostic.h"

namespace pssp {
namespace ast {
class IRootSymbolScope;
class IScopeChild;
}
namespace lint {

/**
 * Whether a text is a rule file (pss-rules-format.md §6.2), as
 * ILintEngine::probeRules() decides it.
 */
enum class RuleProbe {
    RuleFile,       // a top-level `pss-rules` key (or, in text that is not
                    // valid YAML, a line that starts one)
    Empty,          // nothing but comments and white space
    NotYaml,        // not valid YAML, and no line starts `pss-rules:`
    NotMapping,     // the top level is a scalar or a list
    NoKey           // a mapping without `pss-rules`
};

class ILintEngine;
using ILintEngineUP=std::unique_ptr<ILintEngine>;
class ILintEngine {
public:
    virtual ~ILintEngine() { }

    /** The pss-rules format version this engine reads (the `version:` key). */
    virtual int32_t ruleFormatVersion() const = 0;

    virtual uint32_t numRuleSets() const = 0;

    virtual const IRuleSet *getRuleSet(uint32_t idx) const = 0;

    /**
     * Loads one rule file (C4.1). Problems are added to diagnostics(); a bad
     * rule is left out and the rest of the file loads. Returns the rule set,
     * or null when the file as a whole is refused (not a rule file, YAML
     * errors, an unsupported version). `builtin` applies the built-in rules'
     * requirements (format §3.1: family, doc, examples).
     */
    virtual const IRuleSet *loadRules(const LintSource &src, bool builtin=false) = 0;

    /**
     * Loads the built-in rule files embedded in the core (rules/ in the
     * repository; format §6.2), with the built-in requirements. Loads them
     * once: a second call does nothing. Returns the number of built-in files
     * loaded by this call.
     */
    virtual uint32_t loadBuiltinRules() = 0;

    /** The number of built-in rule files embedded in the core. */
    virtual uint32_t numBuiltinRuleFiles() const = 0;

    /**
     * Decides whether `text` is a rule file, for a host listing a directory
     * (format §6.2: files without `pss-rules` are skipped). Loads nothing and
     * reports nothing. A file that is not valid YAML still counts as a rule
     * file when a line starts `pss-rules:`, so that loadRules() reports its
     * YAML errors rather than the host skipping it in silence.
     */
    virtual RuleProbe probeRules(const std::string &text) const = 0;

    /** Every diagnostic from every loadRules() call, in order. */
    virtual const std::vector<RuleDiagnostic> &diagnostics() const = 0;

    /** diagnostics() as JSON: [{"code","severity","message","file","line","col",...}] */
    virtual std::string diagnosticsJson() const = 0;

    /**
     * Every loaded rule, with its metadata, match, computed level and scope,
     * options and examples, as JSON: [{"id","name",...}]. The shape is the
     * one the Python metadata view (C4.4) and the WASM API (C4.3) read.
     */
    virtual std::string rulesJson() const = 0;

    /**
     * Runs the loaded rules over the trees under `roots`, one GlobalScope
     * per file the host owns (lint-core-plan.md C5.4). The request is JSON:
     *   {"enabled": ["ID", ...],          absent or null: every loaded rule
     *    "options": {"ID": {"name": value}},   overriding `default:`
     *    "max_steps": N,                  per rule per file; absent: 10^6
     *    "gate_errors": N,                > 0: run nothing (the gate)
     *    "files": {"<fileid>": "path"},   the host's file names (C6.9)
     *    "base_dir": "dir",               file_of() paths relative to it
     *    "selection": {...}}              instead of enabled and options:
     *                                     resolveSelection()'s input; each
     *                                     file runs and reports the rules
     *                                     enabled for its path (C7.1)
     * The result is JSON:
     *   {"ok":true,"markers":[{"severity","message","fileid","line","col",
     *    "extent","related":[],"code"}],"stats":[{"id","matches","findings",
     *    "steps","ns","errors"}],"index_ns":N,"problems":["..."]}
     * `index_ns` is the time spent building the library's indexes (parent
     * links, symbol occurrences): the run's, in no rule's `ns` (C8).
     * Markers are the findings (walk order) then the rule failures
     * (PSSP220, PSSP221); with `gate_errors` > 0 and a rule enabled, the one
     * PSSP230 marker (no location: fileid -1). Messages carry no "[ID]"
     * prefix. `problems` lists request entries that were ignored: an
     * unknown ID or option, or a value of the wrong type. A request that is
     * not a JSON object gives {"ok":false,"error":"..."}.
     *
     * `model` is the linked root the files belong to (C6.2): the symbol
     * functions (resolves_to, refs, ...) read it, and navigation reaches
     * the model's other files through it. Without one (an unlinked parse),
     * the rules that need symbols (level L1 or above) are not run, and
     * each is listed in `problems`.
     */
    virtual std::string run(const std::vector<ast::IScopeChild *> &roots,
        const std::string &requestJson, ast::IRootSymbolScope *model=nullptr) = 0;

    /**
     * The host's own markers, for selection (lint-core-plan.md C7.1): what a
     * selector, `[severity]` key or `-W` group may name besides the loaded
     * rules (the LRM, tool and core lint markers, a host's plug-in rules).
     * JSON: {"markers": [{"id", "name", "tier", "family", "since", "status",
     * "severity", "aliases", "replaced_by", "default_enabled", "minimal"}],
     * "refused": ["ID", ...]}. Only "id" is required. A loaded rule with a
     * host marker's ID, or listed in "refused", is left out of selection.
     * The markers are added to the embedded catalogue's (C7.3; see
     * catalogJson()): an entry with a core marker's ID replaces it where it
     * stands, others are appended. Replaces an earlier call's markers.
     * Returns the problems, as a JSON list of strings.
     */
    virtual std::string setHostMarkers(const std::string &json) = 0;

    /**
     * Resolves a rule selection (C7.1; lint-framework L3, F2.5): profile,
     * select and ignore, the per-path overrides, the command line's layer,
     * `[severity]` and `-W` groups. The input is the configuration as JSON
     * (pipeline/Selection.h) plus "paths", the files to place. The result:
     *   {"ok": true,
     *    "errors": [{"key", "text", "message"}],    unknown selectors, rules
     *    "lint_ids": [...],                          every lint rule
     *    "groups": [{"overrides": [i...], "profile", "enabled": [...],
     *                "explicit": [...], "held_back": [...],
     *                "options": {ID: {name: value}}}],
     *    "paths": [{"path", "rel", "group"}],
     *    "severity": {ID: {"severity", "key"}},
     *    "warnings": {"error": [...], "error_info", "spelling": {ID: key},
     *                 "no_error": [...]}}
     * Group 0 is the files no override matches. Input that is not JSON
     * gives {"ok": false, "error": "..."}.
     */
    virtual std::string resolveSelection(const std::string &json) = 0;

    /**
     * Collects the source waivers in the host's files (lint-core-plan.md
     * C7.2; docs/waivers.rst): `// pssparser waive` comments in each file's
     * text, and `@lint_pkg::waive` annotations in `roots` (the GlobalScope
     * of each file; none for a run without an AST). The request is JSON:
     *   {"texts": {"path": "source", ...},     the files, with their text
     *    "files": {"<fileid>": "path"}}        roots' paths; a root whose
     *                                          path is not in "texts" is
     *                                          skipped
     * The result: {"ok": true, "waivers": [{"form", "file", "line", "col",
     * "selectors", "reason", "start": [line, col], "end": [line, col]}]},
     * sorted by (file, line, col); "end" is exclusive, and 2^30 stands for
     * "the end of the line" or "the end of the file".
     */
    virtual std::string collectWaivers(const std::vector<ast::IScopeChild *> &roots,
        const std::string &requestJson) = 0;

    /**
     * Applies waivers (C7.2): which diagnostics they waive, and the waiver
     * hygiene markers (PSSP202-205, PSSP004). Selectors resolve against the
     * host markers (setHostMarkers()) and the loaded rules. The request:
     *   {"waivers": [...],                     collectWaivers()'s
     *    "diagnostics": [{"code", "file", "line", "col"}],
     *    "ran": ["ID", ...]}                   codes whose rule ran; absent
     *                                          or null: unknown, and no
     *                                          waiver is reported unused
     * A diagnostic's file and a waiver's are compared as given. The result:
     *   {"ok": true, "kept": [i, ...], "waived": [[i, w], ...],
     *    "waivers": [... with "ids" and "used"],
     *    "markers": [{"severity", "message", "file", "line", "col", "code",
     *                 "extent": -1, "related": []}]}
     * `i` indexes "diagnostics" and `w` "waivers".
     */
    virtual std::string applyWaivers(const std::string &requestJson) = 0;

    /**
     * Finishes a run's diagnostics as the CLI does before printing them
     * (lint-core-plan.md C7.4): the parse, link and rule markers in, what
     * to report out. The stages, in order:
     *   select    a lint code not enabled for its file's group, or (with
     *             "owned") in a file not owned, is dropped; other codes
     *             are never filtered
     *   severity  `[severity]` by ID; "off" drops. No code, PSSP000 and a
     *             core error are never changed
     *   waive     applyWaivers(); its hygiene markers get the severity map
     *             and join the diagnostics
     *   policy    --no-warnings drops warnings; then -Wno-error,
     *             -Werror=ID|group, -Werror=info, -Werror promote
     * The request:
     *   {"diagnostics": [{"code", "severity", "file", "line", "col"}],
     *    "selection": {...},              resolveSelection()'s input; its
     *                                     "warnings" may also hold
     *                                     "error": true and "none": true
     *    "stages": [...],                 absent: all four
     *    "owned": [path...],              absent or null: no ownership check
     *    "waivers": [...],                collectWaivers()'s
     *    "ran": [ID...] | "auto" | null,  "auto": the core's active markers
     *                                     and the loaded rules some file of
     *                                     "paths" enables, less "off"
     *    "paths": [path...],              the run's files, for "auto"
     *    "policy": {"error_all", "error_info", "none", "error": [ID],
     *               "no_error": [ID], "spelling": {ID: selector}}}
     *                                     instead of the selection's
     *                                     "warnings", already resolved
     * Paths are compared as given. The result:
     *   {"ok": true,
     *    "diagnostics": [{"index", "severity", "original_severity"?,
     *                     "werror"?}],    the kept ones, in order; then the
     *                                     hygiene markers, with "index" -1
     *                                     and "code", "message", "file",
     *                                     "line", "col", "extent", "related"
     *    "waived": [{"index", "severity", "waiver"}],
     *    "waivers": [... with "ids" and "used"],
     *    "dropped": {"outside": N},
     *    "problems": ["..."]}
     * `index` is into "diagnostics" and `waiver` into "waivers".
     */
    virtual std::string finish(const std::string &requestJson) = 0;

    /**
     * The marker catalogue (lint-core-plan.md C7.3), for an editor's hover,
     * `codeDescription` and quick-info: every marker the engine knows, the
     * embedded core catalogue's (PSS, PSSP and core LINT, generated from the
     * Python MarkerDefs), then the host's (setHostMarkers()), then the loaded
     * rules'. JSON:
     *   {"schema": "pssparser-catalog/1",
     *    "taxonomy": {"tiers": [[tier, severity]], "families", "profiles",
     *                 "default_profile", "profile_tiers": {profile: [tier]},
     *                 "doc_url"},
     *    "markers": [{"id", "name", "tier", "family", "since", "status",
     *                 "severity" (the effective one), "aliases",
     *                 "replaced_by", "default_enabled", "minimal",
     *                 "summary", "detail", "lrm", "doc_url",
     *                 "source": "core" | "rules" | "host"}]}
     * A loaded rule's summary and detail are its `summary` and `doc`; a
     * host-only marker has none. Retired and reserved codes are included.
     */
    virtual std::string catalogJson() const = 0;

    /**
     * The code the catalogue's message patterns give a core marker's
     * message (C7.3); "" when none matches. The core's marker collector
     * already sets it on every marker that carries none; this is for a
     * message that reached the host some other way.
     */
    virtual std::string coreCode(const std::string &message) const = 0;
};

}
}
