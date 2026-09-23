/**
 * ActivityScopes.h
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
#include "pssp/ast/IActivityAtomicBlock.h"
#include "pssp/ast/IActivityDecl.h"
#include "pssp/ast/IActivityForeach.h"
#include "pssp/ast/IActivityIfElse.h"
#include "pssp/ast/IActivityLabeledScope.h"
#include "pssp/ast/IActivityMatch.h"
#include "pssp/ast/IActivityMatchChoice.h"
#include "pssp/ast/IActivityRepeatCount.h"
#include "pssp/ast/IActivityRepeatWhile.h"
#include "pssp/ast/IActivityReplicate.h"
#include "pssp/ast/IActivitySelect.h"
#include "pssp/ast/IActivitySelectBranch.h"
#include "pssp/ast/IMonitorActivityDecl.h"
#include "pssp/ast/IMonitorActivityEventually.h"
#include "pssp/ast/IMonitorActivityLabeledScope.h"

namespace pssp {

/**
 * The activity scope model (symbol-resolution plan WS4.1, LRM 11.8.2).
 *
 * Every activity block is a scope, and so is every compound statement. A
 * compound statement's children are the variables it declares (a loop index
 * or iterator); its bodies are data fields, addressed after the children:
 * body `k` is child index `children.size() + k`. That is what makes a block
 * nested in a loop or an `if` reachable by symbol path.
 *
 * Deliberately not a visitor. The generated visitors descend into a scope's
 * data fields after visiting the scope itself, so a visitor asked "what is
 * this node?" of a compound statement goes on to answer for its bodies too --
 * the failure TaskGetSymbolScope, TaskGetItemIndex and ScopeUtil each
 * document for the procedural loops and the template scopes. The query
 * visitors call these first instead.
 */
class ActivityScopes {
public:

    /**
     * `c` as a symbol scope if it is an activity scope -- a declaration, a
     * block or a compound statement, on the action or the monitor side --
     * and null otherwise.
     */
    static ast::ISymbolScope *asScope(ast::IScopeChild *c) {
        if (dynamic_cast<ast::IActivityLabeledScope *>(c)
                || dynamic_cast<ast::IActivityDecl *>(c)
                || dynamic_cast<ast::IMonitorActivityLabeledScope *>(c)
                || dynamic_cast<ast::IMonitorActivityDecl *>(c)) {
            return dynamic_cast<ast::ISymbolScope *>(c);
        }
        return 0;
    }

    /**
     * The bodies of a compound statement, in address order. A missing body
     * (an `if` with no `else`) keeps its slot as a null, so that the index of
     * every other body does not depend on it. Empty for a block.
     */
    static void bodies(ast::IScopeChild *c, std::vector<ast::IScopeChild *> &out) {
        if (ast::IActivityRepeatCount *s = dynamic_cast<ast::IActivityRepeatCount *>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityRepeatWhile *s = dynamic_cast<ast::IActivityRepeatWhile *>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityForeach *s = dynamic_cast<ast::IActivityForeach *>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityReplicate *s = dynamic_cast<ast::IActivityReplicate *>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityAtomicBlock *s = dynamic_cast<ast::IActivityAtomicBlock *>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityIfElse *s = dynamic_cast<ast::IActivityIfElse *>(c)) {
            out.push_back(s->getTrue_s());
            out.push_back(s->getFalse_s());
        } else if (ast::IActivitySelect *s = dynamic_cast<ast::IActivitySelect *>(c)) {
            for (std::vector<ast::IActivitySelectBranchUP>::const_iterator
                it=s->getBranches().begin(); it!=s->getBranches().end(); it++) {
                out.push_back((*it)->getBody());
            }
        } else if (ast::IActivityMatch *s = dynamic_cast<ast::IActivityMatch *>(c)) {
            for (std::vector<ast::IActivityMatchChoiceUP>::const_iterator
                it=s->getChoices().begin(); it!=s->getChoices().end(); it++) {
                out.push_back((*it)->getBody());
            }
        } else if (ast::IMonitorActivityEventually *s =
                dynamic_cast<ast::IMonitorActivityEventually *>(c)) {
            out.push_back(s->getBody());
        }
    }

};

} /* namespace pssp */
