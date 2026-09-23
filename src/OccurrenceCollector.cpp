/**
 * OccurrenceCollector.cpp
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
#include <set>
#include <unordered_set>
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "OccurrenceCollector.h"

namespace pssp {

namespace {

/**
 * The name each kind of declaration is declared by.
 *
 * Only the node itself is inspected. The generated visitor would go on into
 * the node's fields -- a function's parameters, an enum's items, a scope's
 * children -- each of which has a name of its own, so the first name found
 * wins and container fields are not walked.
 */
class TaskGetNameId : public ast::VisitorBase {
public:
    ast::IExprId *get(ast::IScopeChild *c) {
        m_ret = 0;
        if (c) {
            c->accept(this);
        }
        return m_ret;
    }

    virtual void visitNamedScopeChild(ast::INamedScopeChild *i) override { set(i->getName()); }
    virtual void visitNamedScope(ast::INamedScope *i) override { set(i->getName()); }
    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override { set(i->getName()); }
    virtual void visitConstraintStmtField(ast::IConstraintStmtField *i) override { set(i->getName()); }
    virtual void visitFunctionParamDecl(ast::IFunctionParamDecl *i) override { set(i->getName()); }
    virtual void visitFunctionDefinition(ast::IFunctionDefinition *i) override {
        if (i->getProto()) {
            set(i->getProto()->getName());
        }
    }
    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override { set(i->getName()); }
    virtual void visitGenericConstraintParam(ast::IGenericConstraintParam *i) override { set(i->getName()); }
    virtual void visitTemplateParamDecl(ast::ITemplateParamDecl *i) override { set(i->getName()); }
    virtual void visitTypedefDeclaration(ast::ITypedefDeclaration *i) override { set(i->getName()); }
    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) override { set(i->getName()); }
    virtual void visitPackageImportStmt(ast::IPackageImportStmt *i) override { set(i->getAlias()); }
    virtual void visitPackageScope(ast::IPackageScope *i) override {
        if (i->getId().size()) {
            set(i->getId().back().get());
        }
    }
    virtual void visitActivityLabeledScope(ast::IActivityLabeledScope *i) override { set(i->getLabel()); }
    virtual void visitActivityLabeledStmt(ast::IActivityLabeledStmt *i) override { set(i->getLabel()); }
    virtual void visitMonitorActivityLabeledScope(ast::IMonitorActivityLabeledScope *i) override { set(i->getLabel()); }
    virtual void visitMonitorActivityLabeledStmt(ast::IMonitorActivityLabeledStmt *i) override { set(i->getLabel()); }
    virtual void visitCoverStmtInline(ast::ICoverStmtInline *i) override { set(i->getLabel()); }
    virtual void visitCoverStmtReference(ast::ICoverStmtReference *i) override { set(i->getLabel()); }

    // Containers: never walked.
    virtual void visitScope(ast::IScope *i) override { }
    virtual void visitSymbolChildrenScope(ast::ISymbolChildrenScope *i) override { }
    virtual void visitExpr(ast::IExpr *i) override { }
    virtual void visitDataType(ast::IDataType *i) override { }

private:
    void set(ast::IExprId *id) {
        if (!m_ret) {
            m_ret = id;
        }
    }

    ast::IExprId        *m_ret;
};

bool isGeneric(ast::ITypeScope *ts) {
    return ts && ts->getParams()
        && !ts->getParams()->getSpecialized()
        && ts->getParams()->getParams().size();
}

bool isSpecialization(ast::ITypeScope *ts) {
    return ts && ts->getParams() && ts->getParams()->getSpecialized();
}

/**
 * Pass 1: every declaration in every unit, keyed by its name's location.
 * Declarations inside a template specialization are copies of the generic's,
 * at the same locations, and are skipped so that the generic's win.
 */
class DeclWalker : public ast::VisitorBase {
public:
    DeclWalker(OccurrenceCollector *c) : m_coll(c), m_spec_depth(0) { }

    virtual void visitScopeChild(ast::IScopeChild *i) override {
        if (!m_spec_depth) {
            m_coll->addDecl(i);
        }
        VisitorBase::visitScopeChild(i);
    }

    virtual void visitPackageScope(ast::IPackageScope *i) override {
        m_coll->addPackage(i);
        VisitorBase::visitPackageScope(i);
    }

