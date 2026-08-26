/*
 * TaskResolveSuperTypes.cpp
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
#include "TaskResolveSuperTypes.h"
#include "TaskResolveRef.h"
#include "TaskResolveImports.h"
#include "pssp/ast/ITypeScope.h"
#include "pssp/ast/IAction.h"

namespace pssp {

TaskResolveSuperTypes::TaskResolveSuperTypes(ResolveContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskResolveSuperTypes", ctxt->getDebugMgr());
}

TaskResolveSuperTypes::~TaskResolveSuperTypes() { }

void TaskResolveSuperTypes::resolve(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("resolve");
    m_ctxt->pushSymtab(m_ctxt->getFactory()->mkAstSymbolTableIterator(root));

    // Imports must be resolved before super-type identifiers, since a super
    // type is routinely named through one. TaskApplyTypeExtensions already
    // resolves package-level imports and TaskResolveRefs resolves them again,
    // so this pass repeating the work is consistent with existing behaviour.
    if (root->getImports()) {
        TaskResolveImports(m_ctxt).resolve(root);
    }

    visitScopeChildren(root);

    m_ctxt->popSymtab();
    DEBUG_LEAVE("resolve");
}

void TaskResolveSuperTypes::visitScopeChildren(ast::ISymbolScope *i) {
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        // Only scopes carry (or contain) super-type references. Restricting
        // the walk here keeps the pass away from expressions and statements
        // entirely, so it cannot perturb anything the main pass does.
        if (dynamic_cast<ast::ISymbolScope *>(it->get())) {
            it->get()->accept(m_this);
        }
    }
}

void TaskResolveSuperTypes::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
    m_ctxt->symtab()->pushScope(i);
    if (i->getImports()) {
        TaskResolveImports(m_ctxt).resolve(i);
    }
    visitScopeChildren(i);
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitSymbolScope %s", i->getName().c_str());
}

void TaskResolveSuperTypes::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());

    if (!i_ts) {
        return;
    }

    DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());

    // An unspecialized generic has no meaningful resolution context; the
    // main pass skips it for the same reason, and its specializations are
    // created later with their arguments bound.
    if (i_ts->getParams() && !i_ts->getParams()->getSpecialized()) {
        DEBUG("Note: skipping unspecialized templated type");
        DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
        return;
    }

    m_ctxt->symtab()->pushScope(i);

    // A type scope's own imports matter here: a super type is routinely
    // named through one (`component c { import p::*; action a : base_a {} }`).
    if (i->getImports()) {
        TaskResolveImports(m_ctxt).resolve(i);
    }

    ast::IAction *i_a = dynamic_cast<ast::IAction *>(i_ts);

    if (i_a && i_a->getIs_override()) {
        // An override action's super type spells its own name (LRM 19.2.2),
        // so the ordinary lookup would find this very declaration and make
        // the type its own base. TaskResolveOverrideActions resolves it in
        // the enclosing component's base chain instead, after this whole
        // pass has finished -- it needs every component's super type already
        // resolved to walk more than one level up.
        DEBUG("Note: deferring super type of override action %s",
            i->getName().c_str());
    } else if (i_ts->getSuper_t() && !i_ts->getSuper_t()->getTarget()) {
        DEBUG("Resolving super type of %s", i->getName().c_str());
        ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(
            i_ts->getSuper_t());

        if (target) {
            ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
            if (target_c) {
                // Keep the file-dependency bookkeeping the main pass would
                // otherwise have done here.
                m_ctxt->addRef(
                    i_ts->getSuper_t()->getElems().front()->getId()->getLocation().fileid,
                    target_c->getLocation().fileid);
            }
            i_ts->getSuper_t()->setTarget(target);
        } else {
            // Silent by design -- the main pass re-attempts and reports.
            DEBUG("Note: super type of %s did not resolve in the pre-pass",
                i->getName().c_str());
        }
    }

    visitScopeChildren(i);

    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
}

dmgr::IDebug *TaskResolveSuperTypes::m_dbg = 0;

}
