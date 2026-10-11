/*
 * PssLib.cpp
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
 * The PSS function library (lint-core-plan.md C6). Registration order is
 * documentation order (docs/lint-functions.rst), after the standard
 * library's groups.
 */
#include <algorithm>
#include <string>
#include "PssLib.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/IValInt.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/ITemplateValueParamDecl.h"
#include "../../Factory.h"
#include "../../OccurrenceCollector.h"
#include "ConstEval.h"
#include "../cel/CelNode.h"
#include "../run/Walker.h"

namespace pssp {
namespace lint {
namespace lib {

using cel::CallArgs;
using cel::Value;
using run::Walker;

namespace {

uint16_t classId(const char *name) {
    uint16_t k = 0;
    cel::lookupClass(name, k);
    return k;
}

uint16_t globalScopeClass() {
    static const uint16_t k = classId("GlobalScope");
    return k;
}

rf::Node asNode(const Value &v) {
    rf::Node n;
    if (v.kind == Value::Kind::Node) {
        n.kind = v.node.kind;
        n.ptr = v.node.ptr;
    }
    return n;
}

Value asValue(const rf::Node &n) {
    cel::NodeRef r;
    r.kind = n.kind;
    r.ptr = n.ptr;
    return Value::mkNode(r);
}

// Field `name` of a node, by name; null when its class has none.
Value field(const rf::Node &n, const char *name) {
    Value out;
    uint64_t elems = 0;
    if (!n || !cel::readField(asValue(n), name, out, elems)) {
        return Value::null();
    }
    return out;
}

// An ExprId's text, or a string field's value.
std::string text(const Value &v) {
    if (v.kind == Value::Kind::String) {
        return v.s;
    }
    if (v.kind == Value::Kind::Node) {
        Value id = field(asNode(v), "id");
        return (id.kind == Value::Kind::String) ? id.s : std::string();
    }
    return std::string();
}

rf::Node lastElem(const Value &list) {
    if (list.kind != Value::Kind::List || list.list->empty()) {
        return rf::Node();
    }
    return asNode(list.list->back());
}

//* Declaration paths: lint/declpath.py's segments, by class.

enum class Seg : uint8_t { None, Named, Package, Function, Constraint, Exec, Activity, Symbol, Extend };

struct SegInfo {
    Seg     seg = Seg::None;
    bool    leaf = false;       // what is under it takes its path
};

const std::vector<SegInfo> &segments() {
    static const std::vector<SegInfo> table = [] {
        std::vector<SegInfo> t(rf::NumClasses + 1);
        struct Entry { const char *cls; Seg seg; bool leaf; };
        const Entry entries[] = {
            {"PackageScope", Seg::Package, false},
            {"Component", Seg::Named, false}, {"Action", Seg::Named, false},
            {"Struct", Seg::Named, false}, {"Monitor", Seg::Named, false},
            {"CovergroupType", Seg::Named, true}, {"EnumDecl", Seg::Named, true},
            {"TypedefDeclaration", Seg::Named, true},
            {"FunctionDefinition", Seg::Function, true}, {"FunctionPrototype", Seg::Function, true},
            {"FunctionImportProto", Seg::Function, true},
            {"TargetTemplateFunction", Seg::Function, true},
            {"ConstraintBlock", Seg::Constraint, true}, {"ExecBlock", Seg::Exec, true},
            {"ActivityDecl", Seg::Activity, true}, {"SymbolDeclaration", Seg::Symbol, true},
            {"ExtendType", Seg::Extend, false}, {"ExtendEnum", Seg::Extend, true},
        };
        for (const Entry &e : entries) {
            if (uint16_t k = classId(e.cls)) {
                t[k].seg = e.seg;
                t[k].leaf = e.leaf;
            }
        }
        return t;
    }();
    return table;
}

const SegInfo &segOf(const rf::Node &n) {
    static const SegInfo none;
    return (n && n.kind <= rf::NumClasses) ? segments()[n.kind] : none;
}

bool numbered(Seg s) {
    return s == Seg::Constraint || s == Seg::Exec || s == Seg::Activity || s == Seg::Extend;
}

// An enum member's name less its prefix: ExecKind_PostSolve -> post_solve.
std::string execKind(int64_t v) {
    static const char *const names[] = {
        "body", "header", "declaration", "run_start", "run_end", "init_down", "init_up",
        "pre_solve", "post_solve", "pre_body", "file"};
    return (v >= 0 && v < 11) ? names[v] : std::to_string(v);
}

std::string extendKind(int64_t v) {
    static const char *const names[] = {
        "action", "annotation", "buffer", "component", "enum", "resource", "state", "stream",
        "struct", "monitor"};
    return (v >= 0 && v < 10) ? names[v] : std::to_string(v);
}

// A TypeIdentifier as written: `p::C::A`, `::A`.
std::string spelled(const rf::Node &tid) {
    Value elems = field(tid, "elems");
    if (elems.kind != Value::Kind::List) {
        return "?";
    }
    std::string out = field(tid, "is_global").b ? "::" : "";
    for (size_t i=0; i<elems.list->size(); i++) {
        out += (i ? "::" : "") + text(field(asNode((*elems.list)[i]), "id"));
    }
    return out;
}

// The segment a node contributes to a path (declpath.py's _segment).
std::string segText(const rf::Node &n, Seg seg) {
    switch (seg) {
        case Seg::Package: {
            Value ids = field(n, "id");
            std::string out;
            if (ids.kind == Value::Kind::List) {
                for (const Value &i : *ids.list) {
                    out += (out.empty() ? "" : "::") + text(i);
                }
            }
            return out.empty() ? "?" : out;
        }
        case Seg::Named: {
            std::string name = text(field(n, "name"));
            return name.empty() ? "?" : name;
        }
        case Seg::Function: {
            Value proto = field(n, "proto");
            std::string name = text(field(proto.kind == Value::Kind::Node ? asNode(proto) : n,
                "name"));
            return "function " + (name.empty() ? std::string("?") : name);
        }
        case Seg::Constraint: {
            std::string name = text(field(n, "name"));
            return name.empty() ? "constraint" : "constraint " + name;
        }
        case Seg::Exec: return "exec " + execKind(field(n, "kind").i);
        case Seg::Activity: return "activity";
        case Seg::Symbol: {
            std::string name = text(field(n, "name"));
            return "symbol " + (name.empty() ? std::string("?") : name);
        }
        case Seg::Extend: {
            std::string what = (n.kind == classId("ExtendEnum")) ? std::string("enum")
                : extendKind(field(n, "kind").i);
            return "extend " + what + " " + spelled(asNode(field(n, "target")));
        }
        default: return std::string();
    }
}

bool located(const rf::Node &n) {
    int32_t fileid, line, col;
    return Walker::location(n, fileid, line, col);
}

}

rf::Node refIdent(rf::Node n) {
    static const uint16_t
        exprId = classId("ExprId"), tie = classId("TypeIdentifierElem"),
        mpe = classId("ExprMemberPathElem"), refName = classId("ExprRefName"),
        tid = classId("TypeIdentifier"), hid = classId("ExprHierarchicalId"),
        ctx = classId("ExprRefPathContext"), sup = classId("ExprRefPathSuper"),
        rooted = classId("ExprRefPathStaticRooted"), stat = classId("ExprRefPathStatic"),
        udt = classId("DataTypeUserDefined"), call = classId("ExprMemberCall");
    for (int hops=0; n && hops<8; hops++) {
        if (n.kind == exprId) {
            return n;
        } else if (n.kind == tie || n.kind == mpe || n.kind == refName) {
            n = asNode(field(n, "id"));
        } else if (n.kind == tid || n.kind == hid) {
            n = lastElem(field(n, "elems"));
        } else if (n.kind == ctx || n.kind == sup) {
            n = asNode(field(n, "hier_id"));
        } else if (n.kind == rooted) {
            n = asNode(field(n, "leaf"));
        } else if (n.kind == stat) {
            n = lastElem(field(n, "base"));
        } else if (n.kind == udt) {
            n = asNode(field(n, "type_id"));
        } else if (n.kind == call) {
            n = lastElem(field(n, "members"));
        } else {
            return rf::Node();
        }
    }
    return rf::Node();
}

std::string spelledType(const rf::Node &n) {
    static const uint16_t tid = classId("TypeIdentifier");
    return (n && n.kind == tid) ? spelled(n) : std::string();
}

Context::Context() { }

Context::~Context() { }

void Context::indexTree(const rf::Node &root, bool owned) const {
    if (!root) {
        return;
    }
    if (owned) {
        m_owned.insert(root.ptr);
    }
    if (m_parent.count(root.ptr)) {
        return;
    }
    m_parent.emplace(root.ptr, rf::Node());
    // Iterative: a deep expression must not overflow the (WASM) stack.
    std::vector<rf::Node> work{root}, kids;
    while (!work.empty()) {
        rf::Node n = work.back();
        work.pop_back();
        kids.clear();
        Walker::children(n, kids);
        for (const rf::Node &k : kids) {
            if (k.kind <= rf::NumClasses && m_parent.emplace(k.ptr, n).second) {
                work.push_back(k);
            }
        }
    }
}

void Context::indexModel() const {
    if (m_modelIndexed || !m_model) {
        return;
    }
    m_modelIndexed = true;
    for (const ast::IGlobalScopeUP &u : m_model->getUnits()) {
        ast::IScopeChild *c = u.get();      // a GlobalScope is a ScopeChild
        indexTree(rf::classify(c), false);
    }
}

rf::Node Context::parentOf(const rf::Node &n) const {
    auto it = m_parent.find(n.ptr);
    if (it == m_parent.end() && m_model && !m_modelIndexed) {
        indexModel();
        it = m_parent.find(n.ptr);
    }
    return (it == m_parent.end()) ? rf::Node() : it->second;
}

rf::Node Context::rootOf(const rf::Node &n) const {
    if (!n || (!indexed(n) && (indexModel(), !indexed(n)))) {
        return rf::Node();
    }
    rf::Node r = n;
    for (rf::Node p=parentOf(r); p; p=parentOf(p)) {
        r = p;
    }
    return (r.kind == globalScopeClass()) ? r : rf::Node();
}

bool Context::owned(const rf::Node &n) const {
    rf::Node r = rootOf(n);
    return r && m_owned.count(r.ptr);
}

int32_t Context::fileidOf(const rf::Node &n) const {
    rf::Node r = rootOf(n);
    return r ? static_cast<ast::IGlobalScope *>(r.ptr)->getFileid() : -2;
}

void Context::collectSymbols() const {
    if (m_symbols || !m_model) {
        return;
    }
    m_symbols = true;
    OccurrenceCollector oc(nullptr);
    std::vector<Occurrence> occs;
    oc.collect(m_model, occs);
    for (const Occurrence &o : occs) {
        if (o.decl) {
            rf::Node d = rf::classify(o.decl);
            m_decl.emplace(static_cast<const void *>(o.id), d);
            if (!o.is_decl) {
                m_uses[d.ptr].push_back(rf::classify(static_cast<ast::IExpr *>(o.id)));
            }
        }
    }
}

const std::vector<rf::Node> *Context::usesOf(const rf::Node &decl) const {
    static const std::vector<rf::Node> none;
    if (!m_model) {
        return nullptr;
    }
    collectSymbols();
    auto it = m_uses.find(decl.ptr);
    return (it == m_uses.end()) ? &none : &it->second;
}

bool Context::constFold(const rf::Node &n, int64_t &v, bool &isBool) const {
    if (!m_model || !n) {
        return false;
    }
    // A template value parameter is bound in a specialization, which the
    // linker makes outside every file; in a file it is the generic one.
    ConstEval ev(Factory::inst(), m_model, [this](ast::ITemplateValueParamDecl *p) {
        return !rootOf(rf::classify(static_cast<ast::IScopeChild *>(p)));
    });
    std::unique_ptr<IVal> val;
    if (ast::IExpr *e = rf::asExpr(n)) {
        val.reset(ev.eval(e));
    } else if (ast::IScopeChild *c = rf::asScopeChild(n)) {
        // A declaration: what a reference to it would fold to.
        if (ast::IField *f = NodeKind::cast<ast::IField>(c)) {
            if ((f->getAttr() & ast::FieldAttr::Const) != ast::FieldAttr::NoFlags
                    && f->getInit()) {
                val.reset(ev.eval(f->getInit()));
            }
        } else if (ast::ITemplateValueParamDecl *p =
                NodeKind::cast<ast::ITemplateValueParamDecl>(c)) {
            if (p->getDflt() && !rootOf(n)) {
                val.reset(ev.eval(p->getDflt()));
            }
        }
    }
    IValInt *iv = dynamic_cast<IValInt *>(val.get());
    if (!iv || iv->getWidth() > 64
            || (!iv->isSigned() && iv->getValU() > static_cast<uint64_t>(INT64_MAX))) {
        return false;
    }
    v = iv->getValS();
    isBool = (!iv->isSigned() && iv->getWidth() == 1);
    return true;
}

bool Context::within(const rf::Node &n, const rf::Node &anc) const {
    for (rf::Node p=n; p; p=parentOf(p)) {
        if (p.ptr == anc.ptr) {
            return true;
        }
    }
    return false;
}

bool Context::declOf(const rf::Node &id, rf::Node &decl) const {
    if (!m_model) {
        return false;
    }
    collectSymbols();
    auto it = m_decl.find(id.ptr);
    decl = (it == m_decl.end()) ? rf::Node() : it->second;
    return true;
}

bool Context::declares(const rf::Node &n) const {
    if (segOf(n).seg != Seg::None) {
        return true;
    }
    return !text(field(n, "name")).empty();
}

int32_t Context::segmentNumber(const rf::Node &scope, const rf::Node &seg) const {
    if (!m_numbered.count(scope.ptr)) {
        // declpath.py's _walk over the scope: through `children` lists and
        // the non-segment nodes holding them, a segment's own children
        // being a scope of their own. `seen` counts per segment text.
        m_numbered.insert(scope.ptr);
        std::unordered_map<std::string, int32_t> seen;
        // Frames: a `children` list and the next element to look at.
        struct Frame {
            Value   kids;
            size_t  next = 0;
        };
        std::vector<Frame> frames;
        frames.push_back({field(scope, "children"), 0});
        while (!frames.empty()) {
            Frame &f = frames.back();
            if (f.kids.kind != Value::Kind::List || f.next >= f.kids.list->size()) {
                frames.pop_back();
                continue;
            }
            rf::Node k = asNode((*f.kids.list)[f.next++]);
            const SegInfo &si = segOf(k);
            if (si.seg == Seg::None) {
                Value kids = field(k, "children");
                frames.push_back({kids, 0});    // may move `f`; not used after
            } else if (located(k) && numbered(si.seg)) {
                m_segNum[k.ptr] = ++seen[segText(k, si.seg)];
            }
        }
    }
    auto it = m_segNum.find(seg.ptr);
    return (it == m_segNum.end()) ? 1 : it->second;
}

const std::string &Context::declPath(const rf::Node &n, uint64_t &steps) const {
    auto memo = m_path.find(n.ptr);
    if (memo != m_path.end()) {
        return memo->second;
    }
    bool reached;
    return m_path.emplace(n.ptr, buildPath(n, steps, reached)).first->second;
}

bool Context::namedPath(const rf::Node &n, std::string &path) const {
    uint64_t steps;
    bool reached;
    path = buildPath(n, steps, reached);
    return reached;
}

bool Context::ownPath(const rf::Node &n) const {
    if (segOf(n).seg == Seg::None) {
        return false;
    }
    uint64_t steps;
    bool reached;
    buildPath(n, steps, reached);
    return reached;
}

std::string Context::buildPath(const rf::Node &n, uint64_t &steps, bool &reached) const {
    std::vector<rf::Node> chain;
    for (rf::Node p=n; p; p=parentOf(p)) {
        chain.push_back(p);
    }
    steps = chain.size();
    std::reverse(chain.begin(), chain.end());

    std::string path;
    bool stopped = false;
    reached = false;
    rf::Node scope = chain.front();     // what segment numbers are relative to
    for (size_t i=1; i<chain.size() && !stopped; i++) {
        const rf::Node &c = chain[i];
        const SegInfo &si = segOf(c);
        if (si.seg == Seg::None) {
            if (i + 1 == chain.size() && declares(c)) {
                path += (path.empty() ? "" : "::") + text(field(c, "name"));
                reached = true;
            }
            continue;
        }
        if (!located(c)) {
            // declpath.py leaves out a scope with no location, and what is
            // under it.
            break;
        }
        std::string seg = segText(c, si.seg);
        if (numbered(si.seg)) {
            int32_t k = segmentNumber(scope, c);
            if (k > 1) {
                seg += "#" + std::to_string(k);
            }
        }
        path += (path.empty() ? "" : "::") + seg;
        scope = c;
        stopped = si.leaf;
        reached = (i + 1 == chain.size());
    }
    return path;
}

namespace {

rf::Node toNode(const Value &v) {
    rf::Node n;
    n.kind = v.node.kind;
    n.ptr = v.node.ptr;
    return n;
}

Value nodeValue(const rf::Node &n) {
    cel::NodeRef r;
    r.kind = n.kind;
    r.ptr = n.ptr;
    return Value::mkNode(r);
}

Value nodeList(const std::vector<rf::Node> &nodes) {
    cel::ValueList l;
    l.reserve(nodes.size());
    for (const rf::Node &n : nodes) {
        l.push_back(nodeValue(n));
    }
    return Value::mkList(std::move(l));
}

// The run's context, or null when the call has none (CelEval on its own).
const Context *context(const CallArgs &c) {
    return dynamic_cast<const Context *>(c.host);
}

Value noContext(const char *fn) {
    return Value::error(std::string(fn) + "() needs the parent links of a lint run");
}

// The class a type value names; false for a type that is not a node class
// (the checker refuses those where it can see them).
bool classOf(const Value &t, uint16_t &cls) {
    return t.kind == Value::Kind::Type && cel::lookupClass(t.s, cls);
}

//* Kind tests

Value isaImpl(CallArgs &c) {
    uint16_t cls;
    if (!classOf(c[0], cls)) {
        return Value::error("isa(): '" + c[0].s + "' is not a node class");
    }
    return Value::boolean(cel::isSubclass(c.target->node.kind, cls));
}

//* Navigation

Value parentImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("parent");
    }
    rf::Node p = ctx->parentOf(toNode(c[0]));
    return p ? nodeValue(p) : Value::null();
}

Value ancestorsImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("ancestors");
    }
    std::vector<rf::Node> out;
    for (rf::Node p=ctx->parentOf(toNode(c[0])); p; p=ctx->parentOf(p)) {
        out.push_back(p);
    }
    c.steps = out.size();
    return nodeList(out);
}

