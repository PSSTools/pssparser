/**
 * AstSymbolTable.h
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
#include <unordered_map>
#include "dmgr/IDebugMgr.h"
#include "pssp/ISymbolTable.h"

namespace pssp {




class AstSymbolTable : public ISymbolTable {
public:
    struct NameScope;
    using NameScopeUP=std::unique_ptr<NameScope>;
    struct NameScope {
        NameScope(ast::IScopeChild *item) : m_item(item) { }

        NameScope *find(const std::string &name) {
            std::unordered_map<std::string, NameScopeUP>::const_iterator it = m_syms.find(name);
            return (it != m_syms.end())?it->second.get():0;
        }

        ast::IScopeChild                                *m_item;
        std::unordered_map<std::string, NameScopeUP>    m_syms;
        NameScopeUP                                     m_params_s;
    };

public:
    AstSymbolTable(dmgr::IDebugMgr *dmgr);

    virtual ~AstSymbolTable();

    virtual void init(INameResolver *resolver) override {
//        m_name_resolver = resolver;
    }

    virtual ISymbolTableIterator *mkIterator() override;

    virtual void enterPackage(const std::string &name) override;

    /**
     * @brief Declares a new 
     * 
     * @param t 
     * @return ast::ITypeScope* if a duplicate type exists
     */
    virtual ast::IScopeChild *defineSymbol(
        const std::string &name, ast::IScopeChild *t) override;

    virtual ast::IScopeChild *defineSymbolScope(
        const std::string       &name, 
        ast::IScopeChild        *t) override;

    virtual void leaveSymbolScope() override;

    virtual void enterParamsScope() override;

    virtual void leaveParamsScope() override;

    /**
     * @brief Declares a new field
     * 
     * @param s 
     * @return ast::IField* if a duplicate field exists
     */
    virtual ast::IField *declareField(ast::IField *f) override;

    virtual void enterTypeScope(ast::ITypeScope *s) override;

    virtual void leaveTypeScope(ast::ITypeScope *s) override;

    virtual void leavePackage(const std::string &name) override;

    NameScope *findRootSymbol(const std::string &name);

private:

private:
    static dmgr::IDebug             *m_dbg;
    dmgr::IDebugMgr                 *m_dmgr;
    NameScopeUP                     m_root;
    std::vector<NameScope *>        m_scope_s;

};

}
