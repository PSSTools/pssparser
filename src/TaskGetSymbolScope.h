/**
 * TaskGetSymbolScope.h
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




class TaskGetSymbolScope :
    public virtual ast::VisitorBase {
public:

    virtual ~TaskGetSymbolScope() { }

    ast::ISymbolScope *get(ast::IScopeChild *i) {
        m_ret = 0;
        i->accept(m_this);
        return m_ret;
    }

    virtual void visitExecScope(ast::IExecScope *i) override {
        m_ret = i;
    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *s) override {
        m_ret = s;
    }

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *s) override {
        m_ret = s;
    }

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *s) override {
        m_ret = s;
    }

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *s) override {
        m_ret = s;
    }

    // 4.7.1 -- template scopes, for the same reason the two procedural loops
    // above need explicit overrides: the *generated* visitors descend.
    //
    // TemplateString and TemplateBlock both reach visitSymbolScope (which sets
    // m_ret) and then walk their elements, each of which is itself a
    // SymbolScope and overwrites m_ret. Without these, asking for the symbol
    // scope of a template returns its **last element** -- whose symtab is
    // empty -- so every template-local name failed to resolve.
    virtual void visitTemplateString(ast::ITemplateString *s) override {
        m_ret = s;
    }

    virtual void visitTemplateBlock(ast::ITemplateBlock *s) override {
        m_ret = s;
    }

    virtual void visitTemplateElem(ast::ITemplateElem *s) override {
        m_ret = s;
    }

    // Same failure, and the reason field references inside a parameterized
    // type's constraints did not resolve. The generated visitor reaches
    // visitSymbolScope (setting m_ret) and then descends into the type's
    // `<plist>` and into each of its specializations -- every one of which is
    // itself a SymbolScope and overwrites m_ret. So asking for the symbol
    // scope of `struct S<int W>` handed back the scope holding `W`, and the
    // type's own fields were never searched.
    //
    // Invisible for a non-parameterized type, which has a null plist and no
    // specializations, hence nothing to descend into.
    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *s) override {
        m_ret = s;
    }

    // Likewise: this descends into its constraint, and a nested foreach/forall
    // carries a ConstraintSymbolScope of its own that would overwrite m_ret.
    virtual void visitConstraintSymbolScope(ast::IConstraintSymbolScope *s) override {
        m_ret = s;
    }

    virtual void visitSymbolScope(ast::ISymbolScope *s) override {
        m_ret = s;
    }

protected:
    ast::ISymbolScope       *m_ret;
};

} /* namespace pssp */


