/*
 * Waivers.cpp
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
#include <sstream>
#include <tuple>
#include "Waivers.h"
#include "Selection.h"
#include "../../FmtTokenStream.h"
#include "../run/Walker.h"
#include "../util/JsonWriter.h"
#include "../yaml/YamlDoc.h"
#include "pssp/ast/IAnnotation.h"
#include "pssp/ast/IAnnotationParam.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IExprRefName.h"
#include "pssp/ast/IExprString.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IScope.h"
#include "pssp/ast/IScopeChild.h"
#include "pssp/ast/ITypeIdentifier.h"
#include "pssp/ast/ITypeIdentifierElem.h"
#include "pssp/impl/NodeKind.h"

namespace pssp {
namespace lint {
namespace pipeline {

namespace {

const char *const UNUSED = "PSSP202";
const char *const UNKNOWN_RULE = "PSSP203";
const char *const ON_ERROR = "PSSP204";
const char *const NO_REASON = "PSSP205";
const char *const ALIAS = "PSSP004";

// Codes a source waiver cannot waive: it could hide the warning that it is
// itself unused.
bool hygiene(const std::string &code) {
    return code == UNUSED || code == UNKNOWN_RULE || code == ON_ERROR
        || code == NO_REASON || code == ALIAS;
}

// Python's str.isspace() over ASCII, and \s in its regexes.
bool space(unsigned char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
}

// A regex \w character: non-ASCII counts, as most of it is in Python.
bool word(unsigned char c) {
    return c >= 0x80 || c == '_' || (c >= '0' && c <= '9')
        || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

std::string strip(const std::string &s) {
    size_t b = 0, e = s.size();
    while (b < e && space(static_cast<unsigned char>(s[b]))) {
        b++;
    }
    while (e > b && space(static_cast<unsigned char>(s[e - 1]))) {
        e--;
    }
    return s.substr(b, e - b);
}

// `text.split(",")`, each stripped, the empty ones dropped.
std::vector<std::string> splitIds(const std::string &text) {
    std::vector<std::string> out;
    size_t from = 0;
    while (true) {
        size_t comma = text.find(',', from);
        std::string part = strip(text.substr(from, comma == std::string::npos
            ? std::string::npos : comma - from));
        if (!part.empty()) {
            out.push_back(part);
        }
        if (comma == std::string::npos) {
            break;
        }
        from = comma + 1;
    }
    return out;
}

// ^//\s*pssparser\s+waive\b(.*)$: true with `body` set on a match.
bool matchPragma(const std::string &text, std::string &body) {
    std::string t = text;
    while (!t.empty() && (t.back() == '\r' || t.back() == '\n')) {
        t.pop_back();
    }
    if (t.compare(0, 2, "//") != 0) {
        return false;
    }
    size_t i = 2;
    while (i < t.size() && space(static_cast<unsigned char>(t[i]))) {
        i++;
    }
    if (t.compare(i, 9, "pssparser") != 0) {
        return false;
    }
    i += 9;
    size_t ws = i;
    while (i < t.size() && space(static_cast<unsigned char>(t[i]))) {
        i++;
    }
    if (i == ws || t.compare(i, 5, "waive") != 0) {
        return false;
    }
    i += 5;
    if (i < t.size() && word(static_cast<unsigned char>(t[i]))) {
        return false;
    }
    body = t.substr(i);
    return true;
}

bool trivia(const FmtToken &t) {
    return t.channel == FmtTokenChannel_WS || t.channel == FmtTokenChannel_SlComment
        || t.channel == FmtTokenChannel_MlComment || t.channel == FmtTokenChannel_Bom;
}

bool isWaiveAnnotation(const ast::IAnnotation *ann) {
    const ast::ITypeIdentifier *t = ann->getType();
    if (!t || t->getElems().size() != 2) {
        return false;
    }
    const char *const want[] = {"lint_pkg", "waive"};
    for (size_t i = 0; i < 2; i++) {
        const ast::ITypeIdentifierElem *e = t->getElems()[i].get();
        if (!e || !e->getId() || e->getId()->getId() != want[i]) {
            return false;
        }
    }
    return true;
}

Waiver waiverFrom(const ast::IAnnotation *ann, const std::string &path,
        const LineCol &start, const LineCol &end) {
    Waiver w;
    w.form = "annotation";
    w.file = path;
    for (const ast::IAnnotationParamUP &p : ann->getParameters()) {
        if (!p || !p->getName() || !p->getName()->getId()) {
            continue;
        }
        const ast::IExprString *v = NodeKind::cast<ast::IExprString>(p->getValue());
        if (!v) {
            continue;
        }
        const std::string &name = p->getName()->getId()->getId();
        if (name == "id") {
            w.selectors = splitIds(v->getValue());
        } else if (name == "reason") {
            w.reason = strip(v->getValue());
        }
    }
    w.line = ann->getLocation().lineno;
    w.col = ann->getLocation().linepos;
    w.start = start;
    w.end = end;
    return w;
}

void marker(std::vector<WaiverMarker> &out, const char *code, const Waiver &w,
        const std::string &message, const char *severity="warning") {
    WaiverMarker m;
    m.code = code;
    m.severity = severity;
    m.message = message;
    m.file = w.file;
    m.line = w.line;
    m.col = w.col;
    out.push_back(m);
}

std::string where(const Waiver &w) {
    return w.form == "annotation" ? "waiver" : "waiver comment";
}

std::string join(const std::vector<std::string> &v, const char *sep) {
    std::string out;
    for (size_t i = 0; i < v.size(); i++) {
        out += (i ? sep : "") + v[i];
    }
    return out;
}

}

void Waiver::toJson(JsonWriter &w, bool withResult) const {
    w.beginObject()
        .kv("form", form)
        .kv("file", file)
        .kv("line", line)
        .kv("col", col);
    w.key("selectors").beginArray();
    for (const std::string &s : selectors) {
        w.value(s);
    }
    w.endArray();
    w.kv("reason", reason);
    w.key("start").beginArray().value(start.first).value(start.second).endArray();
    w.key("end").beginArray().value(end.first).value(end.second).endArray();
    if (withResult) {
        w.key("ids").beginArray();
        for (const std::string &id : ids) {
            w.value(id);
        }
        w.endArray();
        w.kv("used", used);
    }
    w.endObject();
}

bool Waiver::fromJson(const yaml::Node &n, Waiver &out) {
    using NK = yaml::Node::Kind;
    if (n.kind != NK::Map) {
        return false;
    }
    auto str = [&](const char *k, std::string &v) {
        const yaml::Node *x = n.get(k);
        if (x && x->kind == NK::String) {
            v = x->s;
        }
    };
    auto num = [&](const yaml::Node *x, int32_t &v) {
        if (x && x->kind == NK::Int) {
            v = static_cast<int32_t>(x->i);
            return true;
        }
        return false;
    };
    auto pos = [&](const char *k, LineCol &v) {
        const yaml::Node *x = n.get(k);
        return x && x->kind == NK::Seq && x->items.size() == 2
            && num(x->items[0].get(), v.first) && num(x->items[1].get(), v.second);
    };
    str("form", out.form);
    str("file", out.file);
    str("reason", out.reason);
    num(n.get("line"), out.line);
    num(n.get("col"), out.col);
    if (const yaml::Node *s = n.get("selectors")) {
        for (const yaml::NodeUP &i : s->items) {
            if (i->kind == NK::String) {
                out.selectors.push_back(i->s);
            }
        }
    }
    return pos("start", out.start) && pos("end", out.end);
}

void collectPragmas(const std::string &path, const std::string &text,
        std::vector<Waiver> &out) {
    if (text.find("pssparser") == std::string::npos) {
        return;
    }
    std::istringstream in(text);
    FmtTokenStream toks(&in);
    // The line of the last code token so far: a pragma after one on its
    // line trails code.
    int32_t lastCode = -1;
    for (uint32_t i = 0; i < toks.size(); i++) {
        const FmtToken &tok = toks.at(i);
        if (!trivia(tok)) {
            lastCode = tok.line;
            continue;
        }
        std::string body;
        if (tok.channel != FmtTokenChannel_SlComment || !matchPragma(tok.text, body)) {
            continue;
        }
        Waiver w;
        w.form = "pragma";
        w.file = path;
        w.line = tok.line;
        w.col = tok.col + 1;
        size_t colon = body.find(':');
        w.selectors = splitIds(body.substr(0, colon));
        if (colon != std::string::npos) {
            w.reason = strip(body.substr(colon + 1));
        }
        // Trailing code on the line covers that line; alone, the next line
        // that holds code.
        int32_t target = tok.line;
        if (lastCode != tok.line) {
            for (uint32_t j = i + 1; j < toks.size(); j++) {
                const FmtToken &t = toks.at(j);
                if (!trivia(t) && t.line > tok.line) {
                    target = t.line;
                    break;
                }
            }
        }
        w.start = {target, 1};
        w.end = {target, WaiverEol};
        out.push_back(w);
    }
}

void collectAnnotations(ast::IScopeChild *root, const std::string &path,
        std::vector<Waiver> &out) {
    namespace rf = ast::reflect;
    std::set<LineCol> seen;
    std::vector<rf::Node> stack{rf::classify(root)}, kids;
    // Pre-order, children in walk order (run::Walker::children).
    while (!stack.empty()) {
        rf::Node n = stack.back();
        stack.pop_back();
        if (ast::IScopeChild *c = rf::asScopeChild(n)) {
            const ast::Location &b = c->getLocation();
            for (const ast::IAnnotationUP &a : c->getAnnotations()) {
                if (!a || !isWaiveAnnotation(a.get()) || b.lineno < 1) {
                    continue;
                }
                LineCol at(a->getLocation().lineno, a->getLocation().linepos);
                if (!seen.insert(at).second) {
                    continue;
                }
                // From the annotation itself, which precedes the element: a
                // field's location is its name, and a finding on its type is
                // still within the declaration.
                const ast::Location &e = c->getEndLocation();
                LineCol end = e.lineno < 1 ? LineCol(b.lineno, WaiverEol)
                    : LineCol(e.lineno, e.linepos);
                out.push_back(waiverFrom(a.get(), path,
                    std::min(LineCol(b.lineno, b.linepos), at), end));
            }
            ast::IAnnotation *ann = NodeKind::cast<ast::IAnnotation>(c);
            if (ann && ann->getIs_standalone() && isWaiveAnnotation(ann)) {
                LineCol at(ann->getLocation().lineno, ann->getLocation().linepos);
                if (seen.insert(at).second) {
                    LineCol end(WaiverEol, WaiverEol);
                    ast::IScope *parent = ann->getParent();
                    if (parent && !NodeKind::cast<ast::IGlobalScope>(parent)
                            && parent->getEndLocation().lineno >= 1) {
                        end = {parent->getEndLocation().lineno,
                            parent->getEndLocation().linepos};
                    }
                    out.push_back(waiverFrom(ann, path, at, end));
                }
            }
        }
        kids.clear();
        run::Walker::children(n, kids);
        stack.insert(stack.end(), kids.rbegin(), kids.rend());
    }
}

void sortWaivers(std::vector<Waiver> &waivers) {
    std::stable_sort(waivers.begin(), waivers.end(), [](const Waiver &a, const Waiver &b) {
        return std::tie(a.file, a.line, a.col) < std::tie(b.file, b.line, b.col);
    });
}

WaiverResult applyWaivers(const Catalogue &cat, const std::vector<WaiverDiag> &diags,
        std::vector<Waiver> &waivers, const std::set<std::string> *ran) {
    WaiverResult res;
    std::vector<uint32_t> active;
    auto isCoreError = [&](const std::string &code) {
        const MarkerMeta *m = cat.byId(code);
        return m && m->isCoreError();
    };

    for (uint32_t wi = 0; wi < waivers.size(); wi++) {
        Waiver &w = waivers[wi];
        bool ann = w.form == "annotation";
        if (w.reason.empty()) {
            marker(res.markers, NO_REASON, w, where(w)
                + " gives no reason; say why the finding is "
                + (ann ? "intended in '.reason'" : "intended after ':'"));
        }
        if (w.selectors.empty()) {
            marker(res.markers, UNKNOWN_RULE, w, where(w) + " names no rule; "
                + (ann ? "set '.id' to a marker ID or rule name" : "write the ID before ':'"));
            continue;
        }
        std::vector<std::string> core;
        for (const std::string &sel : w.selectors) {
            std::string text = sel;
            // An old ID (a rule's alias, or a retired code's successor).
            auto al = cat.aliases().find(sel);
            if (al != cat.aliases().end()) {
                marker(res.markers, ALIAS, w, "'" + sel + "' is the old ID of " + al->second
                    + "; write '" + al->second + "' in the waiver", "info");
                text = al->second;
            }
            Selector s;
            std::string err;
            if (!cat.parse(text, s, err)) {
                marker(res.markers, UNKNOWN_RULE, w, where(w) + ": " + err);
                continue;
            }
            s.text = text;
            std::set<std::string> ids, errors;
            for (const auto &e : cat.expand({s}, true)) {
                if (hygiene(e.first)) {
                    continue;
                }
                ids.insert(e.first);
                if (isCoreError(e.first)) {
                    errors.insert(e.first);
                }
            }
            if (!errors.empty() && errors == ids) {
                core.push_back(sel);
            }
            for (const std::string &id : ids) {
                if (!errors.count(id)) {
                    w.ids.insert(id);
                }
            }
        }
        for (const std::string &sel : core) {
            marker(res.markers, ON_ERROR, w, "'" + sel
                + "' is an error, which cannot be waived; fix it and delete the waiver");
        }
        if (!w.ids.empty()) {
            active.push_back(wi);
        }
    }

    for (uint32_t di = 0; di < diags.size(); di++) {
        const WaiverDiag &d = diags[di];
        int64_t hit = -1;
        if (!d.code.empty() && !hygiene(d.code) && !isCoreError(d.code)) {
            for (uint32_t wi : active) {
                const Waiver &w = waivers[wi];
                if (w.ids.count(d.code) && w.covers(d.file, d.line, d.col)) {
                    hit = wi;
                    break;
                }
            }
        }
        if (hit < 0) {
            res.kept.push_back(di);
        } else {
            waivers[hit].used++;
            res.waived.emplace_back(di, static_cast<uint32_t>(hit));
        }
    }

    if (ran) {
        for (uint32_t wi : active) {
            const Waiver &w = waivers[wi];
            if (w.used) {
                continue;
            }
            bool any = false;
            for (const std::string &id : w.ids) {
                if (ran->count(id)) {
                    any = true;
                    break;
                }
            }
            if (any) {
                marker(res.markers, UNUSED, w, where(w) + " for '" + join(w.selectors, ", ")
                    + "' matched no diagnostic; delete it if the finding was fixed");
            }
        }
    }

    std::stable_sort(res.markers.begin(), res.markers.end(),
        [](const WaiverMarker &a, const WaiverMarker &b) {
            return std::tie(a.file, a.line, a.col, a.code)
                < std::tie(b.file, b.line, b.col, b.code);
        });
    return res;
}

}
}
}
