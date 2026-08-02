/*
 * TaskResolveOverrideActions.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskResolveOverrideActions.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/ITypeScope.h"
#include "pssp/ast/ISymbolTypeScope.h"

namespace pssp {

TaskResolveOverrideActions::TaskResolveOverrideActions(ResolveContext *ctxt)
    : m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskResolveOverrideActions", ctxt->getDebugMgr());
}

TaskResolveOverrideActions::~TaskResolveOverrideActions() { }

void TaskResolveOverrideActions::resolve(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("resolve");
    visitScopeChildren(root);
    DEBUG_LEAVE("resolve");
}

void TaskResolveOverrideActions::visitScopeChildren(ast::ISymbolScope *i) {
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        // Only scopes can contain (or be) an override action. Restricting the
        // walk keeps this pass away from expressions entirely, so it cannot
        // perturb what the main resolution pass does.
        if (dynamic_cast<ast::ISymbolScope *>(it->get())) {
            it->get()->accept(m_this);
        }
    }
}

void TaskResolveOverrideActions::visitSymbolScope(ast::ISymbolScope *i) {
    visitScopeChildren(i);
}

void TaskResolveOverrideActions::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());

    if (!ts) {
        return;
    }

    // An unspecialized generic is never resolved -- its specializations are,
    // with their arguments bound. Matches TaskResolveSuperTypes.
    if (ts->getParams() && !ts->getParams()->getSpecialized()) {
        return;
    }

    ast::IAction *a = dynamic_cast<ast::IAction *>(ts);

    if (a) {
        if (a->getIs_override()) {
            checkOverride(i, a);
        } else {
            checkNotShadowingAnOverride(i, a);
        }
    }

    bool is_comp = (dynamic_cast<ast::IComponent *>(ts) != 0);

    if (is_comp) {
        m_comp_s.push_back(i);
    }

    visitScopeChildren(i);

    if (is_comp) {
        m_comp_s.pop_back();
    }
}

TaskResolveOverrideActions::Found TaskResolveOverrideActions::findInBaseChain(
        ast::ISymbolScope *comp, const std::string &name) {
    Found res;

    // Deliberately starts at the *base*: an override's target is by
    // definition not the declaring component's own declaration, which is the
    // override itself.
    ast::ISymbolScope *cur = comp;

    // A cycle in a super-type chain is diagnosed elsewhere; bound the walk so
    // that a malformed model cannot spin here.
    for (int32_t depth=0; cur && depth<100; depth++) {
        ast::ITypeScope *cur_ts = dynamic_cast<ast::ITypeScope *>(
            dynamic_cast<ast::ISymbolTypeScope *>(cur)
                ? dynamic_cast<ast::ISymbolTypeScope *>(cur)->getTarget()
                : 0);

        if (!cur_ts || !cur_ts->getSuper_t() || !cur_ts->getSuper_t()->getTarget()) {
            break;
        }

        ast::ISymbolRefPath *base_p = cur_ts->getSuper_t()->getTarget();
        ast::ISymbolScope *base_s = dynamic_cast<ast::ISymbolScope *>(
            m_ctxt->resolveSymbolPathRef(base_p));

        if (!base_s) {
            break;
        }

        std::unordered_map<std::string,int32_t>::const_iterator it =
            base_s->getSymtab().find(name);

        if (it != base_s->getSymtab().end()
            && it->second < (int32_t)base_s->getChildren().size()) {
            ast::ISymbolTypeScope *cand_s = dynamic_cast<ast::ISymbolTypeScope *>(
                base_s->getChildren().at(it->second).get());
            ast::IAction *cand = cand_s
                ? dynamic_cast<ast::IAction *>(cand_s->getTarget()) : 0;

            if (cand) {
                res.scope = base_s;
                res.action = cand;

                // The path to the base component, plus one step to the action
                // within it. There is no ElemKind that steps through a super
                // type, so the base component's own path is the only usable
                // starting point -- which is exactly what getSuper_t()
                // resolved to.
                res.path = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
                res.path->getPath() = base_p->getPath();
                res.path->getPath().push_back({
                    ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
                    it->second});
                return res;
            }
        }

        cur = base_s;
    }

    return res;
}

void TaskResolveOverrideActions::checkOverride(
        ast::ISymbolTypeScope *i, ast::IAction *a) {
    DEBUG_ENTER("checkOverride %s", i->getName().c_str());

    if (m_comp_s.empty()) {
        // The grammar only admits `override action` in a component body, so
        // this is unreachable from source. Guard rather than dereference.
        DEBUG("Note: override action %s outside a component", i->getName().c_str());
        DEBUG_LEAVE("checkOverride");
        return;
    }

    Found found = findInBaseChain(m_comp_s.back(), i->getName());

    if (!found.action) {
        // LRM 19.2.2a.
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            a->getName()->getLocation(),
            "cannot override action '%s': no action of that name is declared "
            "in a base component of '%s'",
            i->getName().c_str(),
            m_comp_s.back()->getName().c_str());
        DEBUG_LEAVE("checkOverride -- no target");
        return;
    }

    if (found.action->getParams() && found.action->getParams()->getParams().size()) {
        // LRM 19.2.2c. Reported in addition to binding the super type below:
        // the reference is well-formed, it is the overriding that is not
        // allowed, and suppressing the link would produce a second error for
        // every member the body uses.
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            a->getName()->getLocation(),
            "cannot override template action '%s'",
            i->getName().c_str());
    }

    DEBUG("Override %s resolves to an action in '%s'",
        i->getName().c_str(), found.scope->getName().c_str());

    a->getSuper_t()->setTarget(found.path);

    m_ctxt->addRef(
        a->getSuper_t()->getElems().front()->getId()->getLocation().fileid,
        found.action->getLocation().fileid);

    DEBUG_LEAVE("checkOverride");
}

void TaskResolveOverrideActions::checkNotShadowingAnOverride(
        ast::ISymbolTypeScope *i, ast::IAction *a) {
    if (m_comp_s.empty()) {
        return;
    }

    Found found = findInBaseChain(m_comp_s.back(), i->getName());

    if (found.action && found.action->getIs_override()) {
        // LRM 19.2.2b. Note this fires only when the base declaration is
        // itself an override: a base component declaring a plain action of
        // the same name is a different situation, and the LRM does not
        // require the keyword there.
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            a->getName()->getLocation(),
            "action '%s' must be declared 'override': '%s' declares it as an "
            "override action",
            i->getName().c_str(),
            found.scope->getName().c_str());
    }
}

dmgr::IDebug *TaskResolveOverrideActions::m_dbg = 0;

}
