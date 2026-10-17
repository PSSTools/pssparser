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
 *   resource object type without `ref` (20.2.2) -- PSS129;
 * - an operand of a type its operator does not take (8.4 Table 10, 8.3
 *   Table 9, 7.7 for a chandle) -- PSS131;
 * - a condition that is not Boolean (20.7.9, 20.7.7 a, 8.5.8) -- PSS132;
 * - `null` assigned to what is not a reference (8.3) -- PSS133;
 * - enum item values: duplicates, outside the base type, an implicit value
 *   past its greatest, a base type with a domain (7.5.1 c, e) -- PSS134;
 * - a variable of an enum with no items (7.5.1 j) -- PSS135;
 * - a generic or varargs parameter of a user-written function (20.2.5,
 *   ruling R23) -- PSS136;
 * - an import or export parameter or result of a type the foreign mapping
 *   does not take, and an export's non-const struct parameter (20.4.1 c,
 *   20.4.2.1) -- PSS137.
 *
 * Enumeration operands are left alone by PSS131: 7.5.1 permits an enum in
 * assignment and equality ("may be used"), and says nothing stronger.
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

    virtual void visitExprUnary(ast::IExprUnary *i) override;

    virtual void visitExprCond(ast::IExprCond *i) override;

    virtual void visitProceduralStmtIfClause(ast::IProceduralStmtIfClause *i) override;

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) override;

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) override;

    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitFunctionImportProto(ast::IFunctionImportProto *i) override;

    virtual void visitFunctionImportType(ast::IFunctionImportType *i) override;

    virtual void visitExportFunction(ast::IExportFunction *i) override;

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

    /** What an operator takes (Table 10). */
    enum class Opd { Numeric, Integer, Boolean };

    /** True when `t` is known not to be an operand of class `c`. */
    static bool badOperand(const ExprType &t, Opd c);

    /** Report the first operand of `op` that is not of class `c`. */
    bool checkOperands(const char *op, Opd c, const char *clause,
        ast::IExpr *a, ast::IExpr *b=0);

    void checkCondition(const char *what, const char *clause, ast::IExpr *cond);

    void checkNullInit(const ExprType &target, ast::IExpr *value);

    /** An integer type's width, when it folds; -1 otherwise. */
    int64_t intWidth(const ExprType &t);

    /** `t` with its width, for a message: `bit[65]`. */
    std::string typeName(const ExprType &t);

    /** True unless `t` is known not to be an import type (20.4.1 c). */
    bool importTypeOk(const ExprType &t, int32_t depth=0);

    /** True unless `t` is known not to be an export type (20.4.2.1). */
    bool exportTypeOk(const ExprType &t, int32_t depth=0);

    /** PSS137 on an import's prototype; `at` is where the import is written. */
    void checkImport(ast::IFunctionPrototype *proto, const ast::Location &at, bool use_at);

    /** PSS135: `name` declares a variable of type `dt`. */
    void checkItemlessEnum(ast::IExprId *name, ast::IDataType *dt);

private:
    static dmgr::IDebug                 *m_dbg;
    ResolveContext                      *m_ctxt;
    TaskExprTypeCat                     m_typer;
    ast::Location                       m_stmt_loc;
};

}
