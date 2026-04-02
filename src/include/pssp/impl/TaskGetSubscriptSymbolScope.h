/**
 * TaskGetSubscriptSymbolScope.h
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
#include "TaskResolveSymbolPathRef.h"
#include "pssp/impl/TaskGetElemSymbolScope.h"

namespace pssp {


class TaskGetSubscriptSymbolScope : public virtual TaskGetElemSymbolScope {
public:

    TaskGetSubscriptSymbolScope(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root,
        const std::string       &logid="pssp::TaskGetSubscriptSymbolScope") : 
        TaskGetElemSymbolScope(dmgr, root, logid) {
    }

    virtual ~TaskGetSubscriptSymbolScope() { }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope \"%s\"", i->getName().c_str());
        if (i->getName().find("array<") != -1) {
            DEBUG("TODO: array subscript");
            ast::ITypeScope *type = dynamic_cast<ast::ITypeScope *>(i->getTarget());
            type->getParams()->getParams().at(0)->accept(m_this);
        } else {
            m_ret = i;
        }
        DEBUG_LEAVE("visitSymbolTypeScope");
    }


protected:

};

}
