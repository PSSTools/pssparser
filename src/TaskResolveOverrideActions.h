/*
 * TaskResolveOverrideActions.h
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
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * Resolves the super type of an `override action`, and checks LRM 19.2.2.
 *
 * An override action is a **new action in the declaring component** that
 * implicitly inherits from the same-named action in a base component:
 *
 * @code
 * component base_c { action base_a { } }
 * component inh1_c : base_c { override action base_a { rand int x; } }
 * @endcode
 *
 * `inh1_c::base_a` is a distinct action from `base_c::base_a`; it has `x`,
 * and the base does not. Until this pass existed the construct was built as
 * an `extend action base_a`, which is the opposite: an extension would have
 * added `x` to the base action for every component that uses it.
 *
 * The super type spells the action's **own name**, so it cannot go through
 * the ordinary lookup -- that finds this very declaration and makes the type
 * its own base. Resolution starts from the enclosing component's base chain
 * instead, which is why this runs as a separate pass rather than inside
 * TaskResolveSuperTypes: walking more than one level up requires every
 * component's super type to be resolved already, and that pass is still
 * producing them.
 *
 * The rules checked here, all from LRM 19.2.2:
 *
 * - **a)** an action may be declared override only if a same-named action is
 *   declared in a base component;
 * - **b)** if an override action is declared in a component, a subtype
 *   declaring a same-named action shall also declare it override;
 * - **c)** template actions shall not be overridden.
 */
class TaskResolveOverrideActions : public ast::VisitorBase {
public:
    TaskResolveOverrideActions(ResolveContext *ctxt);

    virtual ~TaskResolveOverrideActions();

    void resolve(ast::IRootSymbolScope *root);

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

private:
    void visitScopeChildren(ast::ISymbolScope *i);

    /**
     * Result of searching a component's base chain for an action by name.
     */
    struct Found {
        ast::ISymbolScope   *scope = 0;  //< the base component that declares it
        ast::ISymbolRefPath *path = 0;   //< a path to the action itself
        ast::IAction        *action = 0;
    };

    /**
     * Search `comp`'s base chain -- not `comp` itself -- for an action named
     * `name`. Returns the nearest one, which is the one being overridden.
     */
    Found findInBaseChain(ast::ISymbolScope *comp, const std::string &name);

    void checkOverride(ast::ISymbolTypeScope *i, ast::IAction *a);

    void checkNotShadowingAnOverride(ast::ISymbolTypeScope *i, ast::IAction *a);

private:
    static dmgr::IDebug                     *m_dbg;
    ResolveContext                          *m_ctxt;
    // The component symbol scope currently being walked, if any. An override
    // action is only meaningful relative to its declaring component.
    std::vector<ast::ISymbolScope *>        m_comp_s;

};

}
