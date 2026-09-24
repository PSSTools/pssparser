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

namespace pssp {




TaskResolveImports::TaskResolveImports(ResolveContext *ctxt) : TaskResolveBase(ctxt) {
    DEBUG_INIT("TaskResolveImports", ctxt->getDebugMgr());
}

TaskResolveImports::~TaskResolveImports() {

}

void TaskResolveImports::resolveAll(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("resolveAll");
    m_ctxt->pushSymtab(m_ctxt->getFactory()->mkAstSymbolTableIterator(root));
    m_visited.clear();
    m_visited.insert(root);
    resolve(root);
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

dmgr::IDebug *TaskResolveImports::m_dbg = 0;

}
