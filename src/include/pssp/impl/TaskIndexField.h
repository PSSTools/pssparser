/**
 * TaskIndexField.h
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




class TaskIndexField : ast::VisitorBase {
public:

    TaskIndexField(
        dmgr::IDebugMgr     *dmgr,
        ast::ISymbolScope   *root_scope) : 
        m_dmgr(dmgr), m_dbg(0), m_root_scope(root_scope) {
        DEBUG_INIT("pssp::TaskIndexField", dmgr);
    }

    virtual ~TaskIndexField() { }

    ast::IScopeChild *index(
        ast::IScopeChild *root, 
        int32_t     idx,
        int32_t     super_idx) {
        DEBUG_ENTER("idx=%d super_idx=%d", idx, super_idx);
        m_idx = idx;
        m_super_idx = super_idx;
        m_ret = 0;

        root->accept(m_this);

        DEBUG_LEAVE("index => %p", m_ret);
        return m_ret;
    }

    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override { 
        DEBUG_ENTER("visitFieldCompRef");
        i->getType()->accept(m_this);
        DEBUG_LEAVE("visitFieldCompRef");
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        ast::IScopeChild *target = TaskResolveSymbolPathRef(
            m_dmgr, m_root_scope).resolve(
                i->getType_id()->getTarget());
        target->accept(m_this);
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitSymbolRefPath(ast::ISymbolRefPath *i) override {
        DEBUG_ENTER("visitSymbolRefPath");
        DEBUG_LEAVE("visitSymbolRefPath");
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope");
        m_ret = i->getChildren().at(m_idx).get();
        DEBUG_LEAVE("visitSymbolScope");
    }

    virtual void visitTypeScope(ast::ITypeScope *i) override {
        DEBUG_ENTER("visitTypeScope (super_idx=%d)", m_super_idx);
        if (m_super_idx > 0) {
            m_super_idx--;
            ast::IScopeChild *super_t = TaskResolveSymbolPathRef(
                m_dmgr, m_root_scope).resolve(
                    i->getSuper_t()->getTarget());
            super_t->accept(m_this);
            m_super_idx++;
        }
        DEBUG_LEAVE("visitTypeScope (super_idx=%d)", m_super_idx);
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope");
        if (m_super_idx > 0) {
            i->getTarget()->accept(m_this);
        } else {
            m_ret = i->getChildren().at(m_idx).get();
        }
        DEBUG_LEAVE("visitSymbolTypeScope");
    }

protected:
    dmgr::IDebugMgr                     *m_dmgr;
    dmgr::IDebug                        *m_dbg;
    ast::ISymbolScope                   *m_root_scope;
    int32_t                             m_idx;
    int32_t                             m_super_idx;
    ast::IScopeChild                    *m_ret;

};

} /* namespace pssp */


