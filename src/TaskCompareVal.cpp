/*
 * TaskCompareVal.cpp
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
#include "TaskCompareVal.h"


namespace pssp {



TaskCompareVal::TaskCompareVal(dmgr::IDebugMgr *dmgr) {
    DEBUG_INIT("pssp::TaskCompareVal", dmgr);
}

TaskCompareVal::~TaskCompareVal() {

}

bool TaskCompareVal::equal(IVal *v1, IVal *v2) {
    DEBUG_ENTER("equal");
    m_ret = true;

    if (!v1 || !v2) {
        m_ret = false;
    } else if (v1->getKind() != v2->getKind()) {
        m_ret = false;
    } else {
        m_val2 = v2;
        v1->accept(this);
    }

    DEBUG_LEAVE("equal %d", m_ret);
    return m_ret;
}

void TaskCompareVal::visitValInt(IValInt *v) {
    DEBUG_ENTER("visitValInt");
    if (m_val2->getKind() != ValKind::Int) {
        DEBUG("Unequal values: v_val2::kind=%d", m_val2->getKind());
        m_ret = false;
    } else {
        IValInt *v2 = dynamic_cast<IValInt *>(m_val2);
        if (!v->isSigned() && !v2->isSigned()) {
            // Perform unsigned comparison
            DEBUG("v1=%llu v2=%llu", v->getValS(), v2->getValU());
            m_ret &= (v->getValU() == v2->getValU());
        } else {
            // Signed comparison
            DEBUG("v1=%lld v2=%lld", v->getValS(), v2->getValU());
            m_ret &= (v->getValS() == v2->getValS());
        }
    }
    DEBUG_LEAVE("visitValInt ret=%d", m_ret);
}

dmgr::IDebug *TaskCompareVal::m_dbg = 0;

}
