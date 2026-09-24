/*
 * NameLookup.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/IActivityDecl.h"
#include "pssp/ast/IActivityLabeledScope.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/IExecScope.h"
#include "pssp/ast/IExtendEnum.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IMonitorActivityDecl.h"
#include "pssp/ast/IMonitorActivityLabeledScope.h"
#include "pssp/ast/INamedScopeChild.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ISymbolExtendScope.h"
#include "pssp/ast/ITemplateElem.h"
#include "pssp/ast/ITemplateString.h"
#include "pssp/impl/TaskGetName.h"
#include "pssp/impl/TaskGetSymbolRefPath.h"
#include "pssp/impl/TaskGetSymbolRefPathKind.h"
#include "FunctionScopeUtil.h"
#include "NameLookup.h"
#include "TaskResolveSuperTypeRef.h"


namespace pssp {

namespace {

/**
 * A bound on walking up an inheritance chain. TaskCheckTypeCycles marks a
 * ring, and TaskResolveSuperTypeRef stops at a marked type, but it has not run
 * when the earliest passes look names up; a chain this long is a ring.
 */
const int32_t MAX_SUPER_DEPTH = 64;

/**
 * The base type of `s`, or null: none declared, not resolved, a parameter
 * bound to nothing, or `s` is not a type.
 */
ast::ISymbolScope *baseOf(
        dmgr::IDebugMgr     *dmgr,
        ast::ISymbolScope   *root,
        ast::ISymbolScope   *s) {
    ast::ISymbolTypeScope *ts_s = dynamic_cast<ast::ISymbolTypeScope *>(s);
    ast::ITypeScope *ts = (ts_s)
        ? dynamic_cast<ast::ITypeScope *>(ts_s->getTarget()) : 0;
    if (!ts || !ts->getSuper_t() || !ts->getSuper_t()->getTarget()) {
        return 0;
    }
    return dynamic_cast<ast::ISymbolScope *>(
        TaskResolveSuperTypeRef(dmgr, root).resolve(ts));
}

/**
 * The package `name` in `ns` forwards to, as its index in `root`; -1 if none.
 *
 * LRM 21.13, footnotes 1 and 2 (F28): PSS 2.0 declared `endianness_e`,
 * `packed_s` and `sizeof_s` in addr_reg_pkg. They are std_pkg's now, and
 * "tools shall support referencing these declarations in either std_pkg or
 * addr_reg_pkg as if they were the same types". So addr_reg_pkg forwards
 * them: a qualified step or an import that misses them in addr_reg_pkg finds
 * std_pkg's. The enum items come with `endianness_e`, for a wildcard import.
 */
int32_t forwardOf(
        ast::ISymbolScope   *root,
        ast::ISymbolScope   *ns,
        const std::string   &name) {
    static const std::set<std::string> names = {
        "endianness_e", "LITTLE_ENDIAN", "BIG_ENDIAN", "packed_s", "sizeof_s"
    };
    if (!root || ns->getName() != "addr_reg_pkg" || !names.count(name)) {
        return -1;
    }
    std::unordered_map<std::string, int32_t>::const_iterator from =
        root->getSymtab().find("addr_reg_pkg");
    std::unordered_map<std::string, int32_t>::const_iterator to =
        root->getSymtab().find("std_pkg");
    if (from == root->getSymtab().end() || to == root->getSymtab().end()
            || from->second < 0
            || from->second >= (int32_t)root->getChildren().size()
            || root->getChildren().at(from->second).get() != ns
            || to->second < 0
            || to->second >= (int32_t)root->getChildren().size()
            || !dynamic_cast<ast::ISymbolScope *>(
                root->getChildren().at(to->second).get())) {
        return -1;
    }
    return to->second;
}

}

void NameLookup::Member::appendTo(ast::ISymbolRefPath *path) const {
    if (fwd_pkg >= 0) {
        path->getPath().clear();
        path->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx, fwd_pkg});
    }
    for (int32_t s=0; s<super_depth; s++) {
        path->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_Super, 0});
    }
    path->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, idx});
}

NameLookup::NameLookup(ResolveContext *ctxt) : m_ctxt(ctxt), m_id(0),
        m_ref(0), m_super_depth(0), m_abs_base(0), m_fwd_decl(0),
        m_static_fn(0), m_static_hit(0), m_all_imports(false),
        m_skipped_imp(false), m_found_imp(0) {
    DEBUG_INIT("pssp::NameLookup", ctxt->getDebugMgr());
}

NameLookup::~NameLookup() {

}

