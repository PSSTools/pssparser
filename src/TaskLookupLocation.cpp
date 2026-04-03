/*
 * TaskLookupLocation.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskLookupLocation.h"


namespace pssp {



TaskLookupLocation::TaskLookupLocation(dmgr::IDebugMgr *dmgr) {
    m_dmgr = dmgr;
    DEBUG_INIT("pssp::TaskLookupLocation", dmgr);

}

TaskLookupLocation::~TaskLookupLocation() {

}

ILookupLocationResult *TaskLookupLocation::lookup(
        ast::IRootSymbolScope   *root,
        ast::IScope             *scope,
        int32_t                 lineno,
        int32_t                 linepos) {
    ILookupLocationResult *ret = 0;
    DEBUG_ENTER("lookup");
    m_root = root;
    m_lineno = lineno;
    m_linepos = linepos;

    m_result = 0;
    scope->accept(m_this);

    DEBUG_LEAVE("lookup %p", m_result);
    return m_result;
}

void TaskLookupLocation::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
    if (isMatch(i->getLocation())) {
        // Field
        DEBUG("Field");
    } else if (isMatch(i->getType()->getLocation())) {
        // Type reference
        DEBUG("Field type %d", m_path.size());
//        TaskResolveSymbolPathRef(m_dmgr, m_root).resolve());
    }
    DEBUG("loc: %d:%d:%d", 
        i->getLocation().lineno, 
        i->getLocation().linepos,
        i->getLocation().extent);
    DEBUG("type: %d:%d:%d", 
        i->getType()->getLocation().lineno, 
        i->getType()->getLocation().linepos,
        i->getType()->getLocation().extent);
    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
}

void TaskLookupLocation::visitNamedScope(ast::INamedScope *i) {
    DEBUG_ENTER("visitNamedScope");
    if (isMatch(i->getName()->getLocation())) {
        // Referencing this type
    } else {
        visitScope(i);
    }
    DEBUG_LEAVE("visitNamedScope");
}

void TaskLookupLocation::visitScope(ast::IScope *i) {
    DEBUG_ENTER("visitScope");

    if (i->getChildren().size() && 
        ((m_lineno >= i->getLocation().lineno && m_lineno <= i->getEndLocation().lineno) ||
        i->getLocation().lineno == -1 && i->getEndLocation().lineno == -1)) {
        DEBUG("Target %d is inside range %d..%d", 
            m_lineno, 
            i->getLocation().lineno,
            i->getEndLocation().lineno);
        // Worth searching here
        if (i->getChildren().size() == 1 || m_lineno >= i->getChildren().back()->getLocation().lineno) {
            // Search the last scope
            if (i->getLocation().lineno != -1) {
                m_path.push_back(i);
            }
            i->getChildren().back()->accept(m_this);
            if (i->getLocation().lineno != -1) {
                m_path.pop_back();
            }
        } else {
            uint32_t ii_low = 0;
            uint32_t ii_high = i->getChildren().size()-1;
            uint32_t count = 0;
            while (ii_low != ii_high && count < 10) {
                uint32_t ii_mid = ii_low + (ii_high-ii_low)/2;
                DEBUG("ii_low=%d ii_high=%d ii_mid=%d", ii_low, ii_high, ii_mid);
                if (m_lineno < i->getChildren().at(ii_mid)->getLocation().lineno) {
                    DEBUG("less than mid");
                    if (ii_mid) {
                        ii_high = ii_mid-1;
                    } else {
                        DEBUG("ii_mid=0");
                        break;
                    }
                } else if (m_lineno >= i->getChildren().at(ii_mid)->getLocation().lineno) {
                    DEBUG("greater-equal mid");
                    if (ii_low == ii_mid) {
                        // Try to move the needle
                        if (ii_mid+1 < i->getChildren().size()) {
                            if (m_lineno >= i->getChildren().at(ii_mid+1)->getLocation().lineno) {
                                DEBUG("Move low -> ii_mid+1");
                                ii_low = ii_mid+1;
                            }
                        }
                    } else {
                        ii_low = ii_mid;
                    }
                } else {
                    DEBUG("neither??");
                }
                DEBUG("end: ii_low=%d ii_high=%d", ii_low, ii_high);
                count++;
            }

            if (i->getLocation().lineno != -1) {
                m_path.push_back(i);
            }
            i->getChildren().at(ii_low)->accept(m_this);
            if (i->getLocation().lineno != -1) {
                m_path.pop_back();
            }
        }
    } else {
        DEBUG("Target %d is outside range %d..%d", 
            m_lineno, 
            i->getLocation().lineno,
            i->getEndLocation().lineno);
    }

    DEBUG_LEAVE("visitScope");
}

void TaskLookupLocation::visitScopeChild(ast::IScopeChild *i) {
    DEBUG_ENTER("visitScopeChild");
    DEBUG("loc: %d:%d", i->getLocation().lineno, i->getLocation().linepos);
    DEBUG_LEAVE("visitScopeChild");
}

void TaskLookupLocation::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope");
    // First, check super-type
    if (i->getSuper_t() && isMatch(i->getSuper_t())) {
        // Pointed at some element of the super type
        // TODO: need to pick this apart a bit more...
    } else {
        visitNamedScope(i);
    }
    DEBUG_LEAVE("visitTypeScope");
}

bool TaskLookupLocation::isMatch(const ast::Location &loc) {
    int32_t extent = (loc.extent > 0)?loc.extent:1;

    return (m_lineno == loc.lineno && 
        (m_linepos >= loc.linepos && m_linepos <= (loc.lineno+extent)));
}

bool TaskLookupLocation::isMatch(ast::ITypeIdentifier *ti) {
    return false;
}

dmgr::IDebug *TaskLookupLocation::m_dbg = 0;

}