Value enclosingImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("enclosing");
    }
    uint16_t cls;
    if (!classOf(c[1], cls)) {
        return Value::error("enclosing(): '" + c[1].s + "' is not a node class");
    }
    for (rf::Node p=ctx->parentOf(toNode(c[0])); p; p=ctx->parentOf(p)) {
        c.steps++;
        if (cel::isSubclass(p.kind, cls)) {
            return nodeValue(p);
        }
    }
    return Value::null();
}

Value childrenImpl(CallArgs &c) {
    std::vector<rf::Node> out;
    Walker::children(toNode(c[0]), out);
    c.steps = out.size();
    return nodeList(out);
}

Value descendantsImpl(CallArgs &c) {
    // Pre-order, as the walk visits them: a node, then its children's trees.
    std::vector<rf::Node> out, work, kids;
    Walker::children(toNode(c[0]), kids);
    work.assign(kids.rbegin(), kids.rend());
    while (!work.empty()) {
        rf::Node n = work.back();
        work.pop_back();
        out.push_back(n);
        kids.clear();
        Walker::children(n, kids);
        work.insert(work.end(), kids.rbegin(), kids.rend());
    }
    c.steps = out.size();
    return nodeList(out);
}

Value siblingsImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("siblings");
    }
    rf::Node n = toNode(c[0]);
    std::vector<rf::Node> elems;
    int32_t at;
    if (!Walker::listOf(ctx->parentOf(n), n, elems, at)) {
        return Value::mkList(cel::ValueList());
    }
    elems.erase(elems.begin() + at);
    c.steps = elems.size();
    return nodeList(elems);
}