ast::ISymbolRefPath *NameLookup::lookupFirst(const ast::IExprId *id) {
    DEBUG_ENTER("lookupFirst %s", id->getId().c_str());
    m_ref = 0;

    // A keyword the lexer returns as an ID. `\this` is an ordinary name.
    if (id->getId() == "this" && !id->getIs_escaped()) {
        m_ref = lookupThis();
        DEBUG_LEAVE("lookupFirst this %p", m_ref);
        return m_ref;
    }

    m_id = id;
    m_all_imports = false;
    m_skipped_imp = false;
    walk();

    // A miss that passed over a later declaration of the name is reported
    // as a use before declaration, not as an unknown name (18.2a/b).
    m_ctxt->setFwdDeclHint(id, (m_ref)?0:m_fwd_decl);
    m_ctxt->setStaticCtxtHint(id, (m_ref && m_static_hit)?m_static_fn:0);

    // 18.1.3, decision Q5: an import applies only in the file and the
    // statement it is written in. A miss that some other statement's import
    // would have satisfied is still a miss, but the report can name that
    // import -- the model's author almost certainly meant it. Found by
    // searching again with every import of each namespace, as the linker did
    // before 6.3a; quietly, so an ambiguity there is not reported.
    ast::IPackageImportStmt *leak = 0;
    if (!m_ref && m_skipped_imp) {
        m_all_imports = true;
        m_ctxt->pushQuiet();
        walk();
        m_ctxt->popQuiet();
        m_all_imports = false;
        if (m_ref) {
            leak = m_found_imp;
            delete m_ref;
            m_ref = 0;
        }
    }
    m_ctxt->setImportLeakHint(id, leak);

    DEBUG_LEAVE("lookupFirst %p (%d)", m_ref, (m_ref)?(int)m_ref->getPath().size():-1);
    return m_ref;
}

void NameLookup::walk() {
    m_ref = 0;
    m_super_depth = 0;
    m_abs_base = 0;
    m_fwd_decl = 0;
    m_static_fn = 0;
    m_static_hit = 0;
    m_found_imp = 0;

    // A clone, because the walk pops the iterator as it goes.
    m_ctxt->pushCloneSymtab();

    // 17.2: a member an `extend` contributed is resolved in the package chain
    // of the `extend` statement, which takes over from the extended type's
    // package chain where the type levels end. The extended type's packages
    // are still searched after it -- 17.2 does not make them visible, but the
    // linker always has, and taking them away is 6.5's diagnostic.
    ast::ISymbolScope *ext = m_ctxt->extensionCtxt();
    bool ext_pending = (ext != 0);
    bool seen_type = false;
    std::set<ast::ISymbolScope *> searched;

    while (!m_ref && m_ctxt->symtab()->hasScopes()) {
        // hasScopes() and getScope() do not answer the same question, and the
        // gap between them used to be a segfault (P7-X3). getScope() returns
        // the innermost entry that *is* a symbol scope, or 0 when there is
        // none -- `foreach (i : a) { a[0] == 1; }` reached it. Popping rather
        // than breaking keeps the answer right: the scope `a` lives in is
        // further out.
        ast::ISymbolScope *scope = m_ctxt->symtab()->getScope();
        if (!scope) {
            m_ctxt->symtab()->popScope();
            continue;
        }

        if (ext_pending && seen_type && isPackageLevel(scope)) {
            ext_pending = false;
            if (searchExtensionChain(ext, searched)) {
                break;
            }
        }

        if (!searched.count(scope)) {
            if (dynamic_cast<ast::ISymbolTypeScope *>(scope)) {
                seen_type = true;
            }
            DEBUG_ENTER("search %s", scope->getName().c_str());
            searchLevel(scope);
            DEBUG_LEAVE("search %s", scope->getName().c_str());
        }

        if (!m_ref) {
            m_ctxt->symtab()->popScope();
        }
    }

    if (!m_ref && ext_pending) {
        searchExtensionChain(ext, searched);
    }

    m_ctxt->popSymtab();
}

ast::ISymbolRefPath *NameLookup::lookupGlobal(const ast::IExprId *id) {
    ast::ISymbolScope *root = m_ctxt->root();
    if (!root) {
        return 0;
    }
    std::unordered_map<std::string,int32_t>::const_iterator it =
        root->getSymtab().find(id->getId());
    if (it == root->getSymtab().end()) {
        return 0;
    }
    ast::ISymbolRefPath *ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
    ret->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second});
    return ret;
}

