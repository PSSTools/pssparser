/**
 * TaskResolveRef.h
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
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "TaskResolveBase.h"
#include "ResolveContext.h"

namespace pssp {



class TaskResolveRef : public TaskResolveBase {
public:
    TaskResolveRef(
        ResolveContext *ctxt,
        bool           search_imp=true);

    virtual ~TaskResolveRef();

    ast::ISymbolRefPath *resolve(ast::ITypeIdentifier *type_id);

    ast::ISymbolRefPath *resolve(ast::IExpr *ref);

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

    virtual void visitExprId(ast::IExprId *i) override;

    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) override;

    virtual void visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) override;

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

private:
    ast::ISymbolRefPath *findRoot(const ast::IExprId *sym);

    ast::ISymbolRefPath *specializeParameterizedRef(
        ast::ISymbolRefPath             *target,
        ast::ITemplateParamValueList    *plist);

private:
    static dmgr::IDebug                 *m_dbg;
    bool                                m_search_imp;
    ast::ISymbolRefPath                 *m_ref;

};

}
