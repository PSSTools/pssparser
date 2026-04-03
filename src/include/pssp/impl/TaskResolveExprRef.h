/**
 * TaskResolveExprRef.h
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
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"


namespace pssp {


class TaskResolveExprRef : public virtual ast::VisitorBase {
public:

    TaskResolveExprRef(
        dmgr::IDebugMgr                 *dmgr,
        ast::ISymbolChildrenScope       *root) :
        m_dbg(0), m_dmgr(dmgr), m_root(root), m_ret(0) {
        DEBUG_INIT("pssp::TaskResolveExprRef", dmgr);
    }

    virtual ~TaskResolveExprRef() { }

    ast::IExpr *resolve(ast::IScopeChild *ref) {
        m_ret = 0;
        ref->accept(m_this);
        return m_ret;
    }

    virtual void visitExpr(ast::IExpr *i) override {
        DEBUG_ENTER("visitExpr");
        m_ret = i;
        DEBUG_LEAVE("visitExpr");
    }

    virtual void visitExprBin(ast::IExprBin *i) override {
        DEBUG_ENTER("visitExprBin");
        m_ret = i;
        DEBUG_LEAVE("visitExprBin");
    }

    virtual void visitExprBitSlice(ast::IExprBitSlice *i) override {
        DEBUG_ENTER("visitExprBitSlice");
        m_ret = i;
        DEBUG_LEAVE("visitExprBitSlice");
    }

    virtual void visitExprCast(ast::IExprCast *i) override {
        DEBUG_ENTER("visitExprCast");
        m_ret = i;
        DEBUG_LEAVE("visitExprCast");
    }

    virtual void visitExprCond(ast::IExprCond *i) override {
        DEBUG_ENTER("visitExprCond");
        m_ret = i;
        DEBUG_LEAVE("visitExprCond");
    }

    virtual void visitExprDomainOpenRangeList(ast::IExprDomainOpenRangeList *i) override {
        DEBUG_ENTER("visitExprDomainOpenRangeList");
        m_ret = i;
        DEBUG_LEAVE("visitExprDomainOpenRangeList");
    }

    virtual void visitExprDomainOpenRangeValue(ast::IExprDomainOpenRangeValue *i) override {
        DEBUG_ENTER("visitExprDomainOpenRangeValue");
        m_ret = i;
        DEBUG_LEAVE("visitExprDomainOpenRangeValue");
    }
    
    virtual void visitExprHierarchicalId(ast::IExprHierarchicalId *i) override {
        DEBUG_ENTER("visitExprHierarchicalId");
        m_ret = i;
        DEBUG_LEAVE("visitExprHierarchicalId");
    }

    virtual void visitExprId(ast::IExprId *i) override {
        DEBUG_ENTER("visitExprId");
        m_ret = i;
        DEBUG_LEAVE("visitExprId");
    }

    virtual void visitExprOpenRangeList(ast::IExprOpenRangeList *i) override {
        DEBUG_ENTER("visitExprOpenRangeList");
        m_ret = i;
        DEBUG_LEAVE("visitExprOpenRangeList");
    }

    virtual void visitExprRefPath(ast::IExprRefPath *i) override {
        DEBUG_ENTER("visitExprRefPath");
        m_ret = i;
        DEBUG_LEAVE("visitExprRefPath");
    }

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        if (i->getDflt()) {
            i->getDflt()->accept(this);
        }
    }
    
    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        if (i->getDflt()) {
            i->getDflt()->accept(this);
        }
    }
    
    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
        if (i->getDflt()) {
            m_ret = i->getDflt();
        }
    }

protected:
    dmgr::IDebug                *m_dbg;
    dmgr::IDebugMgr             *m_dmgr;
    ast::ISymbolChildrenScope   *m_root;
    ast::IExpr                  *m_ret;

};

}
