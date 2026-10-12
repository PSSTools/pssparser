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
#include <cstdlib>
#include <map>
#include <memory>
#include <set>
#include <unordered_map>
#include "LintEngine.h"
#include "Reflect.h"
#include "pssp/IMarker.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/impl/NodeKind.h"
#include "pssp/ast/IScopeChild.h"
#include "run/Runner.h"
#include "yaml/YamlDoc.h"
#include "pipeline/Waivers.h"
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

std::string LintEngine::setHostMarkers(const std::string &json) {
    using NK = yaml::Node::Kind;
    std::vector<std::string> problems;
    m_hostMarkers.clear();
    m_refused.clear();
    yaml::NodeUP doc;
    try {
        doc = yaml::parse("<host markers>", json);
    } catch (const yaml::YamlError &e) {
        problems.push_back(e.what());
    }
    auto strings = [&](const yaml::Node *n, const std::string &what,
            std::vector<std::string> &out) {
        if (!n || n->kind == NK::Null) {
            return;
        }
        if (n->kind != NK::Seq) {
            problems.push_back(what + ": not a list of strings");
            return;
        }
        for (const yaml::NodeUP &i : n->items) {
            if (i->kind == NK::String) {
                out.push_back(i->s);
            } else {
                problems.push_back(what + ": not a list of strings");
            }
        }
    };
    const yaml::Node *ms = doc ? doc->get("markers") : nullptr;
    if (ms && ms->kind == NK::Seq) {
        for (const yaml::NodeUP &m : ms->items) {
            const yaml::Node *id = m->get("id");
            if (!id || id->kind != NK::String) {
                problems.push_back("markers: an entry without an \"id\"");
                continue;
            }
            pipeline::MarkerMeta mm;
            mm.id = id->s;
            for (auto f : std::vector<std::pair<const char *, std::string *>>{
                    {"name", &mm.name}, {"tier", &mm.tier}, {"family", &mm.family},
                    {"since", &mm.since}, {"status", &mm.status},
                    {"severity", &mm.severity}}) {
                const yaml::Node *v = m->get(f.first);
                if (v && v->kind == NK::String) {
                    *f.second = v->s;
                } else if (v && v->kind != NK::Null) {
                    problems.push_back("markers: " + mm.id + "." + f.first + ": not a string");
                }
            }
            strings(m->get("aliases"), "markers: " + mm.id + ".aliases", mm.aliases);
            strings(m->get("replaced_by"), "markers: " + mm.id + ".replaced_by", mm.replacedBy);
            for (auto f : std::vector<std::pair<const char *, bool *>>{
                    {"default_enabled", &mm.defaultEnabled}, {"minimal", &mm.minimal}}) {
                const yaml::Node *v = m->get(f.first);
                if (v && v->kind == NK::Bool) {
                    *f.second = v->b;
                } else if (v && v->kind != NK::Null) {
                    problems.push_back("markers: " + mm.id + "." + f.first + ": not a boolean");
                }
            }
            m_hostMarkers.push_back(mm);
        }
    } else if (ms && ms->kind != NK::Null) {
        problems.push_back("markers: not a list");
    }
    std::vector<std::string> refused;
    strings(doc ? doc->get("refused") : nullptr, "refused", refused);
    m_refused.insert(refused.begin(), refused.end());

    JsonWriter w;
    w.beginArray();
    for (const std::string &p : problems) {
        w.value(p);
    }
    w.endArray();
    return w.str();
}

std::string LintEngine::resolveSelection(const std::string &json) {
    using NK = yaml::Node::Kind;
    JsonWriter w;
    yaml::NodeUP doc;
    try {
        doc = yaml::parse("<selection>", json);
    } catch (const yaml::YamlError &e) {
        w.beginObject().kv("ok", false).kv("error", std::string(e.what())).endObject();
        return w.str();
    }
    if (!doc || (doc->kind != NK::Map && doc->kind != NK::Null)) {
        w.beginObject().kv("ok", false).kv("error", "the selection is not a JSON object")
            .endObject();
        return w.str();
    }
    pipeline::Catalogue cat(m_hostMarkers, m_refused, ruleList());
    pipeline::Selection sel(cat, *doc);
    std::vector<std::string> paths;
    if (const yaml::Node *ps = doc->get("paths")) {
        for (const yaml::NodeUP &p : ps->items) {
            if (p->kind == NK::String) {
                paths.push_back(p->s);
            }
        }
    }
    sel.toJson(w, paths);
    return w.str();
}

