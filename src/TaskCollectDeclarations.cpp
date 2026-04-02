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

#define DEBUG_ENTER(fmt, ...) \
	fprintf(stdout, "--> TaskCollectDeclarations::"); \
	fprintf(stdout, fmt, ##__VA_ARGS__); \
	fprintf(stdout, "\n");

#define DEBUG(fmt, ...) \
	fprintf(stdout, "TaskCollectDeclarations: "); \
	fprintf(stdout, fmt, ##__VA_ARGS__); \
	fprintf(stdout, "\n");

#define DEBUG_LEAVE(fmt, ...) \
	fprintf(stdout, "<-- TaskCollectDeclarations::"); \
	fprintf(stdout, fmt, ##__VA_ARGS__); \
	fprintf(stdout, "\n");

#include "Marker.h"

namespace pssp {



TaskCollectDeclarations::TaskCollectDeclarations(
    IMarkerListener     *listener,
    ISymbolTable        *symtab) : m_listener(listener), m_symtab(symtab) {

}

TaskCollectDeclarations::~TaskCollectDeclarations() {

}

void TaskCollectDeclarations::collect(ast::IGlobalScope *root) {
    root->accept(m_this);
}

void TaskCollectDeclarations::visitPackageScope(ast::IPackageScope *i) {
    DEBUG_ENTER("visitPackageScope %s", i->getId().at(0)->getId().c_str());
    m_symtab->defineSymbolScope(
        i->getId().at(0)->getId(),
        i);

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }

    m_symtab->leaveSymbolScope();
    DEBUG_LEAVE("visitPackageScope %s", i->getId().at(0)->getId().c_str());
}

void TaskCollectDeclarations::visitAction(ast::IAction *i) {
    DEBUG_ENTER("visitAction %s", i->getName()->getId().c_str());
    ast::IScopeChild *dup = m_symtab->defineSymbolScope(i->getName()->getId(), i);
    if (dup) {
        duplicateSymbolDeclError(i, dup);
    } else {
        VisitorBase::visitAction(i);
        m_symtab->leaveSymbolScope();
    }
    DEBUG_LEAVE("visitAction %s", i->getName()->getId().c_str());
}

void TaskCollectDeclarations::visitComponent(ast::IComponent *i) {
    DEBUG_ENTER("visitComponent %s", i->getName()->getId().c_str());
    ast::IScopeChild *dup = m_symtab->defineSymbolScope(i->getName()->getId(), i);
    if (dup) {
        duplicateSymbolDeclError(i, dup);
    } else {
        VisitorBase::visitComponent(i);
        m_symtab->leaveSymbolScope();
    }
    DEBUG_LEAVE("visitComponent %s", i->getName()->getId().c_str());
}

void TaskCollectDeclarations::visitEnumDecl(ast::IEnumDecl *i) {
    DEBUG_ENTER("visitEnumDecl %s", i->getName()->getId().c_str());

    ast::IScopeChild *dup = m_symtab->defineSymbolScope(i->getName()->getId(), i);

    if (dup) {
        duplicateSymbolDeclError(i, dup);
    } else {
        VisitorBase::visitEnumDecl(i);
        m_symtab->leaveSymbolScope();
    }

    DEBUG_LEAVE("visitEnumDecl %s", i->getName()->getId().c_str());
}

void TaskCollectDeclarations::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
    ast::IScopeChild *dup = m_symtab->defineSymbol(i->getName()->getId(), i);
    if (dup) {
        duplicateSymbolDeclError(i, dup);
    }
    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
}

void TaskCollectDeclarations::visitScopeChildRef(ast::IScopeChildRef *i) {
    DEBUG_ENTER("visitScopeChildRef");
    i->getTarget()->accept(this);
    DEBUG_LEAVE("visitScopeChildRef");
}

void TaskCollectDeclarations::visitStruct(ast::IStruct *i) {
    DEBUG_ENTER("visitStruct %s", i->getName()->getId().c_str());
    ast::IScopeChild *dup = m_symtab->defineSymbolScope(i->getName()->getId(), i);
    if (dup) {
        duplicateSymbolDeclError(i, dup);
    } else {
        VisitorBase::visitStruct(i);
        m_symtab->leaveSymbolScope();
    }
    DEBUG_LEAVE("visitStruct %s", i->getName()->getId().c_str());
}

void TaskCollectDeclarations::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope %s", i->getName()->getId().c_str());
    // How do we handle scoping wrt optional scopes?
    // - Always have an anonymous scope for parameters?
    // - Only create if needed?
    // - What about 'super'?

    m_symtab->enterParamsScope();
    if (i->getParams()) {
        i->getParams()->accept(this);
    }
    m_symtab->leaveParamsScope();

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }
    DEBUG_LEAVE("visitTypeScope %s", i->getName()->getId().c_str());
}

void TaskCollectDeclarations::duplicateSymbolDeclError(
        ast::IScopeChild            *new_sym,
        ast::IScopeChild            *ex_sym) {
    Marker m(
        "duplicate symbol declaration",
        MarkerSeverityE::Error,
        new_sym->getLocation());
    m_listener->marker(&m);
}

}
