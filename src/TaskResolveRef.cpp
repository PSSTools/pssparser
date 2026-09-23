/*
 * TaskResolveRef.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskBuildParamValList.h"
#include "TaskGetSpecializedTemplateType.h"
#include "TaskSpecializeParameterizedRef.h"
#include "TaskResolveRef.h"
#include "TaskResolveRefs.h"
#include "TaskResolveRootRef.h"
#include "pssp/ast/IExprRefPath.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprRefPathStatic.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "TaskFindPathElem.h"
#include "TaskResolveFieldRef.h"
#include "CoreLibraryLookup.h"
#include "Marker.h"

#include <algorithm>

namespace pssp {


static int editDistance(const std::string &a, const std::string &b) {
    int m = a.size(), n = b.size();
    std::vector<std::vector<int>> dp(m+1, std::vector<int>(n+1, 0));
    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            int cost = (a[i-1] != b[j-1]) ? 1 : 0;
            dp[i][j] = std::min({dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost});
        }
    }
    return dp[m][n];
}

static std::string findCloseMatch(
        const std::string &name,
        ast::ISymbolScope *scope,
        int maxDist = 2) {
    std::string best;
    int bestDist = maxDist + 1;
    if (!scope) return best;
    for (auto &entry : scope->getSymtab()) {
        int d = editDistance(name, entry.first);
        if (d > 0 && d < bestDist) {
            bestDist = d;
            best = entry.first;
        }
    }
    return best;
}



TaskResolveRef::TaskResolveRef(
    ResolveContext                  *ctxt,
    bool                            search_imp,
    bool                            report_unresolved) : 
        TaskResolveBase(ctxt), m_search_imp(search_imp),
        m_report_unresolved(report_unresolved) {
    DEBUG_INIT("TaskResolveRef", ctxt->getDebugMgr());
    m_ref = 0;
}

TaskResolveRef::~TaskResolveRef() {

}

ast::ISymbolRefPath *TaskResolveRef::resolve(ast::ITypeIdentifier *type_id) {
    DEBUG_ENTER("resolve");

    // Push a copy of the symbol iterator
    type_id->accept(m_this);

    if (m_ref) {
        DEBUG("Result:");
        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=m_ref->getPath().begin();
            it!=m_ref->getPath().end(); it++) {
            DEBUG("  %d %d", it->kind, it->idx);
        }
    } else {
        DEBUG("Failed to resolve");
    }

    DEBUG_LEAVE("resolve %p (%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);
    return m_ref;
}

ast::ISymbolRefPath *TaskResolveRef::resolve(ast::IExpr *ref) {
    DEBUG_ENTER("resolve (RefPath)");
    ref->accept(m_this);
    DEBUG_LEAVE("resolve (RefPath) %p (%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);
    return m_ref;
}

void TaskResolveRef::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    DEBUG_ENTER("visitDataTypeUserDefined");
    if (i->getType_id()->getTarget()) {
        DEBUG("Symbol already resolved");
        DEBUG_LEAVE("visitDataTypeUserDefined");
        return;
    }
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i->getType_id());

    if (target) {
        DEBUG("Success");
        i->getType_id()->setTarget(target);
    } else {
        DEBUG("Failed");
        // char tmp[1024];
        // sprintf(tmp, "failed to find user-defined datatype");
        // IMarkerUP marker(m_factory->mkMarker(
        //     tmp,
        //     MarkerSeverityE::Error,
        //     i->getLocation()
        // ));
        // m_marker_l->marker(marker.get());
    }
    DEBUG_LEAVE("visitDataTypeUserDefined");
}

void TaskResolveRef::visitExprId(ast::IExprId *i) {
    DEBUG_ENTER("visitExprId %s", i->getId().c_str());

    ast::ISymbolRefPath *root = findRoot(i);

    m_ref = root;
    DEBUG_LEAVE("visitExprId %s (%p %d)", i->getId().c_str(), m_ref, (m_ref)?m_ref->getPath().size():-1);
}

void TaskResolveRef::visitExprMemberPathElem(ast::IExprMemberPathElem *i) {
    DEBUG_ENTER("visitExprMemberPathElem");
    DEBUG("TODO: visitExprMemberPathElem");
    DEBUG_LEAVE("visitExprMemberPathElem");
}

void TaskResolveRef::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("visitExprRefPathStaticRooted");
    DEBUG("TODO: visitExprRefPathStaticRooted");
    DEBUG_LEAVE("visitExprRefPathStaticRooted");
}

void TaskResolveRef::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext");
    DEBUG("Searching for root element (%s)", 
        i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
    ast::ISymbolRefPath *root = findRoot(i->getHier_id()->getElems().at(0)->getId());
    if (root) {
        if (i->getHier_id()->getElems().size() > 1) {
            DEBUG("TODO: only the first of %d path elements is resolved",
                (int)i->getHier_id()->getElems().size());
        }
        m_ref = root;
    } else {
        // Not reported here: the caller decides whether a miss is an error.
        // This printed "Error: ..." to stdout with nothing counted; the
        // traversal targets that reached it are still silent until the
        // traversal rewrite (symbol-resolution-plan.md 4.2, K6/U7), and are
        // tracked as silent T-miss slots meanwhile.
        DEBUG("Failed to find root element (%s)",
            i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
        DEBUG_LEAVE("visitExprRefPathContext -- not found");
        return;
    }

    DEBUG_LEAVE("visitExprRefPathContext");
}

void TaskResolveRef::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic");
    DEBUG("TODO: visitExprRefPathStatic");
    DEBUG_LEAVE("visitExprRefPathStatic");
}

void TaskResolveRef::visitSymbolScope(ast::ISymbolScope *i) { 
//    m_ref = 
}

void TaskResolveRef::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {

}

void TaskResolveRef::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) { 

}

void TaskResolveRef::visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) {
    DEBUG_ENTER("visitTemplateParamTypeValue");
    i->getValue()->accept(m_this);
    DEBUG_LEAVE("visitTemplateParamTypeValue");
}

/**
 * Resolve a qualified expression-form template argument -- `a[c_c::N]`.
 *
 * Deliberately *not* TaskResolveRefs::visitExprRefPathStatic, which is where
 * the general version of this walk lives. That one runs a TaskIsPyRef check
 * on each element it resolves, and TaskIsPyRef walks the whole type scope it
 * is handed. Reached from here the walk re-enters the very field whose array
 * dimension is being resolved, and recurses until the stack runs out: a
 * component with `bit[2] a[c_c::N]` and any action in it overflowed at
 * ~182,000 frames.
 *
 * So this is the same walk with nothing in it but the lookup: no pyref
 * probe, no specialization, no diagnostics. A parameterized qualifier
 * (`Q<8>::N`) is left unresolved rather than specialized here; it behaves as
 * it did before, and specializing from inside argument resolution is how the
 * recursion above starts.
 */
