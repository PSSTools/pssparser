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
};

}
}
