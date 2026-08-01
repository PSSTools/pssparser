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
#include "pssp/impl/TaskGetName.h"

namespace pssp {

/**
 * Discards every marker.
 *
 * Used for an `extend` target lookup that is allowed to fail -- see
 * visitSymbolExtendScope.
 */
class SwallowMarkers : public IMarkerListener {
public:
    virtual void marker(const IMarker *m) override { }
    virtual bool hasSeverity(MarkerSeverityE s) override { return false; }
};



TaskApplyTypeExtensions::TaskApplyTypeExtensions(
    dmgr::IDebugMgr         *dmgr,
    IFactory                *factory,
    IMarkerListener         *marker_l) : 
        m_factory(factory), m_marker_l(marker_l) {
    DEBUG_INIT("TaskApplyTypeExtensions", dmgr);
    m_target_s = 0;
    m_type_scope_depth = 0;
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

/**
 * Resolve an `extend` target from where the `extend` statement is written.
 *
 * A bare ResolveContext starts its symbol-table iterator at the root, and
 * TaskResolveRootRef resolves an unqualified name by walking that iterator's
 * scope stack outward. With nothing on the stack but the root, the only names
 * in scope were the package names -- which is why `package p { struct S {}
 * extend struct S {} }` reported "unknown type 'S'; did you mean 'p'?" and only
 * a fully-qualified `p::S` ever resolved. LRM Example247 is written unqualified.
 *
 * The traversal already tracks the enclosing scopes in m_symtab_it; handing the
 * resolver a clone of it (a clone because the walk pops as it goes) puts the
 * declaring package, its imports, and any enclosing component back in scope.
 */
void TaskApplyTypeExtensions::seedCtxtScope(ResolveContext &ctxt) {
    ctxt.pushSymtab(m_symtab_it->clone());
}

void TaskApplyTypeExtensions::visitExtendEnum(ast::IExtendEnum *i) {
    DEBUG_ENTER("visitExtendEnum");
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
    seedCtxtScope(ctxt);
    ast::ISymbolRefPath *target_p = TaskResolveRef(&ctxt).resolve(i->getTarget());

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
            target_s->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
        } else {
            // TODO: duplicate name
        }
    }

    DEBUG_LEAVE("visitExtendEnum");
}

void TaskApplyTypeExtensions::visitExtendType(ast::IExtendType *i) {
    DEBUG_ENTER("visitExtendType");
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
    seedCtxtScope(ctxt);
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

    // Inside a type scope, a failed lookup is not reported. `override action A
    // { ... }` is built as an IExtendType targeting A (AstBuilderInt::
    // visitOverride_action_declaration), so an override and a real extension
    // are the same node here and cannot be told apart. They need opposite
    // lookups: LRM 17.3 restricts an in-component `extend` to a type defined
    // in that same component, while LRM 19.2.2a requires an override's target
    // to come from a *base* component -- and super types are not resolved
    // until after this pass, so an override's target cannot be found at all.
    //
    // Reporting the miss would put "unknown type 'base_a'" on LRM Example57,
    // which is valid. Staying quiet keeps an override a no-op, which is what
    // it has always been. Overriding is unimplemented either way; see
    // docs/pssparser-fix-plan.md.
    SwallowMarkers quiet;
    ResolveContext ctxt(
        m_factory,
        m_type_scope_depth?static_cast<IMarkerListener *>(&quiet):m_marker_l,
        m_root);
    seedCtxtScope(ctxt);
    ast::ISymbolRefPath *target_p = TaskResolveRef(&ctxt).resolve(
        ast_target->getTarget());

    if (!target_p) {
        DEBUG_LEAVE("visitSymbolExtendScope - resolution failure");
        return;
    }

    ast_target->getTarget()->setTarget(target_p);
    ast::IScopeChild *ext_target = m_symtab_it->resolveAbsPath(target_p);
    ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(ext_target);
    if (!target_s) {
        // The path resolved to something that is not a scope. A template
        // instance extension (`extend struct S<int>`) does this: its
        // reference path ends in an ElemKind_TypeSpec step, and no
        // specialization exists yet at this point in the link -- extensions
        // are applied before TaskResolveRefs creates any -- so the step
        // indexes into the generic's (empty) specialization list and lands on
        // an unrelated node. That node was then written to as though it were a
        // scope, which is the segfault. See visitSymbolExtendScope's caller
        // and TaskGetSpecializedTemplateType::mk.
        m_marker_l->marker(IMarkerUP(m_factory->mkMarker(
            "cannot extend a template instance: extending a specific "
            "specialization (LRM 17.2.6b) is not supported; extend the "
            "generic type instead, which applies to every instance",
            MarkerSeverityE::Error,
            ast_target->getTarget()->getElems().back()->getId()->getLocation())).get());
        DEBUG_LEAVE("visitSymbolExtendScope - target is not a scope");
        return;
    }
    DEBUG("Target scope: %s", target_s->getName().c_str());

    m_target_s = target_s;
    DEBUG("%d children in extension scope", i->getChildren().size());

    // Merge by name rather than by node type. Dispatching through accept()
    // needs one visit method per contributable construct, and anything
    // without one is silently dropped -- which is how plain fields went
    // missing. TaskGetName() answers for every named construct uniformly,
    // and what has no name (an anonymous constraint or exec block) is
    // appended positionally.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        mergeChild(target_s, it->get());
    }
    m_target_s = 0;

    mergeIntoGenericAst(target_s, ast_target);

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
    } else {
        // Not merging: this is the ordinary walk looking for `extend`
        // statements, and a type scope can contain them. LRM 17.3 makes a
        // component the *expected* place to write one -- "Extending types in a
        // component scope is only allowed for types that are defined in that
        // scope" -- so `component C { action A {...} extend action A {...} }`
        // is the normal form.
        //
        // This method used to stop here, which meant the walk never entered a
        // component at all and every extension written inside one was silently
        // dropped: the target resolved, no diagnostic was issued, and the
        // members simply were not there. Templates had nothing to do with it.
        m_type_scope_depth++;
        visitSymbolScope(i);
        m_type_scope_depth--;
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

void TaskApplyTypeExtensions::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope");
    if (m_target_s) {
        std::unordered_map<std::string,int32_t>::const_iterator it =
            m_target_s->getSymtab().find(i->getName()->getId());

        if (it == m_target_s->getSymtab().end()) {
            // Add new
            m_target_s->getChildren().push_back(ast::IScopeChildUP(i, false));
        } else {
            // TODO: name collision
        }
    }

    DEBUG_LEAVE("visitTypeScope");
}

