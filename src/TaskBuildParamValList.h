/**
 * TaskBuildParamValList.h
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
#include <set>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/IFactory.h"
#include "ResolveContext.h"

namespace pssp {




class TaskBuildParamValList : public ast::VisitorBase {
public:
    TaskBuildParamValList(ResolveContext *ctxt);

    virtual ~TaskBuildParamValList();

    ast::ITemplateParamDeclList *build(
        ast::ISymbolScope               *plist,
        ast::ITemplateParamValueList    *pvals);

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) override;

    virtual void visitDataTypeRef(ast::IDataTypeRef *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

    virtual void visitEnumItem(ast::IEnumItem *i) override;

    virtual void visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) override;
    
    virtual void visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) override;

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override;
    
    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override;
    
    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override;


private:
    static dmgr::IDebug                 *m_dbg; 
    ResolveContext                      *m_ctxt;
    ast::ITemplateParamDeclList         *m_ret;
    // Handle to a static-reference parameter value
    ast::ITemplateParamTypeValue        *m_pval_type;
    // Handle to the expr in case the ref is a value ref
    ast::IExpr                          *m_pval_type_valref_expr;
    bool                                m_pval_type_isval;
    ast::ITemplateParamExprValue        *m_pval_expr;
    ast::ITemplateGenericTypeParamDecl  *m_ptype_generic_type;
    ast::ITemplateCategoryTypeParamDecl *m_ptype_category_type;
    ast::ITemplateValueParamDecl        *m_ptype_value;
    // Track visited types to prevent infinite recursion
    std::set<ast::IScopeChild *>        m_visited;


};

}
