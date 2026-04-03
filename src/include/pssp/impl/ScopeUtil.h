/**
 * ScopeUtil.h
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
#include "pssp/ast/IScopeChild.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class ScopeUtil :
    public virtual ast::VisitorBase {
public:
    enum class Kind {
        Unknown,
        Constraint,
        SymbolChildScope,
        SymbolFuncScope,
        ProcBodyScope,
        ProcSymScope,
        Scope
    };

    ScopeUtil(ast::IScopeChild *c) {
        init(c);
    }

    virtual ~ScopeUtil() { }

    bool init(ast::IScopeChild *c) {
        m_kind = Kind::Unknown;
        if (c) {
            c->accept(m_this);
        }
        return valid();
    }

    bool valid() const {
        return (m_kind != Kind::Unknown);
    }

    ast::IScopeChild *get() const {
        switch (m_kind) {
            case Kind::SymbolChildScope: return m_scope.sym_cs;
            case Kind::SymbolFuncScope: return m_scope.sym_fs;
            case Kind::Scope: return m_scope.scope;
            case Kind::Constraint: return m_scope.constraint_s;
            case Kind::ProcBodyScope: return m_scope.proc_body_s;
        }
        return 0;
    }

    template <class T> T *getT() const {
        return dynamic_cast<T *>(get());
    }

/*
    const std::vector<ast::IScopeChildUP> &getChildren() {
        if (m_sym_cs) {
            return m_sym_cs->getChildren();
        } else if (m_scope) {
            return m_scope->getChildren();
        } else {
//            return m_null;
        }
    }
 */

    int32_t getNumChildren() const {
        switch (m_kind) {
            case Kind::SymbolChildScope:
                return m_scope.sym_cs->getChildren().size();
            case Kind::SymbolFuncScope:
                return m_scope.sym_fs->getChildren().size() + 1;
            case Kind::Scope:
                return m_scope.scope->getChildren().size();
            case Kind::Constraint:
                return m_scope.constraint_s->getConstraints().size();
            case Kind::ProcBodyScope:
                return 1;
            case Kind::ProcSymScope:
                // 'body' counts as 1
                return m_scope.proc_sym_s->getChildren().size() + 1;
        }
        return 0;
    }

    ast::IScopeChild *getChild(int32_t idx) {
        ast::IScopeChild *ret = 0;
        switch (m_kind) {
            case Kind::Constraint:
                if (idx < m_scope.constraint_s->getConstraints().size()) {
                    ret = m_scope.constraint_s->getConstraints().at(idx).get();
                }
                break;
            case Kind::Scope:
                if (idx < m_scope.scope->getChildren().size()) {
                    ret = m_scope.scope->getChildren().at(idx).get();
                }
                break;
            case Kind::SymbolChildScope:
                if (idx < m_scope.sym_cs->getChildren().size()) {
                    ret = m_scope.sym_cs->getChildren().at(idx).get();
                }
                break;
            case Kind::SymbolFuncScope:
                if (idx < m_scope.sym_fs->getChildren().size()) {
                    ret = m_scope.sym_fs->getChildren().at(idx).get();
                } else if (idx == m_scope.sym_fs->getChildren().size()) {
                    ret = m_scope.sym_fs->getBody();
                }
                break;
            case Kind::ProcBodyScope:
                if (idx == 0) {
                    ret = m_scope.proc_body_s->getBody();
                }
                break;
            case Kind::ProcSymScope:
                if (idx < m_scope.proc_sym_s->getChildren().size()) {
                    ret = m_scope.proc_sym_s->getChildren().at(idx).get();
                } else if (idx == m_scope.proc_sym_s->getChildren().size()) {
                    ret = m_scope.proc_sym_s->getBody();
                }
                break;
        }

        return ret;
    }

    std::string getName() {
        switch (m_kind) {
            case Kind::SymbolChildScope:
            case Kind::SymbolFuncScope:
                return m_scope.sym_cs->getName();
            case Kind::ProcSymScope:
                return m_scope.proc_sym_s->getName();
        }
        return "";
    }

    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override {
        m_kind = Kind::Constraint;
        m_scope.constraint_s = i;
    }

    virtual void visitConstraintScope(ast::IConstraintScope *i) override {
        m_kind = Kind::Constraint;
        m_scope.constraint_s = i;
    }

    virtual void visitExecScope(ast::IExecScope *i) override {
        m_kind = Kind::SymbolChildScope;
        m_scope.sym_cs = i;
    }

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override {
        //
    }

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override {
        m_kind = Kind::ProcSymScope;
        m_scope.proc_sym_s = i;
    }

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override {
        m_kind = Kind::ProcSymScope;
        m_scope.proc_sym_s = i;
    }

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) override {
        m_kind = Kind::ProcBodyScope;
        m_scope.proc_body_s = i;
    }

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) override {
        m_kind = Kind::ProcBodyScope;
        m_scope.proc_body_s = i;
    }

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override {
        m_kind = Kind::SymbolChildScope;
        m_scope.sym_cs = i;
    }

    virtual void visitSymbolChildrenScope(ast::ISymbolChildrenScope *i) override {
        m_kind = Kind::SymbolChildScope;
        m_scope.sym_cs = i;
    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        m_kind = Kind::SymbolFuncScope;
        m_scope.sym_fs = i;
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        m_kind = Kind::SymbolChildScope;
        m_scope.sym_cs = i;
    }

    virtual void visitScope(ast::IScope *i) override {
        m_kind = Kind::Scope;
        m_scope.scope = i;
    }

    virtual void visitTypeScope(ast::ITypeScope *i) override {
        m_kind = Kind::Scope;
        m_scope.scope = i;
    }

private:
    Kind                                m_kind;
    union {
        ast::IConstraintScope               *constraint_s;
        ast::ISymbolChildrenScope           *sym_cs;
        ast::ISymbolFunctionScope           *sym_fs;
        ast::IProceduralStmtSymbolBodyScope *proc_sym_s;
        ast::IProceduralStmtBody            *proc_body_s;
        ast::IScope                         *scope;
    }                                   m_scope;

};

} /* namespace pssp */


