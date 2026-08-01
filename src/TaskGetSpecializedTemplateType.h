/**
 * TaskGetSpecializedTemplateType.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/IFactory.h"
#include "pssp/ast/ISymbolScope.h"
#include "ResolveContext.h"

namespace pssp {




class TaskGetSpecializedTemplateType {
public:
    /**
     * How deep a chain of nested specializations may run before it is treated
     * as non-terminating.
     *
     * Legitimate nesting is shallow -- the deepest shape in the core library
     * is a handful of levels -- while a non-terminating chain grows without
     * bound, so a generous limit separates the two cleanly and is only ever
     * reached by a program that would otherwise exhaust the stack.
     */
    static const int32_t MAX_SPECIALIZATION_DEPTH = 64;

    TaskGetSpecializedTemplateType(ResolveContext *ctxt);

    virtual ~TaskGetSpecializedTemplateType();

    ast::ISymbolRefPath *find(
        const ast::ISymbolRefPath           *type,
        const ast::ITemplateParamDeclList   *params);

    ast::ISymbolRefPath *mk(
        const ast::ISymbolRefPath           *type,
        ast::ITemplateParamDeclList         *params);

    std::string mkTypename(
        const ast::ISymbolRefPath           *type,
        ast::ITemplateParamDeclList         *params);

private:
    static dmgr::IDebug                 *m_dbg;
    ResolveContext                      *m_ctxt;
};

}
