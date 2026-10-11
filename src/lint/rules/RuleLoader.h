/*
 * RuleLoader.h
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
 * The pss-rules loader (lint-core-plan.md C4.1; pss-rules-format.md §2-§6).
 *
 * Turns one (name, text) rule file into a RuleSet, reporting every problem
 * as a PSSP21x diagnostic located in the file. Nothing in the input makes it
 * throw. A problem in one rule disables that rule only; the file as a whole
 * is refused only when it is not a rule file at all, cannot be read as YAML,
 * or declares a version this loader does not read.
 *
 * Every field a rule can have is listed once, in ruleFields(): the loader
 * validates against it, and the JSON Schema (C4.4) is generated from it.
 */
#pragma once
#include <string>
#include <vector>
#include "pssp/lint/ILintEngine.h"
#include "pssp/lint/LintRequest.h"
#include "pssp/lint/RuleDiagnostic.h"
#include "Rule.h"

namespace pssp {
namespace lint {
namespace rules {

/** The diagnostic codes (lint-core-plan.md §6). */
namespace code {
constexpr const char *FileStructure     = "PSSP210";    // rule-file-structure
constexpr const char *UnknownKey        = "PSSP211";    // rule-unknown-key
constexpr const char *FieldInvalid      = "PSSP212";    // rule-field-invalid
constexpr const char *UnknownKind       = "PSSP213";    // rule-unknown-kind
constexpr const char *ExprSyntax        = "PSSP214";    // rule-expression-syntax
constexpr const char *ExprType          = "PSSP215";    // rule-expression-type
constexpr const char *ExprLimit         = "PSSP216";    // rule-expression-limit
constexpr const char *IdConflict        = "PSSP217";    // rule-id-conflict (C4.2)
constexpr const char *FileYaml          = "PSSP218";    // rule-file-yaml
constexpr const char *HelperShadowed    = "PSSP219";    // rule-helper-shadowed (info)
}

/** How a field's value is written (format §3.1). */
enum class FieldType {
    String,         // any string
    Line,           // a one-line string, not interpolated (summary)
    Kebab,          // a kebab-case name
    Enum,           // one of FieldSpec::values
    StringList,     // a list of strings
    Code,           // a marker ID the rule owns (format §5.1)
    CodeList,       // a list of marker IDs
    Bool,
    Version,        // "YYYY.N", as a string
    Template,       // a message template, with ${CEL}
    Cel,            // one CEL expression
    Options,        // name -> option spec
    Match,          // the structural selector
    Defines,        // helper head -> CEL
    Lets,           // name -> CEL, in order
    Examples,       // a list of examples
    Reserved        // refused in this version (fix:)
};

/** When a field must be present. */
enum class Need {
    Optional,
    Required,
    Builtin,        // required in a built-in rule file
    Nursery         // required when the rule's tier is nursery
};

struct FieldSpec {
    const char                  *name;
    FieldType                   type;
    Need                        need;
    bool                        defaultable;    // may be set under `defaults:`
    std::vector<std::string>    values;         // Enum
    const char                  *doc;
};

/** Every field a rule object can have, in the order of format §3.1. */
const std::vector<FieldSpec> &ruleFields();

/** The option types (format §3.5): string, int, bool, string-list. */
const std::vector<std::string> &optionTypes();

/**
 * The JSON Schema of a rule file (C4.4; format §6.4), written from
 * ruleFields() and the reflection tables (RuleSchema.cpp).
 */
std::string rulesSchemaJson();

/**
 * The length of the marker ID at `s[i]` (`NS000` or `NS-TEAM000`, format
 * §5.1), or 0 when there is none.
 */
size_t codeAt(const std::string &s, size_t i);

/** The namespace of a well-formed marker ID: `ACME-NET` for `ACME-NET001`. */
std::string namespaceOf(const std::string &code);

/** True for `PSS`, `PSSP`, `PSSX` and `LINT`, which only pssparser may use. */
bool isReservedNamespace(const std::string &ns);

/** Whether `text` is a rule file (ILintEngine::probeRules()). */
RuleProbe probeRuleText(const std::string &text);

/**
 * Loads one rule file, appending its diagnostics to `diags`. Returns null if
 * the file as a whole is refused. `claims` holds the IDs and names of the
 * files loaded before; this file's are added to it.
 */
RuleSetUP loadRuleFile(const LintSource &src, bool builtin, RuleClaims &claims,
        std::vector<RuleDiagnostic> &diags);

}
}
}
