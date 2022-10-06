/**
 * SymbolScope.h
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
#include "pssp/ISymbolScope.h"

namespace pssp {


class SymbolScope : public virtual ISymbolScope {
public:
    SymbolScope(
        const std::string   &name,
        SymbolScopeKind     kind);

    virtual ~SymbolScope();

    virtual const std::string &getName() const override {
        return m_name;
    }

    virtual std::string getFullName() override;

    virtual SymbolScopeKind kind() const override {
        return m_kind;
    }

    virtual ISymbolScope *getParent() const override {
        return m_parent;
    }

    virtual void setParent(ISymbolScope *parent) override {
        m_parent = parent;
    }

    virtual const std::vector<ast::IScopeChild *> &getDeclScopes() const override {
        return m_decl_scopes;
    }

    virtual void addDeclScope(pssp::ast::IScopeChild *scope) override;

    virtual const std::vector<ISymbolScopeUP> &getSubscopes() const override {
        return m_subscopes;
    }

    virtual bool addSubscope(ISymbolScope *scope) override;

    virtual const std::vector<ast::INamedScopeChild *> &getTerminals() const override {
        return m_terminals;
    }

    virtual bool addTerminal(ast::INamedScopeChild *terminal) override;

    virtual bool resolve(
        const std::string       &name,
        ResolveResult           &result) override;

private:
    std::string                                     m_name;
    SymbolScopeKind                                 m_kind;
    ISymbolScope                                    *m_parent;
    std::vector<ast::IScopeChild *>                 m_decl_scopes;
    std::vector<ISymbolScopeUP>                     m_subscopes;
    std::vector<ast::INamedScopeChild *>            m_terminals;
    std::unordered_map<std::string, ResolveResult>  m_symtab;
};

}

