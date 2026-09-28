/**
 * TaskCheckImports.h
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
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The rules 18.1.3 sets on where an import is written, checked once for each
 * import in a user unit (symbol-resolution plan 6.5):
 *
 * - an explicit import shall not name something the importing namespace
 *   declares (CH17-30), nor the same name another explicit import in the
 *   same scope takes from a different package (CH17-31) -- PSS052;
 * - imports come first in their scope: only another import or a `compile
 *   if` may precede one (CH17-34) -- PSS053.
 *
 * PSS052 is an error. PSS053 stays a warning (decided 2026-09-28, plan
 * §8).
 *
 * Runs after the extensions are merged, when a component's import list also
 * holds those of its `extend component` statements, whose namespace is the
 * component's.
 */
class TaskCheckImports {
public:
    TaskCheckImports(ResolveContext *ctxt);

    virtual ~TaskCheckImports();

    /** `n_builtin_units`: the leading units that hold the core library. */
    void check(ast::IRootSymbolScope *root, uint32_t n_builtin_units);

private:
    void walk(ast::ISymbolScope *s, int32_t depth);

    void checkScope(ast::ISymbolScope *s);

    /** CH17-34: nothing but an import or a `compile if` before `imp`. */
    void checkFirst(ast::IPackageImportStmt *imp);

    /** The name an explicit, unaliased import makes visible; else empty. */
    static std::string importedName(ast::IPackageImportStmt *imp);

    /** "package 'p'", "component 'c'" or "the global scope". */
    std::string scopeDesc(ast::ISymbolScope *s) const;

    bool isUserUnit(const ast::Location &loc) const;

private:
    static dmgr::IDebug                     *m_dbg;
    ResolveContext                          *m_ctxt;
    ast::IRootSymbolScope                   *m_root;
    uint32_t                                m_n_builtin;
    std::set<ast::IPackageImportStmt *>     m_seen;
};

}
