/*
 * TaskExpr2DataType.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskExpr2DataType.h"
#include "pssp/impl/TaskCopyAst.h"


namespace pssp {



TaskExpr2DataType::TaskExpr2DataType(ResolveContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("TaskExpr2DataType", ctxt->getDebugMgr());
}

TaskExpr2DataType::~TaskExpr2DataType() {

}

ast::IDataType *TaskExpr2DataType::expr2dt(ast::IExpr *e) {
    m_ret = 0;
    e->accept(m_this);
    return m_ret;
}

void TaskExpr2DataType::visitExpr(ast::IExpr *i) { 
    DEBUG_ENTER("visitExpr");
    DEBUG("TODO: flag error");
    DEBUG_LEAVE("visitExpr");
}

void TaskExpr2DataType::visitExprId(ast::IExprId *i) { 
    DEBUG_ENTER("visitExprId");
    DEBUG("TODO: flag error");
    DEBUG_LEAVE("visitExprId");
}

void TaskExpr2DataType::visitExprHierarchicalId(ast::IExprHierarchicalId *i) { 
    DEBUG_ENTER("visitExprHierarchicalId");
    DEBUG("TODO: flag error");
    DEBUG_LEAVE("visitExprHierarchicalId");
}

void TaskExpr2DataType::visitExprRefPathContext(ast::IExprRefPathContext *i) { 
    DEBUG_ENTER("visitExprRefPathContext");
    DEBUG("super=%p slice=%p elems=%d",
        i->getIs_super(),
        i->getSlice(),
        i->getHier_id()->getElems().size());
    if (i->getIs_super() || i->getSlice() || i->getHier_id()->getElems().size() > 1) {
        DEBUG("TODO: flag error");
    } else {
        ast::ITypeIdentifier *tid = m_ctxt->getFactory()->getAstFactory()->mkTypeIdentifier();
        tid->getElems().push_back(ast::ITypeIdentifierElemUP(
            m_ctxt->getFactory()->getAstFactory()->mkTypeIdentifierElem(
                TaskCopyAst(m_ctxt->getFactory()).copyT<ast::IExprId>(
                    i->getHier_id()->getElems().at(0)->getId()
                ),
                0
        )));
        m_ret = m_ctxt->getFactory()->getAstFactory()->mkDataTypeUserDefined(false, tid);
    }
    DEBUG_LEAVE("visitExprRefPathContext");
}

void TaskExpr2DataType::visitExprRefPathId(ast::IExprRefPathId *i) { 
    DEBUG_ENTER("visitExprRefPathId");
    if (i->getSlice()) {
        DEBUG("TODO: flag error -- slice not permitted on a type identifier");
    } else {
        ast::ITypeIdentifier *tid = m_ctxt->getFactory()->getAstFactory()->mkTypeIdentifier();
        tid->getElems().push_back(ast::ITypeIdentifierElemUP(
            m_ctxt->getFactory()->getAstFactory()->mkTypeIdentifierElem(
                TaskCopyAst(m_ctxt->getFactory()).copyT<ast::IExprId>(i->getId()),
                0
            )));
        m_ret = m_ctxt->getFactory()->getAstFactory()->mkDataTypeUserDefined(
            false,
            tid
        );
    }
    DEBUG_LEAVE("visitExprRefPathId");
}

void TaskExpr2DataType::visitExprRefPathStatic(ast::IExprRefPathStatic *i) { 
    DEBUG_ENTER("visitExprRefPathStatic");
    DEBUG("TODO: flag error");
    DEBUG_LEAVE("visitExprRefPathStatic");
}

void TaskExpr2DataType::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) { 

}

void TaskExpr2DataType::visitExprStaticRefPath(ast::IExprStaticRefPath *i) { 
    DEBUG_ENTER("visitExprStaticRefPath");
    DEBUG("TODO: flag error");
    DEBUG_LEAVE("visitExprStaticRefPath");
}

void TaskExpr2DataType::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier");
    m_ret = m_ctxt->getFactory()->getAstFactory()->mkDataTypeUserDefined(
        false,
        TaskCopyAst(m_ctxt->getFactory()).copyT<ast::ITypeIdentifier>(i)
    );
    DEBUG_LEAVE("visitTypeIdentifier");
}

dmgr::IDebug *TaskExpr2DataType::m_dbg = 0;

}
