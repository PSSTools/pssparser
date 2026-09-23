/**
 * ProceduralScopes.h
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
#include <vector>
#include "pssp/ast/IProceduralStmtBody.h"
#include "pssp/ast/IProceduralStmtIfClause.h"
#include "pssp/ast/IProceduralStmtIfElse.h"
#include "pssp/ast/IProceduralStmtMatch.h"
#include "pssp/ast/IProceduralStmtMatchChoice.h"

namespace pssp {

/**
 * Procedural compound statements that declare nothing (symbol-resolution
 * plan 4.1b): `if`/`else`, `match`, `while` and `repeat`...`while`.
 *
 * They are not symbol scopes -- they have no variables -- but a block in one
 * of their bodies is, and a path to a name in that block has to step through
 * the statement to reach it. So the statement is a path element: its index
 * in the enclosing scope, then body `k` at index `k`. The bodies are numbered
 * by AstBuilderInt: an `if`'s clauses in order and then its `else`, a
 * `match`'s choices in order, and the single body of a loop.
 *
 * `repeat` and `foreach` are not here: they declare their loop variables, so
 * they are symbol scopes, with the body after the variables.
 *
 * Deliberately not a visitor, for the reason ActivityScopes gives: the
 * generated visitors descend into the bodies and answer for them instead.
 */
class ProceduralScopes {
public:

    static bool isCompound(ast::IScopeChild *c) {
        return dynamic_cast<ast::IProceduralStmtIfElse *>(c)
            || dynamic_cast<ast::IProceduralStmtMatch *>(c)
            || dynamic_cast<ast::IProceduralStmtBody *>(c);
    }

    /**
     * The bodies of a compound statement, in address order. A missing body
     * (an empty statement, or an `if` with no `else`) is a null, or is left
     * off the end.
     */
    static void bodies(ast::IScopeChild *c, std::vector<ast::IScopeChild *> &out) {
        if (ast::IProceduralStmtIfElse *s = dynamic_cast<ast::IProceduralStmtIfElse *>(c)) {
            for (std::vector<ast::IProceduralStmtIfClauseUP>::const_iterator
                it=s->getIf_then().begin(); it!=s->getIf_then().end(); it++) {
                out.push_back((*it)->getBody());
            }
            out.push_back(s->getElse_then());
        } else if (ast::IProceduralStmtMatch *s = dynamic_cast<ast::IProceduralStmtMatch *>(c)) {
            for (std::vector<ast::IProceduralStmtMatchChoiceUP>::const_iterator
                it=s->getChoices().begin(); it!=s->getChoices().end(); it++) {
                out.push_back((*it)->getBody());
            }
        } else if (ast::IProceduralStmtBody *s = dynamic_cast<ast::IProceduralStmtBody *>(c)) {
            out.push_back(s->getBody());
        }
    }

};

} /* namespace pssp */
