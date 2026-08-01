/**
 * TaskResolveSuperTypes.h
 *
 * Copyright 2026 Matthew Ballance and Contributors
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
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * Resolves every type's super-type reference ahead of general name
 * resolution.
 *
 * TaskResolveRefs resolves a type's `super_t` when its walk reaches that
 * type, so a reference to an inherited member resolved correctly only when
 * the base type happened to be visited first. Since the walk follows
 * declaration order, that made inheritance depend on the order files were
 * given to the linker:
 *
 *     pure component base_c { function void m(); }
 *     pure component derived_c : base_c { }
 *     component c { derived_c d; exec init_down { d.m(); } }
 *
 * links clean with the declaring file first and reports "Failed to find elem
 * m" with the using file first. PSS has no declare-before-use rule, so both
 * orders must behave the same.
 *
 * This pass walks scope structure only -- no bodies, no expressions -- and
 * resolves nothing but super-type identifiers. It is deliberately silent:
 * TaskResolveRef reports nothing on failure, and anything left unresolved
 * here is picked up and diagnosed by the main pass exactly as before, so a
 * super type this pass cannot see is a missed optimization rather than a new
 * error. TaskResolveRefs::visitTypeIdentifier already skips a node whose
 * target is set, which is what lets the two passes compose.
 */
class TaskResolveSuperTypes : public ast::VisitorBase {
public:
    TaskResolveSuperTypes(ResolveContext *ctxt);

    virtual ~TaskResolveSuperTypes();

    void resolve(ast::IRootSymbolScope *root);

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    /**
     * A function has no super type, and its body is out of scope for this
     * pass. Overridden so the base visitor does not walk into prototypes,
     * parameter lists and statements.
     */
    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override { }

    /**
     * Extension bodies are merged into their target by
     * TaskApplyTypeExtensions before this runs, so their members are reached
     * through the target. Visiting them here would push a scope that the
     * main pass skips too.
     */
    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override { }

private:
    /// Visit only the scope-shaped children of `i`, ignoring everything else.
    void visitScopeChildren(ast::ISymbolScope *i);

private:
    static dmgr::IDebug         *m_dbg;
    ResolveContext              *m_ctxt;

};

}
