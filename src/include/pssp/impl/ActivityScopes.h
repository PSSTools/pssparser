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
#include "pssp/impl/NodeKind.h"

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
 * Not built on the generated visitors, which descend into a scope's data
 * fields after visiting the scope itself: a visitor asked "what is this
 * node?" of a compound statement goes on to answer for its bodies too -- the
 * failure TaskGetSymbolScope, TaskGetItemIndex and ScopeUtil each document
 * for the procedural loops and the template scopes. The query visitors call
 * these first instead. NodeKind classifies without descending.
 */
class ActivityScopes {
public:

    /**
     * `c` as a symbol scope if it is an activity scope -- a declaration, a
     * block or a compound statement, on the action or the monitor side --
     * and null otherwise.
     */
    static ast::ISymbolScope *asScope(ast::IScopeChild *c) {
        NodeKind nk(c);
        return (nk.is<ast::IActivityLabeledScope>() || nk.is<ast::IActivityDecl>()
                || nk.is<ast::IMonitorActivityLabeledScope>()
                || nk.is<ast::IMonitorActivityDecl>())
            ? nk.as<ast::ISymbolScope>() : 0;
    }

    /**
     * The bodies of a compound statement, in address order. A missing body
     * (an `if` with no `else`) keeps its slot as a null, so that the index of
     * every other body does not depend on it. Empty for a block.
     */
    static void bodies(ast::IScopeChild *c, std::vector<ast::IScopeChild *> &out) {
        if (ast::IActivityRepeatCount *s = NodeKind::cast<ast::IActivityRepeatCount>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityRepeatWhile *s = NodeKind::cast<ast::IActivityRepeatWhile>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityForeach *s = NodeKind::cast<ast::IActivityForeach>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityReplicate *s = NodeKind::cast<ast::IActivityReplicate>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityAtomicBlock *s = NodeKind::cast<ast::IActivityAtomicBlock>(c)) {
            out.push_back(s->getBody());
        } else if (ast::IActivityIfElse *s = NodeKind::cast<ast::IActivityIfElse>(c)) {
            out.push_back(s->getTrue_s());
            out.push_back(s->getFalse_s());
        } else if (ast::IActivitySelect *s = NodeKind::cast<ast::IActivitySelect>(c)) {
            for (std::vector<ast::IActivitySelectBranchUP>::const_iterator
                it=s->getBranches().begin(); it!=s->getBranches().end(); it++) {
                out.push_back((*it)->getBody());
            }
        } else if (ast::IActivityMatch *s = NodeKind::cast<ast::IActivityMatch>(c)) {
            for (std::vector<ast::IActivityMatchChoiceUP>::const_iterator
                it=s->getChoices().begin(); it!=s->getChoices().end(); it++) {
                out.push_back((*it)->getBody());
            }
        } else if (ast::IMonitorActivityEventually *s =
                NodeKind::cast<ast::IMonitorActivityEventually>(c)) {
            out.push_back(s->getBody());
        }
    }

    /**
     * The child indices that lead from activity scope `from` down to `target`,
     * a statement or declaration somewhere in its blocks and bodies, in the
     * addressing above. False if `target` is not under `from`. Used for a
     * name found in a named sub-activity (WS4.3), which is addressed where it
     * is written.
     */
    static bool pathTo(
            ast::IScopeChild            *from,
            ast::IScopeChild            *target,
            std::vector<int32_t>        &idx) {
        ast::ISymbolScope *s = asScope(from);
        if (!s) {
            return false;
        }
        int32_t i = 0;
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin(); it!=s->getChildren().end(); it++, i++) {
            if (step(it->get(), i, target, idx)) {
                return true;
            }
        }
        std::vector<ast::IScopeChild *> b;
        bodies(from, b);
        for (std::vector<ast::IScopeChild *>::const_iterator
            it=b.begin(); it!=b.end(); it++, i++) {
            if (*it && step(*it, i, target, idx)) {
                return true;
            }
        }
        return false;
    }

private:

    static bool step(
            ast::IScopeChild            *c,
            int32_t                     i,
            ast::IScopeChild            *target,
            std::vector<int32_t>        &idx) {
        idx.push_back(i);
        if (c == target || pathTo(c, target, idx)) {
            return true;
        }
        idx.pop_back();
        return false;
    }

};

} /* namespace pssp */
