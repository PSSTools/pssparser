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
#include <unordered_map>
#include "ResolveContext.h"
#include "TaskCompareTypeRefs.h"
#include "TaskResolveBase.h"
#include "TaskResolveRootRef.h"
#include "pssp/ast/IActionFieldInitializer.h"
#include "pssp/ast/IExprBitSlice.h"
#include "pssp/ast/IExprBin.h"
#include "pssp/ast/IExprCast.h"
#include "pssp/ast/IExprCond.h"
#include "pssp/ast/IExprIn.h"
#include "pssp/ast/IMethodParameterList.h"
#include "pssp/ast/IExprOpenRangeList.h"
#include "pssp/ast/IConstraintStmtDist.h"
#include "pssp/ast/IProceduralStmtAssignment.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ISymbolEnumScope.h"

namespace pssp {




class TaskResolveRefs : public TaskResolveBase {
public:
    TaskResolveRefs(ResolveContext      *ctxt);

    virtual ~TaskResolveRefs();

    void resolve(ast::ISymbolScope *root);

    void resolve(ast::ISymbolTypeScope *scope);

    /**
     * Bind the names in every `compile if` / `compile assert` condition kept
     * by the builder (CompileCond, pss-scrambler FR-002 case A), each in the
     * scope it was written in. Reports nothing: the builder has already
     * evaluated the condition, and `compile has(X)` names things that need
     * not exist. Runs after resolve().
     */
    void resolveCompileConds(ast::IRootSymbolScope *root);

    virtual void visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) override;
    
    virtual void visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) override;

    virtual void visitActivityDecl(ast::IActivityDecl *i) override;

    virtual void visitProceduralStmtRandomize(ast::IProceduralStmtRandomize *i) override;

    virtual void visitActivitySequence(ast::IActivitySequence *i) override;

    // Compound activity statements are scopes (WS4.1): each is pushed while
    // its bodies resolve, so a loop variable, and a handle declared in a
    // nested block, are found and recorded with a path that leads somewhere.
    // What is written outside the loop -- a count, a collection -- resolves
    // before the push.
    virtual void visitActivityForeach(ast::IActivityForeach *i) override;
    virtual void visitActivityRepeatCount(ast::IActivityRepeatCount *i) override;
    virtual void visitActivityRepeatWhile(ast::IActivityRepeatWhile *i) override;
    virtual void visitActivityReplicate(ast::IActivityReplicate *i) override;
    virtual void visitActivityIfElse(ast::IActivityIfElse *i) override;
    virtual void visitActivitySelect(ast::IActivitySelect *i) override;
    virtual void visitActivityMatch(ast::IActivityMatch *i) override;
    virtual void visitActivityAtomicBlock(ast::IActivityAtomicBlock *i) override;
    virtual void visitMonitorActivityEventually(ast::IMonitorActivityEventually *i) override;

    /** Push `i`, resolve its children and then its bodies, pop. */
    void resolveActivityScope(ast::ISymbolScope *i);
    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override;

    virtual void visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) override;

    virtual void visitConstraintStmtForall(ast::IConstraintStmtForall *i) override;

    virtual void visitExecScope(ast::IExecScope *i) override;

    /**
     * The 8.4.3 contexts: each gives one operand an expected type, which
     * step a of 18.3 reads (symbol-resolution plan 8.1). Only enumeration
     * types are carried for now.
     */
    virtual void visitExprBin(ast::IExprBin *i) override;
    virtual void visitExprIn(ast::IExprIn *i) override;
    virtual void visitExprCast(ast::IExprCast *i) override;

    virtual void visitConstraintStmtDefault(ast::IConstraintStmtDefault *i) override;

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override;
    virtual void visitExprCond(ast::IExprCond *i) override;
    virtual void visitConstraintStmtDist(ast::IConstraintStmtDist *i) override;
    virtual void visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) override;
    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;


    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    /**
     * Step a of 18.3: `id`, a bare name, as an item of its expected type
     * `e`. Null when it is not one. Warns (PSS044) when the item hides a
     * declaration the name has lexically. Also used by TaskResolveRef for
     * a template value argument (8.4).
     */
    static ast::ISymbolRefPath *expectedItem(
        ResolveContext              *ctxt,
        const ast::IExprId          *id,
        ast::ISymbolEnumScope       *e);

    /**
     * PSS046: `id` bound to an item of `e` only because nothing else of the
     * name is in scope, where `expected` (possibly null) did not have it.
     */
    static void warnEnumItemFallback(
        ResolveContext              *ctxt,
        const ast::IExprId          *id,
        ast::ISymbolEnumScope       *e,
        ast::ISymbolEnumScope       *expected);