NameLookup::Member NameLookup::lookupMember(
        dmgr::IDebugMgr             *dmgr,
        ast::ISymbolScope           *root,
        ast::ISymbolScope           *ns,
        const std::string           &name) {
    Member ret;
    // Allocated only once there is a base type: most lookups have none.
    std::vector<ast::ISymbolScope *> chain;
    ast::ISymbolScope *start = ns;

    for (int32_t depth=0; ns && depth<MAX_SUPER_DEPTH; depth++) {
        std::unordered_map<std::string,int32_t>::const_iterator it =
            ns->getSymtab().find(name);
        if (it != ns->getSymtab().end()) {
            int32_t idx = it->second;
            ast::IScopeChild *c = (idx >= 0 && idx < (int32_t)ns->getChildren().size())
                ? ns->getChildren().at(idx).get() : 0;

            // A synthetic scope owns its children list, so the symtab index
            // addresses it directly. A package's symtab records the index a
            // child has in the *physical* scope that declared it, which need
            // not line up. Confirm the candidate by name and fall back to a
            // scan; a type's symtab is exact, and this is the hot path.
            if (!dynamic_cast<ast::ISymbolTypeScope *>(ns)
                    && (!c || TaskGetName().get(c) != name)) {
                for (int32_t ci=0; ci<(int32_t)ns->getChildren().size(); ci++) {
                    ast::IScopeChild *cc = ns->getChildren().at(ci).get();
                    if (TaskGetName().get(cc) == name) {
                        c = cc;
                        idx = ci;
                        break;
                    }
                }
            }

            if (c) {
                ret.sym = c;
                ret.idx = idx;
                ret.super_depth = depth;
            }
            return ret;
        }

        // 18.3 b.3, and a qualified step `C::x` too (Ex. 242). A base
        // already on the chain is a ring; everything past it was searched.
        ns = baseOf(dmgr, root, ns);
        if (ns && (ns == start
                || std::find(chain.begin(), chain.end(), ns) != chain.end())) {
            break;
        }
        chain.push_back(ns);
    }

    // A name addr_reg_pkg forwards to std_pkg (F28). Enum items are not
    // package members here; a wildcard import finds those (searchImport).
    int32_t fwd;
    if (!ret.sym && (fwd=forwardOf(root, start, name)) >= 0) {
        ret = lookupMember(dmgr, root,
            dynamic_cast<ast::ISymbolScope *>(root->getChildren().at(fwd).get()),
            name);
        if (ret.sym) {
            ret.fwd_pkg = fwd;
        }
    }

    return ret;
}

ast::ISymbolRefPath *NameLookup::lookupThis() {
    DEBUG_ENTER("lookupThis");
    ast::ISymbolRefPath *ret = 0;

    m_ctxt->pushCloneSymtab();
    if (seekContextType()) {
        ret = m_ctxt->symtab()->getScopeSymbolPath();
        ret->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_This, 0});
    }
    m_ctxt->popSymtab();

    DEBUG_LEAVE("lookupThis %p", ret);
    return ret;
}

