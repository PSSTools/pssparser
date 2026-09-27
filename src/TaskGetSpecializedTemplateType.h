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
#include <map>
#include <set>
#include "dmgr/IDebugMgr.h"
#include "pssp/IFactory.h"
#include "pssp/ast/ICompileCond.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
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

    /**
     * Create the specialization. `use_loc` is the first reference to it,
     * where a `compile assert` it fails is reported.
     */
    ast::ISymbolRefPath *mk(
        const ast::ISymbolRefPath           *type,
        ast::ITemplateParamDeclList         *params,
        const ast::Location                 &use_loc=ast::Location());

    /// Render one bound argument for the specialization's name.
    std::string argName(ast::IDataType *dt);
    std::string argName(ast::IExpr *e);

    std::string mkTypename(
        const ast::ISymbolRefPath           *type,
        ast::ITemplateParamDeclList         *params);

private:
    /**
     * Copy the instance extensions (17.2.6b) that match `params` into the
     * specialization's AST; `members` maps each copy to the scope that
     * declares its extension.
     */
    void applyInstanceExtensions(
        ast::ISymbolTypeScope               *type_up,
        ast::ITypeScope                     *type_s,
        ast::ITemplateParamDeclList         *params,
        std::map<ast::IScopeChild *, ast::ISymbolScope *> &members);

    /**
     * Queue the check of each `compile assert` the builder deferred in the
     * generic's body (8.5): once every reference is bound, a copy of the
     * condition is resolved in the specialization and evaluated there.
     */
    void queueAsserts(
        const ast::ISymbolRefPath           *type,
        ast::ISymbolTypeScope               *type_up,
        ast::ISymbolTypeScope               *type_ss,
        const ast::Location                 &use_loc);

    static void checkAssert(
        ResolveContext                      *ctxt,
        const ast::ISymbolRefPath           *type,
        ast::ISymbolTypeScope               *type_ss,
        ast::ICompileCond                   *cc,
        const ast::Location                 &use_loc);

private:
    static dmgr::IDebug                 *m_dbg;
    ResolveContext                      *m_ctxt;
};

}
