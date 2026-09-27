/*
 * ExtMemberVisibility.cpp
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
#include <limits>
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/IEnumDecl.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/ISymbolDeclaration.h"
#include "pssp/ast/ISymbolExtendScope.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/impl/NodeKind.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "ExtMemberVisibility.h"
#include "NameLookup.h"

namespace pssp {

namespace {
/** Deeper than any real package nesting; bounds a walk up `upper`. */
const int32_t MAX_DEPTH = 256;

/** Not visible at all. */
const int32_t RANK_HIDDEN = std::numeric_limits<int32_t>::max();
/** A wildcard import brings it in. Own packages rank below this. */
const int32_t RANK_IMPORTED = MAX_DEPTH + 1;
/** The type's own package, or the global scope. */
const int32_t RANK_TYPE_PKG = MAX_DEPTH + 2;
}

ExtMemberVisibility::ExtMemberVisibility(
        dmgr::IDebugMgr         *dmgr,
        ast::IRootSymbolScope   *root) :
            m_dmgr(dmgr), m_root(root), m_pkg_built(false),
            m_imp_built(false) {
    DEBUG_INIT("pssp::ExtMemberVisibility", dmgr);
}

ExtMemberVisibility::~ExtMemberVisibility() { }

ExtMemberVisibility::Choice ExtMemberVisibility::choose(
        ast::ISymbolTypeScope   *t,
        const std::string       &name,
        int32_t                 symtab_idx,
        const ast::Location     &use) {
    Choice ret;
    ret.idx = symtab_idx;

    // The common case, and the hot path: nothing an extension contributed.
    std::vector<ast::ISymbolExtMember *> cands;
    bool symtab_is_ext = false;
    for (std::vector<ast::ISymbolExtMemberUP>::const_iterator
            it=t->getExt_members().begin(); it!=t->getExt_members().end(); it++) {
        if ((*it)->getName() == name) {
            cands.push_back(it->get());
            symtab_is_ext |= ((*it)->getIdx() == symtab_idx);
        }
    }
    // The initial definition's member, when there is one, is the only one of
    // its name (17.2.3): an extension that repeats it was rejected.
    if (cands.empty() || !symtab_is_ext) {
        return ret;
    }

    ast::ISymbolScope *type_pkg = declaringPackage(t);
    ast::ISymbolScope *use_pkg = packageAt(use);
    int32_t best = RANK_HIDDEN;
    std::vector<ast::ISymbolExtMember *> at_best;
    for (std::vector<ast::ISymbolExtMember *>::const_iterator
            it=cands.begin(); it!=cands.end(); it++) {
        int32_t r = rank((*it)->getPkg(), type_pkg, use_pkg, use);
        if (r < best) {
            best = r;
            at_best.clear();
        }
        if (r == best) {
            at_best.push_back(*it);
        }
    }

    if (best == RANK_HIDDEN) {
        DEBUG("%s: no contribution is visible", name.c_str());
        ret.status = Status::Hidden;
        ret.members = cands;
    } else if (best == RANK_IMPORTED && at_best.size() > 1) {
        DEBUG("%s: %d imported contributions", name.c_str(), (int)at_best.size());
        ret.status = Status::Ambiguous;
        ret.members = at_best;
    } else {
        // Two in one own package cannot be (17.2.3); the type's own package
        // and the global scope are both RANK_TYPE_PKG, and then the first is
        // the one merged first, as before.
        ret.idx = at_best.front()->getIdx();
    }
    return ret;
}

bool ExtMemberVisibility::itemHidden(
        ast::ISymbolEnumScope   *e,
        int32_t                 idx,
        const ast::Location     &use,
        ast::ISymbolScope       *&pkg) {
    pkg = 0;
    // The initial definition's items come first; the rest were appended by
    // `extend enum` statements (TaskApplyTypeExtensions::applyEnumExtension).
    ast::IEnumDecl *decl = e->getDecl();
    if (!decl || idx < (int32_t)decl->getItems().size()
            || idx >= (int32_t)e->getChildren().size()) {
        return false;
    }
    const ast::Location &item_loc = e->getChildren().at(idx)->getLocation();
    if (item_loc.fileid < 0 || use.fileid < 0) {
        return false;
    }
    ast::ISymbolScope *item_pkg = packageAt(item_loc);
    if (rank(item_pkg, declaringPackage(e), packageAt(use), use) != RANK_HIDDEN) {
        return false;
    }
    pkg = item_pkg;
    return true;
}

