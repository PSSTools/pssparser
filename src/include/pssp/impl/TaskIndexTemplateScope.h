/**
 * TaskIndexTemplateScope.h
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
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/ITemplateString.h"
#include "pssp/ast/ITemplateElem.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/ScopeUtil.h"

namespace pssp {

/**
 * Numbers the template scopes (4.7.1) belonging to a symbol scope.
 *
 * A `SymbolRefPath` addresses a symbol as a chain of child indices, but a
 * TemplateString is not a child of anything in the symbol tree -- it hangs off
 * an exec block or an expression -- so no `ElemKind_ChildIdx` can name it. It
 * must not become a child either: hoisting template scopes into the enclosing
 * scope's children is what made every diagnostic inside a template appear three
 * times.
 *
 * `ElemKind_TemplateScope` names one positionally instead, and this is what
 * defines that position: a pre-order walk of the enclosing scope, counting
 * every template scope it meets and stopping at any *other* symbol scope --
 * whose own templates are numbered relative to it, one path element further on.
 *
 * Nothing is stored, which is the point. An index recorded on a symbol path and
 * an index resolved from one are produced by this same walk, so they agree by
 * construction rather than by bookkeeping that a later copy could drop (as
 * TaskCopyAst does with any field it does not explicitly carry).
 */
class TaskIndexTemplateScope : public virtual ast::VisitorBase {
public:

    virtual ~TaskIndexTemplateScope() { }

    /**
     * Position of `target` among `scope`'s template scopes, or -1 when it is
     * not one of them -- which is the answer whenever a template sits somewhere
     * this walk cannot reach, and is why an unaddressable template yields an
     * unresolvable path rather than a plausible wrong one.
     */
    int32_t index(ast::IScopeChild *scope, ast::IScopeChild *target) {
        enumerate(scope);

        for (uint32_t i=0; i<m_scopes.size(); i++) {
            if (m_scopes.at(i) == target) {
                return (int32_t)i;
            }
        }

        return -1;
    }

    /**
     * The `idx`'th template scope of `scope`, or null if there is no such one.
     */
    ast::IScopeChild *get(ast::IScopeChild *scope, int32_t idx) {
        if (idx < 0) {
            return 0;
        }

        enumerate(scope);

        return (idx < (int32_t)m_scopes.size())?m_scopes.at(idx):0;
    }

    virtual void visitTemplateString(ast::ITemplateString *i) override {
        m_scopes.push_back(i);
        // Explicitly, rather than through the generated visitor: that one
        // routes through visitSymbolScope, which the children walk below treats
        // as a boundary.
        for (std::vector<ast::ITemplateElemUP>::const_iterator
            it=i->getElems().begin();
            it!=i->getElems().end(); it++) {
            (*it)->accept(m_this);
        }
    }

    // Every other template scope funnels through here -- the generated
    // visitTemplateBlock, visitTemplateIf and visitTemplateExpr all call it
    // before descending, so a nested block is counted once and then walked.
    virtual void visitTemplateElem(ast::ITemplateElem *i) override {
        m_scopes.push_back(i);
    }

private:

    void enumerate(ast::IScopeChild *scope) {
        m_scopes.clear();

        ScopeUtil su(scope);

        if (!su.valid()) {
            return;
        }

        int32_t n = su.getNumChildren();

        for (int32_t i=0; i<n; i++) {
            ast::IScopeChild *c = su.getChild(i);

            if (c && !isBoundary(c)) {
                c->accept(m_this);
            }
        }
    }

    /**
     * A symbol scope of its own -- an exec block, a nested type, a function --
     * so it gets a path element of its own and its templates are numbered
     * relative to it.
     */
    static bool isBoundary(ast::IScopeChild *c) {
        return dynamic_cast<ast::ISymbolScope *>(c) != 0 &&
            dynamic_cast<ast::ITemplateString *>(c) == 0 &&
            dynamic_cast<ast::ITemplateElem *>(c) == 0;
    }

private:
    std::vector<ast::IScopeChild *>     m_scopes;

};

} /* namespace pssp */
