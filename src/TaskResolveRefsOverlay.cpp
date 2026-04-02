/*
 * TaskResolveRefsOverlay.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskGetAstRoot.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskResolveRef.h"
#include "TaskResolveRefsOverlay.h"


namespace pssp {



TaskResolveRefsOverlay::TaskResolveRefsOverlay(ResolveContext *ctxt) : 
    m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskResolveRefsOverlay", ctxt->getDebugMgr());
}

TaskResolveRefsOverlay::~TaskResolveRefsOverlay() {

}

void TaskResolveRefsOverlay::resolve(ast::IGlobalScope * overlay) {
    DEBUG_ENTER("resolve");

    m_overlay = overlay;

    m_ctxt->pushSymtab(m_ctxt->getFactory()->mkAstSymbolTableIterator(
        m_ctxt->root()));
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=overlay->getChildren().begin();
        it!=overlay->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }

    DEBUG_LEAVE("resolve");
}

void TaskResolveRefsOverlay::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier %s", i->getElems().at(0)->getId()->getId().c_str());

    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i);
    i->setTarget(target);

    DEBUG_LEAVE("visitTypeIdentifier");
}

void TaskResolveRefsOverlay::visitPackageScope(ast::IPackageScope *i) {
    DEBUG_ENTER("visitPackageScope");
    // TODO: push symbol scopes

    ast::ISymbolScope *scope = m_ctxt->symtab()->getScope();
    for (std::vector<ast::IExprIdUP>::const_iterator
        it=i->getId().begin();
        it!=i->getId().end(); it++) {
        std::unordered_map<std::string,int32_t>::const_iterator sym_it;
        sym_it = scope->getSymtab().find((*it)->getId());
        scope = dynamic_cast<ast::ISymbolScope *>(
            scope->getChildren().at(sym_it->second).get());
        m_ctxt->symtab()->pushScope(scope);
    }

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }

    // pop symbol scopes
    for (std::vector<ast::IExprIdUP>::const_iterator
        it=i->getId().begin();
        it!=i->getId().end(); it++) {
        m_ctxt->symtab()->popScope();
    }

    DEBUG_LEAVE("visitPackageScope");
}

void TaskResolveRefsOverlay::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope %s", i->getName()->getId().c_str());
    // TODO: push symbol scope
    ast::ISymbolScope *scope = m_ctxt->symtab()->getScope();

    std::unordered_map<std::string,int32_t>::const_iterator sym_it;
    sym_it = scope->getSymtab().find(i->getName()->getId());
    if (sym_it == scope->getSymtab().end()) {
        DEBUG_ERROR("Failed to find %s in %s", 
            i->getName()->getId().c_str(),
            scope->getName().c_str());
        DEBUG_LEAVE("visitTypeScope");
        return;
    }
    ast::ISymbolScope *i_s = dynamic_cast<ast::ISymbolScope *>(
        scope->getChildren().at(sym_it->second).get());
    m_ctxt->symtab()->pushScope(i_s);

    if (i->getSuper_t()) {
        i->getSuper_t()->accept(m_this);

        DEBUG("Have super");
        if (i->getSuper_t()->getTarget()) {
            DEBUG("Super %s has a target", i->getSuper_t()->getElems().front()->getId()->getId().c_str());
            ast::IScopeChild *super_t = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(),
                m_ctxt->root()).resolve(
                i->getSuper_t()->getTarget());

            if (super_t) {
                ast::IGlobalScope *super_t_root = TaskGetAstRoot(
                    m_ctxt->getDebugMgr()).root(super_t);
                DEBUG("File with root: %d", super_t_root->getFileid());

                if (super_t_root->getFileid() == m_overlay->getFileid()
                    && super_t_root != m_overlay) {
                    DEBUG("Required ref went away");
                    m_ctxt->addErrorMarker(
                        i->getSuper_t()->getElems().at(0)->getId()->getLocation(),
                        "Failed to resolve id %s",
                        i->getSuper_t()->getElems().at(0)->getId()->getId().c_str()
                    );
                }
            }
        } else {
            DEBUG("Super does not have a target");
        }
    }

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }

    m_ctxt->symtab()->popScope();

    DEBUG_LEAVE("visitTypeScope");
}

dmgr::IDebug *TaskResolveRefsOverlay::m_dbg = 0;

}