int32_t ExtMemberVisibility::rank(
        ast::ISymbolScope       *pkg,
        ast::ISymbolScope       *type_pkg,
        ast::ISymbolScope       *use_pkg,
        const ast::Location     &use) {
    if (!pkg || pkg == m_root || pkg == type_pkg) {
        return RANK_TYPE_PKG;
    }
    // R's own package, or one enclosing it: nearest first.
    ast::ISymbolScope *s = use_pkg;
    for (int32_t d=0; s && s != m_root && d<MAX_DEPTH; d++, s=s->getUpper()) {
        if (s == pkg) {
            return d;
        }
    }
    if (imported(pkg, use)) {
        return RANK_IMPORTED;
    }
    // A position the linker cannot place: say nothing about it.
    if (use.fileid < 0 || use.lineno < 0) {
        return RANK_TYPE_PKG;
    }
    return RANK_HIDDEN;
}

bool ExtMemberVisibility::imported(
        ast::ISymbolScope       *pkg,
        const ast::Location     &use) {
    if (!m_imp_built) {
        buildImportIndex();
    }
    std::unordered_map<ast::ISymbolScope *, std::vector<ast::IPackageImportStmt *>>::const_iterator
        it = m_imports.find(pkg);
    if (it == m_imports.end()) {
        return false;
    }
    for (std::vector<ast::IPackageImportStmt *>::const_iterator
            i_it=it->second.begin(); i_it!=it->second.end(); i_it++) {
        if (NameLookup::appliesAt(*i_it, use)) {
            return true;
        }
    }
    return false;
}

ast::ISymbolScope *ExtMemberVisibility::declaringPackage(ast::ISymbolScope *t) const {
    ast::ISymbolScope *s = t->getUpper();
    for (int32_t d=0; s && d<MAX_DEPTH; d++, s=s->getUpper()) {
        if (s == m_root || isPackage(s)) {
            return s;
        }
    }
    return m_root;
}

ast::ISymbolScope *ExtMemberVisibility::packageAt(const ast::Location &loc) {
    if (loc.fileid < 0 || loc.lineno < 0) {
        return m_root;
    }
    if (!m_pkg_built) {
        buildPackageIndex();
    }
    std::unordered_map<int32_t, std::vector<PkgStmt>>::const_iterator it =
        m_pkg_stmts.find(loc.fileid);
    if (it == m_pkg_stmts.end()) {
        return m_root;
    }
    // Outer statements are indexed before the ones inside them, so the last
    // that holds `loc` is the innermost.
    ast::ISymbolScope *ret = m_root;
    for (std::vector<PkgStmt>::const_iterator
            s_it=it->second.begin(); s_it!=it->second.end(); s_it++) {
        if (contains(s_it->stmt->getLocation(), s_it->stmt->getEndLocation(), loc)) {
            ret = s_it->pkg;
        }
    }
    return ret;
}

void ExtMemberVisibility::buildPackageIndex() {
    m_pkg_built = true;
    for (std::vector<ast::IGlobalScopeUP>::const_iterator
            it=m_root->getUnits().begin(); it!=m_root->getUnits().end(); it++) {
        indexPackages(it->get(), m_root);
    }
}

void ExtMemberVisibility::indexPackages(
        ast::IScope             *s,
        ast::ISymbolScope       *ns) {
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin(); it!=s->getChildren().end(); it++) {
        ast::IPackageScope *p = NodeKind::cast<ast::IPackageScope>(it->get());
        if (!p) {
            continue;
        }
        // `package a::b { }` opens b, inside a.
        ast::ISymbolScope *pkg = ns;
        for (std::vector<ast::IExprIdUP>::const_iterator
                id_it=p->getId().begin(); pkg && id_it!=p->getId().end(); id_it++) {
            std::unordered_map<std::string,int32_t>::const_iterator s_it =
                pkg->getSymtab().find((*id_it)->getId());
            pkg = (s_it != pkg->getSymtab().end() && s_it->second >= 0
                    && s_it->second < (int32_t)pkg->getChildren().size())
                ? NodeKind::cast<ast::ISymbolScope>(pkg->getChildren().at(s_it->second).get())
                : 0;
        }
        if (!pkg) {
            continue;
        }
        m_pkg_stmts[p->getLocation().fileid].push_back({p, pkg});
        indexPackages(p, pkg);
    }
}