namespace {

// A request that is JSON: the object, or null with {"ok": false} written.
yaml::NodeUP parseRequest(const char *name, const std::string &json, JsonWriter &w) {
    using NK = yaml::Node::Kind;
    yaml::NodeUP doc;
    try {
        doc = yaml::parse(name, json);
    } catch (const yaml::YamlError &e) {
        w.beginObject().kv("ok", false).kv("error", std::string(e.what())).endObject();
        return nullptr;
    }
    if (!doc) {
        doc.reset(new yaml::Node());
    }
    if (doc->kind != NK::Map && doc->kind != NK::Null) {
        w.beginObject().kv("ok", false).kv("error", "the request is not a JSON object")
            .endObject();
        return nullptr;
    }
    return doc;
}

}

std::string LintEngine::collectWaivers(const std::vector<ast::IScopeChild *> &roots,
        const std::string &requestJson) {
    using NK = yaml::Node::Kind;
    JsonWriter w;
    yaml::NodeUP doc = parseRequest("<waivers>", requestJson, w);
    if (!doc) {
        return w.str();
    }
    std::vector<pipeline::Waiver> found;
    std::map<std::string, const std::string *> texts;
    if (const yaml::Node *t = doc->get("texts")) {
        for (const yaml::Node::Member &m : t->members) {
            if (m.value && m.value->kind == NK::String) {
                texts[m.key] = &m.value->s;
                pipeline::collectPragmas(m.key, m.value->s, found);
            }
        }
    }
    const yaml::Node *files = doc->get("files");
    for (ast::IScopeChild *r : roots) {
        ast::IGlobalScope *gs = NodeKind::cast<ast::IGlobalScope>(r);
        const yaml::Node *p = (gs && files) ? files->get(std::to_string(gs->getFileid())) : nullptr;
        if (!p || p->kind != NK::String) {
            continue;
        }
        // A file that does not mention lint_pkg has no waiver annotation.
        auto t = texts.find(p->s);
        if (t == texts.end() || t->second->find("lint_pkg") == std::string::npos) {
            continue;
        }
        pipeline::collectAnnotations(r, p->s, found);
    }
    pipeline::sortWaivers(found);
    w.beginObject().kv("ok", true).key("waivers").beginArray();
    for (const pipeline::Waiver &x : found) {
        x.toJson(w, false);
    }
    w.endArray().endObject();
    return w.str();
}

