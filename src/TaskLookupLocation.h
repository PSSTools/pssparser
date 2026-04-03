/**
 * TaskLookupLocation.h
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
#include "pssp/ast/IScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ILookupLocationResult.h"

namespace pssp {




class TaskLookupLocation : public virtual ast::VisitorBase {
public:
    TaskLookupLocation(dmgr::IDebugMgr *dmgr);

    virtual ~TaskLookupLocation();

    ILookupLocationResult *lookup(
        ast::IRootSymbolScope   *root,
        ast::IScope             *scope,
        int32_t                 lineno,
        int32_t                 linepos);

    virtual void visitField(ast::IField *i) override;

    virtual void visitNamedScope(ast::INamedScope *i) override;

    virtual void visitScope(ast::IScope *i) override;

    virtual void visitScopeChild(ast::IScopeChild *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

private:
    bool isMatch(const ast::Location &loc);

    bool isMatch(ast::ITypeIdentifier *ti);

private:
    static dmgr::IDebug                 *m_dbg;
    dmgr::IDebugMgr                     *m_dmgr;
    ast::IRootSymbolScope               *m_root;
    int32_t                             m_lineno;
    int32_t                             m_linepos;
    ILookupLocationResult               *m_result;
    std::vector<ast::IScopeChild *>     m_path;

};

}
