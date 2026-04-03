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
    DEBUG_ENTER("visitSymbolScope");

    DEBUG_LEAVE("visitSymbolScope");
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
