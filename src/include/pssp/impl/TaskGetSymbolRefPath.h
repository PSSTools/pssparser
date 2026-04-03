/**
 * TaskGetSymbolRefPath.h
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
#include "pssp/ast/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskGetSymbolRefPath : public ast::VisitorBase {
public:

    TaskGetSymbolRefPath(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root,
        ast::IFactory           *factory) : m_dbg(0), m_root(root), m_factory(factory) {
        DEBUG_INIT("pssp::TaskGetSymbolRefPath", dmgr);
    }

    virtual ~TaskGetSymbolRefPath() { }

    ast::ISymbolRefPath *mk(ast::ISymbolScope *target) {
        DEBUG_ENTER("mk %s", target->getName().c_str());
        m_ret = m_factory->mkSymbolRefPath();

        std::vector<ast::ISymbolScope *> scopes;
        ast::ISymbolScope *c = target;
        while (c && c != m_root) {
            scopes.push_back(c);
            c = c->getUpper();
        }

        for (std::vector<ast::ISymbolScope *>::const_reverse_iterator
            it=scopes.rbegin();
            it!=scopes.rend(); it++) {
            (*it)->accept(m_this);
        }

        DEBUG_LEAVE("mk %s", target->getName().c_str());
        return m_ret;
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
        DEBUG("Push ID: %d", i->getId());
        m_ret->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
            i->getId()
        });
        DEBUG_LEAVE("visitSymbolScope %s", i->getName().c_str());
    }
    
    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
        m_ret->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
            i->getId()
        });
        if (ts->getParams() && ts->getParams()->getSpecialized()) {
            DEBUG("Specialized parameterization");
            m_ret->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_TypeSpec,
                ts->getIndex()
            });
        }
        DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
    }


private:
    dmgr::IDebug                *m_dbg;
    ast::ISymbolScope           *m_root;
    ast::IFactory               *m_factory;
    ast::ISymbolRefPath         *m_ret;

};

} /* namespace pssp */