ast::ISymbolRefPath *NameLookup::lookupSuper(
        const ast::IExprId          *id,
        SuperResult                 &res) {
    DEBUG_ENTER("lookupSuper %s", id->getId().c_str());
    res = SuperResult();
    m_ref = 0;
    m_id = id;
    m_abs_base = 0;
    m_static_fn = 0;

    m_ctxt->pushCloneSymtab();
    res.type_s = seekContextType();
    if (!res.type_s) {
        res.status = SuperStatus::NoType;
    } else {
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(res.type_s->getTarget());
        res.base_s = dynamic_cast<ast::ISymbolScope *>(TaskResolveSuperTypeRef(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(ts));

        if (!ts || !ts->getSuper_t()) {
            res.status = SuperStatus::NoBase;
        } else if (!res.base_s) {
            // Unknown base type (reported at the declaration), an inheritance
            // ring (reported by TaskCheckTypeCycles), or a parameter with
            // nothing bound: nothing to search, and nothing new to say.
            res.status = SuperStatus::BaseUnresolved;
        } else {
            // The base, and what it inherits -- never the derived type's own
            // members, and never the lexical scopes outside it (17.1). The
            // iterator stays on the derived type, so the path takes one
            // ElemKind_Super per step, starting with this one.
            m_super_depth = 1;
            if (!searchMembers(res.base_s, false)) {
                searchBases(res.base_s, true);
            }
            m_super_depth = 0;
            res.status = (m_ref)?SuperStatus::Ok:SuperStatus::NotFound;
        }
    }
    m_ctxt->popSymtab();

    DEBUG_LEAVE("lookupSuper %p", m_ref);
    return m_ref;
}

ast::ISymbolTypeScope *NameLookup::contextType() {
    m_ctxt->pushCloneSymtab();
    ast::ISymbolTypeScope *ret = seekContextType();
    m_ctxt->popSymtab();
    return ret;
}

ast::ISymbolTypeScope *NameLookup::seekContextType() {
    // Inside `a with { ... }` the traversed action's scope is pushed on top of
    // the containing action's (visitActivityActionHandleTraversal). Names
    // search it first; `this` and `super` pass over it, which is the whole
    // point of `this` there -- reaching a containing-action field the
    // sub-action's field of the same name shadows.
    ast::ISymbolScope *skip = m_ctxt->inlineCtxt();

    while (m_ctxt->symtab()->hasScopes()) {
        // See lookupFirst() for why a null scope pops rather than breaks.
        ast::ISymbolScope *scope = m_ctxt->symtab()->getScope();
        ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
        if (ts) {
            if (scope == skip) {
                skip = 0;
            } else {
                return ts;
            }
        }
        m_ctxt->symtab()->popScope();
    }
    return 0;
}

bool NameLookup::searchLevel(ast::ISymbolScope *s) {
    // Dispatched by kind here rather than through a visitor: the generated
    // visitor's default for a compound scope (a loop, a template block)
    // descends into its bodies, and a hit in one of those is not in scope.
    if (ast::ISymbolFunctionScope *f = dynamic_cast<ast::ISymbolFunctionScope *>(s)) {
        return searchFunction(f);
    } else if (ast::ISymbolTypeScope *t = dynamic_cast<ast::ISymbolTypeScope *>(s)) {
        return searchType(t);
    } else if (ast::ISymbolDeclaration *d = dynamic_cast<ast::ISymbolDeclaration *>(s)) {
        return searchSymbolDecl(d);
    } else {
        return searchBlock(s);
    }
}

bool NameLookup::searchBlock(ast::ISymbolScope *s) {
    if (searchMembers(s, isOrderSensitive(s)) || searchEnumItems(s)) {
        return true;
    }
    if (s->getImports() && (m_ref=searchImports(m_id, s->getImports()))) {
        DEBUG("Found %s through an import", m_id->getId().c_str());
        return true;
    }
    return false;
}

bool NameLookup::searchType(ast::ISymbolTypeScope *s) {
    // b.1: the type's members, and its own template parameters (10.3; Q3).
    if (searchMembers(s, false)) {
        return true;
    }

    if (s->getPlist()) {
        std::unordered_map<std::string,int32_t>::const_iterator it =
            s->getPlist()->getSymtab().find(m_id->getId());
        if (it != s->getPlist()->getSymtab().end()) {
            DEBUG("Found %s as a template parameter (%d)",
                m_id->getId().c_str(), it->second);
            m_ref = m_ctxt->symtab()->getScopeSymbolPath();
            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ParamIdx, it->second});
            return true;
        }
    }

    if (searchEnumItems(s)) {
        return true;
    }

    // b.3 before b.4: an inherited member hides a name the type imports.
    if (searchBases(s, false)) {
        return true;
    }

    // b.4: the type's own imports. Only a component has any.
    if (s->getImports() && (m_ref=searchImports(m_id, s->getImports()))) {
        DEBUG("Found %s through an import", m_id->getId().c_str());
        return true;
    }

    return false;
}

bool NameLookup::searchFunction(ast::ISymbolFunctionScope *s) {
    // Only a component function can be static and have instance members
    // around it; a package function's walk never reaches a component.
    if (!m_static_fn && declaredStatic(s)) {
        m_static_fn = s;
    }

    // A function scope built from a bare prototype has no plist -- see
    // TaskBuildSymbolTree::visitFunctionPrototype.
    if (s->getPlist()) {
        std::unordered_map<std::string,int32_t>::const_iterator it =
            s->getPlist()->getSymtab().find(m_id->getId());
        if (it != s->getPlist()->getSymtab().end()) {
            DEBUG("Found %s as a function parameter @ %d",
                m_id->getId().c_str(), it->second);
            m_ref = m_ctxt->symtab()->getScopeSymbolPath();
            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ArgIdx, it->second});
            return true;
        }
    }

    return searchBlock(s);
}

bool NameLookup::searchSymbolDecl(ast::ISymbolDeclaration *s) {
    // `symbol s(A aa) { aa; }`: a symbol's parameters are in scope in its body
    // (11.4), addressed by position like a function's. They are a list on the
    // declaration, not children.
    for (uint32_t idx=0; idx<s->getParams().size(); idx++) {
        ast::IFunctionParamDecl *p = s->getParams().at(idx).get();
        if (p->getName() && p->getName()->getId() == m_id->getId()) {
            DEBUG("Found %s as a symbol parameter @ %d", m_id->getId().c_str(), idx);
            m_ref = m_ctxt->symtab()->getScopeSymbolPath();
            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ArgIdx, (int32_t)idx});
            return true;
        }
    }
    return searchBlock(s);
}