ast::ISymbolRefPath *TaskResolveRef::resolveStaticArgPath(
        ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("resolveStaticArgPath");

    if (i->getIs_global() || !i->getBase().size()) {
        DEBUG_LEAVE("resolveStaticArgPath -- unsupported form");
        return 0;
    }

    ast::ISymbolRefPath *target = 0;

    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
        it=i->getBase().begin(); it!=i->getBase().end(); it++) {
        if ((*it)->getParams()) {
            DEBUG("Parameterized qualifier; leaving unresolved");
            return 0;
        }

        if (it == i->getBase().begin()) {
            target = findRoot((*it)->getId());

            if (!target) {
                DEBUG_LEAVE("resolveStaticArgPath -- root not found");
                return 0;
            }
            continue;
        }

        ast::ISymbolScope *scope_s = dynamic_cast<ast::ISymbolScope *>(
            m_ctxt->resolveSymbolPathRef(target));

        if (!scope_s) {
            DEBUG("Qualifier is not a scope");
            return 0;
        }

        TaskFindPathElem::Result res = TaskFindPathElem(
            m_ctxt->getDebugMgr(), m_ctxt->root()).find(scope_s, (*it)->getId());

        if (!res.sym) {
            DEBUG("No member named %s", (*it)->getId()->getId().c_str());
            return 0;
        }

        if (res.super_idx == 0) {
            target->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
                res.idx});
        } else {
            // A symbol path cannot encode a step through a base type; see the
            // same case in TaskResolveRefs::visitExprRefPathStatic.
            DEBUG("Member is inherited; path not extended");
        }
    }

    DEBUG_LEAVE("resolveStaticArgPath %p", target);
    return target;
}

