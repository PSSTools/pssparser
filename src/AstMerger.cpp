/*
 * AstMerger.cpp
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
#include "AstMerger.h"

namespace pssp {



AstMerger::AstMerger(ast::IFactory *factory) : m_factory(factory) {

}

AstMerger::~AstMerger() {

}

ast::ISymbolScope *AstMerger::merge(
        const std::vector<ast::IGlobalScope *> &asts) {
    /*
    ast::ISymbolAggregateScope *ret = m_factory->mkSymbolAggregateScope("");
    m_scope_s.push_back(ret);

    for (std::vector<ast::IGlobalScope *>::const_iterator
        it_ast=asts.begin();
        it_ast!=asts.end(); it_ast++) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it_c=(*it_ast)->getChildren().begin();
            it_c!=(*it_ast)->getChildren().end(); it_c++) {
            (*it_c)->accept(this);
        }
    }
    m_scope_s.pop_back();
    return ret;
     */
    return 0;
}

void AstMerger::visitPackageScope(ast::IPackageScope *i) {
    /*
    for (std::vector<ast::IExprIdUP>::const_iterator
        id_it=i->getId().begin();
        id_it!=i->getId().end(); id_it++) {
        std::map<std::string,int32_t>::const_iterator p_it;
        p_it = m_scope_s.back()->getSymtab().find((*id_it)->getId());

        if (p_it == m_scope_s.back()->getSymtab().end()) {
            ast::IAggregateSymbolScope *pkg = m_factory->mkAggregateSymbolScope((*id_it)->getId());
            int32_t id = m_scope_s.back()->getChildren().size();
            m_scope_s.back()->getSymtab().insert({(*id_it)->getId(), id});
            m_scope_s.back()->getOwned().push_back(ast::IScopeChildUP(pkg));
            m_scope_s.push_back(pkg);
        } else {
            m_scope_s.push_back(dynamic_cast<ast::IAggregateSymbolScope *>(
                m_scope_s.back()->getChildren().at(p_it->second)));
        }
    }

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }

    for (std::vector<ast::IExprIdUP>::const_iterator
        id_it=i->getId().begin();
        id_it!=i->getId().end(); id_it++) {
        m_scope_s.pop_back();
    }
     */
}

void AstMerger::visitScope(ast::IScope *i) {
    /*
    int32_t id = m_scope_s.back()->get
    m_scope_s.back()->getChildren().push_back(
        ast::IScopeChildUP(m_factory->mkScopeChildRef(i)));
     */
}

void AstMerger::visitScopeChild(ast::IScopeChild *i) {
    /*
    m_scope_s.back()->scope->getChildren().push_back(
        ast::IScopeChildUP(m_factory->mkScopeChildRef(i)));
    */
}

}
