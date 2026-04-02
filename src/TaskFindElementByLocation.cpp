/*
 * TaskFindElementByLocation.cpp
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
#include <string.h>
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskFindElementByLocation.h"


namespace pssp {


/**
 * 
 * 
 * @param dmgr 
 */

TaskFindElementByLocation::TaskFindElementByLocation(dmgr::IDebugMgr *dmgr) {
    m_dmgr = dmgr;
    DEBUG_INIT("TaskFindElementByLocation", dmgr);
}

TaskFindElementByLocation::~TaskFindElementByLocation() {

}

ITaskFindElementByLocation::Result TaskFindElementByLocation::find(
        ast::ISymbolScope                   *root,
        ast::IGlobalScope                   *file,
        int32_t                             lineno,
        int32_t                             linepos,
        int32_t                             fuzz) {
    DEBUG_ENTER("find");
    m_root = root;
    m_file = file;
    m_lineno = lineno;
    m_linepos = linepos;
    m_fuzz = fuzz;

    ::memset(&m_result, 0, sizeof(m_result));

    root->accept(m_this);

    DEBUG_LEAVE("find (%d)", m_result.isValid);
    return m_result;
}

void TaskFindElementByLocation::visitExprId(ast::IExprId *i) {
    DEBUG_ENTER("visitExprId");
    DEBUG("%s: %d %d..%d", i->getId().c_str(), 
        i->getLocation().lineno, 
        i->getLocation().linepos,
        i->getLocation().linepos+i->getId().size()-1);
    if (hit(i->getLocation().lineno, 
            i->getLocation().linepos,
            i->getLocation().linepos+i->getId().size())) {
        DEBUG("Found");

        // Now, must determine what we're looking at
        if (m_ctxt_s.back().expr) {
            m_result.sourceKind = ElemKind::Expr;
            m_result.source.e.ctxt = m_ctxt_s.back().expr;
            m_result.source.e.elem = i;
            DEBUG("Upper is an expression");
            if (dynamic_cast<ast::ITypeIdentifier *>(m_ctxt_s.back().expr)) {
                ast::ITypeIdentifier *t = dynamic_cast<ast::ITypeIdentifier *>(m_ctxt_s.back().expr);
                if (i == t->getElems().back().get()->getId()) {
                    // We're pointing at the last element of a path
                    DEBUG("Last Element");

                    m_result.sourceRange.start.lineno = t->getElems().front().get()->getId()->getLocation().lineno;
                    m_result.sourceRange.start.linepos = t->getElems().front().get()->getId()->getLocation().linepos;
                    m_result.sourceRange.end.lineno = t->getElems().back().get()->getId()->getLocation().lineno;
                    m_result.sourceRange.end.linepos = t->getElems().back().get()->getId()->getLocation().linepos;

                    if (t->getTarget()) {
                        ast::IScopeChild *target = TaskResolveSymbolPathRef(
                            m_dmgr, m_root).resolve(t->getTarget());
                        if (dynamic_cast<ast::ISymbolScope *>(target)) {
                            m_result.target = dynamic_cast<ast::ISymbolScope *>(target)->getTarget();
                        } else {
                            m_result.target = target;
                        }
                    }
                    m_result.targetKind = ElemKind::Type;
                    m_result.isValid = m_result.target;
                } else {
                    DEBUG("Not-last Element");
                }
            }
        } else {
            if (dynamic_cast<ast::ITypeScope *>(m_ctxt_s.back().child)) {
                ast::ITypeScope *t = dynamic_cast<ast::ITypeScope *>(m_ctxt_s.back().child);
                DEBUG("Upper is a type declaration (%s)", t->getName()->getId().c_str()); 
                m_result.sourceKind = ElemKind::Expr;
                m_result.targetKind = ElemKind::Type;
                m_result.target = t;
            } else if (dynamic_cast<ast::IField *>(m_ctxt_s.back().child)) {
                ast::IField *t = dynamic_cast<ast::IField *>(m_ctxt_s.back().child);
                DEBUG("Upper is a field (%s)", t->getName()->getId().c_str());
                m_result.sourceKind = ElemKind::Expr;
                m_result.targetKind = ElemKind::Field;
                m_result.target = t;
            }
            m_result.isValid = true;
        }
    }
    DEBUG_LEAVE("visitExprId");
}

void TaskFindElementByLocation::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField");
    m_ctxt_s.push_back({0, i});
    VisitorBase::visitField(i);
    m_ctxt_s.pop_back();
    DEBUG_LEAVE("visitField");
}

void TaskFindElementByLocation::visitSymbolScope(ast::ISymbolScope *i) {
    bool push = (m_ctxt_s.size() == 0 || m_ctxt_s.back().child != i);
    DEBUG_ENTER("visitSymbolScope");

    if (push) {
        m_ctxt_s.push_back({0, i});
    }

    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
        if (it->get()) {
            it->get()->accept(this);
        }
    }
    if (i->getTarget()) {
        i->getTarget()->accept(this);
    }
    if (i->getImports()) {
        i->getImports()->accept(this);
    }

    if (push && !m_result.isValid) {
        m_ctxt_s.pop_back();
    }

    DEBUG_LEAVE("visitSymbolScope");
}

void TaskFindElementByLocation::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier");
    m_ctxt_s.push_back({i, 0});
    VisitorBase::visitTypeIdentifier(i);
    m_ctxt_s.pop_back();
    DEBUG_LEAVE("visitTypeIdentifier");
}

void TaskFindElementByLocation::visitTypeScope(ast::ITypeScope *i) {
    bool push = (m_ctxt_s.size() == 0 || m_ctxt_s.back().child != i);
    DEBUG_ENTER("visitTypeScope");
    if (push) {
        m_ctxt_s.push_back({0, i});
    }

    VisitorBase::visitTypeScope(i);

    if (push && !m_result.isValid) {
        m_ctxt_s.pop_back();
    }

    DEBUG_LEAVE("visitTypeScope");
}

bool TaskFindElementByLocation::hit(int32_t lineno, int32_t start, int32_t end) {
    bool is_hit = false;
    if (lineno == m_lineno) {
        is_hit = (m_linepos >= start && m_linepos <= end);
        for (int32_t i=0; (i<m_fuzz && !is_hit); i++) {
            is_hit = (
                ((m_linepos+i) >= start && (m_linepos+i) <= end)
                || ((m_linepos-i) >= start && (m_linepos-i) <= end));
        }
    }
    return is_hit;
}

dmgr::IDebug *TaskFindElementByLocation::m_dbg = 0;

}
