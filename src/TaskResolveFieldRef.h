/**
 * TaskResolveFieldRef.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IMarkerListener.h"
#include "TaskResolveBase.h"


namespace pssp {



class TaskResolveFieldRef : public TaskResolveBase {
public:
    TaskResolveFieldRef(ResolveContext *ctxt);

    virtual ~TaskResolveFieldRef();

    ast::IScopeChild *resolve(
        ast::IExprId            *id,
        ast::IScopeChild        *ctxt,
        ast::ISymbolRefPath     *path);

    virtual void visitNamedScope(ast::INamedScope *i) override;

    virtual void visitNamedScopeChild(ast::INamedScopeChild *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

//    virtual void visitSymbolExecScope(ast::ISymbolExecScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitScopeChild(ast::IScopeChild *i) override;

private:
    static dmgr::IDebug                     *m_dbg;
    ast::IExprId                            *m_id;
    ast::ISymbolRefPath                     *m_path;
    ast::IScopeChild                        *m_ret;

};

}
