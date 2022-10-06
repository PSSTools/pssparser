/*
 * TaskCollectDeclarations.cpp
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
#include "SymbolScope.h"
#include "TaskCollectDeclarations.h"


namespace pssp {

TaskCollectDeclarations::TaskCollectDeclarations(IMarkerListener *listener) 
    : m_listener(listener) {

}

TaskCollectDeclarations::~TaskCollectDeclarations() {

}

void TaskCollectDeclarations::collect(
        ISymbolScope            *root,
        ast::IScope             *ast) {
    m_scope_s.clear();
    m_scope_s.push_back(root);
    ast->accept(m_this);
    m_scope_s.pop_back();
}

void TaskCollectDeclarations::visitPackageScope(ast::IPackageScope *i) {

    // TODO: Check for existing namespace
    // TODO: handle a declared-nested namespace

    /** TODO: 
    ISymbolScope *scope = new SymbolScope(
        i->getName()->getId(),
        SymbolScopeKind::Namespace);
    m_scope_s.push_back(scope);
    scope->addDeclScope(i);
    m_scope_s.back()->addSubscope(scope);
    VisitorBase::visitPackageScope(i);
    m_scope_s.pop_back();
     */
}

void TaskCollectDeclarations::visitTypeScope(ast::ITypeScope *i) {
    ISymbolScope *scope = new SymbolScope(
        i->getName()->getId(),
        SymbolScopeKind::Type);
    scope->addDeclScope(i);

    m_scope_s.push_back(scope);
    VisitorBase::visitTypeScope(i);
    m_scope_s.pop_back();

}

}