Value indexOfImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("index_of");
    }
    rf::Node n = toNode(c[0]);
    std::vector<rf::Node> elems;
    int32_t at;
    if (!Walker::listOf(ctx->parentOf(n), n, elems, at)) {
        return Value::integer(-1);
    }
    c.steps = elems.size();
    return Value::integer(at);
}


//* Symbols

Value resolvesToImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("resolves_to");
    }
    rf::Node id = (c[0].kind == Value::Kind::Node) ? refIdent(toNode(c[0])) : rf::Node(), decl;
    if (!id) {
        return Value::null();
    }
    if (!ctx->declOf(id, decl)) {
        return Value::error("resolves_to() needs a linked model, and this run has none");
    }
    return decl ? nodeValue(decl) : Value::null();
}

Value declPathImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("decl_path");
    }
    return Value::string(ctx->declPath(toNode(c[0]), c.steps));
}

Value isOwnedImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("is_owned");
    }
    return Value::boolean(c[0].kind == Value::Kind::Node && ctx->owned(toNode(c[0])));
}

Value inLibraryImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("in_library");
    }
    int32_t f = (c[0].kind == Value::Kind::Node) ? ctx->fileidOf(toNode(c[0])) : -2;
    return Value::boolean(f == 0 || f == -1);
}
}