std::string LintEngine::applyWaivers(const std::string &requestJson) {
    using NK = yaml::Node::Kind;
    JsonWriter w;
    yaml::NodeUP doc = parseRequest("<waivers>", requestJson, w);
    if (!doc) {
        return w.str();
    }
    std::vector<pipeline::Waiver> waivers;
    if (const yaml::Node *ws = doc->get("waivers")) {
        for (const yaml::NodeUP &n : ws->items) {
            pipeline::Waiver x;
            if (pipeline::Waiver::fromJson(*n, x)) {
                waivers.push_back(x);
            }
        }
    }
    std::vector<pipeline::WaiverDiag> diags;
    if (const yaml::Node *ds = doc->get("diagnostics")) {
        for (const yaml::NodeUP &n : ds->items) {
            pipeline::WaiverDiag d;
            if (n->kind == NK::Map) {
                const yaml::Node *v;
                if ((v = n->get("code")) && v->kind == NK::String) d.code = v->s;
                if ((v = n->get("file")) && v->kind == NK::String) d.file = v->s;
                if ((v = n->get("line")) && v->kind == NK::Int) d.line = static_cast<int32_t>(v->i);
                if ((v = n->get("col")) && v->kind == NK::Int) d.col = static_cast<int32_t>(v->i);
            }
            diags.push_back(d);
        }
    }
    std::set<std::string> ran;
    const yaml::Node *rn = doc->get("ran");
    bool haveRan = rn && rn->kind == NK::Seq;
    if (haveRan) {
        for (const yaml::NodeUP &n : rn->items) {
            if (n->kind == NK::String) {
                ran.insert(n->s);
            }
        }
    }
    pipeline::Catalogue cat(m_hostMarkers, m_refused, ruleList());
    pipeline::WaiverResult res = pipeline::applyWaivers(cat, diags, waivers,
        haveRan ? &ran : nullptr);

    w.beginObject().kv("ok", true);
    w.key("kept").beginArray();
    for (uint32_t i : res.kept) {
        w.value(i);
    }
    w.endArray().key("waived").beginArray();
    for (const auto &p : res.waived) {
        w.beginArray().value(p.first).value(p.second).endArray();
    }
    w.endArray().key("waivers").beginArray();
    for (const pipeline::Waiver &x : waivers) {
        x.toJson(w, true);
    }
    w.endArray().key("markers").beginArray();
    for (const pipeline::WaiverMarker &m : res.markers) {
        w.beginObject()
            .kv("severity", m.severity)
            .kv("message", m.message)
            .kv("file", m.file)
            .kv("line", m.line)
            .kv("col", m.col)
            .kv("code", m.code)
            .kv("extent", -1);
        w.key("related").beginArray().endArray();
        w.endObject();
    }
    w.endArray().endObject();
    return w.str();
}

std::vector<const rules::Rule *> LintEngine::select(const yaml::Node &selection,
        const std::vector<ast::IScopeChild *> &roots, const std::vector<const rules::Rule *> &all,
        run::RunOptions &opts, std::vector<std::string> &problems) {
    pipeline::Catalogue cat(m_hostMarkers, m_refused, all);
    pipeline::Selection sel(cat, selection);
    sel.defaultBaseDir(opts.baseDir);
    for (const pipeline::SelectionError &e : sel.errors()) {
        problems.push_back("selection: " + e.message);
    }
    std::unordered_map<std::string, const rules::Rule *> byId;
    for (const rules::Rule *r : all) {
        byId.emplace(r->m_id, r);
    }

    // One FileRules per group, shared by its files.
    std::unordered_map<uint32_t, std::shared_ptr<run::FileRules>> byGroup;
    auto rulesOf = [&](uint32_t g) {
        auto it = byGroup.find(g);
        if (it != byGroup.end()) {
            return it->second;
        }
        auto fr = std::make_shared<run::FileRules>();
        const pipeline::SelectionGroup &grp = sel.group(g);
        for (const rules::Rule *r : all) {
            // `[severity] = "off"` drops a rule's findings: it is not run.
            auto sv = sel.severity().find(r->m_id);
            bool off = sv != sel.severity().end() && sv->second.first == "off";
            if (grp.enabled.count(r->m_id) && !off) {
                fr->on.insert(r);
            }
        }
        for (const auto &ro : grp.options) {
            auto ri = byId.find(ro.first);
            if (ri == byId.end()) {
                continue;           // a host's rule: its options are the host's
            }
            const rules::Rule *r = ri->second;
            for (const auto &ov : ro.second) {
                const rules::RuleOption *o = nullptr;
                for (const rules::RuleOption &c : r->m_options) {
                    if (c.name == ov.first) {
                        o = &c;
                    }
                }
                cel::Value v;
                std::string where = "selection: options: ";
                if (!o) {
                    problems.push_back(where + "rule " + r->m_id + " has no option '"
                        + ov.first + "'");
                } else if (!rules::optionValue(*o, ov.second, v)) {
                    problems.push_back(where + r->m_id + "." + ov.first + " must be " + o->type);
                } else {
                    fr->options[r].emplace_back(ov.first, std::move(v));
                }
            }
        }
        byGroup.emplace(g, fr);
        return fr;
    };
    auto placeFile = [&](int32_t fileid) {
        if (opts.perFile.count(fileid)) {
            return;
        }
        auto fn = opts.fileNames.find(fileid);
        uint32_t g = (fn == opts.fileNames.end()) ? 0 : sel.groupOf(fn->second);
        opts.perFile[fileid] = rulesOf(g);
    };
    for (const auto &fn : opts.fileNames) {
        placeFile(fn.first);
    }
    std::set<const rules::Rule *> any;
    for (ast::IScopeChild *r : roots) {
        ast::IGlobalScope *gs = NodeKind::cast<ast::IGlobalScope>(r);
        int32_t fileid = gs ? gs->getFileid() : -1;
        placeFile(fileid);
        any.insert(opts.perFile[fileid]->on.begin(), opts.perFile[fileid]->on.end());
    }
    if (roots.empty()) {
        // No trees (the gate): the rules the named files enable, else the
        // project's, decide whether PSSP230 is said.
        for (const auto &pf : opts.perFile) {
            any.insert(pf.second->on.begin(), pf.second->on.end());
        }
        if (opts.perFile.empty()) {
            std::shared_ptr<run::FileRules> fr = rulesOf(0);
            any.insert(fr->on.begin(), fr->on.end());
        }
    }
    std::vector<const rules::Rule *> on;
    for (const rules::Rule *r : all) {
        if (any.count(r)) {
            on.push_back(r);
        }
    }
    return on;
}

