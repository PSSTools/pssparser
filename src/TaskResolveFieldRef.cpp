/*
 * TaskResolveFieldRef.cpp
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
#include "TaskResolveFieldRef.h"
#include "pssp/impl/TaskGetName.h"


namespace pssp {



TaskResolveFieldRef::TaskResolveFieldRef(ResolveContext *ctxt) : TaskResolveBase(ctxt) {
    DEBUG_INIT("TaskResolveFieldRef", ctxt->getDebugMgr());
    m_id = 0;
    m_path = 0;
    m_ret = 0;
}

TaskResolveFieldRef::~TaskResolveFieldRef() {

}

ast::IScopeChild *TaskResolveFieldRef::resolve(
        ast::IExprId            *id,
        ast::IScopeChild        *ctxt,
        ast::ISymbolRefPath     *path) {
    DEBUG_ENTER("resolve");
    m_id = id;
    m_path = path;
    m_ret = 0;
    ctxt->accept(m_this);
    DEBUG_LEAVE("resolve %p", m_ret);
    return m_ret;
}

void TaskResolveFieldRef::visitNamedScope(ast::INamedScope *i) { 
    DEBUG_ENTER("visitNamedScope");

    DEBUG_LEAVE("visitNamedScope");
}

void TaskResolveFieldRef::visitNamedScopeChild(ast::INamedScopeChild *i) { 

}

void TaskResolveFieldRef::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());

    // A package is an ISymbolScope, not an ISymbolTypeScope. Until this was
    // implemented, only the type-scope case below did any lookup, so the
    // second element of a package-qualified path -- the `s` of `p::s` --
    // could never be found. `extend struct p::s` then failed its target
    // resolution silently and the extension was dropped whole.
    lookup(i);

    DEBUG_LEAVE("visitSymbolScope %p", m_ret);
}

void TaskResolveFieldRef::lookup(ast::ISymbolScope *i) {
    std::unordered_map<std::string,int32_t>::const_iterator it;

    if ((it=i->getSymtab().find(m_id->getId())) == i->getSymtab().end()) {
        return;
    }

    // A synthetic scope owns its children list, so the symtab index addresses
    // it directly. A non-synthetic scope records the child's index in the
    // *physical* AST parent instead, which need not line up. Confirm the
    // candidate by name before trusting it, and fall back to a scan.
    int32_t idx = it->second;
    if (idx >= 0 && idx < (int32_t)i->getChildren().size()) {
        ast::IScopeChild *c = i->getChildren().at(idx).get();
        if (TaskGetName().get(c) == m_id->getId()) {
            m_ret = c;
            m_path->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
                idx
            });
            return;
        }
    }

    for (int32_t ci=0; ci<(int32_t)i->getChildren().size(); ci++) {
        ast::IScopeChild *c = i->getChildren().at(ci).get();
        if (TaskGetName().get(c) == m_id->getId()) {
            DEBUG("symtab index %d did not match; found %s at %d",
                idx, m_id->getId().c_str(), ci);
            m_ret = c;
            m_path->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
                ci
            });
            return;
        }
    }
}

//void TaskResolveFieldRef::visitSymbolExecScope(ast::ISymbolExecScope *i) { 
//
//}

void TaskResolveFieldRef::visitSymbolTypeScope(ast::ISymbolTypeScope *i) { 
    DEBUG_ENTER("visitSymbolTypeScope");
    std::unordered_map<std::string,int32_t>::const_iterator it;

    if ((it=i->getSymtab().find(m_id->getId())) != i->getSymtab().end()) {
        m_ret = i->getChildren().at(it->second).get();
        m_path->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
            it->second
        });
    }

    DEBUG_LEAVE("visitSymbolTypeScope");
}

void TaskResolveFieldRef::visitScopeChild(ast::IScopeChild *i) {

}

dmgr::IDebug *TaskResolveFieldRef::m_dbg = 0;

}
