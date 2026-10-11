/**
 * TaskTemplateCheck.h
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
#include <map>
#include <set>
#include <string>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IExpr.h"
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IScopeChild.h"
#include "pssp/ast/ITemplateElem.h"
#include "pssp/ast/ITemplateString.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * Post-resolution checks over one triple-quoted template string (§4.7).
 *
 * Runs after every expression under the template has been resolved, because
 * all three things it does need to know what a reference *resolved to*:
 *
 * - `is_const` -- §4.7: a template whose special elements reference only
 *   constant expressions is itself constant, and one that does not cannot be
 *   used where a constant string is required (PSS115, raised at the point of
 *   use rather than here).
 * - **PSS113** -- §4.7.1.1 requires a mustache expression to be of scalar
 *   type. Classification is `TaskExprTypeCat`, which answers Unknown far more
 *   often than it answers wrong; nothing is reported for Unknown.
 *
 * PSS114 (non-pure call) is *not* here: purity has to be checked where the
 * callee is resolved, which for a method call is inside the ref-path walk. It
 * lives in TaskResolveRefs, gated on being inside a template.
 */
class TaskTemplateCheck {
public:
    TaskTemplateCheck(ResolveContext *ctxt);

    virtual ~TaskTemplateCheck();

    /** Sets `is_const` on `t` and reports PSS113 against its mustaches. */
    void check(ast::ITemplateString *t);

    /**
     * PSS114 -- §4.7.1.1: "any function called shall be pure".
     *
     * Reports when `target` is a function and *no* signature it offers is
     * declared `pure`. Silent when the call resolved to nothing with a
     * signature: an unresolved callee is already someone else's diagnostic,
     * and guessing would double-report it.
     */
    void checkPure(
        ast::IScopeChild            *target,
        ast::IExprMemberPathElem    *elem);

private:
    /** Walks a list of elements in source order. */
    void elems(const std::vector<ast::ITemplateElemUP> &elems);

    void elem(ast::ITemplateElem *e);

    /**
     * True when `e` references only constants. Contributes to the template's
     * `is_const` as a side effect. A non-null `loc` marks a mustache
     * expression and enables PSS113, reported at that location -- ast::IExpr
     * carries none of its own.
     */
    bool expr(ast::IExpr *e, const ast::Location *loc);

    /**
     * Records the loop variables a foreach/repeat block introduces, and their
     * constness -- which is the collection's, since that is where their values
     * come from.
     */
    void loopVars(ast::ITemplateBlock *b, bool is_const);

    /** Records one template-local declaration under its name. */
    void addLocal(ast::IScopeChild *decl);

    /** The local declaration a `{% x = ...; %}` targets, or null. */
    ast::IScopeChild *assignTarget(ast::ITemplateAssign *a);

    /**
     * Records `decl` -- a template-local declaration -- as non-constant, so
     * that later references to it are non-constant too. The template as a
     * whole stops being constant either way.
     */
    void markNonConst(ast::IScopeChild *decl);

private:
    static dmgr::IDebug             *m_dbg;
    ResolveContext                  *m_ctxt;
    bool                            m_is_const;

    /**
     * Every declaration this template introduces -- `{% int x; %}` variables
     * plus foreach/repeat loop variables -- keyed by name.
     *
     * By name because a reference to a template local cannot be resolved
     * through its symbol path: the symbol tree does not hoist template scopes,
     * so the path addresses the enclosing type and lands on an unrelated node
     * (known issue P5-X2). A later declaration of the same name replaces an
     * earlier one, matching the order a reference resolves in.
     */
    std::map<std::string, ast::IScopeChild *>   m_locals;

    /**
     * Template locals whose value derives from something non-constant: a
     * `{% int x = a; %}` over a rand field, a `{% x = a; %}` assignment, or a
     * loop variable over a non-constant collection. Keyed by declaration
     * identity rather than by name, so that a variable shadowed in a nested
     * block does not inherit the outer one's verdict.
     */
    std::set<ast::IScopeChild *>    m_nonconst;

};

}
