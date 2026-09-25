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
#include <map>
#include <set>
#include <string>
#include <unordered_set>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/IOccurrenceCollector.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "OccurrenceCollector.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The completeness gate (INV-3; symbol-resolution plan 3.5): after
 * resolution, no reference in a user unit may be left unbound unless
 * something has been said about it.
 *
 * This is a *structural* check rather than another point fix, and that is the
 * whole reason it exists. Every silent-drop defect in this front end has had
 * the same shape -- a resolution path that fails, writes nothing to the marker
 * listener, and leaves a null target for a consumer to walk into. A check
 * written against one such path holds only until the next one is added; this
 * one holds for paths nobody has written yet. Whatever route a reference took,
 * if it is still unbound when resolution is over, it is reported here.
 *
 * Every reference node is checked: a TypeIdentifier, an ExprRefName and each
 * ExprRefPath form, which between them hold every `role: ref` field of the
 * schema (tests/python/baselines/reference-roles.yaml). What each name binds to
 * is read from OccurrenceCollector, the pass pssparser.refs reports, so the
 * gate and that API cannot disagree about what is bound. Within a reference,
 * only the first unbound name is considered: the ones after it were never
 * looked up.
 *
 * An unbound name is reported as one of two things:
 *
 * - PSS002, when no declaration anywhere in the model has that name: the
 *   model is wrong ("unknown identifier 'x'", "'p' has no member named 'x'").
 * - PSS042, when something of that name is declared: the resolver missed it,
 *   and that is a pssparser defect. Only on a model with no other error;
 *   with one, a miss is far more likely a consequence of it than a defect.
 *
 * Nothing is reported where an error was already reported at one of the
 * reference's names (ResolveContext::wasReported), nor after an element whose
 * own type failed to resolve: one mistake, one message.
 *
 * It runs *after* the whole of TaskResolveRefs deliberately. A reference into a
 * unit the walk has not reached yet is legitimately unresolved in the middle of
 * the pass. Measuring the end state makes this check independent of the order
 * the files were listed in, which is the property PSS 3.1 18.2 requires and
 * the one the diagnostics have to have too.
 *
 * Only user units are checked (the bundled stdlib is not), and the body of a
 * generic template is checked only where every specialization agrees
 * (OccurrenceResolution::Dependent is not reported). The constructs whose
 * resolution is not done yet are exempt; each exemption names the plan item
 * that removes it.
 */
class TaskCheckRefsResolved : public ast::VisitorBase {
public:
    TaskCheckRefsResolved(ResolveContext *ctxt);

    virtual ~TaskCheckRefsResolved();

    /**
     * Walks every user unit of `root` and reports each unbound reference.
     * `n_builtin_units` is the number of leading units that hold the bundled
     * core library.
     */
    void check(ast::IRootSymbolScope *root, uint32_t n_builtin_units);

    // The reference nodes.
    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

    virtual void visitExprRefName(ast::IExprRefName *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    /**
     * The body of an `extend` whose target does not resolve is never walked
     * by the resolver: the target's failure is the one report.
     */
    virtual void visitExtendType(ast::IExtendType *i) override;

    /**
     * An annotation of an unknown type is disregarded, with a warning
     * (7.13): nothing inside it is looked up. One with no warning was never
     * looked at, and its type is checked like any other reference.
     */
    virtual void visitAnnotation(ast::IAnnotation *i) override;

    /** A parameter name already reported where the parameter is written. */
    virtual void visitAnnotationParam(ast::IAnnotationParam *i) override;

    /** Tracks the enclosing types, for hasUnknownBase(). */
    virtual void visitTypeScope(ast::ITypeScope *i) override;

    // Exemptions: constructs the resolver does not bind yet.

    /** Coverage (WS10, R4): the covergroup's body is `visit: false`. */
    virtual void visitCovergroup(ast::ICovergroup *i) override { }

    /** Coverage (WS10, R4): a covergroup type's body. */
    virtual void visitCovergroupType(ast::ICovergroupType *i) override { }

    /** Coverage (WS10, R4): port-map names and options. */
    virtual void visitCovergroupInstantiation(ast::ICovergroupInstantiation *i) override;

    /** Pool binds (4.5, R4). */
    virtual void visitComponentBind(ast::IComponentBind *i) override { }

    /** Activity binds (4.5, R4). */
    virtual void visitActivityBindStmt(ast::IActivityBindStmt *i) override { }

    /** Scheduling constraints name labelled sub-activities (4.3, R4). */
    virtual void visitActivitySchedulingConstraint(
        ast::IActivitySchedulingConstraint *i) override { }

    /** Instance-override targets (U5). */
    virtual void visitInstanceOverride(ast::IInstanceOverride *i) override { }

    /** Struct-literal member names (U4, 8.9). The values are checked. */
    virtual void visitExprAggrStructElem(ast::IExprAggrStructElem *i) override;

    /**
     * A parameter *declaration* list is not checked.
     *
     * `struct S <type T = base_s>` names `base_s` as T's default. It binds
     * when the generic is specialized, and a generic nothing instantiates
     * never specializes -- which is legal, so an unbound default there is not
     * a finding.
     */
    virtual void visitTemplateParamDeclList(ast::ITemplateParamDeclList *i) override { }

private:
    /**
     * Checks one reference: `ids` are its names in order. `is_type` selects
     * the "unknown type" wording.
     */
    void checkRef(
        const std::vector<ast::IExprId *>   &ids,
        bool                                is_type);

    /** Whether `decl` has a declared type that failed to resolve. */
    static bool hasUnboundType(ast::IScopeChild *decl);

    /**
     * Whether a name looked up in `decl` -- a type, or something of a type --
     * may be one its unknown base type declares: somewhere up the super
     * chain, a base type failed to resolve.
     */
    bool reachesUnknownBase(ast::IScopeChild *decl);

    /** Whether `ts` or a type it inherits from has an unresolved base type. */
    bool hasUnknownBase(ast::ITypeScope *ts);

    /** Every name the model declares, from the units and the symbol tree. */
    void collectNames(ast::IRootSymbolScope *root);

    void collectSymtabNames(ast::IScopeChild *c, std::set<ast::IScopeChild *> &seen);

    static dmgr::IDebug                             *m_dbg;
    ResolveContext                                  *m_ctxt;
    OccurrenceCollector                             m_coll;
    std::map<OccurrenceCollector::LocKey, Occurrence> m_occ;
    std::set<std::string>                           m_names;
    std::unordered_set<ast::IExpr *>                m_checked;
    std::vector<ast::ITypeScope *>                  m_type_s;
    bool                                            m_had_errors;
};

}
