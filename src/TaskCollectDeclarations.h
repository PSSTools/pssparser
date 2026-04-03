/**
 * TaskCollectDeclarations.h
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
#include <vector>
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolScope.h"
#include "pssp/ISymbolTable.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskCollectDeclarations : public virtual ast::VisitorBase {
public:
    TaskCollectDeclarations(
        IMarkerListener *listener,
        ISymbolTable    *symtab);

    virtual ~TaskCollectDeclarations();

    void collect(ast::IGlobalScope *root);

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitAction(ast::IAction *i) override;

    virtual void visitComponent(ast::IComponent *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitScopeChildRef(ast::IScopeChildRef *i) override;

    virtual void visitStruct(ast::IStruct *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

private:
    void duplicateSymbolDeclError(
        ast::IScopeChild            *new_sym,
        ast::IScopeChild            *ex_sym);

private:
    IMarkerListener                 *m_listener;
    ISymbolTable                    *m_symtab;
};

}
