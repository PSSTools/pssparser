/*
 * TaskApplyTypeExtensions.cpp
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
#include "ResolveContext.h"
#include "TaskApplyTypeExtensions.h"
#include "TaskResolveImports.h"
#include "TaskResolveRef.h"

namespace pssp {




TaskApplyTypeExtensions::TaskApplyTypeExtensions(
    dmgr::IDebugMgr         *dmgr,
    IFactory                *factory,
    IMarkerListener         *marker_l) : 
        m_factory(factory), m_marker_l(marker_l) {
    DEBUG_INIT("TaskApplyTypeExtensions", dmgr);
    m_target_s = 0;
    m_ast_body = false;
}

TaskApplyTypeExtensions::~TaskApplyTypeExtensions() {

}

void TaskApplyTypeExtensions::apply(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("apply");
    m_symtab_it = ISymbolTableIteratorUP(m_factory->mkAstSymbolTableIterator(root));

    m_root = root;
    root->accept(this);

    DEBUG_LEAVE("apply");
}

void TaskApplyTypeExtensions::visitExtendEnum(ast::IExtendEnum *i) {
    DEBUG_ENTER("visitExtendEnum");
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
    seedScope(ctxt);
    // report_unresolved=false: the marker below says the same thing with more
    // context, and letting both fire reported one mistake twice.
    ast::ISymbolRefPath *target_p =
        TaskResolveRef(&ctxt, true, false).resolve(i->getTarget());

    if (!target_p) {
        IMarkerUP marker(m_factory->mkMarker(
            "cannot extend unknown enum '" +
            i->getTarget()->getElems().at(0)->getId()->getId() + "'",
            MarkerSeverityE::Error,
            i->getTarget()->getElems().at(0)->getId()->getLocation()));
        m_marker_l->marker(marker.get());
        DEBUG_LEAVE("visitExtendEnum - name resolution failure");
        return;
    }

    i->getTarget()->setTarget(target_p);

    ast::IScopeChild *target = m_symtab_it->resolveAbsPath(i->getTarget()->getTarget());
    ast::ISymbolEnumScope *target_s = dynamic_cast<ast::ISymbolEnumScope *>(target);

    for (std::vector<ast::IEnumItemUP>::const_iterator
        it=i->getItems().begin();
        it!=i->getItems().end(); it++) {
        std::unordered_map<std::string,int32_t>::const_iterator s_it 
            = target_s->getSymtab().find((*it)->getName()->getId());
        
        if (s_it == target_s->getSymtab().end()) {
            // 
            int32_t id = target_s->getChildren().size();
            target_s->getSymtab().insert({(*it)->getName()->getId(), id});
            target_s->getChildren().push_back(it->get());
        } else {
            // TODO: duplicate name
        }
    }

    DEBUG_LEAVE("visitExtendEnum");
}

void TaskApplyTypeExtensions::visitExtendType(ast::IExtendType *i) {
    DEBUG_ENTER("visitExtendType");
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
    seedScope(ctxt);
    ast::ISymbolRefPath *target_p = TaskResolveRef(&ctxt).resolve(i->getTarget());

    if (!target_p) {
        IMarkerUP marker(m_factory->mkMarker(
            "cannot extend unknown type '" + 
            i->getTarget()->getElems().at(0)->getId()->getId() + "'",
            MarkerSeverityE::Error,
            i->getTarget()->getElems().at(0)->getId()->getLocation()));
        m_marker_l->marker(marker.get());
        DEBUG_LEAVE("visitExtendType - resolution failure");
        return;
    }

    i->getTarget()->setTarget(target_p);

    ast::IScopeChild *target = m_symtab_it->resolveAbsPath(i->getTarget()->getTarget());
    ast::ISymbolTypeScope *target_s = dynamic_cast<ast::ISymbolTypeScope *>(target);
    m_target_s = target_s;
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }
    m_target_s = 0;

    DEBUG_LEAVE("visitExtendType");
}

void TaskApplyTypeExtensions::visitRootSymbolScope(ast::IRootSymbolScope *i) {
    DEBUG_ENTER("visitRootSymbolScope");
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("visitRootSymbolScope");
}

void TaskApplyTypeExtensions::visitSymbolEnumScope(ast::ISymbolEnumScope *i) {
    DEBUG_ENTER("visitSymbolEnumScope");
    if (m_target_s) {
        addChild(m_target_s, i, i->getName());
    }
    DEBUG_LEAVE("visitSymbolEnumScope");
}

void TaskApplyTypeExtensions::visitSymbolExtendScope(ast::ISymbolExtendScope *i) {
    DEBUG_ENTER("visitSymbolExtendScope");
    ast::IExtendType *ast_target = dynamic_cast<ast::IExtendType *>(i->getTarget());
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
    seedScope(ctxt);
    ast::ISymbolRefPath *target_p = TaskResolveRef(&ctxt).resolve(
        ast_target->getTarget());

    if (!target_p) {
        DEBUG_LEAVE("visitSymbolExtendScope - resolution failure");
        return;
    }

    ast_target->getTarget()->setTarget(target_p);
    ast::IScopeChild *ext_target = m_symtab_it->resolveAbsPath(target_p);
    ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(ext_target);
    DEBUG("Target scope: %s", target_s->getName().c_str());
    
    m_target_s = target_s;
    DEBUG("%d children in extension scope", i->getChildren().size());
    m_rehomed.clear();
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        // Remember what this symbol scope stands for, so the second walk below
        // does not re-home the same declaration twice. Both forms occur: a type
        // declaration is a separate ISymbolTypeScope wrapping the AST node,
        // while an exec block is built as a symbol scope by the parser and so
        // is *the same object* in the AST body.
        ast::ISymbolScope *ss = dynamic_cast<ast::ISymbolScope *>(it->get());
        if (ss) {
            m_rehomed.insert(ss);
            if (ss->getTarget()) {
                m_rehomed.insert(ss->getTarget());
            }
        }
        it->get()->accept(this);
    }

    // A second walk, over the *AST* extension body, because the loop above
    // cannot see a plain field (P2-A5b).
    //
    // The extension's symbol scope is not synthetic, so
    // TaskBuildSymbolTree::addChild records a named child in its symtab while
    // mapping the name to the child's index in the AST scope rather than
    // pushing it into the symbol scope's children. Nested declarations survive
    // that -- an action or a function becomes a symbol scope of its own, which
    // is pushed -- but a field does not exist in `getChildren()` at all, so
    // `extend struct S { int b; }` contributed nothing to `S` and `s.b` was an
    // error.
    //
    // Resolution depends on this: TaskResolveRefs::visitSymbolExtendScope
    // deliberately skips extension bodies, on the understanding that their
    // contents are reached through the type they extend.
    m_ast_body = true;
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=ast_target->getChildren().begin();
        it!=ast_target->getChildren().end(); it++) {
        if (m_rehomed.find(it->get()) != m_rehomed.end()) {
            DEBUG("Skip %p -- already re-homed on the symbol pass", it->get());
            continue;
        }
        it->get()->accept(this);
    }
    m_ast_body = false;
    m_rehomed.clear();

    m_target_s = 0;

    DEBUG_LEAVE("visitSymbolExtendScope");
}

void TaskApplyTypeExtensions::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
    DEBUG_ENTER("visitSymbolFunctionScope");
    if (m_target_s) {
        addChild(m_target_s, i, i->getName());
    }
    DEBUG_LEAVE("visitSymbolFunctionScope");
}

void TaskApplyTypeExtensions::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
    if (m_target_s) {
        DEBUG("Adding to the target scope (%s)", m_target_s->getName().c_str());
        addChild(m_target_s, i, i->getName());
    }
    DEBUG_LEAVE("visitSymbolTypeScope");
}

void TaskApplyTypeExtensions::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope (%s)", i->getName().c_str());

    if (m_target_s) {
        addChild(m_target_s, i, i->getName());
    } else {
        if (i->getId() >= 0) {
            m_symtab_it->pushScope(i);
        }

        if (i->getImports()) {
            DEBUG_ENTER("  Resolve Imports");
            ResolveContext ctxt(m_factory, m_marker_l, m_root);
            TaskResolveImports(&ctxt).resolve(i);
            DEBUG_LEAVE("  Resolve Imports");
        }

        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            it->get()->accept(this);
        }

        if (i->getId() >= 0) {
            m_symtab_it->popScope();
        }
    }

    DEBUG_LEAVE("visitSymbolScope");
}

void TaskApplyTypeExtensions::visitPackageScope(ast::IPackageScope *i) {
    DEBUG_ENTER("visitPackageScope");
/*
    if (m_symtab_it->pushNamedScope(i->getId().at(0)->getId()) == -1) {
        // Internal error
    }

    ast::ISymbolScope *scope = m_symtab_it->getScope();
    if (scope->getImports()) {
        TaskResolveImports(m_factory, m_marker_l).resolve(
            m_symtab_it.get(),
            scope
        );
    }

    for (std::vector<ast::IScopeChild *>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }

    m_symtab_it->popScope();
 */
    DEBUG_LEAVE("visitPackageScope");
}

