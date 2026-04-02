/**
 * TaskResolveTypeRef.h
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
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {



class TaskResolveTypeRef : public virtual ast::VisitorBase {
public:

    TaskResolveTypeRef(
        dmgr::IDebugMgr             *dmgr,
        ast::ISymbolChildrenScope   *root) : 
            m_dmgr(dmgr), m_dbg(0), m_root(root) {
        DEBUG_INIT("pssp::TaskResolveTypeRef", dmgr);
    }

    virtual ~TaskResolveTypeRef() { }

    ast::IScopeChild *resolve(ast::IScopeChild *ref) {
        DEBUG_ENTER("resolve");
        m_ret = 0;
        ref->accept(m_this);
        DEBUG_LEAVE("resolve %p", m_ret);
        return m_ret;
    }

    virtual void visitDataType(ast::IDataType *i) override {
        DEBUG_ENTER("visitDataType");
        m_ret = i;
        DEBUG_LEAVE("visitDataType");
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        if (i->getType_id()->getTarget()) {
            ast::IScopeChild *res = TaskResolveSymbolPathRef(
                m_dmgr, m_root).resolve(
                    i->getType_id()->getTarget());
            if (res) {
                res->accept(m_this);
            } else {
                DEBUG_ERROR("Failed to resolve user-defined datatype target");
            }
        } else {
            DEBUG_ERROR("Symbol not resolved");
        }
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope");
        m_ret = i;
        DEBUG_LEAVE("visitSymbolTypeScope");
    }

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        } else {
            DEBUG_ERROR("Expecting template parameter to have a default");
        }
        DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        } else {
            DEBUG_ERROR("Expecting template parameter to have a default");
        }
        DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
    }

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
        DEBUG_ENTER("visitTemplateValueParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        } else {
            DEBUG_ERROR("Expecting template parameter to have a default");
        }
        DEBUG_LEAVE("visitTemplateValueParamDecl");
    }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override {
        DEBUG_ENTER("visitTypeIdentifier");
        if (i->getTarget()) {
            ast::IScopeChild *res = TaskResolveSymbolPathRef(
                m_dmgr, m_root).resolve(
                    i->getTarget());
            if (res) {
                res->accept(m_this);
            } else {
                DEBUG_ERROR("Failed to resolve user-defined datatype target");
            }
        } else {
            DEBUG_ERROR("symbol not resolved");
        }
        DEBUG_LEAVE("visitTypeIdentifier");
    }

    virtual void visitTypeScope(ast::ITypeScope *i) override {
        DEBUG_ENTER("visitTypeScope");
        m_ret = i;
        DEBUG_LEAVE("visitTypeScope");
    }


protected:
    dmgr::IDebugMgr                 *m_dmgr;
    dmgr::IDebug                    *m_dbg;
    ast::ISymbolChildrenScope       *m_root;
    ast::IScopeChild                *m_ret;
};

} /* namespace pssp */


