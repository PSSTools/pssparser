/*
 * AstSymbolTable.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "AstSymbolTable.h"
#include "AstSymbolTableIterator.h"


namespace pssp {




AstSymbolTable::AstSymbolTable(dmgr::IDebugMgr *dmgr) : 
        m_dmgr(dmgr), m_root(new AstSymbolTable::NameScope(0)) {
    DEBUG_INIT("AstSymbolTable", dmgr);
    m_scope_s.push_back(m_root.get());
}

AstSymbolTable::~AstSymbolTable() {

}

ISymbolTableIterator *AstSymbolTable::mkIterator() {
//    return new AstSymbolTableIterator(this);
    return 0;
}

void AstSymbolTable::enterPackage(const std::string &name) {
    std::unordered_map<std::string,NameScopeUP>::iterator it = m_scope_s.back()->m_syms.find(name);

    if (it == m_scope_s.back()->m_syms.end()) {
        it = m_scope_s.back()->m_syms.insert({name, NameScopeUP(new NameScope(0))}).first;
    }
    m_scope_s.push_back(it->second.get());
}

    /**
     * @brief Declares a new 
     * 
     * @param t 
     * @return ast::ITypeScope* if a duplicate type exists
     */
ast::IScopeChild *AstSymbolTable::defineSymbol(
        const std::string           &name,
        ast::IScopeChild            *sym) {
    std::unordered_map<std::string,NameScopeUP>::const_iterator it =
        m_scope_s.back()->m_syms.find(name);

    if (it != m_scope_s.back()->m_syms.end()) {
        return it->second->m_item;
    } else {
        m_scope_s.back()->m_syms.insert({name, NameScopeUP(new NameScope(sym))});
        return 0;
    }
}

ast::IScopeChild *AstSymbolTable::defineSymbolScope(
        const std::string       &name, 
        ast::IScopeChild        *t) {
    std::unordered_map<std::string,NameScopeUP>::const_iterator it =
        m_scope_s.back()->m_syms.find(name);

    if (it != m_scope_s.back()->m_syms.end()) {
        return it->second->m_item;
    } else {
        NameScope *ns = new NameScope(t);
        m_scope_s.back()->m_syms.insert({name, NameScopeUP(ns)});
        m_scope_s.push_back(ns);
        return 0;
    }
}

void AstSymbolTable::leaveSymbolScope() {
    m_scope_s.pop_back();
}

void AstSymbolTable::enterParamsScope() {
    if (!m_scope_s.back()->m_params_s) {
        m_scope_s.back()->m_params_s = NameScopeUP(new NameScope(0));
    }
    m_scope_s.push_back(m_scope_s.back()->m_params_s.get());
}

void AstSymbolTable::leaveParamsScope() {
    m_scope_s.pop_back();
}

    /**
     * @brief Declares a new field
     * 
     * @param s 
     * @return ast::IField* if a duplicate field exists
     */
ast::IField *AstSymbolTable::declareField(ast::IField *f) {
    return 0;
}

void AstSymbolTable::enterTypeScope(ast::ITypeScope *s) {

}

void AstSymbolTable::leaveTypeScope(ast::ITypeScope *s) {

}

void AstSymbolTable::leavePackage(const std::string &name) {

}

AstSymbolTable::NameScope *AstSymbolTable::findRootSymbol(
    const std::string &name) {
    std::unordered_map<std::string,NameScopeUP>::const_iterator it = m_root->m_syms.find(name);
    if (it != m_root->m_syms.end()) {
        return it->second.get();
    } else {
        return 0;
    }
}

dmgr::IDebug *AstSymbolTable::m_dbg = 0;

}