    virtual void visitTypeScope(ast::ITypeScope *i) override {
        bool spec = isSpecialization(i);
        m_spec_depth += spec;
        VisitorBase::visitTypeScope(i);
        m_spec_depth -= spec;
    }

private:
    OccurrenceCollector     *m_coll;
    int32_t                 m_spec_depth;
};

/**
 * Pass 1b: a function the source spells more than once -- prototype and
 * definition. Each spelling maps to the symbol tree's primary one, so they
 * group. (Packages split across files are grouped by addPackage().)
 */
class AliasWalker : public ast::VisitorBase {
public:
    AliasWalker(OccurrenceCollector *c) : m_coll(c) { }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        ast::IScopeChild *primary = m_coll->unwrap(i);
        for (auto it=i->getPrototypes().begin(); it!=i->getPrototypes().end(); it++) {
            alias(*it, primary);
        }
        if (i->getDefinition()) {
            alias(i->getDefinition()->getProto(), primary);
        }
        VisitorBase::visitSymbolFunctionScope(i);
    }

    // The symbol tree holds non-owning pointers to the AST's own scopes as
    // children and targets; walking into them is pass 1's job.
    virtual void visitScope(ast::IScope *i) override { }

private:
    void alias(ast::IScopeChild *c, ast::IScopeChild *primary) {
        ast::IExprId *n = m_coll->nameOf(c);
        if (primary && c != primary && OccurrenceCollector::isKeyable(n)) {
            m_coll->decls()[OccurrenceCollector::key(n->getLocation())] = primary;
        }
    }

    OccurrenceCollector     *m_coll;
};

/**
 * What each identifier under a node binds to. The resolver records
 * ExprId::decl at the sites that walk a path; everywhere else a whole
 * reference's binding is on the node (a SymbolRefPath), and is followed here.
 */
class BindingWalker : public ast::VisitorBase {
public:
    BindingWalker(OccurrenceCollector *c) : m_coll(c) { }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override {
        if (i->getElems().size()) {
            fallback(i->getElems().back()->getId(), i->getTarget());
        }
        VisitorBase::visitTypeIdentifier(i);
    }

    virtual void visitExprRefName(ast::IExprRefName *i) override {
        fallback(i->getId(), i->getTarget());
        VisitorBase::visitExprRefName(i);
    }

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override {
        if (i->getBase().size()) {
            fallback(i->getBase().back()->getId(), i->getTarget());
        }
        VisitorBase::visitExprRefPathStatic(i);
    }

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override {
        if (i->getHier_id() && i->getHier_id()->getElems().size()) {
            fallback(i->getHier_id()->getElems().front()->getId(), i->getTarget());
        }
        VisitorBase::visitExprRefPathContext(i);
    }

    // `compile if` / `compile assert` conditions (FR-002 case A), and the
    // path inside `compile has(...)`: neither is walked by the generated
    // visitor.
    virtual void visitScope(ast::IScope *i) override {
        VisitorBase::visitScope(i);
        for (auto it=i->getCompile_conds().begin(); it!=i->getCompile_conds().end(); it++) {
            acceptOpt((*it)->getCond());
        }
    }

    virtual void visitExprCompileHas(ast::IExprCompileHas *i) override {
        VisitorBase::visitExprCompileHas(i);
        acceptOpt(i->getRef());
    }

    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) override {
        // -2: bound by name to a built-in method (a collection method, or a
        // `string` method whose prototype is recorded in decl).
        if (i->getTarget() == -2 && i->getId() && !i->getId()->getDecl()) {
            m_builtin.insert(i->getId());
        }
        VisitorBase::visitExprMemberPathElem(i);
    }

    // Covergroup bodies are not walked by the generated visitor (their
    // fields are `visit: false`: symbol-resolution plan 10.1). Their names
    // are still occurrences.
    virtual void visitCovergroupCoverpoint(ast::ICovergroupCoverpoint *i) override {
        VisitorBase::visitCovergroupCoverpoint(i);
        acceptOpt(i->getTarget());
        acceptOpt(i->getIff());
    }

    virtual void visitCovergroupCross(ast::ICovergroupCross *i) override {
        VisitorBase::visitCovergroupCross(i);
        acceptOpt(i->getIff());
    }

    virtual void visitCoverpointBins(ast::ICoverpointBins *i) override {
        VisitorBase::visitCoverpointBins(i);
        acceptOpt(i->getArray_size());
        for (auto it=i->getRanges().begin(); it!=i->getRanges().end(); it++) {
            acceptOpt(it->get());
        }
        acceptOpt(i->getWith_expr());
    }

    virtual void visitCovergroupCrossBins(ast::ICovergroupCrossBins *i) override {
        VisitorBase::visitCovergroupCrossBins(i);
        acceptOpt(i->getWith_expr());
    }

    virtual void visitCovergroupOption(ast::ICovergroupOption *i) override {
        // `option.<name>`: a built-in option, not a declaration anywhere.
        if (i->getName()) {
            m_builtin.insert(i->getName());
        }
        VisitorBase::visitCovergroupOption(i);
        acceptOpt(i->getValue());
    }

    virtual void visitCovergroupPortmap(ast::ICovergroupPortmap *i) override {
        VisitorBase::visitCovergroupPortmap(i);
        acceptOpt(i->getTarget());
    }

    virtual void visitCovergroupInstantiation(ast::ICovergroupInstantiation *i) override {
        VisitorBase::visitCovergroupInstantiation(i);
        for (auto it=i->getTargets().begin(); it!=i->getTargets().end(); it++) {
            acceptOpt(it->get());
        }
    }

