/**
 * TaskComputeTypePackedSize.h
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
#include "pssp/impl/TaskEvalExpr.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {




class TaskComputeTypePackedSize : public virtual ast::VisitorBase {
public:

    TaskComputeTypePackedSize(
        IFactory                *factory,
        ast::ISymbolScope       *root) : 
            m_dbg(0), m_factory(factory), m_root(root) {
        DEBUG_INIT("pssp::TaskComputeTypePackedSize", factory->getDebugMgr());
    }

    virtual ~TaskComputeTypePackedSize() { }

    int32_t bits(ast::IDataType *t) {
        DEBUG_ENTER("bits");
        m_bits = 0;
        t->accept(m_this);
        DEBUG_LEAVE("bits %d", m_bits);
        return m_bits;
    }

    virtual void visitDataTypeBool(ast::IDataTypeBool *i) override {
        DEBUG_ENTER("visitDataTypeBool");
        m_bits++;
        DEBUG_LEAVE("visitDataTypeBool");
    }

    virtual void visitDataTypeChandle(ast::IDataTypeChandle *i) override {
        DEBUG_ENTER("visitDataTypeChandle");
        m_bits += sizeof(void *);
        DEBUG_LEAVE("visitDataTypeChandle");
    }

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) override {
        DEBUG_ENTER("visitDataTypeEnum");
        m_bits += 32;
        DEBUG_LEAVE("visitDataTypeEnum");
    }

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) override {
        DEBUG_ENTER("visitDataTypeInt");
        IValInt *val = TaskEvalExpr(m_factory, m_root).evalT<IValInt>(i->getWidth());
        if (val) {
            m_bits += val->getValS();
        } else {
            DEBUG_ERROR("Failed to compute width");
        }
        DEBUG_LEAVE("visitDataTypeInt");
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        ast::IScopeChild *t = TaskResolveSymbolPathRef(
            m_factory->getDebugMgr(), m_root).resolve(
                i->getType_id()->getTarget());
        t->accept(m_this);
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());

        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            it->get()->accept(m_this);
        }

        DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
    }

private:
    dmgr::IDebug                *m_dbg;
    IFactory                    *m_factory;
    ast::ISymbolScope           *m_root;
    int32_t                     m_bits;


};

} /* namespace pssp */