private:
    /**
     * Visit `e` with `expected` as its expected type (8.4.3). The type
     * reaches `e` itself and nothing inside it, apart from both arms of a
     * `?:`. A null `expected` visits `e` plainly.
     */
    void visitExpecting(ast::IExpr *e, ast::ISymbolEnumScope *expected);

    /** Each value and bound of `l` expects `expected` (an `in` or a `match`). */
    void visitRangesExpecting(ast::IExprOpenRangeList *l, ast::ISymbolEnumScope *expected);

    /**
     * Each element of an aggregate literal expects `elem`, the element type
     * of the array or collection it is assigned to (8.4.2, 8.4.3).
     */
    void visitAggrExpecting(ast::IExprAggrList *l, ast::ISymbolEnumScope *elem);

    /**
     * A call's arguments, each expecting its formal parameter's type
     * (8.4.3). `callee` is what the call names; anything other than a
     * function visits them plainly.
     */
    void visitCallArgs(ast::IMethodParameterList *params, ast::IScopeChild *callee);

    /** The expected type visitExpecting() gave `e`, or null. */
    ast::ISymbolEnumScope *expectedFor(ast::IExpr *e) const;

    /**
     * expectedItem() for `i`, when it is a bare name.
     */
    ast::ISymbolRefPath *lookupExpectedItem(
        ast::IExprRefPathContext    *i,
        ast::ISymbolEnumScope       *e);

    /**
     * `a == b` with both sides bare names (decision Q2): each side's own
     * type -- the type of its lexical binding -- is the expected type of
     * the other. Reported (PSS045) when both readings would change what a
     * name binds to.
     */
    void resolveBareComparison(
        ast::IExprRefPathContext    *lhs,
        ast::IExprRefPathContext    *rhs);

    /**
     * What `id` binds to lexically, without step a and without reporting
     * anything. Null for an enum item the lookup settled for only because
     * nothing else of the name is in scope: by 18.3 that is no binding (8.2).
     */
    static ast::IScopeChild *peekLexical(ResolveContext *ctxt, const ast::IExprId *id);

    void resolveExprRefPathContext(ast::IExprRefPathContext *i);
    void resolveExprRefPathStatic(ast::IExprRefPathStatic *i);
    void resolveExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i);
    void visitSlice(ast::IExprBitSlice *slice);
    bool defaultsDiffer(ast::IExpr *a, ast::IExpr *b);
    ast::ISymbolScope *traversedType(
        ast::IScopeChild            *decl,
        ast::IExprId                *id,
        uint32_t                    n_sub,
        bool                        report);
    ast::ISymbolScope *randomizedType(ast::IExpr *target);
    void resolveTraversalBody(
        ast::ISymbolScope                                   *type_s,
        ast::IConstraintStmt                                *with_c,
        const std::vector<ast::IActionFieldInitializerUP>   &inits);
    void resolveInitializer(
        ast::ISymbolScope                                   *type_s,
        ast::IActionFieldInitializer                        *i);
