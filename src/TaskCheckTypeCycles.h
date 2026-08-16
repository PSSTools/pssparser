/**
 * TaskCheckTypeCycles.h
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
#include <set>
#include <string>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * Rejects a type that inherits, directly or transitively, from itself.
 *
 *     struct A : B { };
 *     struct B : A { };        // error: cyclic inheritance: 'A' -> 'B' -> 'A'
 *
 * WHY THIS IS ITS OWN PASS.
 *
 * A ring in the inheritance graph is illegal PSS, and until this pass existed
 * nothing said so: a model containing one linked with `0 errors` whenever no
 * name happened to be looked up through it. That silence was the smaller half
 * of the problem. The larger half is that every walk over the super-type
 * chain -- TaskFindPathElem's member search, and anything that asks what a
 * type inherits -- terminates only because the chain ends, and a ring means
 * it does not. The member search reached the ring on the first *failed*
 * lookup against a participating type and overflowed the stack: a typo turned
 * into a segfault with no diagnostic.
 *
 * Those walkers now carry their own loop guards, so this pass is not what
 * keeps the parser alive. It is what tells the user why their model is
 * wrong. Both are needed and neither substitutes for the other: a guard
 * without this pass silently accepts an illegal model, and this pass without
 * the guards leaves every walker one unchecked path away from the crash
 * again.
 *
 * WHERE IT RUNS. After TaskResolveSuperTypes, which is what binds the
 * references this pass follows, and before TaskResolveRefs, which is the pass
 * that would otherwise walk the ring. Reporting a cycle does not stop the
 * link -- the guards make the rest of resolution safe, and stopping early
 * would hide every other diagnostic in the file behind one bad base type.
 *
 * ONE REPORT PER CYCLE, not one per participant: `A -> B -> C -> A` is a
 * single mistake, and naming it three times from three starting points says
 * nothing extra. The report is anchored at whichever member the walk reached
 * first, and the message names the whole loop, so it is actionable wherever
 * it lands.
 */
class TaskCheckTypeCycles : public ast::VisitorBase {
public:
    TaskCheckTypeCycles(ResolveContext *ctxt);

    virtual ~TaskCheckTypeCycles();

    void check(ast::IRootSymbolScope *root);

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    /**
     * A function scope has no super type and cannot participate. Overridden
     * so the base visitor does not descend into prototypes and bodies, which
     * this pass has no business reading.
     */
    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override { }

    /**
     * Extension bodies have already been merged into their targets by
     * TaskApplyTypeExtensions, so an `extend`-supplied super type is reached
     * through the target and checked there. Visiting the extension as well
     * would report the same ring twice.
     */
    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override { }

private:
    /// Visit only the scope-shaped children of `i`, as TaskResolveSuperTypes does.
    void visitScopeChildren(ast::ISymbolScope *i);

    /**
     * Walk the super chain from `i`, reporting if it returns to a type
     * already on it.
     */
    void checkChain(ast::ISymbolTypeScope *i);

    static std::string nameOf(ast::IScopeChild *c);

private:
    static dmgr::IDebug                 *m_dbg;
    ResolveContext                      *m_ctxt;
    ast::IRootSymbolScope               *m_root;

    /// Participants in an already-reported ring; see "one report per cycle".
    std::set<ast::IScopeChild *>        m_reported;

    /**
     * Types whose super chain has already been walked to its end.
     *
     * Without it the pass is quadratic in chain depth -- each of N types
     * re-walks the N above it. Irrelevant at the depth real models use and
     * six seconds at N=5000, which is the kind of cost that gets a check
     * turned off rather than fixed.
     */
    std::set<ast::IScopeChild *>        m_checked;

};

}
