/*
 * TaskFindPathElem.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskFindPathElem.h"


namespace pssp {



TaskFindPathElem::TaskFindPathElem(
    dmgr::IDebugMgr         *dmgr,
    ast::ISymbolScope       *root) : m_dmgr(dmgr), m_root(root) {
    DEBUG_INIT("pssp::TaskFindPathElem", dmgr);
}

TaskFindPathElem::~TaskFindPathElem() {

}

TaskFindPathElem::Result TaskFindPathElem::find(
        ast::ISymbolScope       *src,
        ast::IExprId            *id) {
    DEBUG_ENTER("find: src=%s id=%s", src->getName().c_str(), id->getId().c_str());
    m_ret.idx = -1;
    m_ret.super_idx = -1;
    m_ret.sym = 0;

    m_id = id;
    m_super_depth = 0;
    src->accept(m_this);

    DEBUG_LEAVE("find: sym=%p idx=%d super_idx=%d", 
        m_ret.sym, m_ret.idx, m_ret.super_idx);
    return m_ret;
}

void TaskFindPathElem::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
    std::unordered_map<std::string,int32_t>::const_iterator it;
    it = i->getSymtab().find(m_id->getId());

    if (it != i->getSymtab().end()) {
        DEBUG("Found symbol %s @ idx=%d super_idx=%d (scope=%s)", 
            m_id->getId().c_str(), it->second, m_super_depth,
            i->getName().c_str());
        m_ret.sym = i->getChildren().at(it->second).get();
        m_ret.idx = it->second;
        m_ret.super_idx = m_super_depth;
    }
    DEBUG_LEAVE("visitSymbolScope %s", i->getName().c_str());
}

void TaskFindPathElem::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
    visitSymbolScope(i);

    if (m_ret.sym) {
        // Found the symbol
        DEBUG("Found the symbol in this type scope");
    } else {
        // Try visiting the super scope to see if we have better luck
        i->getTarget()->accept(m_this);
    }

    DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
}

void TaskFindPathElem::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope %s", i->getName()->getId().c_str());
    if (i->getSuper_t()) {
        ast::IScopeChild *c = TaskResolveSymbolPathRef(m_dmgr, m_root).resolve(
            i->getSuper_t()->getTarget());

        m_super_depth++;
        DEBUG_ENTER("search super scope (%d)", m_super_depth);
        c->accept(m_this); 
        DEBUG_LEAVE("search super scope (%d)", m_super_depth);
        m_super_depth--;
    }
    DEBUG_LEAVE("visitTypeScope");
}

dmgr::IDebug *TaskFindPathElem::m_dbg = 0;

}
