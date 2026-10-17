/**
 * TaskCheckOperands.h
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
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "ResolveContext.h"
#include "TaskExprTypeCat.h"

namespace pssp {

/**
 * Rules on the types of operands, arguments and function signatures, judged
 * with the expression typer (TaskExprTypeCat::typeOf) after resolution --
 * pssc's 06-front-end-checks group 3:
 *
 * - a cast from a chandle, struct, string or collection, or to a struct or
 *   collection type (7.12, 7.12.1) -- PSS126;
 * - an `in` with a range list whose left side is not a scalar, or is an
 *   aggregate literal (8.5.9.1) -- PSS127;
 * - `==`/`!=` or assignment of arrays of components or actions (7.9.2)
 *   -- PSS128;
 * - an array argument of another size than its array parameter (8.3,
 *   20.3.2) -- PSS006;
 * - a function returning, or taking, a component, action, or flow or
 *   resource object type without `ref` (20.2.2) -- PSS129.
 *
 * Nothing is reported where an operand's type is not known.
 */
class TaskCheckOperands : public virtual ast::VisitorBase {
public:
    TaskCheckOperands(ResolveContext *ctxt);

    virtual ~TaskCheckOperands();

    void check(ast::IRootSymbolScope *root);

    virtual void visitExecStmt(ast::IExecStmt *i) override;

    virtual void visitConstraintStmt(ast::IConstraintStmt *i) override;

    virtual void visitExprCast(ast::IExprCast *i) override;

    virtual void visitExprIn(ast::IExprIn *i) override;

    virtual void visitExprBin(ast::IExprBin *i) override;

    virtual void visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

private:
    /** Where to report on `e`: its first located identifier, else the
     *  statement being checked. */
    ast::Location locOf(ast::IExpr *e);

    void checkCalls(const std::vector<ast::IExprMemberPathElemUP> &elems,
        ast::IScopeChild *first_decl);

    void checkArraySizes(ast::IExprMemberPathElem *elem, ast::ISymbolFunctionScope *fn);

    /** An array of components or actions: `t` itself, or `t`'s elements. */
    bool isModelingArray(const ExprType &t);

    /** The value type `t` is not allowed as without `ref` (20.2.2), or null. */
    const char *needsRef(const ExprType &t);

private:
    static dmgr::IDebug                 *m_dbg;
    ResolveContext                      *m_ctxt;
    TaskExprTypeCat                     m_typer;
    ast::Location                       m_stmt_loc;
};

}