std::string LintEngine::run(const std::vector<ast::IScopeChild *> &roots,
        const std::string &requestJson, ast::IRootSymbolScope *model) {
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
    const yaml::Node *selNode = req->get("selection");
    if (selNode && selNode->kind == NK::Null) {
        selNode = nullptr;
    }
    if (selNode && (en || req->get("options"))) {
        problems.push_back("selection: given with enabled or options; those are ignored");
        en = nullptr;
    }
    if (selNode) {
        // Every rule some file enables; which files, below.
        on = all;
    } else if (!en || en->kind == NK::Null) {
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
    opts.model = model;
    if (const yaml::Node *ms = req->get("max_steps")) {
        if (ms->kind == NK::Int && ms->i > 0) {
            opts.maxSteps = static_cast<uint64_t>(ms->i);
        } else {
            problems.push_back("max_steps: not a positive integer");
        }
    }
    const yaml::Node *ovNode = selNode ? nullptr : req->get("options");
    if (const yaml::Node *ov = ovNode) {
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
    // The host's file names, as {"<fileid>": "<path>"}, for file_of (C6.9).
    if (const yaml::Node *fs = req->get("files")) {
        if (fs->kind != NK::Map) {
            problems.push_back("files: not an object of fileid to path");
        } else {
            for (const yaml::Node::Member &m : fs->members) {
                char *end = nullptr;
                long id = std::strtol(m.key.c_str(), &end, 10);
                if (m.key.empty() || *end || m.value->kind != NK::String) {
                    problems.push_back("files: '" + m.key + "' is not a fileid with a path");
                } else {
                    opts.fileNames[static_cast<int32_t>(id)] = m.value->s;
                }
            }
        }
    }
    if (const yaml::Node *bd = req->get("base_dir")) {
        if (bd->kind == NK::String) {
            opts.baseDir = bd->s;
        } else if (bd->kind != NK::Null) {
            problems.push_back("base_dir: not a string");
        }
    }
    if (selNode) {
        on = select(*selNode, roots, on, opts, problems);
    }

    // Unlinked: a rule that needs symbols would fail on every file, or
    // worse, find nothing; it is not run, and says so.
    if (!model) {
        std::vector<const rules::Rule *> runnable;
        for (const rules::Rule *r : on) {
            if (r->m_level >= cel::Level::L1) {
                problems.push_back("rule " + r->m_id + " needs a linked model (level "
                    + cel::levelName(r->m_level) + "); not run");
            } else {
                runnable.push_back(r);
            }
        }
        on.swap(runnable);
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
    for (const run::RuleNote &n : runner.notes()) {
        std::unique_ptr<IMarker> m(run::Runner::toMarker(n));
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