public:

    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitActionHandleField(ast::IActionHandleField *i) override;

    virtual void visitActivitySuper(ast::IActivitySuper *i) override;

    virtual void visitProceduralStmtSuper(ast::IProceduralStmtSuper *i) override;

    /** §9.1.6 b) -- `mutable` is not permitted on a component field. */
    void checkMutableField(ast::IField *i);

    /** PSS115 -- `e` is a template string that is not a constant expression. */
    void checkConstTemplate(ast::IExpr *e, const ast::Location &loc);

    /**
     * PSS118 -- 18.2c/d: a constant's initializer references a constant or
     * enum item declared after it, or, at package level, a constant declared
     * in a type.
     */
    void checkConstInitRefs(ast::IField *i);

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) override;

    /**
     * A constant or enum item that `path` binds to, or null if it binds to
     * anything else. PSS118/PSS119 are about these only.
     */
    ast::IScopeChild *constTarget(ast::ISymbolRefPath *path);

    /**
     * True if `target`, used at `use`, comes later in the model: later in the
     * same file, or in a file given after the use's file (decision Q8).
     */
    bool declaredLater(ast::IScopeChild *target, const ast::Location &use);

    /**
     * "on line N", or "in a file given later" when `target` is in another
     * file.
     */
    std::string declSite(ast::IScopeChild *target, const ast::Location &use);

    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override;

    // 4.1b -- the procedural compound statements that declare nothing. Each
    // is a step on the path to a block in one of its bodies; see
    // pushProcScope.
    virtual void visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) override;

    virtual void visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) override;

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) override;

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) override;

    /** Visit a compound statement's bodies, each with `i` pending. */
    void walkProcBodies(ast::IScopeChild *i);

    /**
     * Push a procedural scope -- a block, `repeat` or `foreach` -- preceded by
     * the compound statements pending around it (4.1b).
     *
     * A compound statement such as `if` is on the path to a block in its body,
     * but it cannot simply be pushed around the body: it is not a symbol
     * scope, and the scope stack drops a non-scope entry the moment a lookup
     * runs with it on top -- as in `if (c) x = 1;`, or the collection of a
     * brace-less `if (c) foreach (e : l) ...`. So it is held here until a real
     * scope opens inside it, and pushed together with that scope.
     */
    void pushProcScope(ast::IScopeChild *s);

    /** Pop what the matching pushProcScope pushed, and restore the pending. */
    void popProcScope();

    // 4.7.1 -- template scopes. The generated visitors walk a block's body
    // *after* visitTemplateElem has already pushed and popped the scope, so a
    // foreach iterator would not be visible inside its own block. These push
    // the scope around the body instead.
    virtual void visitTemplateString(ast::ITemplateString *i) override;

    virtual void visitTemplateBlock(ast::ITemplateBlock *i) override;

    virtual void visitTemplateForeach(ast::ITemplateForeach *i) override;

    virtual void visitTemplateRepeat(ast::ITemplateRepeat *i) override;

    virtual void visitTemplateIfClause(ast::ITemplateIfClause *i) override;

    virtual void visitTemplateAssign(ast::ITemplateAssign *i) override;

    /**
     * Give a `foreach` iterator variable the element type of the collection
     * being iterated. The AST builder cannot: at parse time the collection is
     * an unresolved path.
     */
    void typeForeachIterator(ast::IProceduralStmtForeach *i);

    /**
     * The same, for any loop scope: the iterator `it_id` registered in
     * `loop`'s symtab takes the element type of the collection `coll`.
     */
    void typeLoopIterator(
        ast::ISymbolScope       *loop,
        ast::IExprId            *it_id,
        ast::IExprRefPath       *coll);

//    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    /**
     * Visit one child of a symbol scope, putting an extension's declaring
     * package back in scope if this child came from one. See CL-N1.
     */
    void visitMergedScopeChild(ast::IScopeChild *c);

    ast::ISymbolTypeScope *componentScopeOf(ast::ISymbolScope *s);

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

//    virtual void visitSymbolExecScope(ast::ISymbolExecScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitProceduralStmtReturn(ast::IProceduralStmtReturn *i) override;

    virtual void visitProceduralStmtExpr(ast::IProceduralStmtExpr *i) override;

