/**
 * TaskCheckTypeCycles.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskCheckTypeCycles.h"
#include "TaskResolveSuperTypeRef.h"
#include "pssp/ast/ITypeScope.h"

namespace pssp {

TaskCheckTypeCycles::TaskCheckTypeCycles(ResolveContext *ctxt) :
        m_ctxt(ctxt), m_root(0) {
    DEBUG_INIT("pssp::TaskCheckTypeCycles", ctxt->getDebugMgr());
}

TaskCheckTypeCycles::~TaskCheckTypeCycles() { }

void TaskCheckTypeCycles::check(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("check");
    m_root = root;
    m_reported.clear();
    m_checked.clear();
    visitScopeChildren(root);
    DEBUG_LEAVE("check");
}

void TaskCheckTypeCycles::visitScopeChildren(ast::ISymbolScope *i) {
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        if (dynamic_cast<ast::ISymbolScope *>(it->get())) {
            it->get()->accept(m_this);
        }
    }
}

void TaskCheckTypeCycles::visitSymbolScope(ast::ISymbolScope *i) {
    visitScopeChildren(i);
}

void TaskCheckTypeCycles::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    checkChain(i);

    // A nested type (an action inside a component, a struct inside a package)
    // is reached through its enclosing scope, so the walk continues even
    // after this type's own chain has been checked.
    visitScopeChildren(i);
}

void TaskCheckTypeCycles::checkChain(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());

    if (!ts || !ts->getSuper_t()) {
        return;
    }

    // The chain as a set, for the "have I been here" question, and as a
    // sequence, for the message. Both are needed: the set answers in one step
    // and the sequence is what makes the report actionable -- "cyclic
    // inheritance" without the loop leaves the user to find it.
    std::set<ast::IScopeChild *>        on_chain;
    std::vector<ast::IScopeChild *>     order;

    ast::IScopeChild *cur = i;
    on_chain.insert(cur);
    order.push_back(cur);

    TaskResolveSuperTypeRef resolver(m_ctxt->getDebugMgr(), m_root);

    while (true) {
        ast::ISymbolTypeScope *cur_sym = dynamic_cast<ast::ISymbolTypeScope *>(cur);
        ast::ITypeScope *cur_ts = cur_sym
            ? dynamic_cast<ast::ITypeScope *>(cur_sym->getTarget())
            : dynamic_cast<ast::ITypeScope *>(cur);

        if (!cur_ts) {
            return;         // not a type scope: nothing inherits from here
        }

        ast::IScopeChild *super = resolver.resolve(cur_ts);

        if (!super) {
            // No super type, or one that did not resolve. An unresolved base
            // is diagnosed by TaskCheckRefsResolved, which describes it far
            // better than this pass could -- reporting it here as well would
            // give one mistake two unrelated messages.
            break;
        }

        if (m_checked.count(super)) {
            // Everything above `super` has already been walked, from some
            // earlier starting point, and any ring up there was reported
            // then. Without this the pass is quadratic: every type in an
            // N-deep chain re-walks the whole chain above it, which is
            // unnoticeable at the depth real models use and 6s at N=5000.
            break;
        }

        if (!on_chain.insert(super).second) {
            // Closed the ring. Report unless some other starting point in the
            // same ring already did.
            if (m_reported.count(super)) {
                break;
            }

            std::string path;
            bool in_loop = false;
            for (std::vector<ast::IScopeChild *>::const_iterator
                it=order.begin(); it!=order.end(); it++) {
                // A chain can run into a ring without being part of it
                // (`C : B` where `A : B` and `B : A`). Only the ring belongs
                // in the message; the lead-in is where the user is standing,
                // not what is wrong.
                if (!in_loop && *it != super) {
                    continue;
                }
                in_loop = true;
                m_reported.insert(*it);
                if (!path.empty()) {
                    path += "' -> '";
                }
                path += nameOf(*it);
            }
            path += "' -> '" + nameOf(super);

            m_ctxt->addErrorMarker(
                i->getLocation(),
                "cyclic inheritance: '%s'",
                path.c_str());
            break;
        }

        order.push_back(super);
        cur = super;
    }

    // Every type on this chain has now been walked to its end, so no later
    // starting point needs to walk it again -- see the m_checked test above.
    // Recorded on the reporting path too: a ring explored once is a ring
    // explored, and re-deriving it would only produce the report this pass
    // deliberately suppresses.
    m_checked.insert(order.begin(), order.end());
}

std::string TaskCheckTypeCycles::nameOf(ast::IScopeChild *c) {
    if (ast::ISymbolTypeScope *sym = dynamic_cast<ast::ISymbolTypeScope *>(c)) {
        return sym->getName();
    } else if (ast::ISymbolScope *sc = dynamic_cast<ast::ISymbolScope *>(c)) {
        return sc->getName();
    } else if (ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(c)) {
        if (ts->getName()) {
            return ts->getName()->getId();
        }
    }
    return "<anonymous>";
}

dmgr::IDebug *TaskCheckTypeCycles::m_dbg = 0;

}