bool NameLookup::searchMembers(ast::ISymbolScope *s, bool order) {
    std::unordered_map<std::string,int32_t>::const_iterator it =
        s->getSymtab().find(m_id->getId());
    if (it == s->getSymtab().end()) {
        return false;
    }
    ast::IScopeChild *c = s->getChildren().at(it->second).get();

    // 18.2a/b, 4.7.1.2: in a block, a name is declared from its declaration
    // on. A later declaration is not in scope here, so the search carries on
    // outward -- `x = 1; string x;` assigns an outer `x` if there is one.
    if (order && declaredAfter(c, m_id->getLocation())) {
        DEBUG("%s is declared after the reference; hidden", m_id->getId().c_str());
        if (!m_fwd_decl) {
            m_fwd_decl = c;
        }
        return false;
    }

    hit(s, c, TaskGetSymbolRefPathKind(m_ctxt->getDebugMgr()).get(c), it->second);
    return (m_ref != 0);
}

bool NameLookup::searchEnumItems(ast::ISymbolScope *s) {
    const ResolveContext::EnumCache &ec = m_ctxt->enumsOf(s);
    for (std::vector<ast::ISymbolEnumScope *>::const_iterator
            it=ec.enums.begin(); it!=ec.enums.end(); it++) {
        ast::ISymbolEnumScope *e = *it;
        std::unordered_map<std::string,int32_t>::const_iterator e_it =
            e->getSymtab().find(m_id->getId());
        if (e_it != e->getSymtab().end()) {
            DEBUG("Found %s as an item of enum %s",
                m_id->getId().c_str(), e->getName().c_str());
            m_ref = TaskGetSymbolRefPath(
                m_ctxt->getDebugMgr(),
                m_ctxt->root(),
                m_ctxt->getFactory()->getAstFactory()).mk(e);
            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx, e_it->second});
            return true;
        }
    }

    // An item an `extend enum` in `s` contributes is declared here too, though
    // it lives in the extended enum (17.2; Ex. 248 imports the package that
    // extends the enum to use the items it adds).
    for (std::vector<ast::IExtendEnum *>::const_iterator
            it=ec.exts.begin(); it!=ec.exts.end(); it++) {
        bool declares = false;
        for (std::vector<ast::IEnumItemUP>::const_iterator
                i_it=(*it)->getItems().begin();
                i_it!=(*it)->getItems().end() && !declares; i_it++) {
            declares = ((*i_it)->getName()->getId() == m_id->getId());
        }
        if (!declares || !(*it)->getTarget()->getTarget()) {
            continue;
        }
        ast::ISymbolEnumScope *e = dynamic_cast<ast::ISymbolEnumScope *>(
            m_ctxt->resolveSymbolPathRef((*it)->getTarget()->getTarget()));
        std::unordered_map<std::string,int32_t>::const_iterator e_it =
            (e)?e->getSymtab().find(m_id->getId()):std::unordered_map<std::string,int32_t>::const_iterator();
        if (!e || e_it == e->getSymtab().end()) {
            continue;
        }
        DEBUG("Found %s as an item an extension adds to enum %s",
            m_id->getId().c_str(), e->getName().c_str());
        m_ref = TaskGetSymbolRefPath(
            m_ctxt->getDebugMgr(),
            m_ctxt->root(),
            m_ctxt->getFactory()->getAstFactory()).mk(e);
        m_ref->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx, e_it->second});
        return true;
    }
    return false;
}

bool NameLookup::searchBases(ast::ISymbolScope *s, bool members_only) {
    int32_t depth0 = m_super_depth;
    // Allocated only once there is a base type: most types have none.
    std::vector<ast::ISymbolScope *> chain;
    ast::ISymbolScope *start = s;
    bool found = false;

    for (int32_t n=0; !found && n<MAX_SUPER_DEPTH; n++) {
        // Follows a parameter binding when the base is one of the generic's
        // own parameters -- see TaskResolveSuperTypeRef.
        s = baseOf(m_ctxt->getDebugMgr(), m_ctxt->root(), s);
        if (!s || s == start
                || std::find(chain.begin(), chain.end(), s) != chain.end()) {
            break;
        }
        chain.push_back(s);
        m_super_depth++;
        found = searchMembers(s, false) || (!members_only && searchEnumItems(s));
    }

    m_super_depth = depth0;
    return found;
}

bool NameLookup::searchExtensionChain(
        ast::ISymbolScope               *decl_s,
        std::set<ast::ISymbolScope *>   &searched) {
    DEBUG_ENTER("searchExtensionChain %s from %s",
        m_id->getId().c_str(), decl_s->getName().c_str());
    bool found = false;
    int32_t depth0 = m_super_depth;
    m_super_depth = 0;

    for (ast::ISymbolScope *s=decl_s; s && !found; s=s->getUpper()) {
        searched.insert(s);
        m_abs_base = s;
        found = searchMembers(s, false) || searchEnumItems(s);
        m_abs_base = 0;
        // 17.2.3: the imports in effect for an extension body are those at
        // the extension's declaration site.
        if (!found && s->getImports()
                && (m_ref=searchImports(m_id, s->getImports()))) {
            found = true;
        }
        if (s == m_ctxt->root()) {
            break;
        }
    }

    m_super_depth = depth0;
    DEBUG_LEAVE("searchExtensionChain %s %d", m_id->getId().c_str(), found);
    return found;
}

