/**
 * TaskGetItemIndex.h
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
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskGetItemIndex :
    public virtual ast::VisitorBase {
public:

    virtual ~TaskGetItemIndex() { }

    int32_t get(ast::IScopeChild *c) {
        m_index = -1;
        c->accept(m_this);
        // if (m_index == -1) {
        //     fprintf(stdout, "negative\n");
        // }
        return m_index;
    }


    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override {
        m_index = i->getIndex();
    }

    virtual void visitConstraintSymbolScope(ast::IConstraintSymbolScope *i) override {
        m_index = i->getConstraint()->getIndex();
    }

    virtual void visitExecScope(ast::IExecScope *i) override {
        if (i->getId() != -1) {
            m_index = i->getId();
        } else {
            m_index = i->getIndex();
        }
    }

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override {
        if (i->getId() != -1) {
            m_index = i->getId();
        } else {
            m_index = i->getIndex();
        }
    }

    virtual void visitScopeChild(ast::IScopeChild *i) override {
        m_index = i->getIndex();
    }

    virtual void visitScope(ast::IScope *i) override {
        m_index = i->getIndex();
    }

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolChild(ast::ISymbolChild *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolChildrenScope(ast::ISymbolChildrenScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override {
        if (i->getIndex() != -1) {
            m_index = i->getIndex();
        } else {
            m_index = i->getId();
        }
    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        m_index = i->getId();
    }

protected:
    int32_t     m_index;

};

} /* namespace pssp */


