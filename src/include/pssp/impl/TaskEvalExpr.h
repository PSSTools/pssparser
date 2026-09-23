/**
 * TaskEvalExpr.h
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
#include <algorithm>
#include <memory>
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IFactory.h"
#include "pssp/IVal.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {




class TaskEvalExpr : public virtual ast::VisitorBase {
public:
    TaskEvalExpr(
        IFactory                *factory,
        ast::ISymbolScope       *root) : 
        m_dbg(0), m_factory(factory), m_root(root) {
        DEBUG_INIT("pssp::TaskEvalExpr", factory->getDebugMgr());
    }

    virtual ~TaskEvalExpr() {}

    IVal *eval(ast::IExpr *expr) {
        DEBUG_ENTER("eval");
        m_val.reset();
        expr->accept(m_this);
        DEBUG_LEAVE("eval");
        return m_val.release();
    }

    template <class T> T *evalT(ast::IExpr *expr) {
        return dynamic_cast<T *>(eval(expr));
    }

    // virtual void visitExprAggregateLiteral(ast::IExprAggregateLiteral *i) override {
    //     DEBUG_ENTER("visitExprAggregateLiteral");
    //     DEBUG("TODO: visitExprAggregateLiteral");
    //     DEBUG_LEAVE("visitExprAggregateLiteral");
    // }

    /**
     * Integer arithmetic, bitwise and shift operators fold when both
     * operands do -- enough for widths and template value arguments such as
     * reg_c's default `SZ = (8*sizeof_s<R>::nbytes)`. Comparisons and logical
     * operators, and division by zero, leave the result unfolded.
     */
    virtual void visitExprBin(ast::IExprBin *i) override {
        DEBUG_ENTER("visitExprBin %d", i->getOp());
        std::unique_ptr<IVal> lhs(i->getLhs()?eval(i->getLhs()):0);
        std::unique_ptr<IVal> rhs(i->getRhs()?eval(i->getRhs()):0);
        m_val.reset();
        IValInt *l = dynamic_cast<IValInt *>(lhs.get());
        IValInt *r = dynamic_cast<IValInt *>(rhs.get());
        if (l && r) {
            int64_t a = l->getValS(), b = r->getValS(), v = 0;
            bool ok = true;
            switch (i->getOp()) {
                case ast::ExprBinOp::BinOp_Add:    v = a + b; break;
                case ast::ExprBinOp::BinOp_Sub:    v = a - b; break;
                case ast::ExprBinOp::BinOp_Mul:    v = a * b; break;
                case ast::ExprBinOp::BinOp_Div:    ok = (b != 0); if (ok) v = a / b; break;
                case ast::ExprBinOp::BinOp_Mod:    ok = (b != 0); if (ok) v = a % b; break;
                case ast::ExprBinOp::BinOp_Shl:    ok = (b >= 0 && b < 64); if (ok) v = a << b; break;
                case ast::ExprBinOp::BinOp_Shr:    ok = (b >= 0 && b < 64); if (ok) v = a >> b; break;
                case ast::ExprBinOp::BinOp_BitAnd: v = a & b; break;
                case ast::ExprBinOp::BinOp_BitOr:  v = a | b; break;
                case ast::ExprBinOp::BinOp_BitXor: v = a ^ b; break;
                case ast::ExprBinOp::BinOp_Exp: {
                    ok = (b >= 0 && b < 64);
                    v = 1;
                    for (int64_t k=0; ok && k<b; k++) { v *= a; }
                } break;
                default: ok = false; break;
            }
            if (ok) {
                m_val = IValUP(m_factory->mkValInt(
                    l->isSigned() && r->isSigned(),
                    std::max(l->getWidth(), r->getWidth()),
                    v));
            }
        }
        DEBUG_LEAVE("visitExprBin");
    }

    virtual void visitExprBitSlice(ast::IExprBitSlice *i) override {
        DEBUG_ENTER("visitExprBitSlice");
        DEBUG("TODO: visitExprBitSlice");
        DEBUG_LEAVE("visitExprBitSlice");
    }

    virtual void visitExprBool(ast::IExprBool *i) override {
        DEBUG_ENTER("visitExprBool");
        DEBUG("TODO: visitExprBool");
        DEBUG_LEAVE("visitExprBool");
    }

    virtual void visitExprCast(ast::IExprCast *i) override {
        DEBUG_ENTER("visitExprCast");
        DEBUG("TODO: visitExprCast");
        DEBUG_LEAVE("visitExprCast");
    }

    virtual void visitExprCompileHas(ast::IExprCompileHas *i) override {
        DEBUG_ENTER("visitExprCompileHas");
        DEBUG("TODO: visitExprCompileHas");
        DEBUG_LEAVE("visitExprCompileHas");
    }

    virtual void visitExprCond(ast::IExprCond *i) override {
        DEBUG_ENTER("visitExprCond");
        DEBUG("TODO: visitExprCond");
        DEBUG_LEAVE("visitExprCond");
    }

    virtual void visitExprDomainOpenRangeList(ast::IExprDomainOpenRangeList *i) override {
        DEBUG_ENTER("visitExprDomainOpenRangeList");
        DEBUG("TODO: visitExprDomainOpenRangeList");
        DEBUG_LEAVE("visitExprDomainOpenRangeList");
    }

    virtual void visitExprDomainOpenRangeValue(ast::IExprDomainOpenRangeValue *i) override {
        DEBUG_ENTER("visitExprDomainOpenRangeValue");
        DEBUG("TODO: visitExprDomainOpenRangeValue");
        DEBUG_LEAVE("visitExprDomainOpenRangeValue");
    }

    virtual void visitExprId(ast::IExprId *i) override {
        DEBUG_ENTER("visitExprId %s", i->getId().c_str());
        DEBUG("TODO: visitExprId");
        DEBUG_LEAVE("visitExprId");
    }

    virtual void visitExprIn(ast::IExprIn *i) override {
        DEBUG_ENTER("visitExprIn");
        DEBUG("TODO: visitExprIn");
        DEBUG_LEAVE("visitExprIn");
    }

    virtual void visitExprOpenRangeList(ast::IExprOpenRangeList *i) override {
        DEBUG_ENTER("visitExprOpenRangeList");
        DEBUG("TODO: visitExprOpenRangeList");
        DEBUG_LEAVE("visitExprOpenRangeList");
    }

    virtual void visitExprOpenRangeValue(ast::IExprOpenRangeValue *i) override {
        DEBUG_ENTER("visitExprOpenRangeValue");
        DEBUG("TODO: visitExprOpenRangeValue");
        DEBUG_LEAVE("visitExprOpenRangeValue");
    }

    virtual void visitExprRefPath(ast::IExprRefPath *i) override {
        DEBUG_ENTER("visitExprRefPath");
        if (i->getTarget()) {
            ast::IScopeChild *target = TaskResolveSymbolPathRef(
                m_factory->getDebugMgr(),
                m_root).resolve(i->getTarget());
            if (target) {
                target->accept(m_this);
            } else {
                DEBUG("Error: failed to resolve RefPath");
            }
        } else {
            DEBUG("Error: ExprRefPath has null target");
        }
        DEBUG_LEAVE("visitExprRefPath");
    }

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override {
        DEBUG_ENTER("visitExprRefPathContext");
        // The reference may not resolve to anything foldable -- a template
        // parameter used as a width (`bit[SZ]`) has no target until the type
        // is specialized. Leaving m_val empty reports "did not fold", which
        // every caller already distinguishes from "folded to a value".
        ast::IScopeChild *target = i->getTarget()?
            TaskResolveSymbolPathRef(
                m_factory->getDebugMgr(),
                m_root).resolve(i->getTarget()):0;
        if (target) {
            target->accept(m_this);
        } else {
            DEBUG("Reference does not resolve to a foldable target");
        }
        DEBUG_LEAVE("visitExprRefPathContext");
    }

    virtual void visitExprNull(ast::IExprNull *i) override {
        DEBUG_ENTER("visitExprNull");
        DEBUG("TODO: visitExprNull");
        DEBUG_LEAVE("visitExprNull");
    }

    virtual void visitExprSignedNumber(ast::IExprSignedNumber *i) override {
        DEBUG_ENTER("visitExprSignedNumber");
        m_val = IValUP(m_factory->mkValInt(true, i->getWidth(), i->getValue()));
        DEBUG_LEAVE("visitExprSignedNumber");
    }

    virtual void visitExprString(ast::IExprString *i) override {
        DEBUG_ENTER("visitExprString");
        DEBUG("TODO: visitExprString");
        DEBUG_LEAVE("visitExprString");
    }

    virtual void visitField(ast::IField *i) override {
        DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
        if (i->getInit()) {
            i->getInit()->accept(m_this);
        } else {
            DEBUG("TODO: Field doesn't have an initial value");
        }
        DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
    }

    virtual void visitExprUnary(ast::IExprUnary *i) override {
        DEBUG_ENTER("visitExprUnary");
        std::unique_ptr<IVal> rhs(i->getRhs()?eval(i->getRhs()):0);
        m_val.reset();
        IValInt *r = dynamic_cast<IValInt *>(rhs.get());
        if (r) {
            bool ok = true;
            int64_t v = r->getValS();
            switch (i->getOp()) {
                case ast::ExprUnaryOp::UnaryOp_Plus:   break;
                case ast::ExprUnaryOp::UnaryOp_Minus:  v = -v; break;
                case ast::ExprUnaryOp::UnaryOp_BitNeg: v = ~v; break;
                default: ok = false; break;
            }
            if (ok) {
                m_val = IValUP(m_factory->mkValInt(
                    r->isSigned() || i->getOp() == ast::ExprUnaryOp::UnaryOp_Minus,
                    r->getWidth(), v));
            }
        }
        DEBUG_LEAVE("visitExprUnary");
    }

    virtual void visitExprUnsignedNumber(ast::IExprUnsignedNumber *i) override {
        DEBUG_ENTER("visitExprUnsignedNumber width=%d value=%d",
            i->getWidth(), i->getValue());
        m_val = IValUP(m_factory->mkValInt(false, i->getWidth(), i->getValue()));
        DEBUG_LEAVE("visitExprUnsignedNumber");
    }

    virtual void visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) override {
        DEBUG_ENTER("visitTemplateParamTypeValue");
        DEBUG_LEAVE("visitTemplateParamTypeValue");
    }

    virtual void visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) override {
        DEBUG_ENTER("visitTemplateParamExprValue");
        DEBUG_LEAVE("visitTemplateParamExprValue");
    }

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
        DEBUG("TODO: visitTemplateGenericTypeParamDecl");
        DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
        DEBUG("TODO: visitTemplateCategoryTypeParamDecl");
        DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
    }

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
        DEBUG_ENTER("visitTemplateValueParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        }
        DEBUG("TODO: visitTemplateValueParamDecl");
        DEBUG_LEAVE("visitTemplateValueParamDecl");
    }

private:
    dmgr::IDebug                       *m_dbg;
    IFactory                           *m_factory;
    ast::ISymbolScope                  *m_root;
    IValUP                             m_val;

};

}