protected:
    /** What `i` binds to, canonicalized; null if unbound. */
    ast::IScopeChild *bound(ast::IExprId *i) {
        if (i->getDecl()) {
            return m_coll->canonical(i->getDecl());
        }
        auto it = m_pending.find(i);
        return (it != m_pending.end())?m_coll->canonical(it->second):0;
    }

    bool isBuiltinMethod(ast::IExprId *i) const { return m_builtin.count(i); }

    OccurrenceCollector                                         *m_coll;

private:
    void acceptOpt(ast::IExpr *e) {
        if (e) {
            e->accept(this);
        }
    }

    void fallback(ast::IExprId *id, ast::ISymbolRefPath *target) {
        if (!id || id->getDecl() || !target) {
            return;
        }
        // No inline context: a path through `with { ... }` does not resolve
        // here, and is left unbound unless the resolver recorded it.
        ast::IScopeChild *c = TaskResolveSymbolPathRef(
            0, m_coll->root()).resolve(target);
        if (c) {
            m_pending[id] = c;
        }
    }

    std::unordered_set<ast::IExprId *>                          m_builtin;
    std::unordered_map<ast::IExprId *, ast::IScopeChild *>      m_pending;
};

/**
 * Pass 1c: bindings inside template specializations, by location. The
 * linker resolves a generic's body only in its specializations -- copies of
 * the body, at the same locations. A name every specialization binds to the
 * same declaration is bound in the generic too; one they disagree on depends
 * on a parameter (FR-001-Q5).
 */
class SpecBindingWalker : public BindingWalker {
public:
    SpecBindingWalker(OccurrenceCollector *c) : BindingWalker(c) { }

    virtual void visitExprId(ast::IExprId *i) override {
        if (OccurrenceCollector::isKeyable(i)) {
            m_coll->addSpecBinding(i, bound(i));
        }
    }
};

/** Finds the specializations in the symbol tree. */
class SpecFinder : public ast::VisitorBase {
public:
    SpecFinder(OccurrenceCollector *c) : m_coll(c) { }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        for (auto it=i->getSpec_types().begin(); it!=i->getSpec_types().end(); it++) {
            if ((*it)->getTarget()) {
                SpecBindingWalker w(m_coll);
                (*it)->getTarget()->accept(&w);
            }
        }
        VisitorBase::visitSymbolTypeScope(i);
    }

    // Walk the symbol tree only, not the AST it points into.
    virtual void visitScope(ast::IScope *i) override { }

private:
    OccurrenceCollector     *m_coll;
};

/**
 * Pass 2: every identifier in the user units.
 */
class OccurrenceWalker : public BindingWalker {
public:
    OccurrenceWalker(OccurrenceCollector *c) : BindingWalker(c), m_generic_depth(0) { }

    void walk(ast::IGlobalScope *unit, std::vector<Occurrence> &out) {
        m_out = &out;
        unit->accept(this);
    }

    virtual void visitTypeScope(ast::ITypeScope *i) override {
        bool generic = isGeneric(i);
        m_generic_depth += generic;
        VisitorBase::visitTypeScope(i);
        m_generic_depth -= generic;
    }

