/*
 * Rule.h
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
 * A loaded rule and rule set (lint-core-plan.md C4.1; pss-rules-format.md
 * §3). Everything the runner (C5) needs is resolved here, at load: node
 * kinds to reflection classes, expressions to checked ASTs, options to
 * typed values, and the rule's analysis level and scope.
 */
#pragma once
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include "pssp/lint/IRuleSet.h"
#include "pssp/lint/RuleDiagnostic.h"
#include "../cel/CelAst.h"
#include "../cel/CelFunctions.h"
#include "../cel/CelType.h"
#include "../cel/CelValue.h"
#include "../yaml/YamlDoc.h"

namespace pssp {
namespace lint {

class JsonWriter;

namespace rules {

/** A set of node kinds, as written and as reflection classes. */
struct KindSet {
    std::vector<std::string>    names;
    std::vector<uint16_t>       classes;
};

/** `inside:` / `not_inside:` (format §3.2). */
struct AncestorTest {
    bool            present = false;
    KindSet         kind;
    KindSet         stop;       // empty: search to the root
};

/** One declared option (format §3.5; CheckerBase.options_schema's shape). */
struct RuleOption {
    std::string                 name;
    std::string                 type;       // string, int, bool, string-list
    cel::Type                   celType;
    cel::Value                  def;
    std::vector<cel::Value>     choices;
    std::string                 help;
};

/** A named `let:` sub-expression, checked; later ones see earlier ones. */
struct LetBinding {
    std::string     name;
    cel::Type       type;
    cel::ExprUP     expr;
};

/** A literal run of the message, or one `${...}` interpolation. */
struct MessagePart {
    std::string     text;       // the literal, `$${` already reduced to `${`
    cel::ExprUP     expr;       // set for an interpolation
    cel::Type       type;
};

/** A finding an example expects (format §4): `// expect: ID [@ L:C]`. */
struct Expectation {
    std::string     id;
    uint32_t        line = 0;
    uint32_t        col = 0;    // 0: anywhere on the line
};

struct ExampleFile {
    std::string                 name;
    std::string                 text;
    std::vector<Expectation>    expect;
};

struct Example {
    std::string                 name;
    std::vector<ExampleFile>    files;
    yaml::Mark                  mark;
};

class Rule : public virtual IRule {
public:
    virtual const std::string &id() const override { return m_id; }
    virtual const std::string &name() const override { return m_name; }
    virtual const std::string &tier() const override { return m_tier; }
    virtual const std::string &family() const override { return m_family; }
    virtual const char *level() const override { return cel::levelName(m_level); }
    virtual const char *scope() const override { return cel::scopeName(m_scope); }

    void toJson(JsonWriter &w) const;

public:
    std::string                 m_id;
    std::string                 m_name;
    std::string                 m_tier;
    std::string                 m_family;
    std::string                 m_summary;
    std::string                 m_message;
    std::string                 m_doc;
    std::vector<std::string>    m_lrm;
    std::string                 m_since;
    std::string                 m_status = "active";
    std::vector<std::string>    m_aliases;
    std::vector<std::string>    m_replacedBy;
    std::string                 m_severity;         // empty: the tier's
    bool                        m_defaultEnabled = true;

    std::vector<RuleOption>     m_options;

    KindSet                     m_match;
    AncestorTest                m_inside;
    AncestorTest                m_notInside;
    cel::Type                   m_nodeType;         // the nearest common base of m_match

    std::vector<LetBinding>     m_lets;
    cel::ExprUP                 m_where;            // null: true
    cel::ExprUP                 m_report;           // null: [node]
    cel::Type                   m_findingType;
    std::vector<MessagePart>    m_messageParts;

    std::vector<Example>        m_examples;

    cel::Level                  m_level = cel::Level::L0;
    cel::Scope                  m_scope = cel::Scope::File;
    // Every library overload the rule's expressions can call, in
    // registration order: what m_level and m_scope come from.
    std::vector<const cel::Overload *>  m_calls;

    std::string                 m_file;
    yaml::Mark                  m_mark;             // the rule's mapping
};
using RuleUP = std::unique_ptr<Rule>;

class RuleSet : public virtual IRuleSet {
public:
    RuleSet(const std::string &name, bool builtin) : m_name(name), m_builtin(builtin) { }

    virtual const std::string &name() const override { return m_name; }
    virtual uint32_t numRules() const override { return static_cast<uint32_t>(m_rules.size()); }
    virtual const IRule *getRule(uint32_t idx) const override {
        return (idx < m_rules.size()) ? m_rules[idx].get() : nullptr;
    }
    virtual bool builtin() const override { return m_builtin; }

public:
    std::string                 m_name;
    bool                        m_builtin;
    int32_t                     m_version = 1;
    std::vector<RuleUP>         m_rules;
};
using RuleSetUP = std::unique_ptr<RuleSet>;

/** Where a rule claimed an ID or name. */
struct RuleClaim {
    std::string                 file;
    yaml::Mark                  mark;
    std::string                 rule;           // the claiming rule's ID
    std::string                 what;           // "ID", "alias" or "name"
};

/**
 * The IDs and names claimed across every file an engine has loaded (format
 * §5): an ID or alias is unique among IDs and aliases, a name among names.
 */
struct RuleClaims {
    std::map<std::string, RuleClaim>    ids;
    std::map<std::string, RuleClaim>    names;
};

/** Writes diagnostics as the JSON array ILintEngine::diagnosticsJson() returns. */
void diagnosticsToJson(JsonWriter &w, const std::vector<RuleDiagnostic> &diags);

}
}
}
