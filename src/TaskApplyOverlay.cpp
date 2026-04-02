/*
 * TaskApplyOverlay.cpp
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
#include "pssp/ast/IFactory.h"
#include "pssp/ast/ISymbolScope.h"
#include "TaskApplyOverlay.h"


namespace pssp {



TaskApplyOverlay::TaskApplyOverlay(
    dmgr::IDebugMgr     *dmgr,
    ast::IFactory       *factory) : m_factory(factory) {
    DEBUG_INIT("pssp::TaskApplyOverlay", dmgr);
}

TaskApplyOverlay::~TaskApplyOverlay() {

}

void TaskApplyOverlay::apply(
        ast::IRootSymbolScope                   *root,
        ast::IGlobalScope                       *overlay) {
    DEBUG_ENTER("apply");

    // Go through each overlay file, patching its content
    // in and resolving its symbols against itself and
    // the base AST

    m_scope_s.clear();
    m_scope_s.push_back(root);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=overlay->getChildren().begin();
        it!=overlay->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    m_scope_s.pop_back();
    DEBUG_LEAVE("apply");
}

void TaskApplyOverlay::visitNamedScopeChild(ast::INamedScopeChild *i) {
    DEBUG_ENTER("visitNamedScopeChild %s", i->getName()->getId().c_str());
    ast::ISymbolScope *scope = m_scope_s.back();

    std::unordered_map<std::string,int32_t>::iterator ex_it;
    ex_it = scope->getSymtab().find(i->getName()->getId());

    int32_t i_id = scope->getChildren().size();
    scope->getChildren().push_back(ast::IScopeChildUP(i, false));

    if (ex_it != scope->getSymtab().end()) {
        // Need to add remove the existing entry
        DEBUG("Already exists in the symtab ; removing existing mapping");
        scope->getSymtab().erase(ex_it);
    }
    scope->getSymtab().insert({i->getName()->getId(), i_id});

    DEBUG_LEAVE("visitNamedScopeChild %s", i->getName()->getId().c_str());
}

void TaskApplyOverlay::visitPackageScope(ast::IPackageScope *i) {
    DEBUG_ENTER("visitPackageScope");
    // Lookup the matching SymbolScope
    ast::ISymbolScope *scope = m_scope_s.back();
    for (std::vector<ast::IExprIdUP>::const_iterator
        it=i->getId().begin();
        it!=i->getId().end(); it++) {
        std::unordered_map<std::string,int32_t>::const_iterator s_it;
        s_it = scope->getSymtab().find((*it)->getId());

        if (s_it == scope->getSymtab().end()) {
            // This means that this package doesn't exist in the base AST
            DEBUG_ERROR("TODO: handle new-package case");
        } else {
            scope = dynamic_cast<ast::ISymbolScope *>(scope->getChildren().at(s_it->second).get());
        }
    }

    m_scope_s.push_back(scope);
    for (std::vector<ast::IScopeChildUP>::const_iterator 
        it=scope->getChildren().begin();
        it!=scope->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    m_scope_s.pop_back();

    DEBUG_LEAVE("visitPackageScope");
}

void TaskApplyOverlay::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope %s", i->getName()->getId().c_str());
    ast::ISymbolScope *scope = m_scope_s.back();

    std::unordered_map<std::string,int32_t>::const_iterator it_i;
    it_i = scope->getSymtab().find(i->getName()->getId());

    ast::ISymbolScope *scope_i = 0;
    if (it_i == scope->getSymtab().end()) {
        int32_t id = scope->getChildren().size();
        ast::ISymbolScope *plist = 0;
        if (i->getParams()) {
            DEBUG("Build out plist %d", i->getParams()->getParams().size());
            plist = m_factory->mkSymbolScope("");
            for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
                it=i->getParams()->getParams().begin();
                it!=i->getParams()->getParams().end(); it++) {
                int32_t id = plist->getChildren().size();
                std::unordered_map<std::string, int32_t>::const_iterator s_it;
                DEBUG("  Param: %", (*it)->getName()->getId().c_str());
            
                s_it = plist->getSymtab().find((*it)->getName()->getId());
                if (s_it == plist->getSymtab().end()) {
                    plist->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
                    plist->getSymtab().insert({(*it)->getName()->getId(), id});
                } else {
                    // TODO: Find a proper way to report
                    DEBUG_ERROR("duplicate parameter name");
                }
            }
        } else {
            DEBUG("No plist");
        }

        DEBUG("Failed to find symbol %s in type %s", 
            i->getName()->getId().c_str(), scope->getName().c_str());

        ast::ISymbolTypeScope *si = m_factory->mkSymbolTypeScope(
            i->getName()->getId(),
            plist);
        scope->getSymtab().insert({si->getName(), id});
        scope->getChildren().push_back(ast::IScopeChildUP(si, true));
        scope_i = si;
    } else {
        DEBUG("Found type %s in type %s", 
            i->getName()->getId().c_str(), scope->getName().c_str());
        scope_i = dynamic_cast<ast::ISymbolScope *>(
            scope->getChildren().at(it_i->second).get());
        if (!scope_i) {
            DEBUG("Not a symbol scope");
        }
    }

    if (scope_i) {
    // Update the target this the symbol scope points to
    scope_i->setTarget(i);

    m_scope_s.push_back(scope_i);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    m_scope_s.pop_back();
    }

    DEBUG_LEAVE("visitTypeScope");
}

dmgr::IDebug *TaskApplyOverlay::m_dbg = 0;

}
