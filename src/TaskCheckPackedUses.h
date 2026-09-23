/**
 * TaskCheckPackedUses.h
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
#include <tuple>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/TaskClassifyPackable.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The use-site rules for packed types: where the core library's generics
 * that need a packed size are *used*.
 *
 * - ``sizeof_s<T>``: T must be packable (21.13.2.1, PSS015).
 * - ``reg_c<R, ACC, SZ>``: R must have a size, and SZ must be at least that
 *   size (21.14.1, PSS014). An SZ with no primitive access function -- not 8,
 *   16, 32 or 64 -- is a warning (21.14.5, PSS016).
 *
 * The specialization itself cannot report these: it is made once per
 * distinct argument list, has no use-site location, and lives in the core
 * library. So this walks the user's model after resolution and recognizes
 * each type reference (``reg_c<my_s> r;``, ``: reg_c<my_s, READWRITE, 32>``)
 * and static path (``sizeof_s<my_s>::nbits``) that lands on one.
 *
 * See docs/design/packed-struct-checks-plan.md, section 1.4-1.5.
 */
class TaskCheckPackedUses : public ast::VisitorBase {
public:
    TaskCheckPackedUses(ResolveContext *ctxt);

    virtual ~TaskCheckPackedUses();

    void check(ast::IRootSymbolScope *root);

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

    /**
     * Declared parameter lists are not uses. `reg_c`'s own default
     * `SZ = (8*sizeof_s<R>::nbytes)` is the obvious example.
     */
    virtual void visitTemplateParamDeclList(ast::ITemplateParamDeclList *i) override { }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

private:
    void checkUse(ast::ISymbolTypeScope *spec, const ast::Location &loc);

    void checkSizeof(ast::ITypeScope *spec, const ast::Location &loc);

    void checkReg(ast::ITypeScope *spec, const ast::Location &loc);

    ast::IDataType *typeParam(ast::ITypeScope *spec, const char *name);

    void report(
        MarkerSeverityE         severity,
        const ast::Location     &loc,
        const std::string       &msg,
        ast::IScopeChild        *related);

    static std::string typeDesc(ast::IDataType *t);

private:
    static dmgr::IDebug                                 *m_dbg;
    ResolveContext                                      *m_ctxt;
    TaskClassifyPackable                                m_classifier;
    TaskResolveSymbolPathRef                            m_resolver;
    // Each node once: it is reachable both as a symbol-scope child and
    // through the scope's AST target.
    std::set<void *>                                    m_visited;
    std::set<std::tuple<int32_t,int32_t,int32_t,std::string>> m_reported;
};

}
