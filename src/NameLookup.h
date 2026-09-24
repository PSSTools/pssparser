/**
 * NameLookup.h
 *
 * Copyright 2026 Matthew Ballance and Contributors
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
 */
#pragma once
#include <set>
#include <string>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/ast/ISymbolDeclaration.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ISymbolImportSpec.h"
#include "pssp/ast/ISymbolRefPath.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * Name lookup: the one implementation of LRM 18.3, with 17.2 (extensions),
 * 18.1.3 (imports) and 10.3 (template parameters). Every resolver asks this
 * class what a name means; none searches a symbol table itself.
 *
 * The procedure is report D §A (docs/design/symbol-resolution/D-namespaces.md).
 * An unqualified name is looked up along the scope stack of the context's
 * symbol-table iterator, innermost first:
 *
 * - **A block** (exec, activity, function body, template string, loop): its
 *   declarations, those before the use only (18.2a/b); then, for a function
 *   or a `symbol`, its parameters.
 * - **A type** T (b.1-b.4): T's members and T's own template parameters;
 *   then each base type's members, transitively -- never a base's imports
 *   and never its parameters (10.3); then T's imports.
 * - **The first package level** (c): for a member an `extend` contributed,
 *   the package chain of the `extend` statement comes first (17.2), from its
 *   package outward. Then the packages enclosing the extended type, which
 *   17.2 does not make visible but which the linker has always searched.
 * - **A package or the global scope** (c.1-c.3): its members, then its
 *   imports.
 *
 * At every level, the enum items of an enum declared directly in that scope
 * are found after its members. That is not 18.3 -- step a looks enum items up
 * by the expected type, which is 8.1 -- and 8.2 retires it.
 *
 * Imports are tiered (18.1.3): explicit before wildcard, and within a tier two
 * routes to one declaration are one match. More than one distinct target is
 * an ambiguity, reported (PSS017), and resolves to nothing.
 *
 * An import applies only inside the statement it is written in -- a
 * `package` statement, a component declaration or an `extend` -- or, in the
 * global scope, to the rest of its file (18.1.3, decision Q5). A namespace's
 * import list gathers the imports of every statement that opens it; those of
 * other statements are passed over (appliesAt()), and a miss one of them
 * would have satisfied leaves the context an import-leak hint.
 *
 * Not yet (symbol-resolution-plan.md): aliases (6.4); the visibility of
 * extension members by package, from SymbolTypeScope.ext_members (6.5);
 * step a (8.1).
 */
class NameLookup {
public:
    NameLookup(ResolveContext *ctxt);

    virtual ~NameLookup();

    /**
     * The unqualified name `id`, from the site the context's symbol-table
     * iterator is on. Null when nothing is found; the context then carries
     * the use-before-declaration hint for the miss (ResolveContext::
     * fwdDeclHint). Sets the static-context hint either way.
     */
    ast::ISymbolRefPath *lookupFirst(const ast::IExprId *id);

    /**
     * `::id`: a member of the global package, and nothing else (18.1.3) --
     * no imports, no enclosing scope.
     */
    ast::ISymbolRefPath *lookupGlobal(const ast::IExprId *id);

    /**
     * What a qualified step `ns::name` or `ns.name` finds.
     */
    struct Member {
        ast::IScopeChild    *sym = 0;
        /** Its index in the scope it was found in. */
        int32_t             idx = -1;
        /** How many base types were crossed to find it; 0 for `ns` itself. */
        int32_t             super_depth = -1;
        /**
         * For a name `ns` forwards to another package (F28), that package's
         * index in the root, where the path restarts; -1 otherwise.
         */
        int32_t             fwd_pkg = -1;

        /** Append this step to `path`, the path to `ns`. */
        void appendTo(ast::ISymbolRefPath *path) const;
    };

    /**
     * `name` as a member of `ns`. For a type, its own members and then each
     * base type's, transitively (18.3 b.1-b.3; Ex. 242). For a package, its
     * members -- never its imports (Ex. 271) -- and the names it forwards
     * (F28: addr_reg_pkg to std_pkg). Bounded on an inheritance ring,
     * which TaskCheckTypeCycles reports.
     */
    static Member lookupMember(
        dmgr::IDebugMgr             *dmgr,
        ast::ISymbolScope           *root,
        ast::ISymbolScope           *ns,
        const std::string           &name);

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
     * (17.1, Table 27). Null on a miss, with the reason in `res`.
     */
    ast::ISymbolRefPath *lookupSuper(
        const ast::IExprId          *id,
        SuperResult                 &res);

    /**
     * `this`: the context type (13.1.4). The innermost enclosing type scope
     * -- except in an inline `with` block, where the traversed action's scope
     * is innermost and `this` is the *containing* action. Null outside any
     * type.
     */
    ast::ISymbolRefPath *lookupThis();

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

    /**
     * True if import `imp` applies at `use`: `use` is inside the statement
     * the import is written in, or, for an import in the global scope, in
     * the same file (18.1.3, decision Q5). True when either position is
     * unknown.
     */
    static bool appliesAt(
        ast::IPackageImportStmt         *imp,
        const ast::Location             &use);