//    virtual void visitSymbolStmtScope(ast::ISymbolStmtScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitAnnotation(ast::IAnnotation *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) override;

    virtual void visitExprMemberCall(ast::IExprMemberCall *i) override;

    virtual void visitFunctionImportType(ast::IFunctionImportType *i) override;

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override;

    virtual void visitSymbolDeclaration(ast::ISymbolDeclaration *i) override;

    // References whose resolution belongs to a later workstream. Since WS3.2
    // they are bindable paths, which the generic walk would resolve with the
    // ordinary lookup -- the wrong rules for them -- so each is skipped
    // explicitly until its own resolver lands. See TaskResolveRefs.cpp.
    virtual void visitComponentBind(ast::IComponentBind *i) override;
    virtual void visitActivityBindStmt(ast::IActivityBindStmt *i) override { }
    virtual void visitActivitySchedulingConstraint(ast::IActivitySchedulingConstraint *i) override { }
    virtual void visitActionFieldInitializer(ast::IActionFieldInitializer *i) override;
    virtual void visitInstanceOverride(ast::IInstanceOverride *i) override;

    virtual void visitExportFunction(ast::IExportFunction *i) override;

    virtual void visitActivitySymbolCall(ast::IActivitySymbolCall *i) override;
    
    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

    virtual void visitExecBlockTag(ast::IExecBlockTag *i) override;

    virtual void visitStruct(ast::IStruct *i) override;

    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) override;

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override;

