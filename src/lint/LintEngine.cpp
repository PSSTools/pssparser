/*
 * LintEngine.cpp
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
 */
#include "LintEngine.h"
#include "rules/BuiltinRules.h"
#include "rules/RuleLoader.h"
#include "util/JsonWriter.h"

namespace pssp {
namespace lint {

LintEngine::LintEngine() { }

LintEngine::~LintEngine() { }

const IRuleSet *LintEngine::loadRules(const LintSource &src, bool builtin) {
    rules::RuleSetUP set = rules::loadRuleFile(src, builtin, m_claims, m_diagnostics);
    if (!set) {
        return nullptr;
    }
    m_rulesets.push_back(std::move(set));
    return m_rulesets.back().get();
}

uint32_t LintEngine::loadBuiltinRules() {
    if (m_builtinLoaded) {
        return 0;
    }
    m_builtinLoaded = true;
    uint32_t n = 0;
    for (const rules::BuiltinRuleFile *f = rules::builtinRuleFiles(); f->name; f++) {
        LintSource src;
        src.name = f->name;
        src.text.assign(f->text, f->size);
        if (loadRules(src, true)) {
            n++;
        }
    }
    return n;
}

uint32_t LintEngine::numBuiltinRuleFiles() const {
    uint32_t n = 0;
    for (const rules::BuiltinRuleFile *f = rules::builtinRuleFiles(); f->name; f++) {
        n++;
    }
    return n;
}

RuleProbe LintEngine::probeRules(const std::string &text) const {
    return rules::probeRuleText(text);
}

std::string LintEngine::diagnosticsJson() const {
    JsonWriter w;
    rules::diagnosticsToJson(w, m_diagnostics);
    return w.str();
}

std::vector<const rules::Rule *> LintEngine::ruleList() const {
    std::vector<const rules::Rule *> out;
    for (const rules::RuleSetUP &s : m_rulesets) {
        for (const rules::RuleUP &r : s->m_rules) {
            out.push_back(r.get());
        }
    }
    return out;
}

std::string LintEngine::rulesJson() const {
    JsonWriter w;
    w.beginArray();
    for (const rules::RuleSetUP &s : m_rulesets) {
        for (const rules::RuleUP &r : s->m_rules) {
            r->toJson(w);
        }
    }
    w.endArray();
    return w.str();
}

}
}
