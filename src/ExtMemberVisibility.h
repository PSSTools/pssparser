/**
 * ExtMemberVisibility.h
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
#include <map>
#include <string>
#include <unordered_map>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/ast/IPackageScope.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ISymbolExtMember.h"
#include "pssp/ast/ISymbolTypeScope.h"

namespace pssp {

/**
 * Which of the members extensions contribute to a type a reference can see
 * (LRM 17.2.3; symbol-resolution plan 6.5, known-issues L-05).
 *
 * Two packages may each add a field or type of one name to a type, and the
 * type's layout holds both; SymbolTypeScope.ext_members records each with
 * its package. What a reference R sees of them, by 17.2.3:
 *
 * 1. the member its own package declares -- R's package, or one enclosing
 *    it, the innermost first -- which shadows the others;
 * 2. otherwise, one a package wildcard-imported where R is written declares
 *    (18.1.3: "a wildcard import also allows access ... to members declared
 *    in type extensions found in the imported package"); two such are an
 *    ambiguity, and "it shall be an error to reference it";
 * 3. otherwise, one an extension in the global scope, or in the package that
 *    declares the type, contributes. The LRM makes neither visible
 *    everywhere in so many words; both are, here, because their packages are
 *    the type's own, and because warning on them would fire on nearly every
 *    model that extends a type where it is declared.
 *
 * Anything else is not visible at R. Such a use still binds, to the member
 * the linker has always bound, and is warned about (warn-first, plan §8).
 *
 * The same rule applies to an enum item an `extend enum` adds (p46c): its
 * package is that of the statement it is written in.
 *
 * Everything is worked out from source positions, as NameLookup::appliesAt
 * works out an import's reach: R's package is the innermost `package`
 * statement whose extent holds R, and an import applies at R if R is inside
 * its statement. So a specialization's copies, which keep their source
 * locations, are answered as their originals are.
 */
class ExtMemberVisibility {
public:
    ExtMemberVisibility(
        dmgr::IDebugMgr         *dmgr,
        ast::IRootSymbolScope   *root);

    virtual ~ExtMemberVisibility();

    enum class Status {
        Visible,        //!< one member is visible; it is `idx`
        Hidden,         //!< none is; `idx` is the one bound anyway
        Ambiguous       //!< two imported packages declare it
    };

    struct Choice {
        Status                  status = Status::Visible;
        int32_t                 idx = -1;
        /** Hidden: the members not visible; Ambiguous: the rivals. */
        std::vector<ast::ISymbolExtMember *>  members;
    };

    /**
     * Which member named `name` of `t` a reference at `use` sees, when the
     * symtab entry for it is `symtab_idx`. The symtab's entry when no
     * extension contributes the name.
     */
    Choice choose(
        ast::ISymbolTypeScope   *t,
        const std::string       &name,
        int32_t                 symtab_idx,
        const ast::Location     &use);

    /**
     * True if item `idx` of enum `e` is one an `extend enum` adds, and not
     * visible at `use`; its package is then in `pkg`.
     */
    bool itemHidden(
        ast::ISymbolEnumScope   *e,
        int32_t                 idx,
        const ast::Location     &use,
        ast::ISymbolScope       *&pkg);

    /**
     * The innermost package whose `package` statement holds `loc`; the root
     * outside any, or when `loc` is unknown.
     */
    ast::ISymbolScope *packageAt(const ast::Location &loc);

    /** True for a package: a plain symbol scope its parent names. */
    bool isPackage(ast::ISymbolScope *s) const;

    /** "package 'p'", or "the global scope" for the root. */
    std::string packageDesc(ast::ISymbolScope *pkg) const;

    /** `import p::q::*;` spelled for package `pkg`. */
    std::string importFor(ast::ISymbolScope *pkg) const;

private:
    /** How `pkg` is seen from `use`; lower is nearer. See the class comment. */
    int32_t rank(
        ast::ISymbolScope       *pkg,
        ast::ISymbolScope       *type_pkg,
        ast::ISymbolScope       *use_pkg,
        const ast::Location     &use);

    /** True if a wildcard import of `pkg` applies at `use`. */
    bool imported(ast::ISymbolScope *pkg, const ast::Location &use);

    /** The package, or the root, the type `t` is declared in. */
    ast::ISymbolScope *declaringPackage(ast::ISymbolScope *t) const;

    void buildPackageIndex();

    void indexPackages(
        ast::IScope             *s,
        ast::ISymbolScope       *ns);

    void buildImportIndex();

    void indexImports(ast::ISymbolScope *s, int32_t depth);

    static bool contains(
        const ast::Location     &b,
        const ast::Location     &e,
        const ast::Location     &loc);

private:
    struct PkgStmt {
        ast::IPackageScope      *stmt;
        ast::ISymbolScope       *pkg;
    };

    static dmgr::IDebug                             *m_dbg;
    dmgr::IDebugMgr                                 *m_dmgr;
    ast::IRootSymbolScope                           *m_root;
    bool                                            m_pkg_built;
    /** Each file's `package` statements, outer before inner. */
    std::unordered_map<int32_t, std::vector<PkgStmt>> m_pkg_stmts;
    bool                                            m_imp_built;
    /** The wildcard imports of each package. */
    std::unordered_map<ast::ISymbolScope *, std::vector<ast::IPackageImportStmt *>> m_imports;
};

}