bool NameLookup::isPackageLevel(ast::ISymbolScope *s) const {
    for (int32_t n=0; s; n++) {
        if (s == m_ctxt->root()) {
            return true;
        }
        if (n > MAX_SUPER_DEPTH
                || dynamic_cast<ast::ISymbolTypeScope *>(s)
                || dynamic_cast<ast::ISymbolFunctionScope *>(s)
                || dynamic_cast<ast::ISymbolExtendScope *>(s)
                || dynamic_cast<ast::ISymbolEnumScope *>(s)
                || dynamic_cast<ast::ISymbolDeclaration *>(s)) {
            return false;
        }
        // A package is a named child of a package or of the global scope; a
        // block is not in its parent's symtab under its own name.
        ast::ISymbolScope *up = s->getUpper();
        if (!up) {
            return false;
        }
        std::unordered_map<std::string,int32_t>::const_iterator it =
            up->getSymtab().find(s->getName());
        if (it == up->getSymtab().end()
                || it->second < 0
                || it->second >= (int32_t)up->getChildren().size()
                || up->getChildren().at(it->second).get() != s) {
            return false;
        }
        s = up;
    }
    return false;
}

void NameLookup::hit(
        ast::ISymbolScope           *found_in,
        ast::IScopeChild            *c,
        ast::SymbolRefPathElemKind  kind,
        int32_t                     idx) {
    DEBUG("Found %s in %s @ %d (super depth %d)",
        m_id->getId().c_str(), found_in->getName().c_str(), idx, m_super_depth);

    m_ref = (m_abs_base)
        ? absPath(m_abs_base)
        : m_ctxt->symtab()->getScopeSymbolPath();
    if (!m_ref) {
        return;
    }

    for (int32_t s=0; s<m_super_depth; s++) {
        m_ref->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_Super, 0});
    }
    m_ref->getPath().push_back({kind, idx});

    // A static function has no instance to take a member from (20.2). The
    // walk reaches the component's own members only by leaving the function,
    // so this is a member of the component or of a base.
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(found_in);
    if (m_static_fn && ts && dynamic_cast<ast::IComponent *>(ts->getTarget())
            && isInstanceMember(c)) {
        m_static_hit = c;
    }
}

ast::ISymbolRefPath *NameLookup::absPath(ast::ISymbolScope *s) {
    // Built by walking the symbol tree upward and recording each scope's index
    // in its parent. getScopeSymbolPath() answers for the iterator's position,
    // which is exactly the thing that is wrong here.
    std::vector<int32_t> idx;
    ast::ISymbolScope *cur = s;

    while (cur && cur != m_ctxt->root()) {
        if (cur->getId() < 0) {
            // Unnamed position. A partial path would resolve to the wrong
            // node rather than to none.
            DEBUG("absPath: scope %s has no index", cur->getName().c_str());
            return 0;
        }
        idx.push_back(cur->getId());
        cur = cur->getUpper();
    }

    if (cur != m_ctxt->root()) {
        DEBUG("absPath: walk did not reach the root");
        return 0;
    }

    ast::ISymbolRefPath *ret =
        m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
    for (std::vector<int32_t>::const_reverse_iterator
        it=idx.rbegin(); it!=idx.rend(); it++) {
        ret->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx, *it});
    }
    return ret;
}

/**
 * 18.1.3: an explicit import takes precedence over a wildcard import, and a
 * name that more than one import of the same kind provides is not imported
 * at all. So the explicit imports are searched first and the wildcards only
 * when they yield nothing; within a tier, two routes to the *same*
 * declaration are one match (F18). A real ambiguity is reported and
 * resolves to nothing, rather than to the first import, which cascaded.
 *
 * Package aliases come before both (18.3 c.2.i; decision Q3). 18.3 b.4 does
 * not list them for a component, but Ex. 273 needs alias over wildcard there
 * too. Two aliases of one name in one statement are an error reported where
 * they are declared (TaskResolveImports, 18.1.4), and only one statement's
 * imports apply at a use, so the first alias that matches is the answer.
 *
 * `imp` holds the imports of every statement that opens the namespace -- each
 * `package p` statement, a component and all its extensions, every file's
 * global scope. An import applies only within its own statement (6.3a), so the
 * rest are passed over; see appliesAt().
 */
