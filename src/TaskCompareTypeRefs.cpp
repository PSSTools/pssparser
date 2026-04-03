/*
 * TaskCompareTypeRefs.cpp
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
#include "pssp/IVal.h"
#include "pssp/IValInt.h"
#include "TaskCompareTypeRefs.h"
#include "TaskCompareVal.h"


namespace pssp {



TaskCompareTypeRefs::TaskCompareTypeRefs(
    IFactory                *factory,
    ast::ISymbolScope       *root) :
    m_expr_eval(factory, root), m_root(root), m_comp_val(factory->getDebugMgr()) {
    DEBUG_INIT("pssp::TaskCompareTypeRefs", factory->getDebugMgr());
}

TaskCompareTypeRefs::~TaskCompareTypeRefs() {

}

bool TaskCompareTypeRefs::equal(
        ast::IDataType          *tref1,
        ast::IDataType          *tref2) {
    DEBUG_ENTER("equal");
    bool ret = true;
    ast::IDataTypeInt    *type_int = 0;
    ast::IDataTypeString *type_str = 0;

    m_type_int = 0;
    m_type_str = 0;
    tref1->accept(m_this);
    type_int = m_type_int;
    type_str = m_type_str;

    m_type_int = 0;
    m_type_int = 0;
    tref2->accept(m_this);

    if (m_type_int && type_int) {
        // Both are type int
        IVal *w1 = m_expr_eval.eval(m_type_int->getWidth());
        IVal *w2 = m_expr_eval.eval(type_int->getWidth());
        DEBUG("Both are type 'int'");
        DEBUG("T1: width=%d signed=%d", m_type_int->getWidth(), m_type_int->getIs_signed());
        DEBUG("T2: width=%d signed=%d", type_int->getWidth(), type_int->getIs_signed());
        ret &= m_comp_val.equal(w1, w2);
    } else if (m_type_str && type_str) {
        DEBUG("Both are type 'str'");
        // Nothing else to do...
    } else {
        ret = false;
    }
    DEBUG_LEAVE("equal %d", ret);
    return ret;
}

void TaskCompareTypeRefs::visitExprRefPath(ast::IExprRefPath *i) {
    DEBUG_ENTER("visitExprRefPath");

    DEBUG_LEAVE("visitExprRefPath");
}

void TaskCompareTypeRefs::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext");

    DEBUG_LEAVE("visitExprRefPathContext");
}

void TaskCompareTypeRefs::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic");

    DEBUG_LEAVE("visitExprRefPathStatic");
}


void TaskCompareTypeRefs::visitDataTypeInt(ast::IDataTypeInt *i) {
    DEBUG_ENTER("visitDataTypeInt");
    m_type_int = i;
    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskCompareTypeRefs::visitDataTypeRef(ast::IDataTypeRef *i) {
    DEBUG_ENTER("visitDataTypeRef");

    DEBUG_LEAVE("visitDataTypeRef");
}

void TaskCompareTypeRefs::visitDataTypeString(ast::IDataTypeString *i) {
    DEBUG_ENTER("visitDataTypeString");
    m_type_str = i;
    DEBUG_LEAVE("visitDataTypeString");
}

void TaskCompareTypeRefs::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    DEBUG_ENTER("visitDataTypeUserDefined");

    DEBUG_LEAVE("visitDataTypeUserDefined");
}

dmgr::IDebug *TaskCompareTypeRefs::m_dbg = 0;

}