    virtual void visitExprId(ast::IExprId *i) override {
        if (!OccurrenceCollector::hasLocation(i)
                || !m_seen.insert(OccurrenceCollector::key(i->getLocation())).second) {
            // Synthetic (no location), or a copy of one already reported.
            return;
        }
        Occurrence occ = {i, 0, 0, 0, false, OccurrenceResolution::Unresolved};
        ast::IScopeChild *decl = m_coll->lookupDecl(i);
        bool dependent = false;

        if (decl) {
            occ.is_decl = true;
        } else if (!(decl=bound(i)) && m_generic_depth) {
            decl = m_coll->specBinding(i, dependent);
        }

        const std::string &text = i->getId();
        if (!occ.is_decl && (text == "this" || text == "comp")
                && (!decl || dynamic_cast<ast::ITypeScope *>(decl))) {
            // `this` binds to the enclosing type, and `comp` to a synthetic
            // field. Neither is a declaration of that name (FR-001-Q2).
            occ.resolution = OccurrenceResolution::Builtin;
            decl = 0;
        } else if (decl) {
            occ.resolution = m_coll->classify(decl);
        } else if (isBuiltinMethod(i)) {
            occ.resolution = OccurrenceResolution::Builtin;
        } else if (m_generic_depth) {
            occ.resolution = OccurrenceResolution::Dependent;
        }

        occ.decl = decl;
        occ.decl_name = (decl)?m_coll->nameOf(decl):0;
        if (occ.is_decl) {
            occ.base_decl = m_coll->baseDecl(decl);
        }
        m_out->push_back(occ);
    }

private:
    std::vector<Occurrence>                                     *m_out;
    int32_t                                                     m_generic_depth;
    std::set<OccurrenceCollector::LocKey>                       m_seen;
};

}

OccurrenceCollector::OccurrenceCollector(dmgr::IDebugMgr *dmgr) :
    m_dmgr(dmgr), m_root(0) {

}

OccurrenceCollector::~OccurrenceCollector() {

}

void OccurrenceCollector::collect(
        ast::IRootSymbolScope       *root,
        std::vector<Occurrence>     &out) {
    m_root = root;
    m_decls.clear();
    m_packages.clear();
    m_spec_bindings.clear();

    DeclWalker decls(this);
    for (auto it=root->getUnits().begin(); it!=root->getUnits().end(); it++) {
        (*it)->accept(&decls);
    }

    AliasWalker aliases(this);
    for (auto it=root->getChildren().begin(); it!=root->getChildren().end(); it++) {
        (*it)->accept(&aliases);
    }

    SpecFinder specs(this);
    for (auto it=root->getChildren().begin(); it!=root->getChildren().end(); it++) {
        (*it)->accept(&specs);
    }

    OccurrenceWalker occs(this);
    for (auto it=root->getUnits().begin(); it!=root->getUnits().end(); it++) {
        if ((*it)->getFileid() >= 1) {
            occs.walk(it->get(), out);
        }
    }

    std::stable_sort(out.begin(), out.end(),
        [](const Occurrence &a, const Occurrence &b) {
            return key(a.id->getLocation()) < key(b.id->getLocation());
        });
}

ast::IExprId *OccurrenceCollector::nameOf(ast::IScopeChild *c) {
    return TaskGetNameId().get(unwrap(c));
}

ast::IScopeChild *OccurrenceCollector::unwrap(ast::IScopeChild *c) {
    for (int32_t depth=0; c && depth<16; depth++) {
        ast::ISymbolFunctionScope *fs = dynamic_cast<ast::ISymbolFunctionScope *>(c);
        if (fs) {
            if (fs->getPrototypes().size()) {
                return fs->getPrototypes().front();
            } else if (fs->getDefinition()) {
                return fs->getDefinition()->getProto();
            }
        }
        ast::ISymbolEnumScope *es = dynamic_cast<ast::ISymbolEnumScope *>(c);
        if (es && es->getDecl()) {
            return es->getDecl();
        }
        ast::ISymbolChildrenScope *sc = dynamic_cast<ast::ISymbolChildrenScope *>(c);
        if (sc && sc->getTarget() && sc->getTarget() != c) {
            c = sc->getTarget();
            continue;
        }
        ast::ISymbolScope *ss = dynamic_cast<ast::ISymbolScope *>(c);
        if (ss && !ss->getTarget() && ss->getUpper()) {
            auto it = m_packages.find(qname(ss));
            if (it != m_packages.end()) {
                return it->second;
            }
        }
        ast::IFunctionDefinition *fd = dynamic_cast<ast::IFunctionDefinition *>(c);
        if (fd && fd->getProto()) {
            return fd->getProto();
        }
        break;
    }
    return c;
}