ast::ISymbolRefPath *NameLookup::searchImports(
    const ast::IExprId          *id,
    ast::ISymbolImportSpec      *imp) {
    DEBUG_ENTER("searchImports - %d statements", (int)imp->getImports().size());
    ast::ISymbolRefPath *ret = 0;

    // Tier 0: aliases; 1: explicit imports; 2: wildcard imports.
    for (int tier=0; tier<3 && !ret; tier++) {
        bool want_wildcard = (tier == 2);
        bool want_alias = (tier == 0);
        ast::IScopeChild *found = 0;
        bool ambiguous = false;
        for (std::vector<ast::IPackageImportStmt *>::const_iterator
                imp_it=imp->getImports().begin();
                imp_it!=imp->getImports().end(); imp_it++) {
            if ((*imp_it)->getWildcard() != want_wildcard
                    || ((*imp_it)->getAlias() != 0) != want_alias) {
                continue;
            }
            // The namespace's imports are gathered from every statement that
            // opens it; only those of a statement around the use apply.
            if (!m_all_imports && !appliesAt(*imp_it, id->getLocation())) {
                m_skipped_imp = true;
                continue;
            }
            ast::ISymbolRefPath *ret_t = searchImport(id, *imp_it);
            if (!ret_t) {
                continue;
            }
            if (want_alias) {
                ret = ret_t;
                m_found_imp = *imp_it;
                break;
            }
            ast::IScopeChild *node = m_ctxt->resolveSymbolPathRef(ret_t);
            if (!ret) {
                ret = ret_t;
                found = node;
                m_found_imp = *imp_it;
            } else if (node != found) {
                ambiguous = true;
                delete ret_t;
            } else {
                delete ret_t;
            }
        }
        if (ambiguous) {
            m_ctxt->addErrorMarker(
                id->getLocation(),
                "ambiguous reference to '%s': more than one %s import provides "
                "it, so none does (18.1.3); qualify the name",
                id->getId().c_str(),
                want_wildcard ? "wildcard" : "explicit");
            delete ret;
            ret = 0;
            m_found_imp = 0;
            break;
        }
    }

    DEBUG_LEAVE("searchImports %p", ret);
    return ret;
}

ast::ISymbolRefPath *NameLookup::searchImport(
        const ast::IExprId          *id,
        ast::IPackageImportStmt     *imp) {
    ast::ISymbolRefPath *target = imp->getPath()->getTarget();

    if (!target) {
        DEBUG("Skipping an import whose target did not resolve");
        return 0;
    }

    // A single-symbol import names the symbol; it does not open it as a
    // scope. `import p::t;` matches `t` and hands back the import's own path.
    // `import p::q as a;` matches `a` only: an alias does not make `q`
    // visible (18.1.4).
    if (!imp->getWildcard()) {
        const std::vector<ast::ITypeIdentifierElemUP> &elems =
            imp->getPath()->getElems();
        const std::string &name = (imp->getAlias())
            ? imp->getAlias()->getId()
            : (elems.empty() ? std::string() : elems.back()->getId()->getId());
        if (name.empty() || name != id->getId()) {
            return 0;
        }
        ast::ISymbolRefPath *ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
        ret->getPath().insert(
            ret->getPath().begin(),
            target->getPath().begin(),
            target->getPath().end());
        return ret;
    }

    // A wildcard import: a member of the package it names -- never that
    // package's imports (Ex. 271) -- or an item of an enum declared in it.
    ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(
        m_ctxt->resolveSymbolPathRef(target));
    if (!target_s) {
        return 0;
    }

    std::unordered_map<std::string, int32_t>::const_iterator it =
        target_s->getSymtab().find(id->getId());

    if (it != target_s->getSymtab().end()) {
        ast::ISymbolRefPath *ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
        ret->getPath().insert(
            ret->getPath().begin(),
            target->getPath().begin(),
            target->getPath().end());
        ret->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second});
        return ret;
    }

    // A name addr_reg_pkg forwards (F28) is std_pkg's, item or type. It is
    // the same declaration, so importing both packages is not ambiguous.
    int32_t fwd = forwardOf(m_ctxt->root(), target_s, id->getId());
    if (fwd >= 0) {
        ast::ISymbolScope *fwd_s = dynamic_cast<ast::ISymbolScope *>(
            m_ctxt->root()->getChildren().at(fwd).get());
        it = fwd_s->getSymtab().find(id->getId());
        if (it != fwd_s->getSymtab().end()) {
            ast::ISymbolRefPath *ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
            ret->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, fwd});
            ret->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second});
            return ret;
        }
        target_s = fwd_s;
    }

    ast::ISymbolRefPath *saved = m_ref;
    m_ref = 0;
    ast::ISymbolRefPath *ret = (searchEnumItems(target_s))?m_ref:0;
    m_ref = saved;
    return ret;
}

