/*
 * TaskBuildParamValList.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskCopyAst.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskBuildParamValList.h"
#include "TaskExpr2DataType.h"


namespace pssp {



TaskBuildParamValList::TaskBuildParamValList(ResolveContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("TaskBuildParamValList", ctxt->getDebugMgr());

}

TaskBuildParamValList::~TaskBuildParamValList() {

}

ast::ITemplateParamDeclList *TaskBuildParamValList::build(
        ast::ISymbolScope               *plist,
        ast::ITemplateParamValueList    *pvals) {
    DEBUG_ENTER("build plist=%d n_pvals=%d", 
        plist->getChildren().size(),
        pvals->getValues().size());
    TaskCopyAst copier(m_ctxt->getFactory());
    m_ret = 0;

    m_pval_type = 0;
    m_pval_type_valref_expr = 0;
    m_pval_expr = 0;
    m_visited.clear();  // Clear visited set for each build

    if (pvals->getValues().size() > plist->getChildren().size()) {
        char buf[256];
        snprintf(buf, sizeof(buf),
            "type accepts %d template parameter(s) but %d supplied",
            (int)plist->getChildren().size(),
            (int)pvals->getValues().size());
        m_ctxt->addErrorMarker(
            plist->getChildren().at(0)->getLocation(),
            "%s", buf);
        return 0;
    }

    m_ret = m_ctxt->getFactory()->getAstFactory()->mkTemplateParamDeclList();
    
    // First, pick up explicitly-supplied parameter values
//    m_ptype_mk_pval = false;
    uint32_t plist_idx;
    for (plist_idx=0; plist_idx<pvals->getValues().size(); plist_idx++) {
        m_pval_expr = 0;
        m_pval_type = 0;
        m_ptype_value = 0;
        m_ptype_generic_type = 0;
        m_ptype_category_type = 0;

        // Visit the declaration
        DEBUG_ENTER("-- plist");
        plist->getChildren().at(plist_idx)->accept(m_this);
        DEBUG_LEAVE("-- plist");

        DEBUG_ENTER("-- pvals");
        pvals->getValues().at(plist_idx)->accept(m_this);
        DEBUG_LEAVE("-- pvals");

        if (m_ptype_value && m_pval_type) {
            DEBUG("TODO: convert type ref to expression");
        }

        ast::IExpr *pval_expr = (m_pval_expr)?m_pval_expr->getValue():m_pval_type_valref_expr;
        DEBUG("pval_expr: %p (m_pval_expr=%p m_pval_type_valref_expr=%p)",
            pval_expr, m_pval_expr, m_pval_type_valref_expr);

        if (pval_expr) {
            if (m_ptype_value) {
                DEBUG("Value parameter");
                ast::ITemplateValueParamDecl *p = m_ctxt->getFactory()->getAstFactory()->mkTemplateValueParamDecl(
                    copier.copyT<ast::IExprId>(m_ptype_value->getName()),
                    copier.copyT<ast::IDataType>(m_ptype_value->getType()),
                    copier.copyT<ast::IExpr>(pval_expr));

                m_ret->getParams().push_back(ast::ITemplateParamDeclUP(p));
            } else if (m_ptype_generic_type) {
                DEBUG("Generic type parameter");
                ast::IDataType *dt = 0;

                dt = TaskExpr2DataType(m_ctxt).expr2dt(pval_expr);

                ast::ITemplateGenericTypeParamDecl *p = 
                    m_ctxt->getFactory()->getAstFactory()->mkTemplateGenericTypeParamDecl(
                        copier.copyT<ast::IExprId>(m_ptype_generic_type->getName()),
                        dt
                    );
                m_ret->getParams().push_back(ast::ITemplateParamDeclUP(p));
            } else if (m_ptype_category_type) {
                DEBUG("Category type parameter");
            } else {
                DEBUG_ERROR("TODO: expression supplied for value %d, and ptype not set", plist_idx);
                return 0;
            }
        } else { // Type value
            DEBUG("Type parameter");
            DEBUG("ptype_value=%p ptype_category_type=%p ptype_generic_type=%p",
                m_ptype_value, m_ptype_category_type, m_ptype_generic_type);

            // Type value. We always specialize as a generic type parameter
            ast::IExprId *name = 0;
            ast::IDataType *type = 0;
            if (m_ptype_category_type) {
                name = m_ptype_category_type->getName();
                type = m_pval_type->getValue();
            } else if (m_ptype_generic_type) {
                name = m_ptype_generic_type->getName();
                type = m_pval_type->getValue();
            } else if (m_ptype_value) {
                // Note: it is possible to receive both a generic and a value
                // parameter, but we don't expect to only receive a value
                // parameter.
                DEBUG_ERROR("Value parameter used as a type parameter");
                name = m_ptype_value->getName();
                type = m_ptype_value->getType();
            } else {
                DEBUG_ERROR("TODO: no ptype_decl captured\n");
            }

            DEBUG("Add parameter %s", (name)?name->getId().c_str():"<unknown>");
            DEBUG("  value=%p type=%p %p", 
                m_pval_type->getValue(), 
                type,
                copier.copy(m_pval_type->getValue()));

            ast::ITemplateGenericTypeParamDecl *p = m_ctxt->getFactory()->getAstFactory()->mkTemplateGenericTypeParamDecl(
                (name)?copier.copyT<ast::IExprId>(name):0,
                copier.copy(m_pval_type->getValue())
            );
            m_ret->getParams().push_back(ast::ITemplateParamDeclUP(p));

/*
            ast::ITemplateGenericTypeParamDecl *p = m_factory->getAstFactory()->mkTemplateGenericTypeParamDecl(
                copier.copyT<ast::IExprId>(name),
                copier.copyT<ast::ITypeIdentifier>(m_pval_type->getValue())
            );
 */
        }
    }

    // Now, we deal with parameters without explicitly-specified values
    for (; plist_idx<plist->getChildren().size(); plist_idx++) {
        DEBUG("Apply default to parameter (%p)", plist->getChildren().at(plist_idx).get());
        m_ptype_value = 0;
        m_ptype_generic_type = 0;
        m_ptype_category_type = 0;

        // Get the default value
        plist->getChildren().at(plist_idx)->accept(m_this);

        ast::IExprId *name = 0;
        ast::IDataType *type = 0;
        ast::IExpr *value = 0;

        if (m_ptype_value) {
            DEBUG("Note: value parameter");
            name = m_ptype_value->getName();
            type = m_ptype_value->getType();
            value = m_ptype_value->getDflt();
        } else if (m_ptype_category_type) {
            DEBUG("Note: category type parameter");
            name = m_ptype_category_type->getName();
            type = m_ptype_category_type->getDflt();
        } else if (m_ptype_generic_type) {
            DEBUG("Note: generic type parameter");
            name = m_ptype_generic_type->getName();
            type = m_ptype_generic_type->getDflt();
        } else {
            DEBUG("Error: Unknown parameter kind");
        }

        DEBUG("Add parameter %s", (name)?name->getId().c_str():"<unset>");
        ast::ITemplateParamDecl *p = 0;
        if (value) {
            p = m_ctxt->getFactory()->getAstFactory()->mkTemplateValueParamDecl(
                copier.copyT<ast::IExprId>(name),
                copier.copy(type),
                value?copier.copy(value):0
            );
        } else if (type) {
            p = m_ctxt->getFactory()->getAstFactory()->mkTemplateGenericTypeParamDecl(
                copier.copyT<ast::IExprId>(name),
                type?copier.copy(type):0
            );
        } else {
            m_ctxt->addErrorMarker(
                plist->getChildren().at(plist_idx)->getLocation(),
                "No default provided for template parameter %s",
                (name)?name->getId().c_str():"<unknown>"
            );
            delete m_ret;
            m_ret = 0;
            break;
        }
        m_ret->getParams().push_back(ast::ITemplateParamDeclUP(p));
    }

    DEBUG_LEAVE("build %p sz=%d", m_ret, (m_ret)?m_ret->getParams().size():-1);
    return m_ret;
}

