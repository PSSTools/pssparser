/**
 * TaskGetName.h
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
#include <string>
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/TaskIsUnspecializedGenericType.h"

namespace pssp {


class TaskGetName : public virtual ast::VisitorBase {
public:
    TaskGetName() { }

    virtual ~TaskGetName() { }

    const std::string &get(ast::IScopeChild *c, bool bottom_up=false) {
        m_ret = "";
        if (bottom_up) {

            m_sym_s = 0;
            c->accept(m_this);
            std::string full_path;

            if (m_sym_s) {
                // This is a symbol scope
                ast::ISymbolScope *ss = m_sym_s;
                bool prev_elem = false;

                full_path = m_ret;

                while ((ss=ss->getUpper())) {
                    m_ret = "";

                    if (!TaskIsUnspecializedGenericType().check(ss)) {
                        ss->accept(m_this);

                        if (full_path.size() && m_ret.size()) {
                            full_path = "::" + full_path;
                        }
                        full_path = m_ret + full_path;
                    }
                }

                m_ret = full_path;
            } else {
                ast::IScopeChild *ci = c;
                do {
                    m_ret = "";
                    ci->accept(m_this);
                
                    if (full_path.size() && m_ret.size()) {
                        full_path = "::" + full_path;
                    }
                    full_path = m_ret + full_path;
                } while ((ci=ci->getParent()));

                m_ret = full_path;
            }
        } else {
            c->accept(m_this);
        }
        return m_ret;
    }

    virtual void visitNamedScopeChild(ast::INamedScopeChild *i) override {
        m_ret = i->getName()->getId();
    }

    virtual void visitNamedScope(ast::INamedScope *i) override {
        m_ret = i->getName()->getId();
    }

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override {

    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        m_ret = i->getName();
        m_sym_s = i;
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        m_ret = i->getName();
        m_sym_s = i;
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        m_ret = i->getName();
        m_sym_s = i;
    }

private:
    std::string                 m_ret;
    ast::ISymbolScope           *m_sym_s;
};

}
