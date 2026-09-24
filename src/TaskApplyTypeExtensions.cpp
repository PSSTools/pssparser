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
#include <algorithm>
#include "dmgr/impl/DebugMacros.h"
#include "ResolveContext.h"
#include "TaskApplyTypeExtensions.h"
#include "FunctionScopeUtil.h"
#include "TaskBuildSymbolTree.h"
#include "pssp/ast/IActionHandleField.h"
#include "pssp/ast/IConstraintBlock.h"
#include "pssp/ast/ICovergroupInstantiation.h"
#include "pssp/ast/IExecScope.h"
#include "pssp/ast/IFieldClaim.h"
#include "pssp/ast/IFieldCompRef.h"
#include "pssp/ast/IFieldRef.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IGenericConstraintDeclBool.h"
#include "pssp/ast/ISymbolExtMember.h"
#include "pssp/ast/ITypedefDeclaration.h"
#include "TaskResolveRef.h"
#include "TaskResolveRootRef.h"
#include "pssp/impl/TaskGetName.h"

namespace pssp {

TaskApplyTypeExtensions::TaskApplyTypeExtensions(
    dmgr::IDebugMgr         *dmgr,
    IFactory                *factory,
    IMarkerListener         *marker_l) : 
        m_factory(factory), m_marker_l(marker_l) {
    DEBUG_INIT("TaskApplyTypeExtensions", dmgr);
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
 * NameLookup resolves an unqualified name by walking that iterator's
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
    // Guarded: apply() is not the only entry point, and a walk that has not
    // established a symtab iterator yet would otherwise dereference null.
    if (m_symtab_it) {
        ctxt.pushSymtab(m_symtab_it->clone());
    }
}

void TaskApplyTypeExtensions::visitExtendEnum(ast::IExtendEnum *i) {
    DEBUG_ENTER("visitExtendEnum");
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
    seedCtxtScope(ctxt);
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

    // The name resolved, but not to an enum: `extend enum s` where s is a
    // struct or a component. The cast is then null and the loop below writes
    // through it. This is reachable from ordinary mistyped source, so it has
    // to be a marker and not a crash.
    if (!target_s) {
        IMarkerUP marker(m_factory->mkMarker(
            "cannot extend '" +
            i->getTarget()->getElems().at(0)->getId()->getId() +
            "' as an enum: it is not an enum type",
            MarkerSeverityE::Error,
            i->getTarget()->getElems().at(0)->getId()->getLocation()));
        m_marker_l->marker(marker.get());
        DEBUG_LEAVE("visitExtendEnum - target is not an enum");
        return;
    }

    applyEnumExtension(i, target_s);

    DEBUG_LEAVE("visitExtendEnum");
}

void TaskApplyTypeExtensions::visitRootSymbolScope(ast::IRootSymbolScope *i) {
    DEBUG_ENTER("visitRootSymbolScope");
    // Every import is already resolved (TaskResolveImports::resolveAll), so a
    // root-level `extend` sees the root-level imports (F23).
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("visitRootSymbolScope");
}

void TaskApplyTypeExtensions::visitSymbolEnumScope(ast::ISymbolEnumScope *i) {
    // Nothing to do: an enum holds no `extend`. The override stops the base
    // visitor walking its items.
}

void TaskApplyTypeExtensions::visitSymbolExtendScope(ast::ISymbolExtendScope *i) {
    DEBUG_ENTER("visitSymbolExtendScope");
    ast::IExtendType *ast_target = dynamic_cast<ast::IExtendType *>(i->getTarget());

    // A failed lookup is reported wherever the `extend` is written. Inside a
    // type scope it used to be swallowed, because `override action A` was
    // built as an extension of A and its target could not be found this
    // early. An override is an Action now (AstBuilderInt::
    // visitOverride_action_declaration), so a miss here is a real one
    // (report F, N1).
    ResolveContext ctxt(m_factory, m_marker_l, m_root);
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

    // The scope that lexically declared the extension -- the package holding
    // the `extend` statement. Recorded per member so that TaskResolveRefs can
    // put it back in scope when it walks the member in its new home; see
    // ResolveContext::pushExtensionCtxt and known-issues CL-N1.
    //
    // Taken from the symbol-table iterator rather than from i->getUpper(),
    // which is null: TaskBuildSymbolTree::addChild does not set `upper` on an
    // extend scope. The iterator is where this walk tracks its position (see
    // visitSymbolScope), and the `<extend>` scope is not itself pushed, so
    // getScope() is the enclosing package -- or the enclosing component, for
    // the in-component form LRM 17.3 allows, whose own chain reaches the
    // package anyway.
    ast::ISymbolScope *decl_s = m_symtab_it?m_symtab_it->getScope():0;

    applyExtension(i, target_s, target_p, decl_s);

    DEBUG_LEAVE("visitSymbolExtendScope");
}

void TaskApplyTypeExtensions::applyExtension(
        ast::ISymbolExtendScope *ext,
        ast::ISymbolScope       *target_s,
        ast::ISymbolRefPath     *target_p,
        ast::ISymbolScope       *decl_s) {
    DEBUG_ENTER("applyExtension %s", target_s->getName().c_str());
    DEBUG("%d children in extension scope", ext->getChildren().size());

    // Merge by name rather than by node type. Dispatching through accept()
    // needs one visit method per contributable construct, and anything
    // without one is silently dropped -- which is how plain fields went
    // missing. TaskGetName() answers for every named construct uniformly,
    // and what has no name (an anonymous constraint or exec block) is
    // appended positionally.
    std::vector<ast::IScopeChild *> nested;
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=ext->getChildren().begin();
        it!=ext->getChildren().end(); it++) {
        if (dynamic_cast<ast::ISymbolExtendScope *>(it->get())
                || dynamic_cast<ast::IExtendEnum *>(it->get())) {
            // Not a member: an `extend` of one of the target's own types.
            // Merged into the target, it was a stray child that nothing
            // applied (report F, N1).
            nested.push_back(it->get());
            continue;
        }
        if (decl_s) {
            m_ext_decl_scope[it->get()] = decl_s;
        }
        mergeChild(target_s, it->get(), decl_s);
    }

