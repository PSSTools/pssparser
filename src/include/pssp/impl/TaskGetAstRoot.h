/**
 * TaskGetAstRoot.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskGetAstRoot : public virtual ast::VisitorBase {
public:

    TaskGetAstRoot(dmgr::IDebugMgr *dmgr) : m_dbg(0) {
        DEBUG_INIT("pssp::TaskGetAstRoot", dmgr);
    }

    virtual ~TaskGetAstRoot() { }

    ast::IGlobalScope *root(ast::IScopeChild *i) {
        m_ret = 0;
        i->accept(m_this);
        return dynamic_cast<ast::IGlobalScope *>(m_ret);
    }

    virtual void visitScopeChild(ast::IScopeChild *i) override {
        DEBUG_ENTER("visitScopeChild");
        ast::IScopeChild *c = i;

        while (c->getParent()) {
            c = c->getParent();
        }

        m_ret = dynamic_cast<ast::IScope *>(c);

        DEBUG_LEAVE("visitScopeChild");
    }

    virtual void visitTypeScope(ast::ITypeScope *i) override {
        visitScopeChild(i);
    }
    
    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
        if (i->getTarget()) {
            i->getTarget()->accept(m_this);
        } else {
            DEBUG("No target specified");
        }
        DEBUG_LEAVE("visitSymbolScope");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        visitSymbolScope(i);
    }

private:
    dmgr::IDebug            *m_dbg;
    ast::IScope             *m_ret;

};

} /* namespace pssp */