void TaskBuildParamValList::visitDataTypeEnum(ast::IDataTypeEnum *i) {
    DEBUG_ENTER("visitDataTypeEnum");
    DEBUG("TODO: visitDataTypeEnum");
    DEBUG_LEAVE("visitDataTypeEnum");
}

void TaskBuildParamValList::visitDataTypeRef(ast::IDataTypeRef *i) {
    DEBUG_ENTER("visitDataTypeRef");
    // For ref types in template parameters, we don't recurse into the referenced type
    // The ref type itself is the parameter value, not what it references
    // This prevents infinite recursion when processing types like array<ref A, 10>
    DEBUG_LEAVE("visitDataTypeRef");
}

void TaskBuildParamValList::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    DEBUG_ENTER("visitDataTypeUserDefined %s", 
        i->getType_id()->getElems().back()->getId()->getId().c_str());

    // If this is an external resolved reference, 
    // follow it and check its source
    if (i->getType_id()->getTarget()) {
        ast::IScopeChild *target = TaskResolveSymbolPathRef(
            m_ctxt->getDebugMgr(),
            m_ctxt->root()).resolve(i->getType_id()->getTarget());
        
        // Check if we've already visited this target to prevent infinite recursion
        if (target && m_visited.find(target) == m_visited.end()) {
            m_visited.insert(target);
            m_pval_type_isval = false;
            target->accept(m_this);
            
            if (m_pval_type_isval || m_ptype_value) {
                // Save the reference
                m_pval_type_valref_expr = i->getType_id();
            }
        } else if (target) {
            DEBUG("Skipping already-visited target to prevent infinite recursion");
        }
    }
    DEBUG_LEAVE("visitDataTypeUserDefined");
}

void TaskBuildParamValList::visitEnumItem(ast::IEnumItem *i) {
    DEBUG_ENTER("visitEnumItem");
    m_pval_type_isval = true;
    DEBUG_LEAVE("visitEnumItem");
}

void TaskBuildParamValList::visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) {
    DEBUG_ENTER("visitTemplateParamTypeValue");
    m_pval_type_valref_expr = 0;
    if (i->getValue()) {
        DEBUG_ENTER("Visit type-value");
        i->getValue()->accept(m_this);
        DEBUG_LEAVE("Visit type-value");
    }
    m_pval_type = i;
    if (m_pval_type_valref_expr) {
        DEBUG("Actually a value");
    }
    DEBUG_LEAVE("visitTemplateParamTypeValue");
}
    
void TaskBuildParamValList::visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) { 
    DEBUG_ENTER("visitTemplateParamExprValue");
    m_pval_expr = i;
    DEBUG_LEAVE("visitTemplateParamExprValue");
}

void TaskBuildParamValList::visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) { 
    DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
    m_ptype_generic_type = i;
    DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
}
    
void TaskBuildParamValList::visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) { 
    DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
    m_ptype_category_type = i;
    DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
}
    
void TaskBuildParamValList::visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) { 
    DEBUG_ENTER("visitTemplateValueParamDecl %s", i->getName()->getId().c_str());
    m_ptype_value = i;
    DEBUG_LEAVE("visitTemplateValueParamDecl");
}

dmgr::IDebug *TaskBuildParamValList::m_dbg = 0;

}
