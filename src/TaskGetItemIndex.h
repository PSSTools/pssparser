/**
 * TaskGetItemIndex.h
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
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/ISymbolDeclaration.h"
#include "pssp/impl/ActivityScopes.h"
#include "pssp/impl/ProceduralScopes.h"

namespace pssp {




class TaskGetItemIndex :
    public virtual ast::VisitorBase {
public:

    virtual ~TaskGetItemIndex() { }

    int32_t get(ast::IScopeChild *c) {
        m_index = -1;
        if (ast::ISymbolScope *as = ActivityScopes::asScope(c)) {
            // Not visited: the generated visitor goes on into a compound
            // statement's bodies, and into a parallel's join spec, and each of
            // those overwrote the index. An activity scope's id is its position
            // in the scope that holds it (TaskBuildSymbolTree, WS4.1).
            return as->getId();
        }
        if (ProceduralScopes::isCompound(c)) {
            // The same descent: the visit would go on into the bodies, and
            // each of them overwrote the statement's own index (4.1b).
            return c->getIndex();
        }
        c->accept(m_this);
        return m_index;
    }


    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override {
        m_index = i->getIndex();
    }

    // Likewise not left to the default, which descends into the parameters
    // (see visitSymbolDeclaration).
    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) override {
        m_index = i->getIndex();
    }

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override {
        m_index = i->getIndex();
    }

    virtual void visitConstraintSymbolScope(ast::IConstraintSymbolScope *i) override {
        m_index = i->getConstraint()->getIndex();
    }

    virtual void visitExecScope(ast::IExecScope *i) override {
        if (i->getId() != -1) {
            m_index = i->getId();
        } else {
            m_index = i->getIndex();
        }
    }

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override {
        if (i->getId() != -1) {
            m_index = i->getId();
        } else {
            m_index = i->getIndex();
        }
    }

    // Same shape as repeat, and for the same reason: the loop's own symtab is
    // built by AstBuilderInt rather than TaskBuildSymbolTree, so `getId()` is
    // the position among a scope's *symbols* and `getIndex()` the position
    // among its children. Without this, the inherited SymbolChildrenScope
    // handler used getId() unconditionally and a `foreach` whose id and index
    // disagreed produced a ref-path that resolved to the loop statement
    // instead of to its iterator variable -- so `foreach (e : l) { e.f }`
    // linked or failed depending on where in the block the loop sat.
    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override {
        if (i->getId() != -1) {
            m_index = i->getId();
        } else {
            m_index = i->getIndex();
        }
    }

    virtual void visitScopeChild(ast::IScopeChild *i) override {
        m_index = i->getIndex();
    }

    virtual void visitScope(ast::IScope *i) override {
        m_index = i->getIndex();
    }

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolChild(ast::ISymbolChild *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolChildrenScope(ast::ISymbolChildrenScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override {
        if (i->getIndex() != -1) {
            m_index = i->getIndex();
        } else {
            m_index = i->getId();
        }
    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        m_index = i->getId();
    }

    // Not left to the default, which descends into the parameters: a
    // parameter's visitScopeChild then overwrote the index with its own -1,
    // so every path into a symbol body was unaddressable (4.4).
    virtual void visitSymbolDeclaration(ast::ISymbolDeclaration *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        m_index = i->getId();
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
        if (ts && ts->getParams() && ts->getParams()->getSpecialized()) {
            // A specialization is not a child of any scope: it is addressed
            // by its position in the generic's spec_types vector, and that
            // position is carried in the type scope's index (the convention
            // TaskGetSymbolRefPath::visitSymbolTypeScope already reads).
            // Using getId() here made every specialization after the first
            // resolve its own parameters through specialization 0.
            m_index = ts->getIndex();
        } else {
            m_index = i->getId();
        }
    }

protected:
    int32_t     m_index;

};

} /* namespace pssp */