    // The extension's imports join the type's, where the type level of a
    // lookup (18.3 b.4) searches them. They apply only inside the `extend`
    // statement (NameLookup::appliesAt), so the type's own body and its other
    // extensions do not see them. Resolved already, from the extension's own
    // site (TaskResolveImports::resolveAll).
    if (ext->getImports() && ext->getImports()->getImports().size()) {
        if (!target_s->getImports()) {
            target_s->setImports(m_factory->getAstFactory()->mkSymbolImportSpec());
        }
        std::vector<ast::IPackageImportStmt *> &dst =
            target_s->getImports()->getImports();
        for (std::vector<ast::IPackageImportStmt *>::const_iterator
                it=ext->getImports()->getImports().begin();
                it!=ext->getImports()->getImports().end(); it++) {
            if (std::find(dst.begin(), dst.end(), *it) == dst.end()) {
                dst.push_back(*it);
            }
        }
    }

    ast::IExtendType *ast_ext = dynamic_cast<ast::IExtendType *>(ext->getTarget());
    if (ast_ext) {
        mergeIntoGenericAst(target_s, ast_ext);
    }

    for (std::vector<ast::IScopeChild *>::const_iterator
        it=nested.begin(); it!=nested.end(); it++) {
        applyNestedExtension(*it, target_s, target_p, decl_s);
    }

    DEBUG_LEAVE("applyExtension %s", target_s->getName().c_str());
}

