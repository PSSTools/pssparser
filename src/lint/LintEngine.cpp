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
#include <memory>
#include <unordered_map>
#include "LintEngine.h"
#include "Reflect.h"
#include "pssp/IMarker.h"
#include "pssp/ast/IScopeChild.h"
#include "run/Runner.h"
#include "yaml/YamlDoc.h"
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

namespace {

const char *severityName(MarkerSeverityE s) {
    switch (s) {
        case MarkerSeverityE::Error: return "error";
        case MarkerSeverityE::Warn: return "warning";
        case MarkerSeverityE::Info: return "info";
        default: return "hint";
    }
}

void markerJson(JsonWriter &w, const IMarker &m) {
    const ast::Location &l = m.loc();
    w.beginObject();
    w.kv("severity", severityName(m.severity())).kv("message", m.msg());
    w.kv("fileid", static_cast<int64_t>(l.fileid)).kv("line", static_cast<int64_t>(l.lineno));
    w.kv("col", static_cast<int64_t>(l.linepos)).kv("extent", static_cast<int64_t>(l.extent));
    w.key("related").beginArray().endArray();
    w.kv("code", m.id());
    w.endObject();
}

}

std::string LintEngine::run(const std::vector<ast::IScopeChild *> &roots,
        const std::string &requestJson) {
    using NK = yaml::Node::Kind;
    JsonWriter w;
    yaml::NodeUP req;
    try {
        req = yaml::parse("<lint request>", requestJson);
    } catch (const yaml::YamlError &e) {
        req.reset();
        w.beginObject().kv("ok", false).kv("error", std::string(e.what())).endObject();
        return w.str();
    }
    if (!req || (req->kind != NK::Map && req->kind != NK::Null)) {
        w.beginObject().kv("ok", false).kv("error", "the request is not a JSON object")
            .endObject();
        return w.str();
    }
    std::vector<std::string> problems;

    std::vector<const rules::Rule *> all = ruleList();
    std::unordered_map<std::string, const rules::Rule *> byId;
    for (const rules::Rule *r : all) {
        byId.emplace(r->m_id, r);
    }

    // The enabled rules, in load order.
    std::vector<const rules::Rule *> on;
    const yaml::Node *en = req->get("enabled");
    if (!en || en->kind == NK::Null) {
        on = all;
    } else if (en->kind == NK::Seq) {
        std::unordered_map<const rules::Rule *, bool> want;
        for (const yaml::NodeUP &i : en->items) {
            auto it = byId.find(i->s);
            if (i->kind == NK::String && it != byId.end()) {
                want[it->second] = true;
            } else {
                problems.push_back("enabled: no rule '" + i->s + "' is loaded");
            }
        }
        for (const rules::Rule *r : all) {
            if (want.count(r)) {
                on.push_back(r);
            }
        }
    } else {
        problems.push_back("enabled: not a list of rule IDs");
    }

    run::RunOptions opts;
    if (const yaml::Node *ms = req->get("max_steps")) {
        if (ms->kind == NK::Int && ms->i > 0) {
            opts.maxSteps = static_cast<uint64_t>(ms->i);
        } else {
            problems.push_back("max_steps: not a positive integer");
        }
    }
    if (const yaml::Node *ov = req->get("options")) {
        for (const yaml::Node::Member &rm : ov->members) {
            auto it = byId.find(rm.key);
            if (it == byId.end()) {
                problems.push_back("options: no rule '" + rm.key + "' is loaded");
                continue;
            }
            const rules::Rule *r = it->second;
            for (const yaml::Node::Member &om : rm.value->members) {
                const rules::RuleOption *o = nullptr;
                for (const rules::RuleOption &c : r->m_options) {
                    if (c.name == om.key) {
                        o = &c;
                    }
                }
                cel::Value v;
                if (!o) {
                    problems.push_back("options: rule " + rm.key + " has no option '"
                        + om.key + "'");
                } else if (!rules::optionValue(*o, om.value.get(), v)) {
                    problems.push_back("options: " + rm.key + "." + om.key + " must be "
                        + o->type);
                } else {
                    opts.options[r].emplace_back(om.key, std::move(v));
                }
            }
        }
    }
    uint32_t gateErrors = 0;
    if (const yaml::Node *g = req->get("gate_errors")) {
        if (g->kind == NK::Int && g->i >= 0) {
            gateErrors = static_cast<uint32_t>(g->i);
        } else {
            problems.push_back("gate_errors: not a non-negative integer");
        }
    }

    run::Runner runner(on, opts);
    std::unique_ptr<IMarker> skipped;
    if (gateErrors && !on.empty()) {
        skipped.reset(run::Runner::skippedMarker(gateErrors));
    } else if (!gateErrors) {
        // Every file first: navigation may cross from one file to another.
        for (ast::IScopeChild *r : roots) {
            runner.index(ast::reflect::classify(r));
        }
        for (ast::IScopeChild *r : roots) {
            runner.run(ast::reflect::classify(r));
        }
    }

    w.beginObject();
    w.kv("ok", true);
    w.key("markers").beginArray();
    if (skipped) {
        markerJson(w, *skipped);
    }
    for (const run::Finding &f : runner.findings()) {
        std::unique_ptr<IMarker> m(run::Runner::toMarker(f));
        markerJson(w, *m);
    }
    for (const run::RuleFailure &f : runner.failures()) {
        std::unique_ptr<IMarker> m(run::Runner::toMarker(f));
        markerJson(w, *m);
    }
    w.endArray();
    w.key("stats").beginArray();
    for (size_t i=0; i<on.size(); i++) {
        const run::RuleStats &s = runner.stats()[i];
        w.beginObject();
        w.kv("id", on[i]->m_id).kv("matches", s.matches).kv("findings", s.findings);
        w.kv("steps", s.steps).kv("ns", s.ns).kv("errors", s.errors);
        w.endObject();
    }
    w.endArray();
    w.key("problems").beginArray();
    for (const std::string &p : problems) {
        w.value(p);
    }
    w.endArray();
    w.endObject();
    return w.str();
}

}
}