protected:
    /**
     * Check every annotation that belongs directly to `scope` -- that is, all
     * annotations reachable from its children without crossing into a nested
     * symbol scope, plus any attached to the declaration `scope` wraps.
     *
     * Annotations are not reachable from the ordinary traversal: most of the
     * visitors overridden here (visitField, visitFunctionPrototype, the
     * activity/constraint statements) recurse into the members they care about
     * rather than chaining to visitScopeChild, which is what carries the
     * annotation list. Collecting per symbol scope keeps the symbol-table stack
     * correct for name resolution while reaching them all.
     */
    void checkScopeAnnotations(ast::ISymbolScope *scope);

    /**
     * The same for a block that is not a symbol scope of its own kind (a
     * procedural block, a loop body): the annotations on its statements.
     */
    void checkBlockAnnotations(ast::IScope *scope);

    /** Resolve each of `anns` not already resolved. */
    void checkAnnotations(const std::vector<ast::IAnnotationUP> &anns);

    /**
     * Resolve the leaf of a package-qualified reference (`p::g(1,2,3)`)
     * against the scope its static root names. See known-issues P3-X6e.
     */
    void resolveStaticRootedLeaf(ast::IExprRefPathStaticRooted *i);

    /**
     * Reports why `super.<id>` did not resolve. Silent when the base type
     * itself is unresolved: that is reported at the declaration.
     */
    void checkSuperStmt(ast::IScopeChild *stmt);

    void reportSuperMiss(
        ast::IExprId                                *id,
        const TaskResolveRootRef::SuperResult       &res);

    /**
     * If the lookup of `id` that just missed passed over a later declaration
     * of it (18.2a/b), reports the use as coming before that declaration and
     * returns true. Otherwise reports nothing.
     */
    bool reportUseBeforeDecl(const ast::IExprId *id);

    /**
     * If the lookup of `id` that just succeeded left a static function to
     * reach an instance member of the component (the static-context hint),
     * reports it.
     */
    void reportStaticContext(const ast::IExprId *id);

    /**
     * If the lookup of `id` that just succeeded settled for an enum item
     * because nothing else of the name is in scope (the enum-item hint),
     * warns (PSS046): 18.3 finds an item unqualified only by the expected
     * type, `expected`, which did not have it (8.2).
     */
    void reportEnumItemFallback(
        ast::IExprRefPathContext    *ref,
        ast::ISymbolEnumScope       *expected);

    /**
     * `T::m`, where `scope` is the type T and `member` is m. 18.3: a type
     * namespace holds "types, static constants, static functions, and enum
     * items", so an instance member is reported -- unless the reference is
     * written inside T, a subtype of T, or an extension of either, where a
     * qualified call to a base member is a common idiom and the LRM does not
     * say otherwise. Returns true if it reported.
     */
    bool checkTypeMember(
        ast::ISymbolScope       *scope,
        ast::IScopeChild        *member,
        const ast::IExprId      *id);

    /**
     * True if a scope enclosing the current position is `t`, derives from
     * it, or extends either.
     */
    bool insideTypeOrSubtype(ast::ISymbolTypeScope *t);

    /**
     * `comp.<...>.m`, where `scope` is the component searched and `member`
     * is m. 9.1.4.1 f: "It shall be illegal to access static component
     * members using the comp handle." Reports, and the name stays bound.
     */
    void checkStaticViaComp(
        ast::ISymbolScope       *scope,
        ast::IScopeChild        *member,
        const ast::IExprId      *id,
        bool                    direct);

    /**
     * The lookup `{% x = expr; %}` makes for its target: the innermost scope
     * declaring `x` before the assignment. True if found; `in_template` says
     * whether that scope is the template string's own, and `decl` is what
     * was found. `fwd_decl` is a later declaration of `x` passed over on the
     * way, if any.
     */
    bool findTemplateAssignTarget(
        const ast::IExprId          *id,
        bool                        &in_template,
        ast::IScopeChild            *&decl,
        ast::IScopeChild            *&fwd_decl);

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
    std::set<ast::IAnnotation *>        m_checked_annotations;

    // Same reason as m_checked_annotations: a declaration is reachable both
    // through its symbol scope and through the scope's target, so a node with
    // no dedicated visitor override is resolved twice. That is invisible while
    // resolution succeeds -- `getTarget()` short-circuits the second pass --
    // and shows up only as a duplicated diagnostic when it fails.
    std::set<ast::IExecBlockTag *>      m_checked_exec_tags;

    // 4.1b -- compound statements waiting to be pushed (pushProcScope), each
    // with the scope stack it belongs on; and, per pushed procedural scope,
    // the pending list to restore and how many entries it pushed.
    struct PendingProcStmt {
        ast::IScopeChild        *stmt;
        ISymbolTableIterator    *symtab;
    };
    struct ProcFrame {
        std::vector<PendingProcStmt>    saved;
        int32_t                         n_pushed;
    };
    std::vector<PendingProcStmt>        m_proc_pending;
    std::vector<ProcFrame>              m_proc_frames;

    // Non-zero while resolving inside a triple-quoted template string.
    //
    // PSS114 -- §4.7.1.1's "any function called shall be pure" -- has to be
    // checked where the callee is resolved: for `a.b.f()` that happens deep in
    // the ref-path walk, and only there is the declaration in hand. Rather
    // than duplicate that walk, the call sites ask this counter whether the
    // call they just resolved is inside a template.
    int32_t                             m_template_depth = 0;

    /**
     * The prototypes of the function bodies currently being walked, innermost
     * last. Empty while walking anything that is not a function body -- an
     * action's `exec` block, say -- which is why a `return` seen with this
     * empty is left alone rather than reported.
     */
    std::vector<ast::IFunctionPrototype *> m_func_s;

    /** Expected types in force, by operand; see visitExpecting(). */
    std::unordered_map<ast::IExpr *, ast::ISymbolEnumScope *> m_expected;

    /**
     * A bare call argument whose formal parameter's type is not bound yet --
     * declared in a later file, which the order of resolution allows. Its
     * expected type is known only once resolution is done, so PSS046 on the
     * argument is decided then (reportEnumItemFallback).
     */
    std::unordered_map<ast::IExpr *, ast::IFunctionParamDecl *> m_pending_formal;

};

}