//* References

// How the reference `id` (an ExprId) is used where it is written: the name
// an assignment's left-hand side or a traversal's field initializer
// assigns, and whether that assignment also reads it (`+=`).
uint64_t accessOf(const Context &ctx, const rf::Node &id, bool &written, bool &read) {
    static const uint16_t assign = classId("ProceduralStmtAssignment"),
        init = classId("ActionFieldInitializer");
    written = false;
    read = true;
    uint64_t steps = 0;
    // A declaration's own name is not a use.
    rf::Node owner = ctx.parentOf(id);
    if (owner && asNode(field(owner, "name")).ptr == id.ptr) {
        read = false;
        return 1;
    }
    for (rf::Node p=ctx.parentOf(id); p; p=ctx.parentOf(p)) {
        steps++;
        if (p.kind == assign || p.kind == init) {
            rf::Node target = asNode(field(p, p.kind == assign ? "lhs" : "path"));
            if (target && refIdent(target).ptr == id.ptr) {
                written = true;
                // AssignOp_Eq is 0; every other operator reads first.
                read = (p.kind == assign && field(p, "op").i != 0);
            }
            return steps;
        }
    }
    return steps;
}

Value isWrittenImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("is_written");
    }
    rf::Node id = refIdent(toNode(c[0]));
    bool written = false, read = false;
    if (id) {
        c.steps = accessOf(*ctx, id, written, read);
    }
    return Value::boolean(written);
}