    /**
     * Report the miss on `id` as an import that does not reach it, if the
     * context holds an import-leak hint for it. `kind` is "type" or
     * "identifier". False, and nothing reported, when there is no hint.
     */
    static bool reportImportLeak(
        ResolveContext                  *ctxt,
        const ast::IExprId              *id,
        const char                      *kind);

    /** `imp` as written: `p::q::*`, `p::t` or `p as a`. */
    static std::string importText(ast::IPackageImportStmt *imp);

private:

    /**
     * The lexical search for m_id from the context's iterator: every level of
     * the scope stack, and the extension chain. The hit is in m_ref.
     */
    void walk();

    /**
     * Search one level of the scope stack -- the scope the iterator is on --
     * as its kind requires. True on a hit, which is in m_ref.
     */
    bool searchLevel(ast::ISymbolScope *s);

    /** A block, a package or the global scope: members, enum items, imports. */
    bool searchBlock(ast::ISymbolScope *s);

    /** b.1-b.4 for the type the iterator is on. */
    bool searchType(ast::ISymbolTypeScope *s);

    bool searchFunction(ast::ISymbolFunctionScope *s);

    bool searchSymbolDecl(ast::ISymbolDeclaration *s);

    /**
     * `s`'s own declarations. `order` applies 18.2a/b: in a block, a later
     * declaration is not in scope. `s` is m_super_depth base types above the
     * scope the iterator is on.
     */
    bool searchMembers(ast::ISymbolScope *s, bool order);

    /** Items of an enum declared directly in `s` (see the class comment). */
    bool searchEnumItems(ast::ISymbolScope *s);

    /**
     * b.3: `s`'s base types, transitively, members and enum items only.
     * With `members_only`, enum items too are skipped (`super.x`).
     */
    bool searchBases(ast::ISymbolScope *s, bool members_only);

    /**
     * The package chain of the `extend` statement that contributed the member
     * being resolved (17.2), from the statement's scope outward. `searched`
     * collects the scopes it covers, so that the lexical walk does not search
     * them twice.
     */
    bool searchExtensionChain(
        ast::ISymbolScope           *decl_s,
        std::set<ast::ISymbolScope *> &searched);

    /**
     * True for the global scope and for a package: the levels at which the
     * package chain (18.3 c) runs.
     */
    bool isPackageLevel(ast::ISymbolScope *s) const;

    ast::ISymbolRefPath *searchImports(
        const ast::IExprId          *id,
        ast::ISymbolImportSpec      *imp);

    ast::ISymbolRefPath *searchImport(
        const ast::IExprId          *id,
        ast::IPackageImportStmt     *imp);

    /**
     * Record a hit on `c`, child `idx` of `found_in`. The path is the
     * iterator's, then one ElemKind_Super per base type crossed, then `kind`
     * and `idx`; or, when m_abs_base is set (a scope that is not on the
     * iterator), that scope's absolute path instead of the iterator's.
     */
    void hit(
        ast::ISymbolScope           *found_in,
        ast::IScopeChild            *c,
        ast::SymbolRefPathElemKind  kind,
        int32_t                     idx);

    /**
     * Pop the iterator to the context type and return it; see contextType().
     */
    ast::ISymbolTypeScope *seekContextType();

    /**
     * A root-relative path to `s`, or null if one cannot be built.
     */
    ast::ISymbolRefPath *absPath(ast::ISymbolScope *s);

private:
    static dmgr::IDebug             *m_dbg;
    ResolveContext                  *m_ctxt;
    const ast::IExprId              *m_id;
    ast::ISymbolRefPath             *m_ref;

    /**
     * How many base types the search has crossed from the scope the iterator
     * is on. The iterator walks *lexically* and knows nothing of inheritance,
     * so each step needs an explicit ElemKind_Super in the recorded path, or
     * a base's child index lands on the derived type (CL-N4).
     */
    int32_t                         m_super_depth;

    /**
     * Set while searching a scope that is not on the iterator -- the
     * `extend` statement's package chain. The path starts from its absolute
     * path.
     */
    ast::ISymbolScope               *m_abs_base;

    /**
     * The innermost declaration of the name hidden because it comes after the
     * reference. Handed to the context when the whole search misses, so the
     * miss can be reported as a use before declaration.
     */
    ast::IScopeChild                *m_fwd_decl;

    /**
     * The static component function the walk has passed out of, and the
     * instance member of the component it then found (20.2). Handed to the
     * context as the static-context hint; see ResolveContext.
     */
    ast::ISymbolFunctionScope       *m_static_fn;
    ast::IScopeChild                *m_static_hit;

    /**
     * Search every import of a namespace, whether or not it applies at the
     * use: the pre-6.3a lookup, run only to explain a miss.
     */
    bool                            m_all_imports;

    /** The walk passed over an import that does not apply at the use. */
    bool                            m_skipped_imp;

    /** The import the hit in m_ref came through, if it came through one. */
    ast::IPackageImportStmt         *m_found_imp;
};

}