void TaskResolveRef::visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) {
    DEBUG_ENTER("visitTemplateParamExprValue");
    // An expression-form template argument is written at the *use* site and
    // has to be resolved there, exactly as visitTemplateParamTypeValue does
    // for the type-form argument. This used to be an empty stub, and the
    // consequence was CL-N2: the unresolved expression was copied into the
    // specialization and resolved in the generic's declaring scope instead.
    // For a declared array -- which AstBuilderInt rewrites into the builtin
    // `array<T, SZ>` generic, the one generic in the tree whose argument
    // arrives as an already-parsed expression -- that scope is BuiltinsFactory's
    // separate global scope, so `bit[32] a[N]` could not see `N` at all.
    //
    // Only the target is recorded here; TaskCopyAst carries it into the
    // specialization under setPreserveExprTargets(), and TaskResolveRefs
    // honors an already-resolved target rather than resolving again.
    //
    // *Every* reference in the argument, not only a bare name: `S<N+1>` used
    // to resolve nothing here, because the argument is an ExprBin. Its `N`
    // was then resolved inside the new specialization's own parameter list,
    // where it found the callee's `N` -- a self-reference that left the
    // argument unevaluable (`T<?>`) and ended self-recursion silently (K5),
    // and bound the wrong `N` whenever caller and callee share a parameter
    // name (F5). See docs/design/symbol-resolution/A-crashes.md.
    //
    // The walk stops at a reference: its subscripts and arguments are part
    // of it and are resolved with it, where they are resolved at all.
    class ArgRefs : public ast::VisitorBase {
    public:
        ArgRefs(TaskResolveRef *r) : m_r(r) { }

        virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *rp) override {
            if (!rp->getTarget()) {
                ast::ISymbolRefPath *target = m_r->resolveStaticArgPath(rp);
                if (target) {
                    rp->setTarget(target);
                }
            }
        }

        virtual void visitExprRefPathContext(ast::IExprRefPathContext *rp) override {
            // Only the single-element form; a member path is resolved later,
            // in the specialization, as before.
            if (!rp->getTarget() && rp->getHier_id()->getElems().size() == 1) {
                const ast::IExprId *id = rp->getHier_id()->getElems().at(0)->getId();
                ast::ISymbolRefPath *target = m_r->findRoot(id);
                if (target) {
                    rp->setTarget(target);
                } else {
                    // A name that does not resolve where it is written does
                    // not resolve at all: an argument cannot refer to the
                    // callee's parameters. Report it here, and bind it to
                    // nothing so that resolving the copy inside the
                    // specialization cannot find the callee's own parameter
                    // of the same name -- `S<M+1>` with no `M` in scope used
                    // to bind S's `M` and link cleanly (plan 1.4 (d)).
                    m_r->m_ctxt->addErrorMarker(
                        id->getLocation(),
                        "unknown identifier '%s'",
                        id->getId().c_str());
                    rp->setTarget(unresolvable(m_r->m_ctxt));
                }
            }
        }

        /**
         * A target that resolves to nothing: an element no scope can have.
         * Distinct from no target at all, which later passes read as "not
         * yet resolved" and try again.
         */
        static ast::ISymbolRefPath *unresolvable(ResolveContext *ctxt) {
            ast::ISymbolRefPath *ret =
                ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
            ret->getPath().push_back(
                {ast::SymbolRefPathElemKind::ElemKind_ChildIdx, -1});
            return ret;
        }

    private:
        TaskResolveRef      *m_r;
    };

    if (i->getValue()) {
        ArgRefs v(this);
        i->getValue()->accept(&v);
    }
    DEBUG_LEAVE("visitTemplateParamExprValue");
}