Value isReadImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("is_read");
    }
    rf::Node id = refIdent(toNode(c[0]));
    bool written = false, read = false;
    if (id) {
        c.steps = accessOf(*ctx, id, written, read);
    }
    return Value::boolean(id && read);
}

// A function is declared by its prototype, which calls resolve to; the
// definition (or import) holding it is the function's extent. Either one
// may be passed: `key` is what uses name, `extent` what "inside" means.
void functionDecl(const Context &ctx, const rf::Node &d, rf::Node &key, rf::Node &extent) {
    static const uint16_t proto = classId("FunctionPrototype"),
        def = classId("FunctionDefinition"), imp = classId("FunctionImportProto"),
        tmpl = classId("TargetTemplateFunction");
    key = extent = d;
    if (d.kind == def || d.kind == imp || d.kind == tmpl) {
        rf::Node p = asNode(field(d, "proto"));
        if (p) {
            key = p;
        }
    } else if (d.kind == proto) {
        rf::Node owner = ctx.parentOf(d);
        if (owner.kind == def || owner.kind == imp || owner.kind == tmpl) {
            extent = owner;
        }
    }
}

Value refsImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("refs");
    }
    if (c[0].kind != Value::Kind::Node) {
        return Value::mkList(cel::ValueList());
    }
    rf::Node key, extent;
    functionDecl(*ctx, toNode(c[0]), key, extent);
    const std::vector<rf::Node> *uses = ctx->usesOf(key);
    if (!uses) {
        return Value::error("refs() needs a linked model, and this run has none");
    }
    c.steps = uses->size();
    return nodeList(*uses);
}

