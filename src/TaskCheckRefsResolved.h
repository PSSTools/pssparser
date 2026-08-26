/**
 * TaskCheckRefsResolved.h
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
 *
 * Created on:
 *     Author:
 */
#pragma once
#include <set>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The completeness gate: after resolution, no type reference may still be
 * unbound.
 *
 * This is a *structural* check rather than another point fix, and that is the
 * whole reason it exists. Every silent-drop defect in this front end has had
 * the same shape -- a resolution path that fails, writes nothing to the marker
 * listener, and leaves a null target for a consumer to walk into:
 *
 *   - TaskResolveRefs::visitDataTypeUserDefined's failure branch was a
 *     commented-out marker, so an unresolvable field type produced no
 *     diagnostic, no count and no exit status at all;
 *   - the same null reached TaskIsPyRef, which printed `Error:` to stderr
 *     through DEBUG_ERROR -- uncounted, so a run could print 104 `Error:` lines
 *     and then report `0 errors in 0 files` and exit 0.
 *
 * A check written against either of those individually holds only until the
 * next such path is added. This one holds for paths nobody has written yet,
 * including every `TODO:` still in the resolver: whatever route a reference
 * took, if it is still unbound when resolution is over, it is reported here.
 *
 * It runs *after* the whole of TaskResolveRefs deliberately. A reference into a
 * unit the walk has not reached yet is legitimately unresolved in the middle of
 * the pass -- that mid-pass state is what made the old TaskIsPyRef messages a
 * function of file order. Measuring the end state instead makes this check
 * independent of the order the files were listed in, which is the property PSS
 * 3.1 18.2 requires and the one the diagnostics have to have too.
 *
 * Only user units are checked; the bundled stdlib is skipped (see
 * `resolve()`), because an incomplete stdlib is a known, separate problem and
 * reporting it on every run would train users to ignore this check.
 */
class TaskCheckRefsResolved : public ast::VisitorBase {
public:
    TaskCheckRefsResolved(ResolveContext *ctxt);

    virtual ~TaskCheckRefsResolved();

    /**
     * Walks every user unit of `root` and reports each unresolved type
     * reference as an error marker. `n_builtin_units` is the number of
     * leading units that hold the bundled core library.
     */
    void check(ast::IRootSymbolScope *root, uint32_t n_builtin_units);

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    /**
     * A parameter *declaration* list is not checked.
     *
     * `struct S <type T = base_s>` names `base_s` as T's default. It binds
     * when the generic is specialized, and a generic nothing instantiates
     * never specializes -- which is legal, so an unbound default there is not
     * a finding. The specializations that do exist are reached through
     * getSpec_types() and checked with their arguments substituted, which is
     * where a real failure would show.
     */
    virtual void visitTemplateParamDeclList(ast::ITemplateParamDeclList *i) override { }

private:
    /**
     * Collects the names every type declaration introduces as template
     * parameters, so `T item;` inside `struct S<struct T>` is not reported.
     */
    class ParamNameCollector;

    static dmgr::IDebug         *m_dbg;
    ResolveContext              *m_ctxt;
    std::set<ast::IScopeChild *> m_visited;
    std::set<std::string>        m_param_names;
    std::set<std::string>        m_type_names;
};

}
