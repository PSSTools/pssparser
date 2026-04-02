/**
 * TaskGetSymbolRefPathKind.h
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


class TaskGetSymbolRefPathKind : public virtual ast::VisitorBase {
public:
    TaskGetSymbolRefPathKind(dmgr::IDebugMgr *dmgr) : m_dbg(0) {
        DEBUG_INIT("pssp::TaskGetSymbolRefPathKind", dmgr);
    }

    virtual ~TaskGetSymbolRefPathKind() { }

    ast::SymbolRefPathElemKind get(ast::IScopeChild *c) {
        DEBUG_ENTER("get");
        m_kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;
        c->accept(m_this);
        DEBUG_LEAVE("get");
        return m_kind;
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope");
        m_kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;
        DEBUG_LEAVE("visitSymbolScope");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope");
        m_kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;
        DEBUG_LEAVE("visitSymbolTypeScope");
    }

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
        m_kind = ast::SymbolRefPathElemKind::ElemKind_ParamIdx;
        DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
        m_kind = ast::SymbolRefPathElemKind::ElemKind_ParamIdx;
        DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
    }

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
        DEBUG_ENTER("visitTemplateValueParamDecl");
        m_kind = ast::SymbolRefPathElemKind::ElemKind_ParamIdx;
        DEBUG_LEAVE("visitTemplateValueParamDecl");
    }


private:
    dmgr::IDebug                    *m_dbg;
    ast::SymbolRefPathElemKind      m_kind;
};

} /* namespace pssp */


