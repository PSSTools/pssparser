/**
 * TaskApplyOverlay.h
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
#include "TaskResolveRefs.h"

namespace pssp {




class TaskApplyOverlay : ast::VisitorBase {
public:
    TaskApplyOverlay(
        dmgr::IDebugMgr     *dmgr,
        ast::IFactory       *factory);

    virtual ~TaskApplyOverlay();

    virtual void apply(
        ast::IRootSymbolScope                   *root,
        ast::IGlobalScope                       *overlay
    );

    virtual void visitNamedScopeChild(ast::INamedScopeChild *i) override;

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

private:
    static dmgr::IDebug                         *m_dbg;
    ast::IFactory                               *m_factory;
    std::vector<ast::ISymbolScope *>            m_scope_s;

};

}
