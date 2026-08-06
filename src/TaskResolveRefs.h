/**
 * TaskResolveRefs.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "dmgr/IDebugMgr.h"
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include <set>
#include "ResolveContext.h"
#include "TaskCompareTypeRefs.h"
#include "TaskResolveBase.h"

namespace pssp {




class TaskResolveRefs : public TaskResolveBase {
public:
    TaskResolveRefs(ResolveContext      *ctxt);

    virtual ~TaskResolveRefs();

    void resolve(ast::ISymbolScope *root);

    void resolve(ast::ISymbolTypeScope *scope);

    virtual void visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) override;
    
    virtual void visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) override;

    virtual void visitActivityDecl(ast::IActivityDecl *i) override;

    virtual void visitActivitySequence(ast::IActivitySequence *i) override;

    virtual void visitActivityForeach(ast::IActivityForeach *i) override;
    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override;

    virtual void visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) override;

    virtual void visitConstraintStmtForall(ast::IConstraintStmtForall *i) override;

    virtual void visitExecScope(ast::IExecScope *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override;

    /**
     * Give a `foreach` iterator variable the element type of the collection
     * being iterated. The AST builder cannot: at parse time the collection is
     * an unresolved path.
     */
    void typeForeachIterator(ast::IProceduralStmtForeach *i);

//    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

//    virtual void visitSymbolExecScope(ast::ISymbolExecScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitProceduralStmtReturn(ast::IProceduralStmtReturn *i) override;

    virtual void visitProceduralStmtExpr(ast::IProceduralStmtExpr *i) override;

//    virtual void visitSymbolStmtScope(ast::ISymbolStmtScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;
    
    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

    virtual void visitStruct(ast::IStruct *i) override;

    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) override;

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override;

protected:
    ast::IScopeChild *resolvePath(ast::ISymbolRefPath *path);

    bool isGenericConstraintParam(const std::string &name) const;

    bool isBuiltinWithMethods(ast::IScopeChild *c);

    /**
     * Check a call's argument count against the callee's declared parameters.
     *
     * `elem` is the path element that carries the argument list; `target` is
     * whatever that element resolved to. Does nothing unless `elem` is
     * actually a call and `target` is actually a function -- calling a
     * non-function is a separate defect, and reporting it from here would
     * also catch every built-in and collection method, whose parameters the
     * parser does not model.
     */
    void checkCallArity(
        ast::IExprMemberPathElem *elem,
        ast::IScopeChild         *target);

    /**
     * Report a call to a void function whose value is used (LRM 20.5:
     * "Functions not returning a value (declared with void return type) may
     * only be called as standalone procedural statements").
     *
     * Called from checkCallArity() for *every* call element of a path.
     * Restricting it to the last element -- which it did until §39 -- misses
     * `f().x`, where the member access is itself a use of the result. An
     * intermediate element that is not a call never reaches here, because
     * checkCallArity() returns early when the element has no parameter list.
     */
    void checkVoidCallUse(
        ast::IExprMemberPathElem  *elem,
        ast::ISymbolFunctionScope *fn);

    /**
     * Report declarations of one function that do not agree with each other.
     *
     * Called from visitSymbolFunctionScope *after* the prototypes have been
     * walked, because the comparisons are only worth making once the types
     * have resolved: unresolved, `S` and `p::S` are two spellings that
     * routinely denote one type, and comparing them by name would report
     * valid code.
     *
     * Reports at most once per function. Two declarations that disagree
     * wholesale -- a different return type *and* a different parameter list --
     * are one mistake, and the second report would tell the user nothing the
     * first did not.
     *
     * What is deliberately *not* compared is as much of the design as what is;
     * see the two helpers below and §41 of the fix plan.
     */
    void checkDeclarationConsistency(ast::ISymbolFunctionScope *i);

    /**
     * The return-type half of checkDeclarationConsistency(). True if it
     * reported.
     *
     * Only a *certain* difference is reported; see TaskCompareTypeRefs::Rel.
     */
    bool checkReturnTypeConsistency(
        ast::IFunctionPrototype     *base,
        ast::IFunctionPrototype     *p,
        TaskCompareTypeRefs         &comp);

    /**
     * The parameter-list half of checkDeclarationConsistency(). True if it
     * reported.
     *
     * Compares arity, parameter kind, type and direction, and applies LRM
     * 20.2.4 c -- a default value may be given by only one declaration, "even
     * if the value is the same".
     *
     * Parameter *names* are not compared. PSS calls are positional -- the
     * grammar's `function_parameter_list` is a list of expressions, with no
     * named-argument form -- and nothing in the LRM requires the names to
     * match, so a definition naming its parameters differently from an
     * earlier declaration is legal. (That it currently breaks resolution
     * inside the definition's own body is a separate defect; see §41.5.)
     *
     * `pure` is not compared either: LRM 20.2.6 b explicitly permits omitting
     * it in a definition whose declaration carries it.
     */
    bool checkParamListConsistency(
        ast::IFunctionPrototype     *base,
        ast::IFunctionPrototype     *p,
        TaskCompareTypeRefs         &comp);

    /**
     * Resolve the leaf elements of a static-rooted path -- the `f` of
     * `p::f(1)` -- against the scope the static root resolved to.
     *
     * The branch this fills was a `DEBUG("TODO")`, so the leaf's names were
     * never looked up in anything.
     */
    void resolveStaticRootedLeaf(ast::IExprRefPathStaticRooted *i);