Value usedOnlyByItselfImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("used_only_by_itself");
    }
    rf::Node d, key;
    functionDecl(*ctx, toNode(c[0]), key, d);
    const std::vector<rf::Node> *uses = ctx->usesOf(key);
    if (!uses) {
        return Value::error("used_only_by_itself() needs a linked model, and this run has none");
    }
    bool all = !uses->empty();
    for (const rf::Node &u : *uses) {
        c.steps++;
        if (!ctx->within(u, d)) {
            all = false;
            break;
        }
    }
    return Value::boolean(all);
}

//* Constants

Value constIntImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("const_int");
    }
    if (!ctx->model()) {
        return Value::error("const_int() needs a linked model, and this run has none");
    }
    int64_t v;
    bool isBool;
    if (c[0].kind == Value::Kind::Node && ctx->constFold(toNode(c[0]), v, isBool)) {
        return Value::some(Value::integer(v));
    }
    return Value::none();
}

Value constBoolImpl(CallArgs &c) {
    const Context *ctx = context(c);
    if (!ctx) {
        return noContext("const_bool");
    }
    if (!ctx->model()) {
        return Value::error("const_bool() needs a linked model, and this run has none");
    }
    int64_t v;
    bool isBool;
    if (c[0].kind == Value::Kind::Node && ctx->constFold(toNode(c[0]), v, isBool) && isBool) {
        return Value::some(Value::boolean(v != 0));
    }
    return Value::none();
}
}

