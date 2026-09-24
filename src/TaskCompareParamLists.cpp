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
#include "pssp/ast/IExprBin.h"
#include "pssp/ast/IExprBool.h"
#include "pssp/ast/IExprCond.h"
#include "pssp/ast/IExprHierarchicalId.h"
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprRefPathStatic.h"
#include "pssp/ast/IExprSignedNumber.h"
#include "pssp/ast/IExprString.h"
#include "pssp/ast/IExprUnary.h"
#include "pssp/ast/IExprUnsignedNumber.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/ITypeIdentifier.h"
#include "pssp/ast/ITypeIdentifierElem.h"
#include "TaskCompareParamLists.h"


namespace pssp {



TaskCompareParamLists::TaskCompareParamLists(
    IFactory                *factory,
    ast::ISymbolScope       *root) :
    m_factory(factory), m_root(root),
    m_tref_comp(factory, root),
    m_eval(factory, root),
    m_comp_val(factory->getDebugMgr()) {
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

    // Constant value parameters. Two arguments that fold are equal when their
    // values are (10.4: `S<2+2>`, `S<W>` with W=4, and `S<4>` are one
    // specialization). One that does not fold -- a reference to an enclosing
    // generic's parameter, an enum item, a default copied without its
    // targets -- is compared by its form instead. Nothing is assumed equal:
    // two defaults that were not supplied are copies of one expression, so
    // they still match structurally.
    //
    // Only one side folding is not yet a difference: a default is copied
    // without its targets (it may name an earlier parameter, which must bind
    // to the specialization's), so the copy in a requested list does not fold
    // while the same default in an existing, resolved specialization does.
    // The structural compare recognizes that pair by its source location.
    if (e0 == e1) {
        DEBUG_LEAVE("valueParamDfltEqual (same) 1");
        return true;
    }
    // Two literals, the common case, need no evaluator.
    ast::IExprUnsignedNumber *n0 = dynamic_cast<ast::IExprUnsignedNumber *>(e0);
    ast::IExprUnsignedNumber *n1 = dynamic_cast<ast::IExprUnsignedNumber *>(e1);
    if (n0 && n1) {
        DEBUG_LEAVE("valueParamDfltEqual (literals)");
        return (n0->getValue() == n1->getValue());
    }
    // Two bound references: the same declaration has the same value, and
    // two declarations that hold no value to fold -- enum items, types -- are
    // different ones. Resolving a path is costly; this spares the evaluator
    // from resolving both again.
    ast::ISymbolRefPath *p0 = refTarget(e0);
    ast::ISymbolRefPath *p1 = refTarget(e1);
    if (p0 && p1) {
        TaskResolveSymbolPathRef resolver(m_factory->getDebugMgr(), m_root);
        ast::IScopeChild *c0 = resolver.resolve(p0);
        ast::IScopeChild *c1 = resolver.resolve(p1);
        if (c0 && c0 == c1) {
            DEBUG_LEAVE("valueParamDfltEqual (same declaration) 1");
            return true;
        }
        if (c0 && c1 && !holdsValue(c0) && !holdsValue(c1)) {
            DEBUG_LEAVE("valueParamDfltEqual (different declarations) 0");
            return false;
        }
    }
    IValUP v0(m_eval.eval(e0));
    IValUP v1(m_eval.eval(e1));
    if (v0 && v1) {
        bool ret = m_comp_val.equal(v0.get(), v1.get());
        DEBUG_LEAVE("valueParamDfltEqual (value) %d", ret);
        return ret;
    }

    bool ret = exprEqual(e0, e1);
    DEBUG_LEAVE("valueParamDfltEqual (structural) %d", ret);
    return ret;
}

bool TaskCompareParamLists::exprEqual(ast::IExpr *e0, ast::IExpr *e1) {
    if (!e0 || !e1) {
        return (e0 == e1);
    }
    if (e0 == e1) {
        return true;
    }

    if (ast::IExprUnsignedNumber *n0 = dynamic_cast<ast::IExprUnsignedNumber *>(e0)) {
        ast::IExprUnsignedNumber *n1 = dynamic_cast<ast::IExprUnsignedNumber *>(e1);
        return (n1 && n0->getValue() == n1->getValue());
    }
    if (ast::IExprSignedNumber *n0 = dynamic_cast<ast::IExprSignedNumber *>(e0)) {
        ast::IExprSignedNumber *n1 = dynamic_cast<ast::IExprSignedNumber *>(e1);
        return (n1 && n0->getValue() == n1->getValue());
    }
    if (ast::IExprBool *b0 = dynamic_cast<ast::IExprBool *>(e0)) {
        ast::IExprBool *b1 = dynamic_cast<ast::IExprBool *>(e1);
        return (b1 && b0->getValue() == b1->getValue());
    }
    if (ast::IExprString *s0 = dynamic_cast<ast::IExprString *>(e0)) {
        ast::IExprString *s1 = dynamic_cast<ast::IExprString *>(e1);
        return (s1 && s0->getValue() == s1->getValue());
    }
    if (ast::IExprBin *b0 = dynamic_cast<ast::IExprBin *>(e0)) {
        ast::IExprBin *b1 = dynamic_cast<ast::IExprBin *>(e1);
        return (b1 && b0->getOp() == b1->getOp()
            && exprEqual(b0->getLhs(), b1->getLhs())
            && exprEqual(b0->getRhs(), b1->getRhs()));
    }
    if (ast::IExprUnary *u0 = dynamic_cast<ast::IExprUnary *>(e0)) {
        ast::IExprUnary *u1 = dynamic_cast<ast::IExprUnary *>(e1);
        return (u1 && u0->getOp() == u1->getOp()
            && exprEqual(u0->getRhs(), u1->getRhs()));
    }
    if (ast::IExprCond *c0 = dynamic_cast<ast::IExprCond *>(e0)) {
        ast::IExprCond *c1 = dynamic_cast<ast::IExprCond *>(e1);
        return (c1 && exprEqual(c0->getCond_e(), c1->getCond_e())
            && exprEqual(c0->getTrue_e(), c1->getTrue_e())
            && exprEqual(c0->getFalse_e(), c1->getFalse_e()));
    }
    if (ast::IExprId *i0 = dynamic_cast<ast::IExprId *>(e0)) {
        ast::IExprId *i1 = dynamic_cast<ast::IExprId *>(e1);
        return (i1 && i0->getId() == i1->getId());
    }

    // A reference -- to a constant, an enum item, a parameter, or a type
    // (the element type of array<T,N> is carried as a value parameter whose
    // default is a type identifier, so array<ch_c,N> and array<reg_c,N> must
    // differ): the same declaration when both are bound. Otherwise only one
    // default copied twice is equal to itself -- the same names written at
    // the same place.
    ast::ISymbolRefPath *p0 = refTarget(e0);
    ast::ISymbolRefPath *p1 = refTarget(e1);
    std::vector<ast::IExprId *> ids0, ids1;
    bool is_ref0 = refIds(e0, ids0);
    bool is_ref1 = refIds(e1, ids1);
    if (is_ref0 || is_ref1 || p0 || p1) {
        if (p0 && p1) {
            TaskResolveSymbolPathRef resolver(m_factory->getDebugMgr(), m_root);
            ast::IScopeChild *c0 = resolver.resolve(p0);
            ast::IScopeChild *c1 = resolver.resolve(p1);
            return (c0 && c0 == c1);
        }
        if (!is_ref0 || !is_ref1 || ids0.size() != ids1.size() || !ids0.size()) {
            return false;
        }
        for (uint32_t k=0; k<ids0.size(); k++) {
            const ast::Location &l0 = ids0.at(k)->getLocation();
            const ast::Location &l1 = ids1.at(k)->getLocation();
            if (ids0.at(k)->getId() != ids1.at(k)->getId()
                    || l0.lineno < 0
                    || l0.fileid != l1.fileid
                    || l0.lineno != l1.lineno
                    || l0.linepos != l1.linepos) {
                return false;
            }
        }
        return true;
    }

    // Any other form -- an aggregate, a call, a cast -- is not known to be
    // equal, so the two are different specializations.
    DEBUG("exprEqual: unhandled expression form");
    return false;
}

bool TaskCompareParamLists::holdsValue(ast::IScopeChild *c) {
    return dynamic_cast<ast::IField *>(c)
        || dynamic_cast<ast::ITemplateValueParamDecl *>(c);
}

ast::ISymbolRefPath *TaskCompareParamLists::refTarget(ast::IExpr *e) {
    if (ast::IExprRefPath *r = dynamic_cast<ast::IExprRefPath *>(e)) {
        return r->getTarget();
    }
    if (ast::ITypeIdentifier *t = dynamic_cast<ast::ITypeIdentifier *>(e)) {
        return t->getTarget();
    }
    return 0;
}

bool TaskCompareParamLists::refIds(ast::IExpr *e, std::vector<ast::IExprId *> &ids) {
    if (ast::IExprRefPathContext *c = dynamic_cast<ast::IExprRefPathContext *>(e)) {
        if (!c->getHier_id()) {
            return false;
        }
        for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
                it=c->getHier_id()->getElems().begin();
                it!=c->getHier_id()->getElems().end(); it++) {
            if (!(*it)->getId()) {
                return false;
            }
            ids.push_back((*it)->getId());
        }
        return true;
    }
    const std::vector<ast::ITypeIdentifierElemUP> *elems = 0;
    if (ast::IExprRefPathStatic *st = dynamic_cast<ast::IExprRefPathStatic *>(e)) {
        elems = &st->getBase();
    } else if (ast::ITypeIdentifier *t = dynamic_cast<ast::ITypeIdentifier *>(e)) {
        elems = &t->getElems();
    } else {
        return false;
    }
    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=elems->begin(); it!=elems->end(); it++) {
        if (!(*it)->getId()) {
            return false;
        }
        ids.push_back((*it)->getId());
    }
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