public:
    /**
     * A deliberately coarse classification of a type or an expression.
     *
     * There is no expression-type inference in this parser, and building a
     * full one means deciding PSS's assignment compatibility -- numeric
     * widths, signedness, enum-to-integer, struct subtyping -- where a wrong
     * rule rejects valid code at every call site in every model. These four
     * categories are the part of that which needs no such judgement: nothing
     * in PSS makes a string interchangeable with a number, or either with a
     * struct.
     *
     * `Unknown` is the answer for anything not certainly in one of the
     * others, and it is never reported against. Arithmetic, casts, calls,
     * multi-element paths, `chandle`, type parameters, reference parameters
     * and unresolved types all land there on purpose.
     */
    enum class TypeCat {
        Unknown,    //< not certainly anything; never reported
        Numeric,    //< int, bit, bool, enum -- mutually convertible in PSS
        Str,        //< string
        Aggregate   //< struct, component, action -- a composite value
    };

protected:
    TypeCat catOfDataType(ast::IDataType *dt);

    TypeCat catOfExpr(ast::IExpr *e);

    /**
     * Report an argument whose category cannot be what the parameter
     * declares. Called from checkCallArity() once the count is known good.
     */
    void checkCallArgTypes(
        ast::IExprMemberPathElem  *elem,
        ast::ISymbolFunctionScope *fn);

    /**
     * Resolve the field names in a masked register write (PSS 3.1 §21.14.1).
     *
     * `regs.csr.write_field("ch_en", 1)` names a *declared field* of the
     * register's value type; the string spelling is forced by the LRM's
     * signature `write_field(string, bit[SZ])`, not a sign that it is data.
     * Resolving it is name binding, and name binding is the front end's job --
     * a compiler that had to do it would be a second implementation, and every
     * other consumer of this parser would need a third.
     *
     * Called from the member-call site alongside checkCallArity(), where the
     * receiver's scope is in hand. What the *bits* of a resolved field are is
     * deliberately NOT decided here: `packed_s<>` layout is a target
     * representation (the C and SV backends order it oppositely on purpose),
     * so it belongs to the compiler.
     */
    void checkRegFieldRefs(
        ast::IExprMemberPathElem *elem,
        ast::ISymbolScope        *recv_s);

    /**
     * The value type of a register-typed scope.
     *
     * Walks the super chain looking for the `reg_c<R, ACC, SZ>` specialization
     * -- `pure component csr_r : reg_c<csr_s, ...>` puts one level between the
     * field's type and the register, and an inline `reg_c<csr_s, ...> csr;`
     * puts none -- and returns its bound `R`.
     *
     * Returns false when the scope is not a register at all, which is the
     * quiet case: a user type may legitimately have a method called
     * `write_field`. When it returns true, `*vs` is the value struct, or null
     * if `R` is a scalar (`reg_c<bit[32]>`) and therefore has no named fields.
     */
    bool regValueStruct(
        ast::ISymbolScope  *recv_s,
        ast::IStruct      **vs);

    /**
     * Check one field-name argument. Returns the resolved field, or null
     * (having reported why).
     */
    ast::IField *resolveRegField(
        ast::IExprMemberPathElem *elem,
        ast::IStruct             *vs,
        ast::IExpr               *name_e);

private:
    /**
     * The expression of the `ProceduralStmtExpr` currently being walked, or
     * null when the walk is not inside one.  This is the whole of what makes
     * "standalone procedural statement" decidable here: a call whose ref-path
     * *is* this expression is a statement, and any other call is an operand.
     */
    ast::IExpr                          *m_stmt_expr = 0;

    /** The ref-path expression currently being walked; see m_stmt_expr. */
    ast::IExpr                          *m_cur_refpath = 0;

    static dmgr::IDebug                 *m_dbg;
    std::set<std::string>               m_generic_constraint_params;

    /**
     * The prototypes of the function bodies currently being walked, innermost
     * last. Empty while walking anything that is not a function body -- an
     * action's `exec` block, say -- which is why a `return` seen with this
     * empty is left alone rather than reported.
     */
    std::vector<ast::IFunctionPrototype *> m_func_s;

};

}