void TaskApplyTypeExtensions::mergeIntoGenericAst(
        ast::ISymbolScope       *target_s,
        ast::IExtendType        *ext) {
    // Extending a *generic* has to reach the AST, not just the symbol tree.
    //
    // LRM 17.2.6a: extending the generic template type applies the extension
    // to every instance of it. But a specialization is not built from the
    // generic's symbol scope -- TaskGetSpecializedTemplateType::mk copies the
    // generic's **AST** type scope and builds a fresh symbol tree from the
    // copy. Everything this task merged above went into the symbol scope
    // only, so the copy never saw it and no specialization had the extension's
    // members: `extend struct p::S { int added; }` followed by `S<int> s;
    // s.added` reported "Failed to find elem added".
    //
    // Contributing to the AST as well is also what makes an extension body
    // that mentions a template parameter work at all. `extend struct p::S
    // { T w; }` has to bind `T` per instance, so the member must be *copied*
    // into each specialization and resolved there -- one shared node merged
    // into the generic could only ever have one binding.
    //
    // Non-templated types are left alone: they are never copied, so the symbol
    // merge above is the whole story for them, and adding the same nodes twice
    // would only create a second path to them.
    ast::ITypeScope *target_ast = dynamic_cast<ast::ITypeScope *>(
        target_s->getTarget());

    if (!target_ast || !target_ast->getParams()) {
        return;
    }

    DEBUG_ENTER("mergeIntoGenericAst %s", target_s->getName().c_str());
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=ext->getChildren().begin();
        it!=ext->getChildren().end(); it++) {
        // Non-owning, for the reason spelled out in addChild: the `extend`
        // statement holds the sole owning reference.
        target_ast->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
    }
    DEBUG_LEAVE("mergeIntoGenericAst %s", target_s->getName().c_str());
}

void TaskApplyTypeExtensions::mergeChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child) {
    // By value: get() returns a reference into the TaskGetName instance, so
    // binding to the temporary's result leaves a dangling reference.
    std::string name = TaskGetName().get(child);

    if (name.size()) {
        addChild(target, child, name);
    } else {
        // Anonymous contribution -- an unnamed constraint or an exec block.
        // It has no symtab entry to make, but it still belongs to the
        // extended type's logical body.
        DEBUG("Appending anonymous %s child", "extension");
        if (dynamic_cast<ast::ISymbolChild *>(child)) {
            dynamic_cast<ast::ISymbolChild *>(child)->setUpper(target);
        }
        target->getChildren().push_back(ast::IScopeChildUP(child, false));
    }
}

void TaskApplyTypeExtensions::addChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        const std::string       &name) {
    DEBUG_ENTER("addChild %s to %s", name.c_str(), target->getName().c_str());
    std::unordered_map<std::string,int32_t>::const_iterator it;

    if ((it=target->getSymtab().find(name)) == target->getSymtab().end()) {
        int32_t id = target->getChildren().size();
        if (dynamic_cast<ast::ISymbolChild *>(child)) {
            ast::ISymbolChild *sc = dynamic_cast<ast::ISymbolChild *>(child);
            sc->setUpper(target);
            // Re-index into the target. getId() is what
            // AstSymbolTableIterator emits as the ChildIdx step for this
            // scope, and until this was set it still held the member's
            // position in the `<extend>` scope. A function contributed by an
            // extension then resolved to whatever sat at that index in the
            // extended type, and paths through it dead-ended.
            sc->setId(id);
        }
        target->getSymtab().insert({name, id});
        // Non-owning: the logical (symbol) view borrows from the physical
        // view, which keeps the sole owning reference in its GlobalScope.
        // IScopeChildUP's implicit constructor defaults to owned=true, so
        // pushing the raw pointer here would make the extended type a second
        // owner of a node the `extend` statement already owns.
        target->getChildren().push_back(ast::IScopeChildUP(child, false));
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
