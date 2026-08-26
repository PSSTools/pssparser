/**
 * TaskBuildSymbolTree.h
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
#include <unordered_set>
#include "dmgr/IDebugMgr.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {


class TaskBuildSymbolTree : public virtual ast::VisitorBase {
public:
    TaskBuildSymbolTree(
        dmgr::IDebugMgr         *dmgr,
        ast::IFactory           *factory,
        IMarkerListener         *marker_l
    );

    virtual ~TaskBuildSymbolTree();

    ast::IRootSymbolScope *build(
        const std::vector<ast::IGlobalScope *>  &roots,
        bool                                    owned);

    ast::ISymbolTypeScope *build(ast::ITypeScope *ts);

    virtual void visitActivityDecl(ast::IActivityDecl *i) override;

    void registerActivityLabels(ast::ISymbolScope *scope);
    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override;

    virtual void visitConstraintScope(ast::IConstraintScope *i) override;
    
    virtual void visitConstraintStmt(ast::IConstraintStmt *i) override;

    virtual void visitConstraintStmtForall(ast::IConstraintStmtForall *i) override;

    virtual void visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) override;

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitTypedefDeclaration(ast::ITypedefDeclaration *i) override;

    virtual void visitEnumItem(ast::IEnumItem *i) override;

    virtual void visitExecBlock(ast::IExecBlock *i) override;

    virtual void visitExecStmt(ast::IExecStmt *i) override;

    virtual void visitExecScope(ast::IExecScope *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override;

    virtual void visitFieldRef(ast::IFieldRef *i) override;

    virtual void visitFieldClaim(ast::IFieldClaim *i) override;

    virtual void visitFunctionDefinition(ast::IFunctionDefinition *i) override;

    virtual void visitFunctionImportProto(ast::IFunctionImportProto *i) override;

    virtual void visitFunctionImportType(ast::IFunctionImportType *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

    virtual void visitTargetTemplateFunction(ast::ITargetTemplateFunction *i) override;

    virtual void visitTemplateString(ast::ITemplateString *i) override;

    virtual void visitGlobalScope(ast::IGlobalScope *i) override;

    virtual void visitPackageImportStmt(ast::IPackageImportStmt *i) override;

    virtual void visitPyImportStmt(ast::IPyImportStmt *i) override;

    virtual void visitPyImportFromStmt(ast::IPyImportFromStmt *i) override;


    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) override;

    virtual void visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override;

    virtual void visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) override;

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) override;

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) override;

//    virtual void visitProceduralStmtIfClause(ast::IProceduralStmtIfClause *i) override;

    virtual void visitScope(ast::IScope *i) override;

    virtual void visitScopeChild(ast::IScopeChild *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;;


protected:

    /**
     * Copy the doc comment from a declaration onto the symbol-tree scope that
     * wraps it, so `getDocstring()` is correct on the linked tree.
     *
     * Without this, every scope kind hid its doc comment: a consumer had to
     * know that a `SymbolTypeScope` keeps it behind `getTarget()`, and that a
     * `SymbolScope`, `SymbolEnumScope` and `SymbolFunctionScope` do not
     * expose it at all because they set no target. That is four rules for one
     * question; this makes it none.
     *
     * The raw text, form and location travel with it, so a consumer
     * implementing another doc dialect sees the same view from either tree.
     *
     * **First non-empty wins.** A scope can be produced by more than one
     * declaration -- a package re-opened in another file, a function declared
     * and then defined -- so this only ever fills an empty docstring and never
     * replaces one. The rule is the same for every kind, it needs no merge,
     * and it matches how a reader expects a re-opened scope to read. It is
     * documented in docs/doc_comments.rst because it is observable behavior.
     */
    void copyDocInfo(ast::IScopeChild *dst, ast::IScopeChild *src);

    /**
     * Give a symbol-tree scope the source range of the declaration it wraps.
     *
     * Replaces the bare `setLocation(i->getLocation())` each scope-creating
     * site did: `endLocation` was never carried across, so every scope in the
     * linked tree reported a start and an end of -1.
     */
    void copyExtent(ast::IScopeChild *dst, ast::IScopeChild *src);

    void reportDuplicateSymbol(
        ast::ISymbolScope       *scope,
        ast::IScopeChild        *orig,
        ast::IScopeChild        *dup);

    /**
     * Register a prototype's parameters in the function scope's `<plist>`.
     *
     * All four builders that can create an ISymbolFunctionScope go through
     * here, so that a parameter is found in the same place no matter how its
     * function was declared. Registration only -- reportDuplicateParams()
     * owns the duplicate diagnostic, since it also runs for the prototypes
     * that never reach this function.
     */
    void addFunctionParams(
        ast::ISymbolFunctionScope   *func_sym,
        ast::IFunctionPrototype     *proto);

    /**
     * Report any repeated parameter name in `proto`.
     *
     * Separate from the symtab loops in the three function visitors because
     * those loops run only when the function scope is being created: a
     * prototype seen after a definition, or a second prototype, skips them
     * entirely. This runs for every prototype. It also has to be its own
     * routine rather than a reportDuplicateSymbol() call, since a parameter
     * decl carries neither a name that TaskGetName() can read nor a location
     * of its own -- both live on its name node.
     */
    void reportDuplicateParams(ast::IFunctionPrototype *proto);

    /**
     * Report a parameter with no default that follows one that has a default.
     * Called from reportDuplicateParams(), so it reaches the same three
     * function visitors.
     */
    void checkParamDefaultOrder(ast::IFunctionPrototype *proto);

    /**
     * Report a `pure` function that returns void or takes an output/inout
     * parameter (LRM 20.2.6 rule a).  Called from reportDuplicateParams(),
     * so it reaches the same three function visitors.
     */
    void checkPureQualifier(ast::IFunctionPrototype *proto);

    /**
     * Report a parameter direction modifier on a function that has a PSS
     * body (LRM 20.2.2, 20.3.2).  Called only from visitFunctionDefinition:
     * a direction on a prototype is legal until an implementation appears.
     */
    bool checkNativeParamDir(ast::IFunctionPrototype *proto);

    ast::IScopeChild *findSymbol(const std::string &name);

    void pushSymbolScope(ast::ISymbolChild *s);

    ast::ISymbolScope *symbolScope();

    void popSymbolScope();

    void addChild(
        ast::IScopeChild    *c,
        bool                owned);

    void addChild(
        ast::ISymbolScope   *c,
        bool                owned);

    bool addChild(
        ast::IScopeChild    *c, 
        const std::string   &name,
        bool                owned=true);

    bool addChild(
        ast::ISymbolChild   *c, 
        const std::string   &name,
        bool                owned=true);

private:
    static dmgr::IDebug                         *m_dbg;
    ast::IFactory                               *m_factory;
    IMarkerListener                             *m_marker_l;
    std::vector<ast::ISymbolChild *>            m_scope_s;

};

}
