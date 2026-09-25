/**
 * TaskSpecializeParameterizedRef.h
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
#include <functional>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/ISymbolRefPath.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ITemplateParamValueList.h"
#include "pssp/ast/ITemplateValueParamDecl.h"
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "ResolveContext.h"

namespace pssp {




class TaskSpecializeParameterizedRef {
public:
    TaskSpecializeParameterizedRef(ResolveContext *ctxt);

    virtual ~TaskSpecializeParameterizedRef();

    /**
     * @param use_loc the location of the reference being specialized, used to
     *   report an argument-list error where the reader can act on it.
     */
    ast::ISymbolRefPath *specialize(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateParamValueList        *pvals,
        const ast::Location                 &use_loc);

    /**
     * The enumeration type value parameter `p` of the generic `target` is
     * declared with, or null. Its type is bound first, in the generic's
     * declaring scope, if nothing has bound it yet: the generic may be
     * declared after the use (the core library is linked last).
     */
    ast::ISymbolEnumScope *paramEnum(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateValueParamDecl        *p);

private:
    /** Run `f` with the scope that declares `target` as the symbol table. */
    void inDeclScope(
        ast::ISymbolRefPath                 *target,
        const std::function<void()>         &f);

    void bindDefaults(
        ast::ISymbolRefPath                 *target,
        ast::ISymbolTypeScope               *target_c);

private:
    static dmgr::IDebug                     *m_dbg;
    ResolveContext                          *m_ctxt;

};

}
