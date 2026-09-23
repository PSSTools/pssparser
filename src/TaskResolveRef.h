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
    /**
     * @param report_unresolved when false, a type identifier that cannot be
     *        resolved is reported only through the null return value, with no
     *        marker. Required by §7.13, which obliges tools to *disregard*
     *        unrecognized annotations rather than reject them.
     */
    TaskResolveRef(
        ResolveContext *ctxt,
        bool           search_imp=true,
        bool           report_unresolved=true);

    virtual ~TaskResolveRef();

    ast::ISymbolRefPath *resolve(ast::ITypeIdentifier *type_id);

    ast::ISymbolRefPath *resolve(ast::IExpr *ref);

    /// `::x`: `x` in the global package only -- no imports, no enclosing
    /// scopes (18.1.3). Null when there is none; nothing is reported.
    ast::ISymbolRefPath *resolveGlobal(const ast::IExprId *id) { return findGlobalRoot(id); }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

    virtual void visitExprId(ast::IExprId *i) override;

    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;


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

    /// `::x`: the first element, looked up in the global package only.
    ast::ISymbolRefPath *findGlobalRoot(const ast::IExprId *sym);

    /// Resolve a qualified expression-form template argument. See the
    /// definition for why this is not TaskResolveRefs' version of the walk.
    ast::ISymbolRefPath *resolveStaticArgPath(ast::IExprRefPathStatic *i);

private:
    static dmgr::IDebug                 *m_dbg;
    bool                                m_search_imp;
    bool                                m_report_unresolved;
    ast::ISymbolRefPath                 *m_ref;

};

}
