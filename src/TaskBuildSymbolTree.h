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

    virtual void visitFunctionDefinition(ast::IFunctionDefinition *i) override;

    virtual void visitFunctionImportProto(ast::IFunctionImportProto *i) override;

    virtual void visitFunctionImportType(ast::IFunctionImportType *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

    virtual void visitGlobalScope(ast::IGlobalScope *i) override;

    virtual void visitPackageImportStmt(ast::IPackageImportStmt *i) override;

    virtual void visitPyImportStmt(ast::IPyImportStmt *i) override;

    virtual void visitPyImportFromStmt(ast::IPyImportFromStmt *i) override;


    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) override;

    virtual void visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) override;

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) override;

//    virtual void visitProceduralStmtIfClause(ast::IProceduralStmtIfClause *i) override;

    virtual void visitScope(ast::IScope *i) override;

    virtual void visitScopeChild(ast::IScopeChild *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;;


protected:

    void reportDuplicateSymbol(
        ast::ISymbolScope       *scope,
        ast::IScopeChild        *orig,
        ast::IScopeChild        *dup);

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