void TaskResolveRef::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier %s", i->getElems().at(0)->getId()->getId().c_str());
	// Find the first element

    ast::ISymbolRefPath *root = findRoot(i->getElems().at(0)->getId());

    if (!root) {
        const std::string &name = i->getElems().at(0)->getId()->getId();
        DEBUG("Note: failed to resolve root symbol %s", name.c_str());
        if (!m_report_unresolved) {
            return;
        }
        std::string suggestion = findCloseMatch(
            name, dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()));
        // See the matching block in TaskResolveRefs::visitExprRefPathContext:
        // a core-library type that is simply not imported gets an actionable
        // message rather than a bare "unknown type".
        std::string core_pkg = findCoreLibraryPackage(
            dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()), name);

        if (!core_pkg.empty()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getElems().at(0)->getId()->getLocation(),
                "unknown type '%s'; declared in %s -- add "
                "'import %s::*;'",
                name.c_str(),
                core_pkg.c_str(),
                core_pkg.c_str());
        } else if (suggestion.empty()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getElems().at(0)->getId()->getLocation(),
                "unknown type '%s'",
                name.c_str());
        } else {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getElems().at(0)->getId()->getLocation(),
                "unknown type '%s'; did you mean '%s'?",
                name.c_str(),
                suggestion.c_str());
        }
        return;
    }

    if (i->getElems().at(0)->getParams()) {
        // Resolve parameter refs

        DEBUG_ENTER("resolve parameter references");
        for (std::vector<ast::ITemplateParamValueUP>::const_iterator
            it=i->getElems().at(0)->getParams()->getValues().begin();
            it!=i->getElems().at(0)->getParams()->getValues().end(); it++) {
            (*it)->accept(m_this);
        }
        DEBUG_LEAVE("resolve parameter references");

        ast::ISymbolRefPath *root_s = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                root, 
                i->getElems().at(0)->getParams(),
                i->getElems().at(0)->getId()->getLocation());

        delete root;
        root = root_s;

        if (!root_s) {
            // Had an error that will be marked by an error marker
            return;
        }
    }

    ast::IScopeChild *root_t = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(root);

    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
        it=i->getElems().begin()+1;
        it!=i->getElems().end(); it++) {
        ast::IScopeChild *next = TaskResolveFieldRef(m_ctxt).resolve(
            (*it)->getId(),
            root_t,
            root);

        if (next) {
            DEBUG("Resolve %s", (*it)->getId()->getId().c_str());
            if ((*it)->getParams()) {
               root = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                        root, 
                        (*it)->getParams(),
                        (*it)->getId()->getLocation());
               root_t = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(root);
            } else {
                root_t = next;
            }

        } else {
            // Before P2-A5a this branch was unreachable-in-practice noise: the
            // qualified lookup itself was broken, so *every* multi-element type
            // identifier landed here and reporting would have been all false
            // positives. Now that the lookup works, arriving here means the
            // name genuinely is not in the qualifying scope.
            DEBUG("Note: failed to resolve element %s", (*it)->getId()->getId().c_str());

            // A qualifier that is a component *instance* rather than a scope
            // is left alone. `tx::send_pkt s;` in an activity, with `tx` a
            // `tx_c` field, is legal PSS: the path is resolved by instance,
            // which this scope walk does not do, so the miss here says nothing
            // about the model. Reporting it rejected working models --
            // TaskCheckRefsResolved exempts the same shape, and for the same
            // reason (see its last-segment lookup).
            bool qualifier_is_instance =
                dynamic_cast<ast::IField *>(root_t) != 0
                || dynamic_cast<ast::IProceduralStmtDataDeclaration *>(root_t) != 0;

            if (m_report_unresolved && !qualifier_is_instance) {
                // Name the whole qualifying prefix, not just the root: with a
                // nested package `p::q::Nope`, "in 'p'" would point at the
                // wrong scope.
                std::string scope_name;
                for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
                    p_it=i->getElems().begin(); p_it!=it; p_it++) {
                    if (scope_name.size()) {
                        scope_name += "::";
                    }
                    scope_name += (*p_it)->getId()->getId();
                }
                m_ctxt->addMarker(
                    MarkerSeverityE::Error,
                    (*it)->getId()->getLocation(),
                    "unknown type '%s' in '%s'",
                    (*it)->getId()->getId().c_str(),
                    scope_name.c_str());
            }
            delete root;
            root = 0;
            break;
        }
    }

    m_ref = root;
    
    DEBUG_LEAVE("visitTypeIdentifier %p", m_ref);
}

ast::ISymbolRefPath *TaskResolveRef::findRoot(
        const ast::IExprId              *sym) {
    return TaskResolveRootRef(m_ctxt).resolve(sym);
}

dmgr::IDebug *TaskResolveRef::m_dbg = 0;

}
