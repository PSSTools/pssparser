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

namespace pssp {




TaskResolveImports::TaskResolveImports(ResolveContext *ctxt) : TaskResolveBase(ctxt) {
    DEBUG_INIT("TaskResolveImports", ctxt->getDebugMgr());
}

TaskResolveImports::~TaskResolveImports() {

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
