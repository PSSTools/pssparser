/**
 * TaskCloneSymbolScope.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskCloneSymbolScope : 
    public virtual ast::VisitorBase {
public:
    TaskCloneSymbolScope(
        dmgr::IDebugMgr     *dmgr,
        ast::IFactory       *factory) : m_dbg(0), m_factory(factory) {
        DEBUG_INIT("pssp::TaskCloneSymbolScope", dmgr);
    }

    virtual ~TaskCloneSymbolScope() { }

    virtual ast::IRootSymbolScope *clone(ast::IRootSymbolScope *scope) {
        DEBUG_ENTER("clone");
        m_scope_s.clear();
        m_depth = 1;
        scope->accept(m_this);
        DEBUG_LEAVE("clone %p", dynamic_cast<ast::IRootSymbolScope *>(m_ret));

        return dynamic_cast<ast::IRootSymbolScope *>(m_ret);
    }

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override {
        DEBUG_ENTER("visitRootSymbolScope (%d %d)", m_scope_s.size(), m_depth);
        ast::IRootSymbolScope *ic;
        if (m_scope_s.size() < m_depth) {
            ic = m_factory->mkRootSymbolScope(i->getName());
            ic->setTarget(i->getTarget());
            m_scope_s.push_back(ic);
        } else {
            ic = dynamic_cast<ast::IRootSymbolScope *>(m_scope_s.back());
        }
        visitSymbolScope(i);

        if (m_scope_s.size() == m_depth) {
            m_ret = m_scope_s.back();
            m_scope_s.pop_back();
        }
        DEBUG_LEAVE("visitRootSymbolScope (%d %d)", m_scope_s.size(), m_depth);
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope %s (%d %d)", i->getName().c_str(),
            m_scope_s.size(), m_depth);
        ast::ISymbolScope *ic;
        if (m_scope_s.size() < m_depth) {
            DEBUG("Clone scope (%d %d)", m_scope_s.size(), m_depth);
            ic = m_factory->mkSymbolScope(i->getName());
            m_scope_s.push_back(ic);
        } else {
            ic = m_scope_s.back();
        }

        // Copy the symbol table
        for (std::unordered_map<std::string,int32_t>::const_iterator
            it=i->getSymtab().begin();
            it!=i->getSymtab().end(); it++) {
            ic->getSymtab().insert({it->first, it->second});
        }

        // Clone imports
        if (i->getImports()) {
            ast::ISymbolImportSpec *impc = m_factory->mkSymbolImportSpec();
            for (std::vector<ast::IPackageImportStmt *>::const_iterator
                it=i->getImports()->getImports().begin();
                it!=i->getImports()->getImports().end(); it++) {
                impc->getImports().push_back(*it);
            }

            for (std::unordered_map<std::string,ast::ISymbolRefPathUP>::const_iterator
                it=i->getImports()->getSymtab().begin();
                it!=i->getImports()->getSymtab().end(); it++) {
                impc->getSymtab().insert({
                    it->first, 
                    ast::ISymbolRefPathUP(clone(it->second.get()))});
            }

            ic->setImports(impc, true);
        }
        
        // Set flags (synthetic, opaque)
        ic->setSynthetic(i->getSynthetic());
        ic->setOpaque(i->getOpaque());

        // Move child references over. These are not owned references
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            m_ret = 0;
            m_depth++;
            (*it)->accept(m_this);
            if (m_ret) {
                ic->getChildren().push_back(ast::IScopeChildUP(m_ret, true));
            } else {
                ic->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
            }
            m_depth--;
            m_ret = 0;
        }

        if (m_scope_s.size() == m_depth) {
            m_ret = m_scope_s.back();
            m_scope_s.pop_back();
        }
        DEBUG_LEAVE("visitSymbolScope %s (%d %d)", i->getName().c_str(),
            m_scope_s.size(), m_depth);
    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        DEBUG_ENTER("visitSymbolFunctionScope %s", i->getName().c_str());
        ast::ISymbolFunctionScope *ic;
        if (m_scope_s.size() < m_depth) {
            ic = m_factory->mkSymbolFunctionScope(i->getName());
            m_scope_s.push_back(ic);
        } else {
            ic = dynamic_cast<ast::ISymbolFunctionScope *>(m_scope_s.back());
        }

        // Copy prototype references
        for (std::vector<ast::IFunctionPrototype *>::const_iterator
            it=i->getPrototypes().begin();
            it!=i->getPrototypes().end(); it++) {
            ic->getPrototypes().push_back(*it);
        }

        // Copy import specs
        for (std::vector<ast::IFunctionImportUP>::const_iterator
            it=i->getImport_specs().begin();
            it!=i->getImport_specs().end(); it++) {
            ast::IFunctionImport *fic = m_factory->mkFunctionImport(
                (*it)->getPlat(), 
                (*it)->getLang());
            ic->getImport_specs().push_back(ast::IFunctionImportUP(fic));
        }

        ic->setDefinition(i->getDefinition());

        // Copy the parameter list
        ic->setBody(i->getBody());

        visitSymbolScope(i);

        if (m_scope_s.size() == m_depth) {
            m_ret = m_scope_s.back();
            m_scope_s.pop_back();
        }
        DEBUG_LEAVE("visitSymbolFunctionScope %s", i->getName().c_str());
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope %s (%d %d)", i->getName().c_str(),
            m_scope_s.size(), m_depth);
        ast::ISymbolTypeScope *ic;
        if (m_scope_s.size() < m_depth) {
            ast::ISymbolScope *plistc = 0;

            if (i->getPlist()) {
                plistc = clone(i->getPlist());
            }

            ic = m_factory->mkSymbolTypeScope(i->getName(), plistc);
            ic->setTarget(i->getTarget());
            m_scope_s.push_back(ic);
        } else {
            ic = dynamic_cast<ast::ISymbolTypeScope *>(m_scope_s.back());
        }

        DEBUG_ENTER("call visitSymbolScope(%d %d)", m_scope_s.size(), m_depth);
        visitSymbolScope(i);
        DEBUG_LEAVE("call visitSymbolScope(%d %d)", m_scope_s.size(), m_depth);
        
        for (std::vector<ast::ISymbolTypeScopeUP>::const_iterator
            it=i->getSpec_types().begin();
            it!=i->getSpec_types().end(); it++) {
            ast::ISymbolTypeScope *sci = cloneT<ast::ISymbolTypeScope>(it->get());
            ic->getSpec_types().push_back(ast::ISymbolTypeScopeUP(sci));
        }

        if (m_scope_s.size() == m_depth) {
            m_ret = m_scope_s.back();
            m_scope_s.pop_back();
        }
        
        DEBUG_LEAVE("visitSymbolTypeScope %s (%d %d)", i->getName().c_str(),
            m_scope_s.size(), m_depth);
    }

    ast::ISymbolRefPath *clone(ast::ISymbolRefPath *i) {
        ast::ISymbolRefPath *ic = m_factory->mkSymbolRefPath();
        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=i->getPath().begin();
            it!=i->getPath().end(); i++) {
            ic->getPath().push_back(*it);
        }
        ic->setPyref_idx(i->getPyref_idx());

        return ic;
    }

private:

    ast::ISymbolScope *clone(ast::ISymbolScope *i) {
        int32_t depth = m_depth;
        m_depth = m_scope_s.size()+1;
        i->accept(m_this);

        if (!m_ret) {
            fprintf(stdout, "failed to clone\n");
        }
        m_depth = depth;
        return m_ret;
    }

    template <class T> T *cloneT(ast::ISymbolScope *i) {
        return dynamic_cast<T *>(clone(i));
    }

private:
    dmgr::IDebug                            *m_dbg;
    ast::IFactory                           *m_factory;
    int32_t                                 m_depth;
    std::vector<ast::ISymbolScope *>        m_scope_s;
    ast::ISymbolScope                       *m_ret;

};

} /* namespace pssp */


