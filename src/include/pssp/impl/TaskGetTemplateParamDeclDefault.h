/**
 * TaskGetTemplateParamDeclDefault.h
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




class TaskGetTemplateParamDeclDefault : public virtual ast::VisitorBase {
public:

    TaskGetTemplateParamDeclDefault(dmgr::IDebugMgr *dmgr) : m_dbg(0) {
        DEBUG_INIT("pssp::TaskGetTemplateParamDeclDefault", dmgr);
    }

    virtual ~TaskGetTemplateParamDeclDefault() { }

    std::pair<ast::IDataType *, ast::IExpr *> default_val(ast::ITemplateParamDecl *p) {
        m_type = 0;
        m_expr = 0;

        p->accept(m_this);
        return {m_type, m_expr};
    }

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        m_type = i->getDflt();
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        m_type = i->getDflt();
    }

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
        m_expr = i->getDflt();
    }

private:
    dmgr::IDebug                        *m_dbg;
    ast::IDataType                      *m_type;
    ast::IExpr                          *m_expr;

};

} /* namespace pssp */


