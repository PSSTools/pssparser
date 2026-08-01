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




/**
 * Builds the bound parameter list for one use of a parameterized type.
 *
 * Two separate roles run through the same visitor, and keeping them apart is
 * the whole difficulty here:
 *
 * - the **declaration** side (``m_ptype_*``), captured by visiting the
 *   generic's own parameter declaration, says what kind of thing this position
 *   wants and supplies its name;
 * - the **argument** side (``m_pval_*``), captured by visiting the supplied
 *   value.
 *
 * The argument side also follows a resolved type reference one hop, to notice
 * that an id which looks like a type is really a value (an enum item, or a
 * value parameter). That hop is a *probe*: it must not write the declaration
 * captures, or the parameter ends up named after the argument instead of after
 * the declaration -- see ``probe()``.
 *
 * When the argument names a template parameter of an enclosing specialized
 * generic, the parameter's *binding* is what must be passed down, not the
 * parameter reference itself. ``m_pval_param_ref`` carries that, and the two
 * ``subst*`` helpers apply it.
 */
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

    /// Follow a resolved argument reference one hop without disturbing the
    /// declaration-side captures.
    void probe(ast::IScopeChild *target);

    /// If the argument names a bound template parameter, yield its binding.
    /// Returns null when there is nothing to substitute.
    ast::IDataType *substTypeArg();
    ast::IExpr *substValueArg();

    /// A parameter default may name an earlier parameter of the same list
    /// (``struct S<type T, type U = T>``). By the time the default is applied
    /// the earlier parameter is already bound in ``m_ret``, so resolve the
    /// name against what has been built so far.
    ast::ITemplateParamDecl *findBuiltParam(const std::string &name);
    ast::IDataType *substTypeDflt(ast::IDataType *dflt);
    ast::IExpr *substValueDflt(ast::IExpr *dflt);

    /// The single-element, unparameterized name a type reference spells, or
    /// the empty string if it spells anything more complicated.
    static std::string simpleTypeName(ast::IDataType *dt);

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
    // The template parameter declaration the supplied argument refers to, if
    // it refers to one. Set by probe(); read by the subst* helpers.
    ast::ITemplateParamDecl             *m_pval_param_ref;
    // Track visited types to prevent infinite recursion
    std::set<ast::IScopeChild *>        m_visited;


};

}
