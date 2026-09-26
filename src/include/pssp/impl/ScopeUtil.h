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
#include "pssp/ast/IGenericConstraintDeclValue.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/ActivityScopes.h"
#include "pssp/impl/ProceduralScopes.h"

namespace pssp {




class ScopeUtil :
    public virtual ast::VisitorBase {
public:
    enum class Kind {
        Unknown,
        Constraint,
        SymbolChildScope,
        SymbolFuncScope,
        ProcCompound,
        ProcSymScope,
        ActivityScope,
        // A value generic constraint (13.1.2): its parameters, reached by
        // ElemKind_ArgIdx, and no children.
        GenericConstraint,
        Scope
    };

    ScopeUtil(ast::IScopeChild *c) {
        init(c);
    }

    virtual ~ScopeUtil() { }

    bool init(ast::IScopeChild *c) {
        m_kind = Kind::Unknown;
        m_bodies.clear();
        if (!c) {
            // Nothing to classify.
        } else if (ast::ISymbolScope *as = ActivityScopes::asScope(c)) {
            // Classified before the visit, which would descend into a
            // compound statement's bodies and answer for the last of them.
            m_kind = Kind::ActivityScope;
            m_scope.sym_cs = as;
            ActivityScopes::bodies(c, m_bodies);
        } else if (ProceduralScopes::isCompound(c)) {
            // Likewise, and the statement has no children of its own: its
            // bodies are the whole of its address space (4.1b).
            m_kind = Kind::ProcCompound;
            m_scope.proc_c = c;
            ProceduralScopes::bodies(c, m_bodies);
        } else {
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
            case Kind::ProcCompound: return m_scope.proc_c;
            case Kind::ProcSymScope: return m_scope.proc_sym_s;
            case Kind::ActivityScope: return m_scope.sym_cs;
            case Kind::GenericConstraint: return m_scope.proc_c;
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
            case Kind::ProcCompound:
                return m_bodies.size();
            case Kind::ProcSymScope:
                // 'body' counts as 1
                return m_scope.proc_sym_s->getChildren().size() + 1;
            case Kind::ActivityScope:
                // A compound statement's bodies follow its children.
                return m_scope.sym_cs->getChildren().size() + m_bodies.size();
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
            case Kind::ProcCompound:
                if (idx >= 0 && idx < (int32_t)m_bodies.size()) {
                    ret = m_bodies.at(idx);
                }
                break;
            case Kind::ProcSymScope:
                if (idx < m_scope.proc_sym_s->getChildren().size()) {
                    ret = m_scope.proc_sym_s->getChildren().at(idx).get();
                } else if (idx == m_scope.proc_sym_s->getChildren().size()) {
                    ret = m_scope.proc_sym_s->getBody();
                }
                break;
            case Kind::ActivityScope: {
                int32_t n_c = m_scope.sym_cs->getChildren().size();
                if (idx >= 0 && idx < n_c) {
                    ret = m_scope.sym_cs->getChildren().at(idx).get();
                } else if (idx >= n_c && idx-n_c < (int32_t)m_bodies.size()) {
                    ret = m_bodies.at(idx-n_c);
                }
            } break;
        }

        return ret;
    }

    std::string getName() {
        switch (m_kind) {
            case Kind::SymbolChildScope:
            case Kind::SymbolFuncScope:
            case Kind::ActivityScope:
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

    // Explicit, so the visit does not go on into the parameters.
    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) override {
        m_kind = Kind::Constraint;
        m_scope.constraint_s = i;
    }

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override {
        m_kind = Kind::GenericConstraint;
        m_scope.proc_c = i;
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

    // 4.7.1 -- the same shape as TaskGetSymbolScope's overrides. The generated
    // visitors descend: visitTemplateString routes through visitSymbolScope
    // (recording the string) and then walks its elements, each of which is
    // itself a SymbolScope and *overwrites* what was just recorded. So asking
    // for a template's children used to hand back its last element's.
    virtual void visitTemplateString(ast::ITemplateString *i) override {
        m_kind = Kind::SymbolChildScope;
        m_scope.sym_cs = i;
    }

    virtual void visitTemplateBlock(ast::ITemplateBlock *i) override {
        m_kind = Kind::SymbolChildScope;
        m_scope.sym_cs = i;
    }

    virtual void visitTemplateElem(ast::ITemplateElem *i) override {
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
    // Kind::ActivityScope and Kind::ProcCompound: the compound statement's
    // bodies, in address order.
    std::vector<ast::IScopeChild *>     m_bodies;
    union {
        ast::IConstraintScope               *constraint_s;
        ast::ISymbolChildrenScope           *sym_cs;
        ast::ISymbolFunctionScope           *sym_fs;
        ast::IProceduralStmtSymbolBodyScope *proc_sym_s;
        ast::IScopeChild                    *proc_c;
        ast::IScope                         *scope;
    }                                   m_scope;

};

} /* namespace pssp */