void TaskApplyTypeExtensions::applyNestedExtension(
        ast::IScopeChild        *nested,
        ast::ISymbolScope       *target_s,
        ast::ISymbolRefPath     *target_p,
        ast::ISymbolScope       *decl_s) {
    ast::ISymbolExtendScope *ext = dynamic_cast<ast::ISymbolExtendScope *>(nested);
    ast::IExtendEnum *ext_e = dynamic_cast<ast::IExtendEnum *>(nested);
    ast::ITypeIdentifier *tid = (ext)?
        dynamic_cast<ast::IExtendType *>(ext->getTarget())->getTarget() :
        ext_e->getTarget();
    const char *kind = (ext)?"type":"enum";

    // 17.3: "Extending types in a component scope is only allowed for types
    // that are defined in that scope." So the name is one of the component's
    // own members -- including one an extension of it has just contributed --
    // and a qualified name cannot be.
    std::unordered_map<std::string,int32_t>::const_iterator it =
        target_s->getSymtab().end();
    if (tid->getElems().size() == 1) {
        it = target_s->getSymtab().find(tid->getElems().at(0)->getId()->getId());
    }

    const ast::Location &loc = tid->getElems().back()->getId()->getLocation();
    if (it == target_s->getSymtab().end()) {
        m_marker_l->marker(IMarkerUP(m_factory->mkMarker(
            std::string("cannot extend unknown ") + kind + " '"
                + tid->getElems().back()->getId()->getId() + "' in '"
                + target_s->getName() + "'; an extension inside a component "
                + "may extend only a type the component declares (17.3)",
            MarkerSeverityE::Error,
            loc)).get());
        return;
    }

    ast::IScopeChild *c = target_s->getChildren().at(it->second).get();
    ast::ISymbolRefPath *path = m_factory->getAstFactory()->mkSymbolRefPath();
    path->getPath() = target_p->getPath();
    path->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second});
    tid->setTarget(path);

    if (ext) {
        ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(c);
        if (!ts) {
            m_marker_l->marker(IMarkerUP(m_factory->mkMarker(
                "cannot extend '" + tid->getElems().back()->getId()->getId()
                    + "': it is not an extendable type",
                MarkerSeverityE::Error,
                loc)).get());
            return;
        }
        applyExtension(ext, ts, path, decl_s);
    } else {
        ast::ISymbolEnumScope *es = dynamic_cast<ast::ISymbolEnumScope *>(c);
        if (!es) {
            m_marker_l->marker(IMarkerUP(m_factory->mkMarker(
                "cannot extend '" + tid->getElems().back()->getId()->getId()
                    + "' as an enum: it is not an enum type",
                MarkerSeverityE::Error,
                loc)).get());
            return;
        }
        applyEnumExtension(ext_e, es);
    }
}

void TaskApplyTypeExtensions::applyEnumExtension(
        ast::IExtendEnum        *i,
        ast::ISymbolEnumScope   *target_s) {
    for (std::vector<ast::IEnumItemUP>::const_iterator
        it=i->getItems().begin();
        it!=i->getItems().end(); it++) {
        const std::string &name = (*it)->getName()->getId();
        std::unordered_map<std::string,int32_t>::const_iterator s_it
            = target_s->getSymtab().find(name);

        if (s_it == target_s->getSymtab().end()) {
            int32_t id = target_s->getChildren().size();
            target_s->getSymtab().insert({name, id});
            target_s->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
        } else {
            // 7.5.1 g: an enum item is unique "across its initial definition
            // and extensions". No per-package exemption, unlike a field.
            reportDuplicate(
                it->get(),
                target_s->getChildren().at(s_it->second).get(),
                "duplicate declaration of enum item '" + name + "' in '"
                    + target_s->getName() + "': an enum item must be unique "
                    "across the enum and all its extensions (7.5.1)");
        }
    }
}

void TaskApplyTypeExtensions::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
    // Nothing to do: a function holds no `extend`.
}

void TaskApplyTypeExtensions::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
    // The ordinary walk looking for `extend` statements, and a type scope
    // can contain them. LRM 17.3 makes a component the *expected* place to
    // write one -- "Extending types in a component scope is only allowed for
    // types that are defined in that scope" -- so `component C { action A
    // {...} extend action A {...} }` is the normal form.
    //
    // This method used to stop here, which meant the walk never entered a
    // component at all and every extension written inside one was silently
    // dropped: the target resolved, no diagnostic was issued, and the
    // members simply were not there. Templates had nothing to do with it.
    visitSymbolScope(i);
    DEBUG_LEAVE("visitSymbolTypeScope");
}

