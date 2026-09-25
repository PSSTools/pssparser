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
#include "dmgr/IDebugMgr.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include <map>
#include <string>
#include <vector>
#include "pssp/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {

class ResolveContext;

class TaskApplyTypeExtensions : public ast::VisitorBase {
public:
    TaskApplyTypeExtensions(
        dmgr::IDebugMgr     *dmgr,
        IFactory            *factory,
        IMarkerListener     *marker_l);

    virtual ~TaskApplyTypeExtensions();

    void apply(ast::IRootSymbolScope *root);

    /**
     * Each member re-homed into an extended type, mapped to the scope that
     * lexically declared it.
     *
     * Valid only after apply(). Handed to ResolveContext so that a name in an
     * extension body can still be looked up in the extension's own package --
     * LRM 17.2 associates an extension with "the nearest package that
     * lexically encloses its definition", which is not in general the package
     * the extended type lives in. See known-issues CL-N1.
     */
    const std::map<ast::IScopeChild *, ast::ISymbolScope *> &
        extensionDeclScopes() const { return m_ext_decl_scope; }


    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitEnumItem(ast::IEnumItem *i) override;

protected:
    /**
     * Put the enclosing scopes back in scope for an `extend` target lookup.
     *
     * Without this an unqualified target name resolves against the root only.
     */
    void seedCtxtScope(ResolveContext &ctxt);

    /**
     * Merge the body of one `extend` into the type it extends: members
     * first, then any `extend` nested in the body (LRM 17.3), whose target
     * may be one of those members.
     */
    void applyExtension(
        ast::ISymbolExtendScope *ext,
        ast::ISymbolScope       *target_s,
        ast::ISymbolRefPath     *target_p,
        ast::ISymbolScope       *decl_s);

    /**
     * An `extend` or `extend enum` written inside an `extend component`. LRM
     * 17.3 allows it only for a type defined in the component, so the target
     * is looked up among the component's own members.
     */
    void applyNestedExtension(
        ast::IScopeChild        *nested,
        ast::ISymbolScope       *target_s,
        ast::ISymbolRefPath     *target_p,
        ast::ISymbolScope       *decl_s);

    void applyEnumExtension(
        ast::IExtendEnum        *i,
        ast::ISymbolEnumScope   *target_s);

    /**
     * Contribute one member of an `extend` body to the extended type's
     * logical scope, keyed by name when it has one.
     */
    void mergeChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        ast::ISymbolScope       *decl_s);

    /**
     * A function declared or defined in an extension joins the function of
     * the same name in the extended type (LRM 20.3): a prototype in one and
     * the body in the other is one function.
     */
    void mergeFunctionScope(
        ast::ISymbolFunctionScope   *existing,
        ast::ISymbolFunctionScope   *incoming);

    /**
     * The package an extension belongs to: "the nearest package that
     * lexically encloses its definition" (17.2). The root stands for the
     * global package.
     */
    ast::ISymbolScope *packageOf(ast::ISymbolScope *decl_s) const;

    std::string packageDesc(ast::ISymbolScope *pkg) const;

    /**
     * Also contribute an extension body to a *generic* type's AST scope.
     *
     * Specializations are built by copying the generic's AST, not its symbol
     * scope, so an extension merged only into the symbol scope is invisible to
     * every instance. No-op for non-templated targets, which are never copied.
     */
    void mergeIntoGenericAst(
        ast::ISymbolScope       *target_s,
        ast::IExtendType        *ext);

    void addChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        const std::string       &name,
        ast::ISymbolScope       *pkg=0);

    void appendChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child);

    /**
     * Record child `idx` of `target`, named `name`, as contributed by an
     * extension in package `pkg` (SymbolTypeScope.ext_members).
     */
    void recordExtMember(
        ast::ISymbolScope       *target,
        const std::string       &name,
        int32_t                 idx,
        ast::ISymbolScope       *pkg);

    /**
     * PSS003 at `dup`, with a "first declared here" note at `orig`.
     */
    void reportDuplicate(
        ast::IScopeChild        *dup,
        ast::IScopeChild        *orig,
        const std::string       &msg);

    void reportDuplicate(
        const ast::Location     &loc,
        const ast::Location     *orig,
        const std::string       &msg);


private:
    static dmgr::IDebug                     *m_dbg;
    IFactory                                *m_factory;
    IMarkerListener                         *m_marker_l;
    ast::IRootSymbolScope                   *m_root;
    ISymbolTableIteratorUP                  m_symtab_it;
    std::map<ast::IScopeChild *, ast::ISymbolScope *> m_ext_decl_scope;

};

}
