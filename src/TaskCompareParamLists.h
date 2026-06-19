/**
 * TaskCompareParamLists.h
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
#include "pssp/IFactory.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskCompareTypeRefs.h"

namespace pssp {


class TaskCompareParamLists : public ast::VisitorBase {
public:
    TaskCompareParamLists(
        IFactory                *factory,
        ast::ISymbolScope       *root);

    virtual ~TaskCompareParamLists();

    bool equal(
        const ast::ITemplateParamDeclList     *plist1,
        const ast::ITemplateParamDeclList     *plist2);

    virtual void visitExpr(ast::IExpr *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override;

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override;

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override;

    virtual void visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) override;

    virtual void visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) override;

private:
    // Compare the default expressions of two value parameters. Handles both
    // type-reference value params (e.g. the element type of array<T,N>, which
    // is carried as a value parameter whose default is a type-identifier) and
    // constant value params (e.g. the size of array<T,N>).
    bool valueParamDfltEqual(ast::IExpr *e0, ast::IExpr *e1);

private:
    static dmgr::IDebug                 *m_dbg;
    IFactory                            *m_factory;
    ast::ISymbolScope                   *m_root;
    uint32_t                            m_idx;
    uint32_t                            m_phase;
    ast::ITemplateGenericTypeParamDecl  *m_type_value;
    ast::ITemplateValueParamDecl        *m_expr_value;
    const ast::ITemplateParamDeclList   *m_plist1;
    const ast::ITemplateParamDeclList   *m_plist2;
    TaskCompareTypeRefs                 m_tref_comp;

};

}
