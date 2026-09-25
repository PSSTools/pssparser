/**
 * TaskResolveImports.h
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
#include "pssp/IFactory.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "TaskResolveBase.h"

namespace pssp {




class TaskResolveImports : public TaskResolveBase {
public:
    TaskResolveImports(ResolveContext *ctxt);

    virtual ~TaskResolveImports();

    /**
     * Resolve the target of every import in the tree, each from where it is
     * written, so that no later pass meets an import not yet resolved. Run
     * once, right after the symbol tree is built; an import path names a
     * package or a type, never something an extension contributes, so
     * nothing it needs comes later.
     */
    void resolveAll(ast::IRootSymbolScope *root);

    /**
     * Resolve `sym_scope`'s own imports from the context's current position.
     * For a specialization, whose imports are copies made after resolveAll.
     */
    void resolve(ast::ISymbolScope *sym_scope);

    virtual void visitPackageImportStmt(ast::IPackageImportStmt *i) override;

private:
    void walk(ast::ISymbolScope *s);

    /**
     * 18.1.4's rules for the package aliases among `s`'s imports: two
     * aliases in one statement shall not share a name, and an alias in a
     * package or the global scope shall not take the name of a package
     * declared there, in this source unit or an earlier one. Run by
     * resolveAll only, so a specialization's copies are not checked again.
     */
    void checkAliases(ast::ISymbolScope *s);

    /** The source unit `fileid` was linked as, or -1 if unknown. */
    int32_t unitOf(int32_t fileid) const;

private:
    static dmgr::IDebug         *m_dbg;
    std::set<ast::ISymbolScope *>   m_visited;
    ast::IRootSymbolScope           *m_root;

};

}
