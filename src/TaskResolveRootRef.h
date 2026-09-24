/**
 * TaskResolveRootRef.h
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
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IFactory.h"
#include "TaskResolveBase.h"

namespace pssp {




class TaskResolveRootRef : public TaskResolveBase {
public:
    TaskResolveRootRef(
        ResolveContext      *ctxt,
        bool                search_imp=true);

    virtual ~TaskResolveRootRef();

    ast::ISymbolRefPath *resolve(const ast::IExprId *id);

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override;

    // 4.7.1 -- consult a template scope's own symtab (its iterator, index and
    // declared variables) without descending into the body.
    virtual void visitTemplateString(ast::ITemplateString *i) override;

    virtual void visitTemplateBlock(ast::ITemplateBlock *i) override;

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

//    virtual void visitSymbolExecScope(ast::ISymbolExecScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitSymbolDeclaration(ast::ISymbolDeclaration *i) override;

    enum class SuperStatus {
        Ok,
        NoType,         //!< not inside a type at all
        NoBase,         //!< the context type declares no base type
        BaseUnresolved, //!< it does, but the base did not resolve (already reported)
        NotFound        //!< the base, and what it inherits, has no such member
    };

    struct SuperResult {
        SuperStatus             status = SuperStatus::NoType;
        ast::ISymbolTypeScope   *type_s = 0;    //!< the context type
        ast::ISymbolScope       *base_s = 0;    //!< its base type's scope
    };

    /**
     * `super.<id>`: `id` looked up in the context type's base type, and in
     * what that inherits -- not in the context type, and not lexically
     * (17.1, Table 27). The context type is the one `this` names. Null on a
     * miss, with the reason in `res`.
     */
    ast::ISymbolRefPath *resolveSuper(
        const ast::IExprId          *id,
        SuperResult                 &res);

    /**
     * The context type -- what `this` names -- or null outside any type.
     */
    ast::ISymbolTypeScope *contextType();

    /**
     * True for a scope in which a name is visible only after its declaration
     * (18.2a/b, 4.7.1.2): exec and activity blocks, and template strings.
     */
    static bool isOrderSensitive(const ast::ISymbolScope *s);

    /**
     * Where `c` declares its name: the name's own location when it has one.
     */
    static const ast::Location &declLocation(const ast::IScopeChild *c);

    /**
     * True if `decl` is declared after `use`, in the same file. False when
     * either position is unknown.
     */
    static bool declaredAfter(
        const ast::IScopeChild      *decl,
        const ast::Location         &use);

private:

    /**
     * Pops the (cloned) symbol-table iterator to the context type -- the
     * innermost enclosing type scope, passing over an inline `with` block's --
     * and returns it, or null outside any type.
     */
    ast::ISymbolTypeScope *seekContextType();

    /**
     * `this`: the context type (LRM 13.1.4). The innermost enclosing type
     * scope -- except in an inline `with` block, where the traversed
     * action's scope is innermost and `this` is the *containing* action.
     * Null outside any type.
     */
    ast::ISymbolRefPath *resolveThis();

    ast::ISymbolRefPath *searchImports(
        const ast::IExprId          *id,
        ast::ISymbolImportSpec      *imp);

    ast::ISymbolRefPath *searchImport(
        const ast::IExprId          *id,
        ast::IPackageImportStmt     *imp);

    /**
     * Look `id` up in the scope that declared the type extension this
     * reference sits inside, or in that scope's imports. Null when there is
     * no extension context, or the name is not there. See CL-N1.
     */
    ast::ISymbolRefPath *searchExtensionCtxt(const ast::IExprId *id);

    /**
     * A root-relative path to `s`, or null if one cannot be built.
     */
    ast::ISymbolRefPath *absPath(ast::ISymbolScope *s);

private:
    static dmgr::IDebug             *m_dbg;
    bool                            m_search_imp;
    const ast::IExprId              *m_id;
    ast::ISymbolRefPath             *m_ref;

    /**
     * How many super-type steps the search has taken from the scope the
     * symbol-table iterator is currently sitting on.
     *
     * The iterator walks *lexically* outward and is popped as it goes, so
     * ``getScopeSymbolPath()`` always names the scope being searched -- except
     * while ``visitSymbolTypeScope`` is recursing up an inheritance chain,
     * which the iterator knows nothing about. Each step there needs an
     * explicit ``ElemKind_Super`` element in the recorded path, or the base
     * type's child index gets appended to a path naming the *derived* type.
     * See known-issues CL-N4.
     */
    int32_t                         m_super_depth;

    /**
     * Set while resolveSuper searches a base type: only members count, so
     * the enum and import fallbacks in visitSymbolScope are skipped.
     */
    bool                            m_member_only;

    /**
     * The innermost declaration of the name hidden because it comes after the
     * reference (visitSymbolScope). Handed to the context when the whole
     * search misses, so the miss can be reported as a use before declaration.
     */
    ast::IScopeChild                *m_fwd_decl;

    /**
     * The static component function the walk has passed out of, and the
     * instance member of the component it then found (20.2). Handed to the
     * context as the static-context hint; see ResolveContext.
     */
    ast::ISymbolFunctionScope       *m_static_fn;
    ast::IScopeChild                *m_static_hit;
};

}
