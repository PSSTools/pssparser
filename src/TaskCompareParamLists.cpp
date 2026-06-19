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
    m_factory(factory), m_root(root),
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
        } else if (expr_value[0] && expr_value[1]) {
            ret &= valueParamDfltEqual(
                expr_value[0]->getDflt(),
                expr_value[1]->getDflt());
            if (!ret) {
                break;
            }
        } else {
            DEBUG("FATAL: didn't hit anything");
            ret = false;
            break;
        }
    }

    DEBUG_LEAVE("equal %d", ret);
    return ret;
}

bool TaskCompareParamLists::valueParamDfltEqual(
        ast::IExpr      *e0,
        ast::IExpr      *e1) {
    DEBUG_ENTER("valueParamDfltEqual");
    if (!e0 || !e1) {
        DEBUG_LEAVE("valueParamDfltEqual (null) %d", (e0 == e1));
        return (e0 == e1);
    }

    // Type-reference value parameters. The element type of a generic such as
    // array<T,N> is carried as a value parameter whose default expression is
    // the type-identifier for T. Compare these by their resolved targets so
    // that, e.g., array<ch_c,N> and array<reg_c,N> are NOT treated as the
    // same specialization.
    ast::ITypeIdentifier *t0 = dynamic_cast<ast::ITypeIdentifier *>(e0);
    ast::ITypeIdentifier *t1 = dynamic_cast<ast::ITypeIdentifier *>(e1);
    if (t0 || t1) {
        if (!t0 || !t1) {
            DEBUG_LEAVE("valueParamDfltEqual (type/non-type mismatch)");
            return false;
        }
        if (!t0->getTarget() || !t1->getTarget()) {
            bool ret = (t0->getTarget() == t1->getTarget());
            DEBUG_LEAVE("valueParamDfltEqual (unresolved type) %d", ret);
            return ret;
        }
        TaskResolveSymbolPathRef resolver(m_factory->getDebugMgr(), m_root);
        ast::IScopeChild *c0 = resolver.resolve(t0->getTarget());
        ast::IScopeChild *c1 = resolver.resolve(t1->getTarget());
        bool ret = (c0 && c1 && c0 == c1);
        DEBUG_LEAVE("valueParamDfltEqual (type %p vs %p) %d", c0, c1, ret);
        return ret;
    }

    // Constant value parameters. Compare structurally on the leaf form rather
    // than evaluating: some defaults are non-constant, recursive expressions
    // (e.g. reg_c's SZ2 default `8*sizeof_s<R>::nbytes`) that are unsafe to
    // evaluate here. Two specializations of the same generic share identical
    // (copied) default expressions for any parameter not explicitly supplied,
    // so the explicitly-supplied leaves are what must be distinguished.

    // Integer literals (e.g. the size of array<T,N>).
    ast::IExprUnsignedNumber *n0 = dynamic_cast<ast::IExprUnsignedNumber *>(e0);
    ast::IExprUnsignedNumber *n1 = dynamic_cast<ast::IExprUnsignedNumber *>(e1);
    if (n0 || n1) {
        bool ret = (n0 && n1 && n0->getValue() == n1->getValue());
        DEBUG_LEAVE("valueParamDfltEqual (number) %d", ret);
        return ret;
    }

    // Identifier references (e.g. an enum value such as READONLY/READWRITE).
    ast::IExprId *i0 = dynamic_cast<ast::IExprId *>(e0);
    ast::IExprId *i1 = dynamic_cast<ast::IExprId *>(e1);
    if (i0 || i1) {
        bool ret = (i0 && i1 && i0->getId() == i1->getId());
        DEBUG_LEAVE("valueParamDfltEqual (id) %d", ret);
        return ret;
    }

    // Other expression forms: these are non-explicit, structurally-identical
    // defaults between two specializations of the same generic, so treat them
    // as equal (matching the historical behavior) without evaluating.
    DEBUG_LEAVE("valueParamDfltEqual (other, assume-equal)");
    return true;
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