bool NameLookup::appliesAt(
        ast::IPackageImportStmt         *imp,
        const ast::Location             &use) {
    // The statement the import is written in: a `package` statement, a
    // component declaration, an `extend`, or a file's global scope. Extension
    // merging never re-parents, and a specialization's copy is given the
    // original's parent (TaskCopyAst), so this is the lexical statement even
    // when the import was gathered into another namespace's list.
    ast::IScope *stmt = imp->getParent();
    if (!stmt || use.fileid < 0 || use.lineno < 0) {
        // Nowhere to measure from: a synthetic node. Apply it, as before.
        return true;
    }

    // 18.1.3: an import in the global scope applies to the rest of its file.
    if (dynamic_cast<ast::IGlobalScope *>(stmt)) {
        return imp->getLocation().fileid < 0
            || imp->getLocation().fileid == use.fileid;
    }

    const ast::Location &b = stmt->getLocation();
    const ast::Location &e = stmt->getEndLocation();
    if (b.lineno < 0 || e.lineno < 0) {
        return true;
    }
    if (b.fileid != use.fileid) {
        return false;
    }
    bool after_b = (use.lineno > b.lineno)
        || (use.lineno == b.lineno && use.linepos >= b.linepos);
    bool before_e = (use.lineno < e.lineno)
        || (use.lineno == e.lineno && use.linepos <= e.linepos);
    return after_b && before_e;
}

bool NameLookup::reportImportLeak(
        ResolveContext                  *ctxt,
        const ast::IExprId              *id,
        const char                      *kind) {
    ast::IPackageImportStmt *imp = ctxt->importLeakHint(id);
    if (!imp) {
        return false;
    }
    std::string text = importText(imp);
    ctxt->addMarker(
        MarkerSeverityE::Error,
        id->getLocation(),
        std::string("unknown ") + kind + " '" + id->getId() + "'; 'import "
            + text + ";' provides it, but an import applies only inside the "
            + "statement it is written in, or to its own file (18.1.3) -- add "
            + "'import " + text + ";' here",
        {{imp->getLocation(), "imported here"}});
    return true;
}

std::string NameLookup::importText(ast::IPackageImportStmt *imp) {
    std::string ret;
    ast::ITypeIdentifier *path = imp->getPath();
    if (path) {
        if (path->getIs_global()) {
            ret += "::";
        }
        for (uint32_t i=0; i<path->getElems().size(); i++) {
            if (i) {
                ret += "::";
            }
            ret += path->getElems().at(i)->getId()->getId();
        }
    }
    if (imp->getWildcard()) {
        ret += "::*";
    } else if (imp->getAlias()) {
        ret += " as " + imp->getAlias()->getId();
    }
    return ret;
}

bool NameLookup::isOrderSensitive(const ast::ISymbolScope *s) {
    // Exec and activity blocks, and template strings (Table G.1 of report G).
    // Type, package and global scopes are not: a member may be used before
    // it is declared (Examples 261, 262). A loop's own scope declares its
    // variables before its body, so there is nothing there to hide.
    return dynamic_cast<const ast::IExecScope *>(s)
        || dynamic_cast<const ast::IActivityDecl *>(s)
        || dynamic_cast<const ast::IActivityLabeledScope *>(s)
        || dynamic_cast<const ast::IMonitorActivityDecl *>(s)
        || dynamic_cast<const ast::IMonitorActivityLabeledScope *>(s)
        || dynamic_cast<const ast::ITemplateString *>(s)
        || dynamic_cast<const ast::ITemplateElem *>(s);
}

const ast::Location &NameLookup::declLocation(const ast::IScopeChild *c) {
    // The declared *name*, not the statement: `int a = 1, b = a;` sees `a`,
    // and `int x = x;` sees itself, as in C and SystemVerilog.
    const ast::INamedScopeChild *n = dynamic_cast<const ast::INamedScopeChild *>(c);
    if (n && n->getName()) {
        return n->getName()->getLocation();
    }
    const ast::IProceduralStmtDataDeclaration *d =
        dynamic_cast<const ast::IProceduralStmtDataDeclaration *>(c);
    if (d && d->getName()) {
        return d->getName()->getLocation();
    }
    return c->getLocation();
}

bool NameLookup::declaredAfter(
        const ast::IScopeChild      *decl,
        const ast::Location         &use) {
    const ast::Location &d = declLocation(decl);
    // No order across files, and none where a position is unknown.
    if (d.fileid != use.fileid || d.lineno < 0 || use.lineno < 0) {
        return false;
    }
    return (d.lineno > use.lineno)
        || (d.lineno == use.lineno && d.linepos > use.linepos);
}

dmgr::IDebug *NameLookup::m_dbg = 0;

}