void TaskApplyTypeExtensions::visitEnumDecl(ast::IEnumDecl *i) {

}

void TaskApplyTypeExtensions::visitEnumItem(ast::IEnumItem *i) {

}

void TaskApplyTypeExtensions::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());

    // Only on the AST pass: a field is invisible to the symbol-scope walk (see
    // visitSymbolExtendScope). Non-owning, because the extension's AST node
    // owns the field -- the target scope holds an alias, exactly as
    // TaskBuildSymbolTree::addChild does for a type's own fields.
    if (m_target_s && m_ast_body) {
        addChild(m_target_s, i, i->getName()->getId(), false);
    }

    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
}

void TaskApplyTypeExtensions::visitConstraintBlock(ast::IConstraintBlock *i) {
    DEBUG_ENTER("visitConstraintBlock");

    // P2-A5c. A constraint block is not a symbol scope, so -- like a field --
    // it is invisible to the symbol-scope walk. Unlike a field it is anonymous
    // as far as lookup is concerned: TaskBuildSymbolTree registers a type's own
    // constraints with the unnamed addChild too, so the name of a constraint
    // block is never in any symtab.
    //
    // Getting it into the target's children is what makes it *checked*:
    // TaskResolveRefs skips extension bodies outright, so until this ran a typo
    // in a constraint added by an extension was silently accepted.
    if (m_target_s && m_ast_body) {
        addAnonChild(m_target_s, i, false);
    }

    DEBUG_LEAVE("visitConstraintBlock");
}