void TaskApplyTypeExtensions::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope (%s)", i->getName().c_str());

    {
        if (i->getId() >= 0) {
            m_symtab_it->pushScope(i);
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

namespace {

/**
 * A field or a type: the two kinds of member LRM 17.2.3 lets extensions in
 * different packages each declare under one name.
 */
bool isFieldOrType(ast::IScopeChild *c) {
    return dynamic_cast<ast::IField *>(c)
        || dynamic_cast<ast::IFieldRef *>(c)
        || dynamic_cast<ast::IFieldCompRef *>(c)
        || dynamic_cast<ast::IFieldClaim *>(c)
        || dynamic_cast<ast::IActionHandleField *>(c)
        || dynamic_cast<ast::ICovergroupInstantiation *>(c)
        || dynamic_cast<ast::ISymbolTypeScope *>(c)
        || dynamic_cast<ast::ISymbolEnumScope *>(c)
        || dynamic_cast<ast::ITypedefDeclaration *>(c);
}

}

void TaskApplyTypeExtensions::mergeChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        ast::ISymbolScope       *decl_s) {
    // By value: get() returns a reference into the TaskGetName instance, so
    // binding to the temporary's result leaves a dangling reference.
    std::string name = TaskGetName().get(child);

    // A plain constraint whose name the type already has is appended
    // unnamed, as every constraint was before constraints were named (5.4):
    // tests/python/linking/test_type_extension_semantics.py pins same-named
    // constraints from two extensions as conjoining. Whether 17.2.3's
    // uniqueness rule covers them is open (symbol-resolution-plan §11).
    ast::IConstraintBlock *cb = dynamic_cast<ast::IConstraintBlock *>(child);
    if (name.size() && cb
            && !dynamic_cast<ast::IGenericConstraintDeclBool *>(child)
            && target->getSymtab().find(name) != target->getSymtab().end()) {
        ast::IScopeChild *prev = target->getChildren().at(
            target->getSymtab().find(name)->second).get();
        if (dynamic_cast<ast::IConstraintBlock *>(prev)
                && !dynamic_cast<ast::IGenericConstraintDeclBool *>(prev)) {
            name = "";
        }
    }

    if (name.size()) {
        addChild(target, child, name, packageOf(decl_s));
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

ast::ISymbolScope *TaskApplyTypeExtensions::packageOf(ast::ISymbolScope *decl_s) const {
    // decl_s is the enclosing package, or a component for the in-component
    // form (17.3); a component's `upper` leads out to its package. A package
    // is a plain symbol scope, with no declaration of its own to point at.
    ast::ISymbolScope *s = decl_s;
    while (s && dynamic_cast<ast::ISymbolTypeScope *>(s)) {
        s = s->getUpper();
    }
    return (s)?s:m_root;
}

std::string TaskApplyTypeExtensions::packageDesc(ast::ISymbolScope *pkg) const {
    if (!pkg || dynamic_cast<ast::IRootSymbolScope *>(pkg)) {
        return "outside any package";
    }
    return "in package '" + pkg->getName() + "'";
}

void TaskApplyTypeExtensions::reportDuplicate(
        ast::IScopeChild        *dup,
        ast::IScopeChild        *orig,
        const std::string       &msg) {
    // A symbol scope stands for the declaration it was built from, whose
    // name is where the report belongs.
    struct Decl {
        static ast::IScopeChild *of(ast::IScopeChild *c) {
            ast::ISymbolScope *ss = dynamic_cast<ast::ISymbolScope *>(c);
            return (ss && ss->getTarget())?ss->getTarget():c;
        }
    };
    reportDuplicate(
        TaskResolveRootRef::declLocation(Decl::of(dup)),
        (orig)?&TaskResolveRootRef::declLocation(Decl::of(orig)):0,
        msg);
}

void TaskApplyTypeExtensions::reportDuplicate(
        const ast::Location     &loc,
        const ast::Location     *orig,
        const std::string       &msg) {
    IMarkerUP marker(m_factory->mkMarker(msg, MarkerSeverityE::Error, loc));
    if (orig && orig->lineno >= 0) {
        marker->addRelated(*orig, "first declared here");
    }
    m_marker_l->marker(marker.get());
}

void TaskApplyTypeExtensions::appendChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child) {
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
    // Non-owning: the logical (symbol) view borrows from the physical
    // view, which keeps the sole owning reference in its GlobalScope.
    // IScopeChildUP's implicit constructor defaults to owned=true, so
    // pushing the raw pointer here would make the extended type a second
    // owner of a node the `extend` statement already owns.
    target->getChildren().push_back(ast::IScopeChildUP(child, false));
}

void TaskApplyTypeExtensions::addChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        const std::string       &name,
        ast::ISymbolScope       *pkg) {
    DEBUG_ENTER("addChild %s to %s", name.c_str(), target->getName().c_str());
    std::unordered_map<std::string,int32_t>::const_iterator it;

    if (name.empty() || name.at(0) == '<') {
        // An exec block is a symbol scope called `<exec>` and an activity is
        // one with no name at all, so the collision check below rejected every
        // extension carrying either -- `extend component C { exec init_down
        // {...} }` reported "Type extension of <exec> conflicts with an
        // existing declaration" whether or not C had an exec of its own.
        // Neither is ever looked up by that name; both are simply appended.
        DEBUG("Appending anonymous child %s", name.c_str());
        appendChild(target, child);
        DEBUG_LEAVE("addChild %s to %s -- anonymous",
            name.c_str(), target->getName().c_str());
        return;
    }

    if (!pkg) {
        pkg = m_root;
    }

    if ((it=target->getSymtab().find(name)) == target->getSymtab().end()) {
        int32_t id = target->getChildren().size();
        appendChild(target, child);
        target->getSymtab().insert({name, id});
        recordExtMember(target, name, id, pkg);
        DEBUG_LEAVE("addChild %s to %s", name.c_str(), target->getName().c_str());
        return;
    }

    ast::IScopeChild *orig = target->getChildren().at(it->second).get();

    // A prototype in one place and the body in another is one function
    // (F25), whichever package each is in. Two bodies are still an error;
    // mergeFunctionScope reports it.
    ast::ISymbolFunctionScope *orig_f = dynamic_cast<ast::ISymbolFunctionScope *>(orig);
    ast::ISymbolFunctionScope *child_f = dynamic_cast<ast::ISymbolFunctionScope *>(child);
    if (orig_f && child_f) {
        mergeFunctionScope(orig_f, child_f);
        DEBUG_LEAVE("addChild %s to %s -- function", name.c_str(), target->getName().c_str());
        return;
    }

    ast::IField *orig_fld = dynamic_cast<ast::IField *>(orig);
    ast::ISymbolTypeScope *target_t = dynamic_cast<ast::ISymbolTypeScope *>(target);

    // Every earlier extension contribution of the name. The symtab's entry
    // is among them unless it is the initial definition's.
    std::vector<ast::ISymbolExtMember *> prev;
    bool orig_is_ext = false;
    if (target_t) {
        for (std::vector<ast::ISymbolExtMemberUP>::const_iterator
            e_it=target_t->getExt_members().begin();
            e_it!=target_t->getExt_members().end(); e_it++) {
            if ((*e_it)->getName() == name) {
                prev.push_back(e_it->get());
                orig_is_ext |= ((*e_it)->getIdx() == it->second);
            }
        }
    }

    if (orig_fld && target_t
            && (orig_fld->getAttr() & ast::FieldAttr::Builtin) != ast::FieldAttr::NoFlags) {
        // The same diagnosis as redeclaring it in the type's own body.
        const char *kind = TaskBuildSymbolTree::builtinKind(
            dynamic_cast<ast::ITypeScope *>(target_t->getTarget()));
        reportDuplicate(child, 0,
            "duplicate declaration of '" + name + "': every "
            + ((kind)?kind:"type") + " has a built-in '" + name + "'");
    } else if (!orig_is_ext) {
        // 17.2.3: an extension may not redeclare a member of the initial
        // definition, from any package.
        reportDuplicate(child, orig,
            "duplicate declaration of '" + name + "' in an extension of '"
            + target->getName() + "': its initial definition already "
            "declares it (17.2.3)");
    } else {
        // Declared by an earlier extension. Two packages may each add a field
        // or type of one name (17.2.3); within one package, the name must be
        // unique. Every earlier contribution of the name is checked, not only
        // the one in the symtab.
        ast::IScopeChild *same = 0;
        bool all_field_or_type = isFieldOrType(child);
        for (std::vector<ast::ISymbolExtMember *>::const_iterator
            p_it=prev.begin(); p_it!=prev.end(); p_it++) {
            ast::IScopeChild *pc = target->getChildren().at((*p_it)->getIdx()).get();
            if ((*p_it)->getPkg() == pkg && !same) {
                same = pc;
            }
            if (!isFieldOrType(pc)) {
                all_field_or_type = false;
            }
        }

        if (same) {
            reportDuplicate(child, same,
                "duplicate declaration of '" + name + "' in an extension of '"
                + target->getName() + "': another extension "
                + packageDesc(pkg) + " already declares it (17.2.3)");
        } else if (!all_field_or_type) {
            reportDuplicate(child, orig,
                "duplicate declaration of '" + name + "' in an extension of '"
                + target->getName() + "': only a field or a type may share "
                "its name with a member an extension in another package "
                "declares (17.2.3)");
        } else {
            // Legal. The type's layout is the union of every contribution,
            // so the member is appended; the symtab keeps the first, and
            // ext_members records this one for lookup (WS6).
            int32_t id = target->getChildren().size();
            appendChild(target, child);
            recordExtMember(target, name, id, pkg);
        }
    }
    DEBUG_LEAVE("addChild %s to %s", name.c_str(), target->getName().c_str());
}

void TaskApplyTypeExtensions::recordExtMember(
        ast::ISymbolScope       *target,
        const std::string       &name,
        int32_t                 idx,
        ast::ISymbolScope       *pkg) {
    if (ast::ISymbolTypeScope *target_t = dynamic_cast<ast::ISymbolTypeScope *>(target)) {
        target_t->getExt_members().push_back(ast::ISymbolExtMemberUP(
            m_factory->getAstFactory()->mkSymbolExtMember(name, idx, pkg)));
    }
}

void TaskApplyTypeExtensions::mergeFunctionScope(
        ast::ISymbolFunctionScope   *existing,
        ast::ISymbolFunctionScope   *incoming) {
    DEBUG_ENTER("mergeFunctionScope %s", existing->getName().c_str());

    // At most one implementation, the same rule TaskBuildSymbolTree applies
    // within one scope.
    ast::IFunctionPrototype *in_proto = (incoming->getPrototypes().size())?
        incoming->getPrototypes().front():0;
    ast::Location at = (in_proto)?
        in_proto->getName()->getLocation() : incoming->getLocation();
    ast::Location first;
    const ast::Location *first_p = 0;
    if (existing->getPrototypes().size()) {
        first = existing->getPrototypes().front()->getName()->getLocation();
        first_p = &first;
    }
    FunctionImpl in_impl = functionImplementation(incoming);
    std::string conflict = functionImplementationConflict(existing, in_impl);
    if (conflict.size()) {
        reportDuplicate(at, first_p, conflict);
    }
    bool take_body = (in_impl == FunctionImpl::Native && conflict.empty());

    // An implementation's parameter names are the ones its body (or
    // template) uses (G-N1). The template's prototype is the one it holds.
    if (conflict.empty() && in_impl == FunctionImpl::Native) {
        resetFunctionParams(existing, in_proto);
    } else if (conflict.empty() && in_impl == FunctionImpl::TargetTemplate) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=incoming->getChildren().begin();
            it!=incoming->getChildren().end(); it++) {
            ast::ITargetTemplateFunction *tt =
                dynamic_cast<ast::ITargetTemplateFunction *>(it->get());
            if (tt) {
                resetFunctionParams(existing, tt->getProto());
                break;
            }
        }
    }

    // Prototypes. The one that carries the body goes first, as
    // TaskBuildSymbolTree::visitFunctionDefinition does: TaskResolveRefs
    // checks a `return` against front().
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=incoming->getPrototypes().begin();
        it!=incoming->getPrototypes().end(); it++) {
        if (take_body && *it == in_proto) {
            existing->getPrototypes().insert(
                existing->getPrototypes().begin(), *it);
        } else {
            existing->getPrototypes().push_back(*it);
        }
    }

    for (std::vector<ast::IFunctionImportUP>::iterator
        it=incoming->getImport_specs().begin();
        it!=incoming->getImport_specs().end(); it++) {
        existing->getImport_specs().push_back(std::move(*it));
    }
    incoming->getImport_specs().clear();

    // Target-template bodies are children of the function scope.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=incoming->getChildren().begin();
        it!=incoming->getChildren().end(); it++) {
        (*it)->setIndex(existing->getChildren().size());
        existing->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
    }

    if (take_body) {
        existing->setBody(incoming->getBody());
        existing->setTarget(incoming->getTarget());
        incoming->setBody(0);
    }
    if (existing->getBody()) {
        // The body's index is one past the children (see
        // TaskBuildSymbolTree::visitFunctionDefinition), and the children
        // may just have grown.
        existing->getBody()->setIndex(existing->getChildren().size());
    }

    // The body is walked in the extended type now, but names in it are still
    // looked up in the extension's package as well (CL-N1).
    std::map<ast::IScopeChild *, ast::ISymbolScope *>::const_iterator d_it =
        m_ext_decl_scope.find(incoming);
    if (take_body && d_it != m_ext_decl_scope.end()) {
        m_ext_decl_scope[existing->getBody()] = d_it->second;
    }

    DEBUG_LEAVE("mergeFunctionScope %s", existing->getName().c_str());
}

dmgr::IDebug *TaskApplyTypeExtensions::m_dbg = 0;

}