void ExtMemberVisibility::buildImportIndex() {
    m_imp_built = true;
    indexImports(m_root, 0);
}

void ExtMemberVisibility::indexImports(ast::ISymbolScope *s, int32_t depth) {
    if (depth > MAX_DEPTH) {
        return;
    }
    if (s->getImports()) {
        TaskResolveSymbolPathRef resolver(m_dmgr, m_root);
        for (std::vector<ast::IPackageImportStmt *>::const_iterator
                it=s->getImports()->getImports().begin();
                it!=s->getImports()->getImports().end(); it++) {
            ast::IPackageImportStmt *imp = *it;
            if (!imp->getWildcard() || imp->getAlias()
                    || !imp->getPath() || !imp->getPath()->getTarget()) {
                continue;
            }
            ast::ISymbolScope *target = NodeKind::cast<ast::ISymbolScope>(
                resolver.resolve(imp->getPath()->getTarget()));
            if (target) {
                m_imports[target].push_back(imp);
            }
        }
    }
    // Imports are only in packages, the global scope, components and their
    // extensions (18.1.3), whose lists already hold their extensions'.
    if (s != m_root && !isPackage(s)) {
        return;
    }
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin(); it!=s->getChildren().end(); it++) {
        ast::ISymbolScope *c = NodeKind::cast<ast::ISymbolScope>(it->get());
        if (c && c->getUpper() == s
                && (isPackage(c) || NodeKind::cast<ast::ISymbolTypeScope>(c))) {
            indexImports(c, depth+1);
        }
    }
}

bool ExtMemberVisibility::isPackage(ast::ISymbolScope *s) const {
    // A package is a plain symbol scope its parent names in its symtab; a
    // block is not named there.
    if (s == m_root
            || NodeKind::cast<ast::ISymbolTypeScope>(s)
            || NodeKind::cast<ast::ISymbolFunctionScope>(s)
            || NodeKind::cast<ast::ISymbolExtendScope>(s)
            || NodeKind::cast<ast::ISymbolEnumScope>(s)
            || NodeKind::cast<ast::ISymbolDeclaration>(s)) {
        return false;
    }
    ast::ISymbolScope *up = s->getUpper();
    if (!up) {
        return false;
    }
    std::unordered_map<std::string,int32_t>::const_iterator it =
        up->getSymtab().find(s->getName());
    return it != up->getSymtab().end()
        && it->second >= 0
        && it->second < (int32_t)up->getChildren().size()
        && up->getChildren().at(it->second).get() == s;
}

std::string ExtMemberVisibility::packageDesc(ast::ISymbolScope *pkg) const {
    if (!pkg || pkg == m_root) {
        return "the global scope";
    }
    return "package '" + pkg->getName() + "'";
}

std::string ExtMemberVisibility::importFor(ast::ISymbolScope *pkg) const {
    std::string path;
    for (int32_t d=0; pkg && pkg != m_root && d<MAX_DEPTH; d++, pkg=pkg->getUpper()) {
        path = (path.size()) ? pkg->getName() + "::" + path : pkg->getName();
    }
    return "import " + path + "::*;";
}

bool ExtMemberVisibility::contains(
        const ast::Location     &b,
        const ast::Location     &e,
        const ast::Location     &loc) {
    if (b.lineno < 0 || e.lineno < 0 || b.fileid != loc.fileid) {
        return false;
    }
    bool after_b = (loc.lineno > b.lineno)
        || (loc.lineno == b.lineno && loc.linepos >= b.linepos);
    bool before_e = (loc.lineno < e.lineno)
        || (loc.lineno == e.lineno && loc.linepos <= e.linepos);
    return after_b && before_e;
}

dmgr::IDebug *ExtMemberVisibility::m_dbg = 0;

}
