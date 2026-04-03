/**
 * TaskResolveEnumRef.h
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
#include "pssp/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "TaskResolveBase.h"

namespace pssp {




class TaskResolveEnumRef : public TaskResolveBase {
public:
    TaskResolveEnumRef(
        ResolveContext          *ctxt,
        ast::ISymbolScope       *scope=0);

    virtual ~TaskResolveEnumRef();

    ast::ISymbolRefPath *resolve(const ast::IExprId *id);

    void visitSymbolEnumScope(ast::ISymbolEnumScope *i);

    virtual void visitSymbolScope(ast::ISymbolScope *i) override { }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override { }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override { }

private:
    static dmgr::IDebug                 *m_dbg;
    const ast::IExprId                  *m_id;
    const ast::ISymbolScope             *m_scope;
    ast::ISymbolRefPath                 *m_ref;

};

}
