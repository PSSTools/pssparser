/**
 * TaskClearLinks.h
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


class TaskClearLinks : public virtual ast::VisitorBase {
public:
    TaskClearLinks(dmgr::IDebugMgr *dmgr) : m_dbg(0) {
        DEBUG_INIT("pssp::TaskClearLinks", dmgr);
    }

    virtual ~TaskClearLinks() { }

    void clear(ast::IScopeChild *c) {
        c->accept(m_this);
    }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override {
        DEBUG_ENTER("visitTypeIdentifier");
        i->setTarget(0);
        DEBUG_LEAVE("visitTypeIdentifier");
    }
    
    virtual void visitField(ast::IField *i) override {
        DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
        i->getType()->accept(m_this);
        DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        if (i->getType_id()) {
            i->getType_id()->accept(m_this);
        }
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override {
        DEBUG_ENTER("visitExprRefPathContext");
        i->setTarget(0);
        DEBUG_LEAVE("visitExprRefPathContext");
    }

    // virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
    //     DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
    //     i->getDflt()->accept(m_this);
    //     DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
    // }

    // virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
    //     DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
    //     i->getDflt()->accept(m_this);
    //     DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
    // }

    // virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
    //     DEBUG_ENTER("visitTemplateValueParamDecl");
    //     i->getDflt()->accept(m_this);
    //     DEBUG_LEAVE("visitTemplateValueParamDecl");
    // }

protected:
    dmgr::IDebug                *m_dbg;

};

}
