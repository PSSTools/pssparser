/**
 * TaskIsUnspecializedGenericType.h
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




class TaskIsUnspecializedGenericType : public virtual ast::VisitorBase {
public:

    virtual ~TaskIsUnspecializedGenericType() { }

    bool check(ast::ISymbolScope *s) {
        m_ret = false;
        s->accept(m_this);
        return m_ret;
    }

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override { }

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override { }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override { }

    virtual void visitSymbolImportSpec(ast::ISymbolImportSpec *i) override { }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override { }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        i->getTarget()->accept(m_this);
    }
    
    virtual void visitTypeScope(ast::ITypeScope *i) override {
        m_ret = (i->getParams() && !i->getParams()->getSpecialized());
    }

private:
    bool                m_ret;

};

} /* namespace pssp */