void TaskApplyTypeExtensions::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope");
    if (m_ast_body) {
        // Already handled on the symbol-scope pass, as an ISymbolTypeScope.
        DEBUG_LEAVE("visitTypeScope -- AST pass");
        return;
    }
    if (m_target_s) {
        std::unordered_map<std::string,int32_t>::const_iterator it =
            m_target_s->getSymtab().find(i->getName()->getId());

        if (it == m_target_s->getSymtab().end()) {
            // Add new
            m_target_s->getChildren().push_back(i);
        } else {
            // TODO: name collision
        }
    }

    DEBUG_LEAVE("visitTypeScope");
}

void TaskApplyTypeExtensions::addAnonChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        bool                    owned) {
    DEBUG_ENTER("addAnonChild to %s @ %d",
        target->getName().c_str(), (int32_t)target->getChildren().size());

    ast::ISymbolScope *ss = dynamic_cast<ast::ISymbolScope *>(child);
    if (ss) {
        ss->setId(target->getChildren().size());
    }
    if (dynamic_cast<ast::ISymbolChild *>(child)) {
        dynamic_cast<ast::ISymbolChild *>(child)->setUpper(target);
    }
    target->getChildren().push_back(ast::IScopeChildUP(child, owned));

    DEBUG_LEAVE("addAnonChild to %s", target->getName().c_str());
}

void TaskApplyTypeExtensions::seedScope(ResolveContext &ctxt) {
    if (m_symtab_it) {
        ctxt.pushSymtab(m_symtab_it->clone());
    }
}

void TaskApplyTypeExtensions::addChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        const std::string       &name,
        bool                    owned) {
    DEBUG_ENTER("addChild %s to %s", name.c_str(), target->getName().c_str());
    std::unordered_map<std::string,int32_t>::const_iterator it;

    if (name.empty() || name.at(0) == '<') {
        // An exec block is a symbol scope called `<exec>` and an activity is one
        // with no name at all, so the collision check below used to reject every
        // extension that carried either -- `extend component C { exec init_down
        // {...} }` reported "Type extension of <exec> conflicts with an existing
        // declaration" whether or not C had an exec of its own. Neither is ever
        // looked up by that name; both are simply appended (P2-A5c).
        //
        // Non-owning regardless of what the caller asked for: unlike the
        // ISymbolTypeScope built to wrap a nested declaration -- which nothing
        // else owns -- these scopes are built by the parser straight into the
        // extension's AST body, which owns them.
        addAnonChild(target, child, false);
        DEBUG_LEAVE("addChild %s to %s -- anonymous",
            name.c_str(), target->getName().c_str());
        return;
    }

    if ((it=target->getSymtab().find(name)) == target->getSymtab().end()) {
        int32_t id = target->getChildren().size();
        if (dynamic_cast<ast::ISymbolChild *>(child)) {
            dynamic_cast<ast::ISymbolChild *>(child)->setUpper(target);
        }
        target->getSymtab().insert({name, id});
        target->getChildren().push_back(ast::IScopeChildUP(child, owned));
    } else {
        std::string msg = "Type extension of ";
        msg += name + " conflicts with an existing declaration";

        IMarkerUP marker(m_factory->mkMarker(
            msg,
            MarkerSeverityE::Error,
            child->getLocation()
        ));
        m_marker_l->marker(marker.get());
    }
    DEBUG_LEAVE("addChild %s to %s", name.c_str(), target->getName().c_str());
}

dmgr::IDebug *TaskApplyTypeExtensions::m_dbg = 0;

}
