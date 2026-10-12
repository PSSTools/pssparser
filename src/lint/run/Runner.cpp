/*
 * Runner.cpp
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
#include <algorithm>
#include <chrono>
#include "Runner.h"
#include "../../Marker.h"
#include "../cel/CelEval.h"
#include "../cel/CelFunctions.h"
#include "../cel/CelNode.h"
#include "../pipeline/Selection.h"
#include "../rules/Rule.h"

namespace pssp {
namespace lint {
namespace run {

namespace {

cel::Value nodeValue(const rf::Node &n) {
    cel::NodeRef r;
    r.kind = n.kind;
    r.ptr = n.ptr;
    return cel::Value::mkNode(r);
}

rf::Node toNode(const cel::Value &v) {
    rf::Node n;
    n.kind = v.node.kind;
    n.ptr = v.node.ptr;
    return n;
}

}

MarkerSeverityE ruleSeverity(const rules::Rule &r) {
    // taxonomy.TIER_SEVERITY (lint-framework L2), from the catalogue (C7.3).
    const std::string s = r.m_severity.empty()
        ? std::string(pipeline::tierSeverity(r.m_tier)) : r.m_severity;
    if (s == "error") {
        return MarkerSeverityE::Error;
    } else if (s == "info") {
        return MarkerSeverityE::Info;
    } else if (s == "hint") {
        return MarkerSeverityE::Hint;
    }
    return MarkerSeverityE::Warn;
}

Runner::Runner(const std::vector<const rules::Rule *> &rules, const RunOptions &opts) :
        m_opts(opts), m_dispatch(rules), m_walker(m_dispatch), m_stats(rules.size()),
        m_file(rules.size()) {
    m_ctx.setModel(opts.model);
    m_ctx.setFiles(opts.fileNames, opts.baseDir);
    for (size_t i=0; i<rules.size(); i++) {
        m_index.emplace(rules[i], i);
    }
}

Runner::~Runner() { }

void Runner::run(const rf::Node &root) {
    // A root is a file: each rule starts it with a fresh budget.
    std::fill(m_file.begin(), m_file.end(), FileState());
    m_ctx.index(root);
    m_fileRules = nullptr;
    if (!m_opts.perFile.empty()) {
        auto it = m_opts.perFile.find(m_ctx.fileidOf(root));
        static const FileRules none;
        m_fileRules = (it == m_opts.perFile.end()) ? &none : it->second.get();
    }
    m_walker.walk(root, [this](const rules::Rule &r, const rf::Node &n) {
        match(r, n);
    });
}

void Runner::match(const rules::Rule &r, const rf::Node &n) {
    size_t idx = m_index.at(&r);
    if (m_file[idx].failed || (m_fileRules && !m_fileRules->on.count(&r))) {
        return;
    }
    auto t0 = std::chrono::steady_clock::now();
    m_ctx.setCurrent(&r, n);
    evaluate(idx, r, n);
    m_stats[idx].ns += static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now() - t0).count());
}

void Runner::evaluate(size_t idx, const rules::Rule &r, const rf::Node &n) {
    RuleStats &st = m_stats[idx];
    st.matches++;
    bool overrun = false;

    Vars vars;
    vars.emplace_back("node", nodeValue(n));
    const auto &optsOf = m_fileRules ? m_fileRules->options : m_opts.options;
    auto set = optsOf.find(&r);
    for (const rules::RuleOption &o : r.m_options) {
        const cel::Value *v = &o.def;
        if (set != optsOf.end()) {
            for (const auto &kv : set->second) {
                if (kv.first == o.name) {
                    v = &kv.second;
                }
            }
        }
        vars.emplace_back("options." + o.name, *v);
    }
    // Each let sees the ones before it. An error is kept as the value: it
    // matters only if where: or report: depends on it.
    for (const rules::LetBinding &b : r.m_lets) {
        cel::Value v = b.expr ? eval(b.expr.get(), vars, idx, overrun)
            : cel::Value::error("not loaded");
        if (overrun) {
            fail(idx, r, "let", v, true, n);
            return;
        }
        vars.emplace_back(b.name, std::move(v));
    }

    if (r.m_where) {
        cel::Value w = eval(r.m_where.get(), vars, idx, overrun);
        if (w.isError()) {
            fail(idx, r, "where", w, overrun, n);
            return;
        }
        if (!w.isBool() || !w.b) {
            return;
        }
    }

    std::vector<rf::Node> reported;
    if (r.m_report) {
        cel::Value rv = eval(r.m_report.get(), vars, idx, overrun);
        if (rv.isError()) {
            fail(idx, r, "report", rv, overrun, n);
            return;
        }
        if (rv.kind == cel::Value::Kind::List && rv.list) {
            for (const cel::Value &e : *rv.list) {
                // An unset field reads as null: nothing to report.
                if (e.kind == cel::Value::Kind::Node && e.node.ptr) {
                    reported.push_back(toNode(e));
                }
            }
        }
    } else {
        reported.push_back(n);
    }

    for (const rf::Node &f : reported) {
        if (!m_reported.emplace(&r, f.ptr).second) {
            continue;
        }
        Finding fd;
        fd.rule = &r;
        fd.node = f;
        fd.severity = ruleSeverity(r);
        // A named declaration is reported at its name, not across its
        // body: a squiggle over a whole component is no use in an editor.
        if (!Walker::nameLocation(f, fd.loc)) {
            fd.loc = locate(f);
        }
        // A model-scope rule may report in a file whose overrides turn it off.
        if (!reportsIn(r, fd.loc.fileid)) {
            continue;
        }
        vars.emplace_back("finding", nodeValue(f));
        fd.message = renderMessage(idx, r, f, vars);
        vars.pop_back();
        st.findings++;
        m_findings.push_back(std::move(fd));
        // A failed message keeps its finding, and ends the rule's file.
        if (m_file[idx].failed) {
            return;
        }
    }
}

bool Runner::reportsIn(const rules::Rule &r, int32_t fileid) const {
    if (m_opts.perFile.empty()) {
        return true;
    }
    auto it = m_opts.perFile.find(fileid);
    return it == m_opts.perFile.end() || it->second->on.count(&r);
}

cel::Value Runner::eval(const cel::Expr *e, const Vars &vars, size_t idx, bool &overrun) {
    // The rule's budget is per file: what is left of it bounds this one.
    FileState &fs = m_file[idx];
    cel::EvalOptions opts;
    opts.maxSteps = (fs.steps < m_opts.maxSteps) ? m_opts.maxSteps - fs.steps : 0;
    opts.host = &m_ctx;
    cel::CelEval ev(opts);
    cel::Value v = ev.eval(e, vars);
    uint64_t used = std::min(ev.steps(), opts.maxSteps);
    fs.steps += used;
    m_stats[idx].steps += used;
    overrun = ev.budgetExceeded();
    return v;
}

std::string Runner::renderMessage(size_t idx, const rules::Rule &r, const rf::Node &finding,
        Vars &vars) {
    std::string out;
    for (const rules::MessagePart &p : r.m_messageParts) {
        if (!p.expr) {
            out += p.text;
            continue;
        }
        if (m_file[idx].failed) {
            // An earlier part failed (an overrun leaves no budget).
            out += "?";
            continue;
        }
        bool overrun = false;
        cel::Value v = eval(p.expr.get(), vars, idx, overrun);
        switch (v.kind) {
            case cel::Value::Kind::String: out += v.s; break;
            case cel::Value::Kind::Int: out += std::to_string(v.i); break;
            case cel::Value::Kind::Double: out += cel::formatDouble(v.d); break;
            case cel::Value::Kind::Bool: out += v.b ? "true" : "false"; break;
            case cel::Value::Kind::Node: out += renderNode(toNode(v)); break;
            case cel::Value::Kind::Error:
                // The finding stands; the rule's message is broken.
                fail(idx, r, "message", v, overrun, finding);
                out += "?";
                break;
            default:
                // An unset node field (null): the checker allows a node type.
                out += "?";
                break;
        }
    }
    return out;
}

void Runner::fail(size_t idx, const rules::Rule &r, const char *in, const cel::Value &v,
        bool overrun, const rf::Node &n) {
    RuleStats &st = m_stats[idx];
    m_file[idx].failed = true;
    if (st.errors++ == 0) {
        st.errorIn = in;
        st.error = v.s;
        st.errorNode = n;
    }

    RuleFailure f;
    f.rule = &r;
    f.code = overrun ? "PSSP221" : "PSSP220";
    f.in = in;
    f.error = v.s;
    f.node = n;
    f.loc = locate(n);
    std::string rule = r.m_id + " (" + r.m_name + ")";
    std::string at = describeNode(n);
    if (overrun) {
        f.message = "rule " + rule + " used its budget of " + std::to_string(m_opts.maxSteps)
            + " evaluation steps for this file, in its " + in + " at " + at
            + "; the rule is skipped for the rest of this file";
    } else {
        f.message = "rule " + rule + " failed in its " + in + " at " + at + ": " + v.s
            + "; the rule is skipped for the rest of this file";
    }
    m_failures.push_back(std::move(f));
}

std::string Runner::describeNode(const rf::Node &n) {
    // "Action 'A'" for a named node; "ExprBin at 6:20" (renderNode's
    // fallback) for one without a name.
    std::string text = renderNode(n);
    std::string kind = cel::nodeClassName(n.kind);
    if (text.compare(0, kind.size(), kind) == 0) {
        return text;
    }
    return kind + " '" + text + "'";
}

std::string Runner::renderNode(const rf::Node &n) {
    // A declaration's path (format §3.4), else a declaration's name, a path
    // element's identifier, an identifier's or a literal's text.
    std::string path;
    if (m_ctx.declares(n) && m_ctx.namedPath(n, path) && !path.empty()) {
        return path;
    }
    std::string type = lib::spelledType(n);
    if (!type.empty()) {
        return type;
    }
    cel::Value v = nodeValue(n);
    uint64_t elems = 0;
    for (const char *f : {"name", "id"}) {
        cel::Value sub;
        if (cel::readField(v, f, sub, elems) && sub.kind == cel::Value::Kind::Node
                && sub.node.ptr) {
            v = sub;
        }
    }
    for (const char *f : {"id", "image"}) {
        cel::Value text;
        if (cel::readField(v, f, text, elems) && text.kind == cel::Value::Kind::String
                && !text.s.empty()) {
            return text.s;
        }
    }
    std::string out = cel::nodeClassName(n.kind);
    ast::Location loc = locate(n);
    if (loc.lineno > 0) {
        out += " at " + std::to_string(loc.lineno) + ":" + std::to_string(loc.linepos);
    }
    return out;
}

ast::Location Runner::locate(const rf::Node &n) {
    ast::Location loc = firstLocated(n);
    if (loc.lineno > 0) {
        return loc;
    }
    // Nothing located under it: the nearest located ancestor, if walked.
    for (rf::Node p=m_walker.parentOf(n); p; p=m_walker.parentOf(p)) {
        if (Walker::location(p, loc)) {
            return loc;
        }
    }
    return ast::Location();
}

const ast::Location &Runner::firstLocated(const rf::Node &n) {
    // The node's own location, else its first child's (in walk order) that
    // has one. Memoised, and iterative (post-order): an expression chain
    // can be thousands deep, and every link of it may be reported.
    auto hit = m_located.find(n.ptr);
    if (hit != m_located.end()) {
        return hit->second;
    }
    struct Frame {
        rf::Node                n;
        std::vector<rf::Node>   kids;
        size_t                  next = 0;
    };
    std::vector<Frame> frames;
    auto enter = [&](const rf::Node &c) {
        ast::Location loc;
        if (Walker::location(c, loc)) {
            m_located.emplace(c.ptr, loc);
            return;
        }
        frames.emplace_back();
        frames.back().n = c;
        Walker::children(c, frames.back().kids);
    };
    enter(n);
    while (!frames.empty()) {
        Frame &f = frames.back();
        // The previous child is resolved: stop at the first located one.
        if (f.next > 0) {
            const ast::Location &prev = m_located.at(f.kids[f.next - 1].ptr);
            if (prev.lineno > 0) {
                m_located.emplace(f.n.ptr, prev);
                frames.pop_back();
                continue;
            }
        }
        if (f.next < f.kids.size()) {
            rf::Node kid = f.kids[f.next++];
            if (!m_located.count(kid.ptr)) {
                enter(kid);
            }
        } else {
            m_located.emplace(f.n.ptr, ast::Location());
            frames.pop_back();
        }
    }
    return m_located.at(n.ptr);
}

IMarker *Runner::toMarker(const Finding &f) {
    return new Marker(f.message, f.severity, f.loc, f.rule->m_id);
}

IMarker *Runner::toMarker(const RuleFailure &f) {
    return new Marker(f.message, MarkerSeverityE::Warn, f.loc, f.code);
}

std::vector<RuleNote> Runner::notes() {
    std::vector<RuleNote> out;
    for (const lib::Context::UnknownType &u : m_ctx.unknownTypes()) {
        RuleNote n;
        n.rule = static_cast<const rules::Rule *>(u.rule);
        n.path = u.path;
        n.node = u.node;
        n.loc = u.node ? locate(u.node) : ast::Location();
        std::string rule = n.rule ? n.rule->m_id + " (" + n.rule->m_name + ")" : "a rule";
        n.message = "rule " + rule + " names the type '" + u.path + "', which the model "
            "does not have: type_named() gives none for it, and derives_from() false";
        out.push_back(std::move(n));
    }
    return out;
}

IMarker *Runner::toMarker(const RuleNote &n) {
    return new Marker(n.message, MarkerSeverityE::Info, n.loc, n.code);
}

IMarker *Runner::skippedMarker(uint32_t nErrors) {
    return new Marker("lint skipped: " + std::to_string(nErrors)
        + ((nErrors == 1) ? " error" : " errors"),
        MarkerSeverityE::Info, ast::Location(), "PSSP230");
}

}
}
}
