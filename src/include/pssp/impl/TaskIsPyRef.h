/**
 * TaskIsPyRef.h
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




class TaskIsPyRef : public ast::VisitorBase {
public:

    TaskIsPyRef(
        dmgr::IDebugMgr     *dmgr,
        ast::ISymbolScope   *root) : m_dmgr(dmgr), m_dbg(0), m_root(root) {
        DEBUG_INIT("pssp::TaskIsPyRef", dmgr);
    }

    virtual ~TaskIsPyRef() { }

    bool check(ast::IScopeChild *it) {
        DEBUG_ENTER("check");
        m_is_pyref = false;
        it->accept(m_this);
        DEBUG_LEAVE("check %d", m_is_pyref);
        return m_is_pyref;
    }

    virtual void visitDataTypePyObj(ast::IDataTypePyObj *i) override {
        DEBUG_ENTER("visitDataTypePyObj");
        m_is_pyref = true;
        DEBUG_LEAVE("visitDataTypePyObj");
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        ast::IScopeChild *target = TaskResolveSymbolPathRef(m_dmgr, m_root).resolve(
            i->getType_id()->getTarget()
        );
        if (target) {
            target->accept(m_this);
        } else {
            DEBUG_ERROR("Failed to resolve user-defined data type target");
        }
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitField(ast::IField *i) override {
        DEBUG_ENTER("visitField");
        i->getType()->accept(m_this);
        DEBUG_LEAVE("visitField");
    }

    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) override {
        DEBUG_ENTER("visitProceduralStmtDataDeclaration");
        i->getDatatype()->accept(m_this);
        DEBUG_LEAVE("visitProceduralStmtDataDeclaration");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
        i->getTarget()->accept(m_this);
        DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
    }

    virtual void visitStruct(ast::IStruct *i) override {
        DEBUG_ENTER("visitStruct %s", i->getName()->getId().c_str());
        DEBUG_LEAVE("visitStruct");
    }

    virtual void visitPyImportStmt(ast::IPyImportStmt *i) override {
        DEBUG_ENTER("visitPyImportStmt");
        m_is_pyref = true;
        DEBUG_LEAVE("visitPyImportStmt");
    }

    virtual void visitPyImportFromStmt(ast::IPyImportFromStmt *i) override {
        DEBUG_ENTER("visitPyImportFromStmt");
        m_is_pyref = true;
        DEBUG_LEAVE("visitPyImportFromStmt");
    }

private:
    dmgr::IDebugMgr         *m_dmgr;
    dmgr::IDebug            *m_dbg;
    ast::ISymbolScope       *m_root;
    bool                    m_is_pyref;
};

} /* namespace pssp */


