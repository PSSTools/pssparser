/**
 * TaskResolveSuperTypeRef.h
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
#include "pssp/ast/ITypeScope.h"
#include "pssp/ast/IDataTypeUserDefined.h"
#include "pssp/ast/ITemplateGenericTypeParamDecl.h"
#include "pssp/ast/ITemplateCategoryTypeParamDecl.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {

/**
 * Resolves a type's super-type reference to the scope it names.
 *
 * The reason this is not just a ``TaskResolveSymbolPathRef`` call: a generic
 * may inherit from one of its own type parameters.
 *
 * @code
 * struct S<type T> : T { }
 * @endcode
 *
 * In the specialization ``S<base_s>`` the super-type reference still spells
 * ``T``, and resolving it lands on the **parameter declaration**, which has no
 * members of its own. Every site that walked the chain therefore stopped
 * there, and every inherited member was invisible -- to member lookup
 * (``s.zork``), to unqualified lookup inside the body, and to the subtype test
 * a category parameter's restriction performs.
 *
 * On a specialized parameter list the ``dflt`` slot holds the bound argument,
 * so the binding is one more hop away. This class takes that hop, repeatedly:
 * a parameter may be bound to a parameter of a further enclosing generic.
 *
 * A parameter with nothing bound yields null -- the same answer an
 * unresolvable super type gives, and one every caller already handles. On an
 * *unspecialized* generic the ``dflt`` slot holds the declared default rather
 * than a binding, but an unspecialized generic's body is never resolved, so
 * that case does not arise in practice.
 */
class TaskResolveSuperTypeRef {
public:
    TaskResolveSuperTypeRef(
        dmgr::IDebugMgr             *dmgr,
        ast::ISymbolChildrenScope   *root) : m_dmgr(dmgr), m_root(root) { }

    virtual ~TaskResolveSuperTypeRef() { }

    /**
     * The scope named by ``ts``'s super-type reference, or null when ``ts``
     * has no super type, the reference did not resolve, or it names a
     * parameter that is not bound.
     */
    ast::IScopeChild *resolve(ast::ITypeScope *ts) {
        if (!ts || !ts->getSuper_t()) {
            return 0;
        }
        return follow(TaskResolveSymbolPathRef(m_dmgr, m_root).resolve(
            ts->getSuper_t()->getTarget()));
    }

    /**
     * Map an already-resolved reference through any parameter bindings.
     *
     * Exposed separately for callers that have the resolved node in hand.
     */
    ast::IScopeChild *follow(ast::IScopeChild *sc) {
        // The bound depth is a loop guard, not a real limit: a parameter
        // bound to itself would otherwise spin here.
        for (uint32_t depth=0; sc && depth<32; depth++) {
            ast::IDataType *bound = 0;
            if (ast::ITemplateGenericTypeParamDecl *g =
                    dynamic_cast<ast::ITemplateGenericTypeParamDecl *>(sc)) {
                bound = g->getDflt();
            } else if (ast::ITemplateCategoryTypeParamDecl *c =
                    dynamic_cast<ast::ITemplateCategoryTypeParamDecl *>(sc)) {
                // Arguments are specialized as generic parameters, so this
                // arm is reached only for a declaration that still carries
                // its category -- but reading the same slot costs nothing and
                // keeps the two kinds from behaving differently.
                bound = c->getDflt();
            } else {
                return sc;
            }

            ast::IDataTypeUserDefined *ud =
                dynamic_cast<ast::IDataTypeUserDefined *>(bound);
            if (!ud || !ud->getType_id()) {
                // Unbound, or bound to something that is not a type
                // reference -- `S<int> : T` is not inheritable either way.
                return 0;
            }
            sc = TaskResolveSymbolPathRef(m_dmgr, m_root).resolve(
                ud->getType_id()->getTarget());
        }
        return sc;
    }

private:
    dmgr::IDebugMgr             *m_dmgr;
    ast::ISymbolChildrenScope   *m_root;
};

}
