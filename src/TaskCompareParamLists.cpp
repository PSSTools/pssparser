/*
 * TaskCompareParamLists.cpp
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
#include "TaskCompareParamLists.h"


namespace pssp {



TaskCompareParamLists::TaskCompareParamLists(
    IFactory                *factory,
    ast::ISymbolScope       *root) :
    m_tref_comp(factory, root) {
    DEBUG_INIT("TaskCompareParamLists", factory->getDebugMgr());

}

TaskCompareParamLists::~TaskCompareParamLists() {

}

bool TaskCompareParamLists::equal(
        const ast::ITemplateParamDeclList     *plist1,
        const ast::ITemplateParamDeclList     *plist2) {
    DEBUG_ENTER("equal");
    if (plist1->getParams().size() != plist2->getParams().size()) {
        DEBUG("Sizes differ: %d vs %d",
            plist1->getParams().size(),
            plist2->getParams().size());
        return false;
    }
    m_plist1 = plist1;
    m_plist2 = plist2;


    bool ret = true;
    ast::ITemplateGenericTypeParamDecl  *type_value[2];
    ast::ITemplateValueParamDecl        *expr_value[2];
    for (m_idx=0; m_idx<plist1->getParams().size(); m_idx++) {
        for (uint32_t i=0; i<2; i++) {
            m_type_value = 0;
            m_expr_value = 0;
            ((i)?plist2:plist1)->getParams().at(m_idx)->accept(m_this);
            type_value[i] = m_type_value;
            expr_value[i] = m_expr_value;
        }

        DEBUG("type_value={%p,%p} expr_value={%p,%p}",
            type_value[0], type_value[1],
            expr_value[0], expr_value[1]);
        if ((!type_value[0] != !type_value[1]) || (!expr_value[0] != !expr_value[1])) {
            ret = false;
            break;
        }

        // How do we compare?
        if (type_value[0]) {
            DEBUG("type_value[0].dflt=%p type_value[1].dflt=%p", 
                type_value[0]->getDflt(),
                type_value[1]->getDflt());
            ret &= m_tref_comp.equal(
                type_value[0]->getDflt(),
                type_value[1]->getDflt());
        } else if (expr_value[0] && expr_value[0]->getDflt()) {
            DEBUG("TODO: Compare value-type parameters");
            expr_value[0]->getDflt()->accept(m_this);
        } else {
            DEBUG("FATAL: didn't hit anything");
            ret = false;
            break;
        }
    }

    DEBUG_LEAVE("equal %d", ret);
    return ret;
}

void TaskCompareParamLists::visitExpr(ast::IExpr *i) {
    DEBUG_ENTER("visitExpr");

    DEBUG_LEAVE("visitExpr");
}

void TaskCompareParamLists::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    DEBUG_ENTER("visitSymbolTypeScope");
    DEBUG("this=%p other=%p", i, m_type_value);
    DEBUG_LEAVE("visitSymbolTypeScope");
}

void TaskCompareParamLists::visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) {
    DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
    m_type_value = i;
    DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
}

void TaskCompareParamLists::visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) {
    DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");

    DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
}

void TaskCompareParamLists::visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) {
    DEBUG_ENTER("visitTemplateValueParamDecl dflt=%p", i->getDflt());
    m_expr_value = i;
    DEBUG_LEAVE("visitTemplateValueParamDecl");
}

void TaskCompareParamLists::visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) {
    DEBUG_ENTER("visitTemplateParamTypeValue");

    DEBUG_LEAVE("visitTemplateParamTypeValue");
}

void TaskCompareParamLists::visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) {
    DEBUG_ENTER("visitTemplateParamExprValue");

    DEBUG_LEAVE("visitTemplateParamExprValue");
}

dmgr::IDebug *TaskCompareParamLists::m_dbg = 0;

}
