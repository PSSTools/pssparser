/**
 * TaskGetFieldType.h
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
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {




class TaskGetFieldType : public ast::VisitorBase {
public:
    TaskGetFieldType(
        dmgr::IDebugMgr             *dmgr,
        ast::ISymbolChildrenScope   *root) : m_dmgr(dmgr), m_root(root) {

    }

    virtual ~TaskGetFieldType() { }

    ast::IScopeChild *get(ast::IScopeChild *f) {
        m_ret = 0;
        f->accept(m_this);
        return m_ret;
    }

    virtual void visitDataType(ast::IDataType *i) override {
        m_ret = i;
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        ast::IScopeChild *target = TaskResolveSymbolPathRef(
            m_dmgr, m_root).resolve(
                i->getType_id()->getTarget());
        target->accept(m_this);
    }


    virtual void visitField(ast::IField *i) override {
        i->getType()->accept(m_this);
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        m_ret = i;
    }

private:
    dmgr::IDebugMgr                 *m_dmgr;
    ast::ISymbolChildrenScope       *m_root;
    ast::IScopeChild                *m_ret;


};

} /* namespace pssp */


