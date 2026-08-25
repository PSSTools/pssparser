/**
 * TaskCheckCallArgs.h
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
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IScopeChild.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * Checks a call site against the signature(s) of the function it resolved to.
 *
 * Every call in the AST -- statement or expression, plain or method -- is an
 * `ExprMemberPathElem` carrying a non-null `params` list. Once the resolver has
 * mapped that element onto a declaration, this task compares the number of
 * arguments supplied against the arity the declaration accepts.
 *
 * Argument *categories* are then checked against the declared parameter types,
 * using `TaskExprTypeCat`. That is a coarser thing than a type: it catches a
 * string where a number belongs and an aggregate literal where a scalar
 * belongs, but says nothing about widths, signedness, or which struct a value
 * came from. Anything it cannot classify is left alone.
 */
class TaskCheckCallArgs {
public:
    TaskCheckCallArgs(ResolveContext *ctxt);

    virtual ~TaskCheckCallArgs();

    /**
     * Check `elem` -- a path element with an argument list -- against `target`,
     * the declaration it resolved to. A no-op unless `elem` is a call and
     * `target` is something with a signature.
     */
    void check(
        ast::IScopeChild            *target,
        ast::IExprMemberPathElem    *elem);

private:
    /** Gathers every signature `target` offers, in declaration order. */
    void collectPrototypes(
        ast::IScopeChild                            *target,
        std::vector<ast::IFunctionPrototype *>      &protos);

    /** The [min,max] argument count `proto` accepts; max is -1 for varargs. */
    static void arity(
        ast::IFunctionPrototype     *proto,
        int32_t                     &min,
        int32_t                     &max);

    /** Renders "expects 1 argument" / "expects 1 to 2 arguments" / etc. */
    static std::string expectation(int32_t min, int32_t max);

    /**
     * Names what `target` is if it is unambiguously a *value* -- "a field",
     * "a variable", "a parameter" -- and so cannot be called. Null for
     * anything else, including anything the resolver models loosely.
     */
    static const char *valueKind(ast::IScopeChild *target);

    /**
     * Compares each argument's type category against the parameter it lands
     * on. Only called when exactly one signature is in play -- with an overload
     * set there is no single parameter list to compare against.
     */
    void checkArgTypes(
        ast::IFunctionPrototype     *proto,
        ast::IExprMemberPathElem    *elem);

private:
    static dmgr::IDebug             *m_dbg;
    ResolveContext                  *m_ctxt;

};

}