namespace cel {

void registerPssLib(FunctionRegistry &r) {
    using C = Cost;
    using namespace lib;
    r.library("pss");
    r.level(Level::L0, Scope::File);

    r.group("Kind tests");
    r.add("node_isa", "node.isa(type) -> bool", &isaImpl, C::Constant,
        "Whether the node is of the class named, or of a class deriving from it: "
        "`node.isa(ConstraintStmt)`. The argument must be a node class. Unlike "
        "`type(n) == K`, which tests the exact class, `isa` follows the `super:` chains of "
        "the AST schema. Like `type(n) == K`, it narrows: on the right of `&&`, and in the "
        "first result of `?:`, `n` has class `K`.")
        .classArg = 1;

    r.group("Navigation");
    r.add("parent_node", "parent(node) -> node", &parentImpl, C::Constant,
        "The node that owns this one: the scope holding a declaration, the expression "
        "holding an operand. `null` for a file's root, and for a node outside the files "
        "the run covers.");
    r.add("ancestors_node", "ancestors(node) -> list(node)", &ancestorsImpl, C::Custom,
        "The node's owners, nearest first, ending with the file's root; empty for a root. "
        "One step per element.");
    Overload &enclosing = r.add("enclosing_node_type", "enclosing(node, type) -> node", &enclosingImpl, C::Custom,
        "The nearest owner of the class named, or of a class deriving from it: "
        "`enclosing(node, Action)`. The result has that class, so its fields can be read "
        "directly (`enclosing(node, Action).name`). `null` when there is none; reading a "
        "field through `null` is an error, so test `enclosing(node, K) != null` first "
        "where there may be none. The node itself is not considered. One step per owner "
        "visited.");
    enclosing.classArg = 1;
    enclosing.resultIsClass = true;
    r.add("children_node", "children(node) -> list(node)", &childrenImpl, C::Custom,
        "The nodes this one owns, in source order: each node field and list element of "
        "the node's class, inherited fields first. References to declarations elsewhere "
        "are not children. One step per element.");
    r.add("descendants_node", "descendants(node) -> list(node)", &descendantsImpl, C::Custom,
        "Every node under this one, in pre-order (a node, then its children's subtrees), "
        "not including the node itself. One step per element.");
    r.add("siblings_node", "siblings(node) -> list(node)", &siblingsImpl, C::Custom,
        "The other elements of the list that holds the node (the statements of its block, "
        "the items of its scope), in order and without the node itself. Empty when the "
        "node is not a list element (`ExprBin.lhs`) or is a root. One step per element.");
    r.add("index_of_node", "index_of(node) -> int", &indexOfImpl, C::Custom,
        "The node's position, from 0, in the list that holds it, as `siblings` defines "
        "it; `-1` when it is not a list element. One step per element of that list.");

    r.group("Symbols");
    r.add("decl_path_node", "decl_path(node) -> string", &declPathImpl, C::Custom,
        "The node's declaration path, as fingerprints and SARIF logical locations use it: "
        "`p::C::A`, `p::C::A::constraint c`, `p::C::A::exec body#2` (the second in its "
        "scope), `p::C::A::f` for a field, `extend action p::C::A` for an extension (where it "
        "is written, not the type it extends). A node that declares nothing has the path of "
        "the declaration it is in, and so does a declaration inside a function, exec, "
        "constraint or activity; a node at file level has `\"\"`. Lexical: it needs no link. "
        "One step per enclosing node.");
    r.level(Level::L1, Scope::File);
    Overload &resolves = r.add("resolves_to_node", "resolves_to(node) -> node", &resolvesToImpl,
        C::Constant,
        "The declaration a reference names, as the linker bound it: an identifier, a type "
        "(`p::S`, `node.super_t`, a field's `DataTypeUserDefined`), or a path (`a.b.c` gives "
        "`c`'s declaration). `null` when the name is unbound or a built-in with no "
        "declaration (`comp`, `this`), and for a node that is not a reference. Two references "
        "to one declaration give the same node, so `resolves_to(a) == resolves_to(b)` "
        "compares declarations. `null` in gives `null` out, so "
        "`resolves_to(node.super_t)` needs no `has()` first. An error when the model is not "
        "linked.");
    resolves.nullable = true;
    r.level(Level::L0, Scope::File);
    r.add("is_owned_node", "is_owned(node) -> bool", &isOwnedImpl, C::Constant,
        "Whether the node is in one of the files being checked: false for the standard "
        "library, and for user files that were only read (a library directory, an "
        "`--include` path the run does not own). `false` for `null`.")
        .nullable = true;
    r.add("in_library_node", "in_library(node) -> bool", &inLibraryImpl, C::Constant,
        "Whether the node is in the standard library (`std_pkg`, the core library) or in a "
        "unit the linker adds itself. Use it on what `resolves_to` returns: "
        "`in_library(resolves_to(node.type))`. `false` for `null` (a type that is not a "
        "reference, such as `int`).")
        .nullable = true;

    r.group("References");
    r.add("is_read_node", "is_read(node) -> bool", &isReadImpl, C::Custom,
        "Whether this use of a name reads it: every use except the target of a plain "
        "`=` assignment or of a traversal's field initializer (`do A(.x = 1)`). A compound "
        "assignment (`x += 1`) both reads and writes. In a path (`a.b.c = 1`) only the last "
        "name is assigned; `a` and `b` are read. A use in a `with` constraint is a read: a "
        "constraint relates values, it does not assign one. Takes an identifier or a "
        "reference (its last name); `false` for a declaration's own name or another node. "
        "One step per enclosing node.");
    r.add("is_written_node", "is_written(node) -> bool", &isWrittenImpl, C::Custom,
        "Whether this use of a name assigns it: the last name of an assignment's left-hand "
        "side (any of `=`, `+=`, ...), or of a traversal's field initializer. Takes an "
        "identifier or a reference, as `is_read` does. One step per enclosing node.");
    r.level(Level::L4, Scope::Model);
    r.add("refs_node", "refs(node) -> list(ExprId)", &refsImpl, C::Custom,
        "Every use of a declaration: the identifiers (`ExprId`) that name it, in every user file of "
        "the model (owned or not), in file, line and column order. The declaration's own "
        "name is not a use. A function's uses are its calls, whether the definition or its "
        "prototype is passed (calls resolve to the prototype). Built once per run, the "
        "first time a rule asks, so a call is a lookup. `[]` for `null`. Whole-model: a rule that calls it is re-run on any "
        "change. An error when the model is not linked. One step per element.")
        .nullable = true;
    r.add("used_only_by_itself_node", "used_only_by_itself(node) -> bool",
        &usedOnlyByItselfImpl, C::Custom,
        "Whether a declaration has uses, and every one is inside the declaration itself: "
        "a function that only calls itself, a field read only in its own initializer. With "
        "`size(refs(d)) == 0`, this is how a rule asks \"is it unused?\". Whole-model. One "
        "step per use looked at.");

    r.group("Constants");
    r.level(Level::L3, Scope::File);
    r.add("const_int_node", "const_int(node) -> optional(int)", &constIntImpl, C::Constant,
        "The value of a constant integer expression, as the linker folds it: literals, "
        "arithmetic, bitwise, shift and comparison operators, `?:` and `in`, through "
        "`const` fields and **bound** template value parameters (a specialization's "
        "arguments). `optional.none()` when it does not fold: a non-`const` field, an enum "
        "item, a call, a string, a bit slice, a template parameter in the generic template "
        "(its default is not its value), and an integer that does not fit `int` (wider than "
        "64 bits, or unsigned above 2^63-1) -- never a truncated value. A `const` field or a "
        "template value parameter may be passed itself. A comparison folds to 0 or 1. Never "
        "an error, except without a linked model.")
        .nullable = true;
    r.add("const_bool_node", "const_bool(node) -> optional(bool)", &constBoolImpl, C::Constant,
        "`const_int` for a boolean expression: `true`, `false`, a comparison, `!`, `&&`, "
        "`||`, `in`, or a `const bool`. `optional.none()` when it does not fold or is not "
        "boolean (a 1-bit unsigned value counts as one).")
        .nullable = true;
}

}
}
}
