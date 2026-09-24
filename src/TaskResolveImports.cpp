/*
 * TaskResolveImports.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
 * Created on:
 *     Author:
 */
#include "dmgr/impl/DebugMacros.h"
#include "TaskResolveImports.h"
#include "TaskResolveRef.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ISymbolExtendScope.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/ISymbolDeclaration.h"

namespace pssp {




TaskResolveImports::TaskResolveImports(ResolveContext *ctxt) :
        TaskResolveBase(ctxt), m_root(0) {
    DEBUG_INIT("TaskResolveImports", ctxt->getDebugMgr());
}

TaskResolveImports::~TaskResolveImports() {

}

void TaskResolveImports::resolveAll(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("resolveAll");
    m_ctxt->pushSymtab(m_ctxt->getFactory()->mkAstSymbolTableIterator(root));
    m_visited.clear();
    m_visited.insert(root);
    m_root = root;
    resolve(root);
    checkAliases(root);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=root->getChildren().begin();
        it!=root->getChildren().end(); it++) {
        if (ast::ISymbolScope *c = dynamic_cast<ast::ISymbolScope *>(it->get())) {
            walk(c);
        }
    }
    m_ctxt->popSymtab();
    DEBUG_LEAVE("resolveAll");
}

void TaskResolveImports::walk(ast::ISymbolScope *s) {
    // An import is a package, component or extension body item (Annex B), so
    // the walk goes only where one can be: a package holds the others, and a
    // type or an extension holds none of them. The visited set guards a scope
    // reachable twice (a hoisted child).
    if (!m_visited.insert(s).second) {
        return;
    }

    if (dynamic_cast<ast::ISymbolTypeScope *>(s)
            || dynamic_cast<ast::ISymbolExtendScope *>(s)) {
        // Pushed for its own imports' sake: an import path resolves from
        // where it is written. An extension has no index to address it by, so
        // its imports resolve from the scope around it.
        bool pushed = (s->getId() >= 0);
        if (pushed) {
            m_ctxt->symtab()->pushScope(s);
        }
        resolve(s);
        checkAliases(s);
        if (pushed) {
            m_ctxt->symtab()->popScope();
        }
        return;
    }

    if (dynamic_cast<ast::ISymbolFunctionScope *>(s)
            || dynamic_cast<ast::ISymbolEnumScope *>(s)
            || s->getId() < 0) {
        return;
    }

    // A package.
    m_ctxt->symtab()->pushScope(s);
    resolve(s);
    checkAliases(s);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=s->getChildren().begin();
        it!=s->getChildren().end(); it++) {
        if (ast::ISymbolScope *c = dynamic_cast<ast::ISymbolScope *>(it->get())) {
            walk(c);
        }
    }
    m_ctxt->symtab()->popScope();
}

void TaskResolveImports::resolve(ast::ISymbolScope *sym_scope) {
    DEBUG_ENTER("resolve");
    if (sym_scope->getImports()) {
        for (std::vector<ast::IPackageImportStmt *>::const_iterator
            it=sym_scope->getImports()->getImports().begin();
            it!=sym_scope->getImports()->getImports().end(); it++) {
            (*it)->accept(this);
        }
    }
    DEBUG_LEAVE("resolve");
}

void TaskResolveImports::visitPackageImportStmt(ast::IPackageImportStmt *i) {
    DEBUG_ENTER("visitPackageImportStmt %s", i->getPath()->getElems().at(0)->getId()->getId().c_str());
    if (!i->getPath()->getTarget()) {
        DEBUG_ENTER("  Resolve path");
        ast::ISymbolRefPath *path = TaskResolveRef(m_ctxt, false).resolve(i->getPath());
        i->getPath()->setTarget(path);
        DEBUG_LEAVE("  Resolve path");
    } else {
        DEBUG("Skip resolution, since the target is already set");
    }
    DEBUG_LEAVE("visitPackageImportStmt");
}

void TaskResolveImports::checkAliases(ast::ISymbolScope *s) {
    if (!s->getImports()) {
        return;
    }
    const std::vector<ast::IPackageImportStmt *> &imps = s->getImports()->getImports();
    // A package or the global scope can hold a package; a type cannot.
    bool pkg_level = !dynamic_cast<ast::ISymbolTypeScope *>(s)
        && !dynamic_cast<ast::ISymbolExtendScope *>(s);

    for (uint32_t k=0; k<imps.size(); k++) {
        ast::IPackageImportStmt *imp = imps.at(k);
        if (!imp->getAlias()) {
            continue;
        }
        const std::string &name = imp->getAlias()->getId();

        // Two aliases of one name in one statement. The namespace's list
        // gathers every statement's imports; the parent tells them apart.
        bool dup = false;
        for (uint32_t j=0; j<k && !dup; j++) {
            ast::IPackageImportStmt *prev = imps.at(j);
            if (prev->getAlias() && prev->getAlias()->getId() == name
                    && prev->getParent() == imp->getParent()) {
                m_ctxt->addMarker(
                    MarkerSeverityE::Error,
                    imp->getAlias()->getLocation(),
                    "package alias '" + name + "' is already declared in this "
                    "scope; two aliases in one scope shall not share a name "
                    "(18.1.4)",
                    {{prev->getAlias()->getLocation(), "first declared here"}});
                dup = true;
            }
        }
        if (dup || !pkg_level) {
            continue;
        }

        // An alias shall not take the name of a package in its namespace,
        // declared in this source unit or an earlier one. One declared in a
        // later unit is legal (18.1.4), and then hides the alias (18.3 c.1).
        std::unordered_map<std::string, int32_t>::const_iterator it =
            s->getSymtab().find(name);
        if (it == s->getSymtab().end() || it->second < 0
                || it->second >= (int32_t)s->getChildren().size()) {
            continue;
        }
        ast::ISymbolScope *pkg = dynamic_cast<ast::ISymbolScope *>(
            s->getChildren().at(it->second).get());
        if (!pkg
                || dynamic_cast<ast::ISymbolTypeScope *>(pkg)
                || dynamic_cast<ast::ISymbolEnumScope *>(pkg)
                || dynamic_cast<ast::ISymbolFunctionScope *>(pkg)
                || dynamic_cast<ast::ISymbolExtendScope *>(pkg)
                || dynamic_cast<ast::ISymbolDeclaration *>(pkg)) {
            continue;
        }
        // A package's location is its first declaration's, in the earliest
        // unit that declares it.
        int32_t pkg_unit = unitOf(pkg->getLocation().fileid);
        int32_t imp_unit = unitOf(imp->getLocation().fileid);
        if (pkg_unit >= 0 && imp_unit >= 0 && pkg_unit > imp_unit) {
            continue;
        }
        std::string where = (s == m_root)
            ? std::string("the global scope")
            : "package '" + s->getName() + "'";
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            imp->getAlias()->getLocation(),
            "package alias '" + name + "' has the same name as a package "
            "declared in " + where + "; rename the alias (18.1.4)",
            {{pkg->getLocation(), "package '" + name + "' declared here"}});
    }
}

int32_t TaskResolveImports::unitOf(int32_t fileid) const {
    if (!m_root || fileid < 0) {
        return -1;
    }
    std::unordered_map<int32_t,int32_t>::const_iterator it =
        m_root->getId2idx().find(fileid);
    return (it == m_root->getId2idx().end())?-1:it->second;
}

dmgr::IDebug *TaskResolveImports::m_dbg = 0;

}
