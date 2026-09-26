/**
 * ConstraintScopes.h
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
 */
#pragma once
#include <cstdint>
#include <vector>
#include "pssp/ast/IActivityActionHandleTraversal.h"
#include "pssp/ast/IActivityActionTypeTraversal.h"
#include "pssp/ast/IActivityConstraint.h"
#include "pssp/ast/IConstraintStmtForeach.h"
#include "pssp/ast/IConstraintStmtIf.h"
#include "pssp/ast/IConstraintSymbolScope.h"
#include "pssp/ast/IMonitorConstraint.h"
#include "pssp/ast/IProceduralStmtRandomize.h"

namespace pssp {

/**
 * The nodes that hold a constraint set but are not a constraint scope
 * themselves (SR-F1): an `if` constraint's branches, a traversal's `with`
 * block, an activity or monitor `constraint` statement, and a `randomize`
 * statement's `with` block. A path to a name declared inside one -- a
 * `foreach` iterator -- steps through the owner, then through the body by its
 * position here, which is the body's `index`. The same shape as
 * ProceduralScopes: the owner has no children of its own, and its bodies are
 * its whole address space. ScopeUtil and TaskGetItemIndex recognize an owner
 * by visit, not by a test here: they run on every path step.
 */
class ConstraintScopes {
public:

    /**
     * The bodies, in address order. A missing `else` is a null, left off the
     * end.
     */
    static void bodies(ast::IScopeChild *c, std::vector<ast::IScopeChild *> &out) {
        if (ast::IConstraintStmtIf *s = dynamic_cast<ast::IConstraintStmtIf *>(c)) {
            out.push_back(s->getTrue_c());
            out.push_back(s->getFalse_c());
        } else if (ast::IActivityActionHandleTraversal *s =
                dynamic_cast<ast::IActivityActionHandleTraversal *>(c)) {
            out.push_back(s->getWith_c());
        } else if (ast::IActivityActionTypeTraversal *s =
                dynamic_cast<ast::IActivityActionTypeTraversal *>(c)) {
            out.push_back(s->getWith_c());
        } else if (ast::IActivityConstraint *s = dynamic_cast<ast::IActivityConstraint *>(c)) {
            out.push_back(s->getConstraint());
        } else if (ast::IMonitorConstraint *s = dynamic_cast<ast::IMonitorConstraint *>(c)) {
            out.push_back(s->getConstraint());
        } else if (ast::IProceduralStmtRandomize *s =
                dynamic_cast<ast::IProceduralStmtRandomize *>(c)) {
            for (std::vector<ast::IConstraintStmtUP>::const_iterator
                    it=s->getConstraints().begin(); it!=s->getConstraints().end(); it++) {
                out.push_back(it->get());
            }
        }
    }

    /**
     * How many body statements a `foreach` constraint has. Its iterators are
     * numbered after them: a `foreach` is addressed as "body statements, then
     * iterators", so that a nested scope's index, which is its position in
     * the body, stays what the builder gave it. Zero for any other scope.
     */
    static int32_t iteratorBase(ast::ISymbolScope *s) {
        ast::IConstraintSymbolScope *cs = dynamic_cast<ast::IConstraintSymbolScope *>(s);
        ast::IConstraintStmtForeach *fe = (cs)
            ? dynamic_cast<ast::IConstraintStmtForeach *>(cs->getConstraint()) : 0;
        return (fe) ? (int32_t)fe->getConstraints().size() : 0;
    }

};

} /* namespace pssp */