void OccurrenceCollector::addPackage(ast::IPackageScope *p) {
    auto ins = m_packages.emplace(qname(p), p);
    ast::IExprId *n = nameOf(p);
    if (!ins.second && isKeyable(n)) {
        // A later `package p { ... }` block names the same package.
        m_decls[key(n->getLocation())] = ins.first->second;
    }
}

std::string OccurrenceCollector::qname(ast::IPackageScope *p) {
    std::string ret;
    for (ast::IScope *s=p; s; s=s->getParent()) {
        ast::IPackageScope *ps = dynamic_cast<ast::IPackageScope *>(s);
        if (!ps) {
            continue;
        }
        std::string n;
        for (auto it=ps->getId().begin(); it!=ps->getId().end(); it++) {
            n += (n.size()?"::":"") + (*it)->getId();
        }
        ret = (ret.size())?(n + "::" + ret):n;
    }
    return ret;
}

std::string OccurrenceCollector::qname(ast::ISymbolScope *s) {
    std::string ret;
    for (; s && s->getUpper(); s=s->getUpper()) {
        ret = (ret.size())?(s->getName() + "::" + ret):s->getName();
    }
    return ret;
}

void OccurrenceCollector::addDecl(ast::IScopeChild *c) {
    ast::IExprId *n = TaskGetNameId().get(c);
    if (isKeyable(n)) {
        // First wins: the declaration is reached before anything the
        // builder synthesized from it.
        m_decls.emplace(key(n->getLocation()), unwrap(c));
    }
}

void OccurrenceCollector::addSpecBinding(ast::IExprId *id, ast::IScopeChild *decl) {
    auto ins = m_spec_bindings.emplace(key(id->getLocation()), SpecBinding{decl, false});
    if (!ins.second && ins.first->second.decl != decl) {
        ins.first->second.conflict = true;
    }
}

ast::IScopeChild *OccurrenceCollector::specBinding(ast::IExprId *id, bool &conflict) {
    auto it = m_spec_bindings.find(key(id->getLocation()));
    conflict = (it != m_spec_bindings.end()) && it->second.conflict;
    return (it != m_spec_bindings.end() && !it->second.conflict)?it->second.decl:0;
}

ast::IScopeChild *OccurrenceCollector::lookupDecl(ast::IExprId *id) const {
    auto it = m_decls.find(key(id->getLocation()));
    return (it != m_decls.end())?it->second:0;
}

ast::IScopeChild *OccurrenceCollector::canonical(ast::IScopeChild *c) {
    c = unwrap(c);
    ast::IExprId *n = TaskGetNameId().get(c);
    if (isKeyable(n)) {
        auto it = m_decls.find(key(n->getLocation()));
        if (it != m_decls.end()) {
            return it->second;
        }
    }
    return c;
}

OccurrenceResolution OccurrenceCollector::classify(ast::IScopeChild *decl) {
    ast::IExprId *n = nameOf(decl);
    int32_t fileid = (n && n->getLocation().lineno > 0)
        ? n->getLocation().fileid
        : -1;
    if (fileid >= 1) {
        return OccurrenceResolution::User;
    } else if (fileid == 0) {
        return OccurrenceResolution::Library;
    } else {
        return OccurrenceResolution::Builtin;
    }
}

ast::IScopeChild *OccurrenceCollector::baseDecl(ast::IScopeChild *d) {
    ast::IExprId *n = nameOf(d);
    if (!n) {
        return 0;
    }
    ast::IScope *parent = d->getParent();
    if (!parent && dynamic_cast<ast::IFunctionPrototype *>(d)) {
        // A prototype owned by its definition; the definition is the member.
        return 0;
    }
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(parent);
    std::set<ast::ITypeScope *> seen;
    while (ts && seen.insert(ts).second && !ts->getSuper_cyclic()) {
        if (!ts->getSuper_t() || !ts->getSuper_t()->getTarget()) {
            return 0;
        }
        ast::ITypeScope *base = dynamic_cast<ast::ITypeScope *>(unwrap(
            TaskResolveSymbolPathRef(0, m_root).resolve(
                ts->getSuper_t()->getTarget())));
        if (!base) {
            return 0;
        }
        for (auto it=base->getChildren().begin(); it!=base->getChildren().end(); it++) {
            ast::IExprId *cn = nameOf(it->get());
            if (cn && cn->getId() == n->getId()) {
                return canonical(it->get());
            }
        }
        ts = base;
    }
    return 0;
}

}
