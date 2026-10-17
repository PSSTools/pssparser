/**
 * TaskCheckProcedural.h
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
#include <string>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "ResolveContext.h"
#include "TaskExprTypeCat.h"

namespace pssp {

/**
 * Rules on procedural statements that need every reference bound, checked
 * after resolution (the front-end checks of pssc's
 * 06-front-end-checks.md, groups 1 and 2):
 *
 * - a constant, or a part of one, on the left of an assignment (7.1), and
 *   a `const` parameter changed in its function (20.2.3) -- PSS121;
 * - a constant of aggregate type passed to a non-const parameter of a PSS
 *   function (20.2.3, Example 291) -- PSS006, beside the aggregate-literal
 *   form of the same rule;
 * - the sub-string operator on the left of an assignment (7.6.2) -- PSS122;
 * - a foreach's index or iterator variable, or its collection, changed in
 *   its body (20.7.8 g) -- PSS123;
 * - `break`/`continue` outside a loop (20.7.11 b) -- PSS124;
 * - two `default` branches in one match (20.7.10 f; 11.4.6 f for an
 *   activity match) -- PSS125.
 *
 * Walks the user units as written. A generic's body is checked once, in the
 * generic (its specializations are copies at the same locations); a
 * reference there that only a specialization binds is not known, and
 * nothing is reported on what is not known.
 */
class TaskCheckProcedural : public virtual ast::VisitorBase {
public:
    TaskCheckProcedural(ResolveContext *ctxt);

    virtual ~TaskCheckProcedural();

    void check(ast::IRootSymbolScope *root);

    virtual void visitFunctionDefinition(ast::IFunctionDefinition *i) override;

    virtual void visitExecBlock(ast::IExecBlock *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) override;

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) override;

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override;

    virtual void visitProceduralStmtBreak(ast::IProceduralStmtBreak *i) override;

    virtual void visitProceduralStmtContinue(ast::IProceduralStmtContinue *i) override;

    virtual void visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) override;

    virtual void visitActivityMatch(ast::IActivityMatch *i) override;

    virtual void visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

private:
    /** One step of a reference: the element and what it names. */
    struct PathStep {
        ast::IExprMemberPathElem    *elem;      ///< null for a static path
        ast::IExprId                *id;        ///< the name as written
        ast::IScopeChild            *decl;      ///< what it names; null if not known
    };

    /** The elements of a reference to a variable, in order. */
    struct LValue {
        std::vector<PathStep>       steps;
        /** False when the expression is not a plain reference (a call,
         *  an operator, a literal ...) or a step is not bound. */
        bool                        valid = false;
    };

    LValue lvalueOf(ast::IExpr *e);

    /**
     * The steps of `elems[0..n)`, `first_decl` standing in for the first
     * element's decl when the linker recorded it on the path instead.
     */
    LValue lvalueOfElems(
        const std::vector<ast::IExprMemberPathElemUP>   &elems,
        uint32_t                                        n,
        ast::IScopeChild                                *first_decl);

    /** Calls among `elems`: const arguments, collection-changing methods. */
    void checkCalls(
        const std::vector<ast::IExprMemberPathElemUP>   &elems,
        ast::IScopeChild                                *first_decl);

    /** The constant `lv` is part of: a const field or const parameter step. */
    int32_t constStep(const LValue &lv);

    void checkConstWrite(const LValue &lv);

    void checkSubstringWrite(ast::IExpr *lhs, const LValue &lv);

    /** A write to `lv`, or a change made by a method of it (`what`). */
    void checkForeachWrite(const LValue &lv, const char *what);

    void checkConstArgs(ast::IExprMemberPathElem *elem, ast::ISymbolFunctionScope *fn);

    void loopBody(ast::IScopeChild *body);

    struct Foreach {
        ast::IProceduralStmtForeach *stmt;
        LValue                      coll;
        ast::IScopeChild            *it;
        ast::IScopeChild            *idx;
    };

private:
    static dmgr::IDebug                 *m_dbg;
    ResolveContext                      *m_ctxt;
    TaskExprTypeCat                     m_typer;
    int32_t                             m_loop_depth;
    std::vector<Foreach>                m_foreach;
};

}
