/**
 * TaskApplyTypeExtensions.h
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
#include <set>
#include "dmgr/IDebugMgr.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "ResolveContext.h"

namespace pssp {



class TaskApplyTypeExtensions : public ast::VisitorBase {
public:
    TaskApplyTypeExtensions(
        dmgr::IDebugMgr     *dmgr,
        IFactory            *factory,
        IMarkerListener     *marker_l);

    virtual ~TaskApplyTypeExtensions();

    void apply(ast::IRootSymbolScope *root);

    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitEnumItem(ast::IEnumItem *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override;

protected:
    /**
     * Seed `ctxt` with the scope stack this walk is currently at.
     *
     * A freshly built ResolveContext starts at the root, so an extension target
     * named without qualification resolved only when the type happened to live
     * at the root: `package p { struct S {...} extend struct S {...} }` reported
     * `unknown type 'S'`.
     */
    void seedScope(ResolveContext &ctxt);

    void addChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        const std::string       &name,
        bool                    owned=true);

    /**
     * Append `child` to `target` without giving it a name.
     *
     * For the anonymous body items -- constraints, exec blocks, activities.
     * They are reached positionally rather than by lookup, and two of them are
     * not a redeclaration of each other, so registering them in the symtab is
     * both useless and actively wrong (see known-issues P2-A5c).
     */
    void addAnonChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        bool                    owned=true);


private:
    static dmgr::IDebug                     *m_dbg;
    IFactory                                *m_factory;
    IMarkerListener                         *m_marker_l;
    ast::IRootSymbolScope                   *m_root;
    ISymbolTableIteratorUP                  m_symtab_it;
    ast::ISymbolScope                       *m_target_s;

    // Set while walking the *AST* body of an extension rather than its symbol
    // scope. See visitSymbolExtendScope for why both walks are needed.
    bool                                    m_ast_body;

    // AST nodes the symbol-scope walk already re-homed, so the AST walk that
    // follows it can skip them.
    std::set<ast::IScopeChild *>            m_rehomed;

};

}
