/*
 * TaskCheckImports.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/IComment.h"
#include "pssp/ast/ICompileCond.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IScope.h"
#include "pssp/impl/NodeKind.h"
#include "NameLookup.h"
#include "TaskCheckImports.h"

namespace pssp {

namespace {
const int32_t MAX_DEPTH = 256;
}

TaskCheckImports::TaskCheckImports(ResolveContext *ctxt) :
        m_ctxt(ctxt), m_root(0), m_n_builtin(0) {
    DEBUG_INIT("pssp::TaskCheckImports", ctxt->getDebugMgr());
}

TaskCheckImports::~TaskCheckImports() { }

void TaskCheckImports::check(ast::IRootSymbolScope *root, uint32_t n_builtin_units) {
    DEBUG_ENTER("check");
    m_root = root;
    m_n_builtin = n_builtin_units;
    m_seen.clear();
    walk(root, 0);
    DEBUG_LEAVE("check");
}

void TaskCheckImports::walk(ast::ISymbolScope *s, int32_t depth) {
    if (depth > MAX_DEPTH) {
        return;
    }
    checkScope(s);

    // Imports are in packages, the global scope and components (18.1.3); a
    // component's list holds its extensions' too.
    if (s != m_root && !m_ctxt->extVisibility().isPackage(s)) {
        return;
    }
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin(); it!=s->getChildren().end(); it++) {
        ast::ISymbolScope *c = NodeKind::cast<ast::ISymbolScope>(it->get());
        if (c && c->getUpper() == s
                && (m_ctxt->extVisibility().isPackage(c) || NodeKind::cast<ast::ISymbolTypeScope>(c))) {
            walk(c, depth+1);
        }
    }
}

void TaskCheckImports::checkScope(ast::ISymbolScope *s) {
    if (!s->getImports()) {
        return;
    }
    const std::vector<ast::IPackageImportStmt *> &imps = s->getImports()->getImports();
    for (uint32_t k=0; k<imps.size(); k++) {
        ast::IPackageImportStmt *imp = imps.at(k);
        if (!m_seen.insert(imp).second || !isUserUnit(imp->getLocation())) {
            continue;
        }
        checkFirst(imp);

        std::string name = importedName(imp);
        if (name.empty() || !imp->getPath()->getTarget()) {
            continue;
        }
        ast::IScopeChild *target = m_ctxt->resolveSymbolPathRef(imp->getPath()->getTarget());
        const ast::Location &at = imp->getPath()->getElems().back()->getId()->getLocation();

        // CH17-30: the importing namespace already declares the name -- in
        // any of its statements, since the namespace is their union.
        std::unordered_map<std::string,int32_t>::const_iterator it =
            s->getSymtab().find(name);
        if (it != s->getSymtab().end() && it->second >= 0
                && it->second < (int32_t)s->getChildren().size()) {
            ast::IScopeChild *decl = s->getChildren().at(it->second).get();
            if (decl != target) {
                m_ctxt->addMarker(
                    MarkerSeverityE::Warn,
                    at,
                    "'import " + NameLookup::importText(imp) + ";' names '"
                        + name + "', which " + scopeDesc(s) + " already "
                        "declares; an explicit import shall not name a "
                        "declaration of the importing namespace (18.1.3)",
                    {{NameLookup::declLocation(decl), "'" + name + "' declared here"}});
                continue;
            }
        }

        // CH17-31: two explicit imports of one name, from different
        // packages, in one scope. The list gathers every statement's
        // imports; the parent tells them apart.
        for (uint32_t j=0; j<k; j++) {
            ast::IPackageImportStmt *prev = imps.at(j);
            if (prev->getParent() != imp->getParent()
                    || importedName(prev) != name
                    || !prev->getPath()->getTarget()
                    || m_ctxt->resolveSymbolPathRef(prev->getPath()->getTarget()) == target) {
                continue;
            }
            m_ctxt->addMarker(
                MarkerSeverityE::Warn,
                at,
                "'" + name + "' is already imported explicitly in this scope, "
                    "by 'import " + NameLookup::importText(prev) + ";'; the same "
                    "name shall not be imported explicitly from two packages "
                    "(18.1.3)",
                {{prev->getLocation(), "first imported here"}});
            break;
        }
    }
}

void TaskCheckImports::checkFirst(ast::IPackageImportStmt *imp) {
    ast::IScope *stmt = imp->getParent();
    if (!stmt) {
        return;
    }
    // A taken `compile if` branch is spliced into the scope, so what it
    // declares sits among the children, and a `compile if` may precede an
    // import. A condition keeps no position to tell the two apart by, so a
    // scope with a `compile if` is not checked.
    if (stmt->getCompile_conds().size()) {
        return;
    }
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=stmt->getChildren().begin(); it!=stmt->getChildren().end(); it++) {
        ast::IScopeChild *c = it->get();
        if (c == imp) {
            return;
        }
        if (NodeKind::cast<ast::IPackageImportStmt>(c) || NodeKind::cast<ast::IComment>(c)) {
            continue;
        }
        m_ctxt->addMarker(
            MarkerSeverityE::Warn,
            imp->getLocation(),
            "'import " + NameLookup::importText(imp) + ";' follows a "
                "declaration; imports shall come first in a package, a "
                "component, an extension or a file (18.1.3)",
            {{NameLookup::declLocation(c), "first declaration here"}});
        return;
    }
}

std::string TaskCheckImports::importedName(ast::IPackageImportStmt *imp) {
    if (imp->getWildcard() || imp->getAlias() || !imp->getPath()
            || imp->getPath()->getElems().empty()) {
        return "";
    }
    return imp->getPath()->getElems().back()->getId()->getId();
}

std::string TaskCheckImports::scopeDesc(ast::ISymbolScope *s) const {
    if (s == m_root) {
        return "the global scope";
    }
    if (ast::ISymbolTypeScope *t = NodeKind::cast<ast::ISymbolTypeScope>(s)) {
        return (NodeKind::cast<ast::IComponent>(t->getTarget()) ? "component '" : "type '")
            + s->getName() + "'";
    }
    return "package '" + s->getName() + "'";
}

bool TaskCheckImports::isUserUnit(const ast::Location &loc) const {
    if (loc.fileid < 0) {
        return false;
    }
    std::unordered_map<int32_t,int32_t>::const_iterator it = m_root->getId2idx().find(loc.fileid);
    return it != m_root->getId2idx().end() && it->second >= (int32_t)m_n_builtin;
}

dmgr::IDebug *TaskCheckImports::m_dbg = 0;

}
