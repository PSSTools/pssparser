/*
 * TaskBuildSymbolTree.cpp
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
#include <set>
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskGetName.h"
#include "BuiltinsFactory.h"
#include "TaskBuildSymbolTree.h"
#include "pssp/ast/IActivityDecl.h"
#include "pssp/ast/IActivityLabeledStmt.h"
#include "pssp/ast/IActivityActionTypeTraversal.h"
#include "pssp/ast/IActivityParallel.h"
#include "pssp/ast/IActivitySchedule.h"
#include "pssp/ast/IActivitySequence.h"
#include "pssp/ast/ISymbolScope.h"
#include "Marker.h"

namespace pssp {




TaskBuildSymbolTree::TaskBuildSymbolTree(
    dmgr::IDebugMgr             *dmgr,
    ast::IFactory               *factory,
    IMarkerListener             *marker_l) :
    m_factory(factory), m_marker_l(marker_l) {
    DEBUG_INIT("TaskBuildSymbolTree", dmgr);

}

TaskBuildSymbolTree::~TaskBuildSymbolTree() {

}

ast::IRootSymbolScope *TaskBuildSymbolTree::build(
        const std::vector<ast::IGlobalScope *>  &roots,
        bool                                    owned) {
    DEBUG_ENTER("build");
    ast::IRootSymbolScope *root = m_factory->mkRootSymbolScope("");
    root->setSynthetic(true);
    pushSymbolScope(root);

    DEBUG_ENTER("visitBuiltins");
    std::vector<ast::IGlobalScope *> all_roots;
    ast::IGlobalScope *builtins = BuiltinsFactory(m_factory).build();
    all_roots.push_back(builtins);
    all_roots.insert(all_roots.end(), roots.begin(), roots.end());
    DEBUG_LEAVE("visitBuiltins");

    for (std::vector<ast::IGlobalScope *>::const_iterator
        it=all_roots.begin();
        it!=all_roots.end(); it++) {
        int32_t idx = root->getUnits().size();

        root->getUnits().push_back(ast::IGlobalScopeUP(*it, owned));
        if ((*it)->getFileid() != -1) {
            root->getId2idx().insert({(*it)->getFileid(), idx});
            if ((*it)->getFilename() != "") {
                root->getFilenames().insert({
                    (*it)->getFileid(),
                    (*it)->getFilename()
                });
            }
        }

        for (std::vector<ast::IScopeChildUP>::const_iterator
            c_it=(*it)->getChildren().begin();
            c_it!=(*it)->getChildren().end(); c_it++) {
            (*c_it)->accept(this);
        }
    }

    DEBUG("%d units", root->getUnits().size());

    popSymbolScope();

    DEBUG_LEAVE("build");
    return root;
}

void TaskBuildSymbolTree::visitActivityDecl(ast::IActivityDecl *i) {
    DEBUG_ENTER("visitActivityDecl");
    // Before adding the activity decl as an opaque child, register any labeled
    // activity stmts (e.g. T1: do tx_data_a) as NAMED children in the PARENT
    // scope (the action type scope). This gives them valid getId() values via
    // setId(), which is needed for correct symbol path resolution (T1.tx_byte).
    registerActivityLabels(i);
    addChild(i, false);

    pushSymbolScope(i);
    DEBUG("Children: %d", i->getChildren().size());
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        DEBUG("Child: %p", it->get());
        it->get()->accept(m_this);
    }
    popSymbolScope();

    DEBUG_LEAVE("visitActivityDecl");
}

ast::ISymbolTypeScope *TaskBuildSymbolTree::build(ast::ITypeScope *ts) {
    DEBUG_ENTER("build");
    ast::ISymbolTypeScope *ret = 0;
    ast::ISymbolScope *root = m_factory->mkSymbolScope("<root>");
    root->setLocation(ts->getLocation());
    root->setOpaque(ts->getOpaque());
    root->setSynthetic(true);
    pushSymbolScope(root);

    ts->accept(m_this);

    popSymbolScope();

    ret = dynamic_cast<ast::ISymbolTypeScope *>(root->getChildren().at(0).get());
    root->getChildren().at(0).release();

    DEBUG_LEAVE("build");
    return ret;
}

void TaskBuildSymbolTree::visitConstraintBlock(ast::IConstraintBlock *i) {
    DEBUG_ENTER("visitConstraintBlock");
    addChild(i, false);
    for (std::vector<ast::IConstraintStmtUP>::const_iterator
        it=i->getConstraints().begin();
        it!=i->getConstraints().end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("visitConstraintBlock");
}

void TaskBuildSymbolTree::visitConstraintScope(ast::IConstraintScope *i) {
    DEBUG_ENTER("visitConstraintScope");
    for (std::vector<ast::IConstraintStmtUP>::const_iterator
        it=i->getConstraints().begin();
        it!=i->getConstraints().end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("visitConstraintScope");
}
    
void TaskBuildSymbolTree::visitConstraintStmt(ast::IConstraintStmt *i) {
    DEBUG_ENTER("visitConstraintStmt");
//    addChild(i, false);
    DEBUG_LEAVE("visitConstraintStmt");
}

void TaskBuildSymbolTree::visitConstraintStmtForall(ast::IConstraintStmtForall *i) {
    DEBUG_ENTER("visitConstraintStmtForall");
    DEBUG_LEAVE("visitConstraintStmtForall");
}

void TaskBuildSymbolTree::visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) {
    DEBUG_ENTER("visitConstraintStmtForeach %p %p", i->getIdx(), i->getIt());
    /*
    for (std::vector<ast::IConstraintStmtUP>::const_iterator
        it=i->getConstraints().begin();
        it!=i->getConstraints().end(); it++) {
        (*it)->accept(m_this);
    }
     */
    DEBUG_LEAVE("visitConstraintStmtForeach");
}

void TaskBuildSymbolTree::visitPackageScope(ast::IPackageScope *i) {
    DEBUG_ENTER("visitPackageScope");
    for (std::vector<ast::IExprIdUP>::const_iterator
        id_it=i->getId().begin();
        id_it!=i->getId().end(); id_it++) {
        DEBUG("  process name-elem %s", (*id_it)->getId().c_str());
        ast::ISymbolScope *scope = dynamic_cast<ast::ISymbolScope *>(symbolScope());
        DEBUG("Scope %s has %d symbols", scope->getName().c_str(), scope->getSymtab().size());
        std::unordered_map<std::string,int32_t>::const_iterator p_it;
        p_it = scope->getSymtab().find((*id_it)->getId());

        if (p_it == scope->getSymtab().end()) {
            int32_t id = scope->getChildren().size();
            ast::ISymbolScope *pkg = m_factory->mkSymbolScope((*id_it)->getId());
            pkg->setLocation(i->getLocation());
            pkg->setSynthetic(true);
            addChild(pkg, (*id_it)->getId(), true);

            pushSymbolScope(pkg);
            scope = pkg;
        } else {
            ast::ISymbolScope *new_scope = 
                dynamic_cast<ast::ISymbolScope *>(scope->getChildren().at(p_it->second).get());
            new_scope->setUpper(symbolScope());
            pushSymbolScope(new_scope);
            scope = new_scope;
        }
    }

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }

    for (std::vector<ast::IExprIdUP>::const_iterator
        id_it=i->getId().begin();
        id_it!=i->getId().end(); id_it++) {
        popSymbolScope();
    }
    DEBUG_LEAVE("visitPackageScope");
}

void TaskBuildSymbolTree::visitEnumDecl(ast::IEnumDecl *i) {
    DEBUG_ENTER("visitEnumDecl %s", i->getName()->getId().c_str());
    ast::ISymbolScope *scope = symbolScope();

    int32_t id = scope->getChildren().size();
    ast::ISymbolEnumScope *ts = m_factory->mkSymbolEnumScope(i->getName()->getId());
    ts->setLocation(i->getLocation());
    ts->setSynthetic(true);


    if (addChild(ts, i->getName()->getId(), true)) {
        pushSymbolScope(ts);
        for (std::vector<ast::IEnumItemUP>::const_iterator
            it=i->getItems().begin();
            it!=i->getItems().end(); it++) {
            (*it)->accept(this);
        }
        popSymbolScope();
    }
    DEBUG_LEAVE("visitEnumDecl %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitTypedefDeclaration(ast::ITypedefDeclaration *i) {
    DEBUG_ENTER("visitTypedefDeclaration %s", i->getName()->getId().c_str());
    addChild(i, i->getName()->getId(), false);
    DEBUG_LEAVE("visitTypedefDeclaration %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitEnumItem(ast::IEnumItem *i) {
    DEBUG_ENTER("visitEnumItem %s", i->getName()->getId().c_str());
    i->setUpper(dynamic_cast<ast::ISymbolEnumScope *>(symbolScope()));
    addChild(i, i->getName()->getId(), false);
    DEBUG_LEAVE("visitEnumItem %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitExecStmt(ast::IExecStmt *i) {
    DEBUG_ENTER("visitExecStmt");
    addChild(i, false);
    DEBUG_LEAVE("visitExecStmt");
}

void TaskBuildSymbolTree::visitExecBlock(ast::IExecBlock *i) {
    DEBUG_ENTER("visitExecBlock");
//    visitExecScope(i);
    addChild(i, false);
    DEBUG_LEAVE("visitExecBlock");
}

void TaskBuildSymbolTree::visitExecScope(ast::IExecScope *i) {
    DEBUG_ENTER("visitExecScope");
    // DEBUG("Adding to scope %s", (symbolScope())?symbolScope()->getName().c_str():"<null>");
    // addChild(i, false);

    pushSymbolScope(i);
    DEBUG("Children: %d", i->getChildren().size());
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        DEBUG("Child: %p", it->get());
        if (dynamic_cast<ast::ISymbolScope *>(it->get())) {
            dynamic_cast<ast::ISymbolScope *>(it->get())->setId(it-i->getChildren().begin());
        }
        it->get()->accept(m_this);
    }
    popSymbolScope();

    DEBUG_LEAVE("visitExecScope");
}

void TaskBuildSymbolTree::visitExtendType(ast::IExtendType *i) {
    DEBUG_ENTER("visitExtendType");
    ast::ISymbolExtendScope *ext = m_factory->mkSymbolExtendScope("<extend>");
    ext->setLocation(i->getLocation());
    ext->setTarget(i);

    // The extend scope must materialize its own children list, exactly as a
    // type scope does. addChild() only pushes into getChildren() for a
    // synthetic scope; for a non-synthetic one it records
    // symtab[name] = child->getIndex(), an index into the *physical* AST
    // parent. That is correct for a scope whose logical contents are exactly
    // one physical body, but an extend scope's contents get merged into
    // another type, so its members need logical indices of their own.
    //
    // Without this, getChildren() stayed empty and every plain field declared
    // in an `extend` was invisible to the merge in TaskApplyTypeExtensions --
    // the reason extension-declared types and functions resolved while
    // extension-declared fields did not.
    ext->setSynthetic(true);

    //addChild(i, false);

    addChild(ext, true);
    pushSymbolScope(ext);
    DEBUG("%d children in extension scope", i->getChildren().size());
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }
    DEBUG("%d children in extension symbol scope", ext->getChildren().size());
    popSymbolScope();

    DEBUG_LEAVE("visitExtendType");
}

void TaskBuildSymbolTree::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());

    addChild(i, i->getName()->getId(), false);

    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFieldCompRef(ast::IFieldCompRef *i) {
    DEBUG_ENTER("visitFieldCompRef %s", i->getName()->getId().c_str());
    addChild(i, i->getName()->getId(), false);
    DEBUG_LEAVE("visitFieldCompRef %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFieldRef(ast::IFieldRef *i) {
    DEBUG_ENTER("visitFieldRef %s", i->getName()->getId().c_str());
    addChild(i, i->getName()->getId(), false);
    DEBUG_LEAVE("visitFieldRef %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFieldClaim(ast::IFieldClaim *i) {
    DEBUG_ENTER("visitFieldClaim %s", i->getName()->getId().c_str());
    // A lock/share claim names a resource instance and must be reachable by
    // that name, exactly as an input/output FieldRef is. Without this the
    // claim parses but never enters the action's symbol table, so
    // `constraint ch.prio > 2` fails with "unknown identifier 'ch'".
    addChild(i, i->getName()->getId(), false);
    DEBUG_LEAVE("visitFieldClaim %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFunctionDefinition(ast::IFunctionDefinition *i) {
    DEBUG_ENTER("visitFunctionDefinition %s", i->getProto()->getName()->getId().c_str());

    reportDuplicateParams(i->getProto());

    ast::IScopeChild *ex_func_b = findSymbol(i->getProto()->getName()->getId());
    ast::ISymbolFunctionScope *func_sym = dynamic_cast<ast::ISymbolFunctionScope *>(ex_func_b);

    // If the existing symbol isn't a FunctionScope, then we have
    // a duplicate symbol
    if (ex_func_b && !func_sym) {
        reportDuplicateSymbol(symbolScope(), ex_func_b, i);
        return;
    }

    // Otherwise, we need to create
    if (!func_sym) {
        DEBUG("mkSymbolFunctionScope %s (1)", i->getProto()->getName()->getId().c_str());
        func_sym = m_factory->mkSymbolFunctionScope(i->getProto()->getName()->getId());
        func_sym->setLocation(i->getLocation());
        addChild(func_sym, i->getProto()->getName()->getId(), false);
        func_sym->getPrototypes().push_back(i->getProto());
        func_sym->setSynthetic(true);

        func_sym->setPlist(m_factory->mkSymbolScope("<plist>"));

        // Parameters go in the plist, as they do in the other two function
        // visitors. This one used to put them in the function scope's own
        // symtab and children instead, so the same declaration produced a
        // different tree depending on which form it took:
        //
        //   definition      plist 0, children 2
        //   import proto    plist 2, children 0
        //   bare prototype  no plist at all
        //
        // A consumer asking "what are this function's parameters?" -- a
        // checker plug-in, say -- got a different answer for each. The plist
        // is the canonical store because ElemKind_ArgIdx resolves through it
        // (TaskResolveSymbolPathRef), and TaskResolveRootRef looks names up
        // there first.
        //
        // Names still resolved from a definition's body before this, but by
        // the fallback path: TaskResolveRootRef::visitSymbolFunctionScope
        // misses in the plist and delegates to visitSymbolScope, which
        // searches the scope's own symtab and yields an ElemKind_ChildIdx
        // path. Two routes to the same answer, only one of which any other
        // pass knows about.
        for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getProto()->getParameters().begin();
            it!=i->getProto()->getParameters().end(); it++) {
            if (!(*it)->getName()) {
                continue;
            }

            const std::string &name = (*it)->getName()->getId();
            int32_t id = func_sym->getPlist()->getChildren().size();

            if (func_sym->getPlist()->getSymtab().find(name)
                != func_sym->getPlist()->getSymtab().end()) {
                // Already reported by reportDuplicateParams(); skip the
                // insert so the first declaration keeps the name.
                DEBUG("Skipping duplicate parameter %s", name.c_str());
                continue;
            }

            DEBUG("Add parameter %s to function plist", name.c_str());
            (*it)->setIndex(id);
            func_sym->getPlist()->getSymtab().insert({name, id});
            func_sym->getPlist()->getChildren().push_back(
                ast::IScopeChildUP(it->get(), false));
        }
    }

    // A function has at most one implementation. Two bodies, or a body
    // alongside an `import`, both leave the tool with no way to say which one
    // runs -- and the second silently overwrote the first via setBody() below.
    if (func_sym->getBody()) {
        Marker m(
            "function '" + i->getProto()->getName()->getId()
                + "' is already defined",
            MarkerSeverityE::Error,
            i->getProto()->getName()->getLocation());
        m_marker_l->marker(&m);
    } else if (func_sym->getImport_specs().size()) {
        Marker m(
            "function '" + i->getProto()->getName()->getId()
                + "' cannot be both defined and imported",
            MarkerSeverityE::Error,
            i->getProto()->getName()->getLocation());
        m_marker_l->marker(&m);
    }

    // Build the body (and subscopes) symbol scopes
    int32_t id = func_sym->getChildren().size();
//    ast::ISymbolExecScope *body = m_factory->mkSymbolExecScope("");
//    body->setLocation(i->getLocation());
//    body->setUpper(symbolScope());
//    pushSymbolScope(func_sym);
    func_sym->setBody(i->getBody());
    // ==size means to get body
    i->getBody()->setIndex(func_sym->getChildren().size());
    // for (std::vector<ast::IScopeChildUP>::const_iterator
    //     it=i->getBody()->getChildren().begin();
    //     it!=i->getBody()->getChildren().end(); it++) {
    //     (*it)->accept(m_this);
    // }
    // popSymbolScope();

    func_sym->setTarget(i);
    // Ensure that the definition takes the primary prototype location
    func_sym->getPrototypes().insert(
        func_sym->getPrototypes().begin(),
        i->getProto()
    );

    // Checked here rather than at the top of the visitor, and over *every*
    // prototype rather than this one. LRM 20.3.2 attaches the rule to the
    // declaration, not to the syntactic form the body arrived in:
    //
    //   function void f(output int a);       // legal alone
    //   function void f(int a) { }           // ... and now it is not
    //
    // The direction is on the earlier prototype, so checking only
    // `i->getProto()` -- which is what the first version of this did -- saw a
    // clean parameter list and accepted the pair.
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=func_sym->getPrototypes().begin();
        it!=func_sym->getPrototypes().end(); it++) {
        // One report per function: a prototype and a definition that both
        // spell the direction are one mistake, not two.
        if (checkNativeParamDir(*it)) {
            break;
        }
    }

    DEBUG_LEAVE("visitFunctionDefinition %s", i->getProto()->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFunctionImportProto(ast::IFunctionImportProto *i) { 
    DEBUG_ENTER("visitFunctionImportProto %s", i->getProto()->getName()->getId().c_str());

    reportDuplicateParams(i->getProto());

    ast::IScopeChild *ex_func_b = findSymbol(i->getProto()->getName()->getId());
    ast::ISymbolFunctionScope *func_sym = dynamic_cast<ast::ISymbolFunctionScope *>(ex_func_b);

    // If the existing symbol isn't a FunctionScope, then we have
    // a duplicate symbol
    if (ex_func_b && !func_sym) {
        reportDuplicateSymbol(symbolScope(), ex_func_b, i);
        return;
    }

    // Otherwise, we need to create
    if (!func_sym) {
        DEBUG("mkSymbolFunctionScope %s (2)", i->getProto()->getName()->getId().c_str());
        func_sym = m_factory->mkSymbolFunctionScope(i->getProto()->getName()->getId());
        func_sym->setLocation(i->getLocation());
        addChild(func_sym, i->getProto()->getName()->getId(), false);

        func_sym->setPlist(m_factory->mkSymbolScope("<plist>"));

        // Add parameters to the function symbol scope
        for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getProto()->getParameters().begin();
            it!=i->getProto()->getParameters().end(); it++) {
            int32_t id = func_sym->getPlist()->getChildren().size();
            std::unordered_map<std::string, int32_t>::const_iterator sym_it =
                func_sym->getPlist()->getSymtab().find((*it)->getName()->getId());
            
            if (sym_it != func_sym->getPlist()->getSymtab().end()) {
                // Already reported by reportDuplicateParams(); skip the
                // insert so the first declaration keeps the name.
                DEBUG("Skipping duplicate parameter %s",
                    (*it)->getName()->getId().c_str());
            } else {
                func_sym->getPlist()->getSymtab().insert({(*it)->getName()->getId(), id});
                func_sym->getPlist()->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
            }
        }
    }

    // The mirror of the check in visitFunctionDefinition, for the other
    // declaration order. Two imports are the same conflict: the second
    // import_spec is appended and nothing ever chooses between them.
    if (func_sym->getBody()) {
        Marker m(
            "function '" + i->getProto()->getName()->getId()
                + "' cannot be both defined and imported",
            MarkerSeverityE::Error,
            i->getProto()->getName()->getLocation());
        m_marker_l->marker(&m);
    } else if (func_sym->getImport_specs().size()) {
        Marker m(
            "function '" + i->getProto()->getName()->getId()
                + "' is already imported",
            MarkerSeverityE::Error,
            i->getProto()->getName()->getLocation());
        m_marker_l->marker(&m);
    }

    i->getProto()->accept(m_this);

    if (i->getPlat() == ast::PlatQual::PlatQual_Solve) {
        i->getProto()->setIs_solve(true);
    }
    if (i->getPlat() == ast::PlatQual::PlatQual_Target) {
        i->getProto()->setIs_target(true);
    }

    func_sym->getImport_specs().push_back(ast::IFunctionImportUP(
        m_factory->mkFunctionImport(i->getPlat(), "")
    ));

    DEBUG_LEAVE("visitFunctionImportProto %s", i->getProto()->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFunctionImportType(ast::IFunctionImportType *i) { 
    DEBUG_ENTER("visitFunctionImportType");
    DEBUG("TODO: visitFunctionImportType");
    DEBUG_LEAVE("visitFunctionImportType");
}

void TaskBuildSymbolTree::visitFunctionPrototype(ast::IFunctionPrototype *i) { 
    DEBUG_ENTER("visitFunctionPrototype %s", i->getName()->getId().c_str());

    // This visitor never built a plist and never looked at the parameters at
    // all, so `function void f(int a, int a);` -- a prototype with no body --
    // was the one form that went entirely unchecked.
    reportDuplicateParams(i);

    ast::IScopeChild *ex_func_b = findSymbol(i->getName()->getId());
    ast::ISymbolFunctionScope *func_sym = dynamic_cast<ast::ISymbolFunctionScope *>(ex_func_b);

    // If the existing symbol isn't a FunctionScope, then we have
    // a duplicate symbol
    if (ex_func_b && !func_sym) {
        DEBUG("Duplicate symbol");
        reportDuplicateSymbol(symbolScope(), ex_func_b, i);
        return;
    }

    // Otherwise, we need to create
    if (!func_sym) {
        DEBUG("mkSymbolFunctionScope %s (3)", i->getName()->getId().c_str());
        func_sym = m_factory->mkSymbolFunctionScope(i->getName()->getId());
        func_sym->setLocation(i->getLocation());
        addChild(func_sym, i->getName()->getId(), false);
    } else {
        DEBUG("Note: Function %s is already defined", func_sym->getName().c_str());
    }

    // Build the parameter list. This visitor did not, which left a bare
    // prototype's function scope with a **null** plist -- the only one of the
    // three forms without one. Two things followed:
    //
    //  - TaskResolveRootRef::visitSymbolFunctionScope opens with
    //    `i->getPlist()->getSymtab()`, unguarded, and
    //    TaskResolveSymbolPathRef does the same for ElemKind_ArgIdx;
    //  - a prototype followed by a definition of the same function left the
    //    parameters registered in neither place, because
    //    visitFunctionDefinition only builds them when it is the visitor that
    //    creates the scope. The body was still walked, but nothing in it
    //    resolved: `function void f(int a); function void f(int a) { v =
    //    nosuch; }` reported nothing at all.
    //
    // Populating it here also settles which of the two stores is canonical:
    // the plist is what ElemKind_ArgIdx resolves through, so it is.
    if (!func_sym->getPlist()) {
        func_sym->setPlist(m_factory->mkSymbolScope("<plist>"));
    }

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=i->getParameters().begin();
        it!=i->getParameters().end(); it++) {
        if (!(*it)->getName()) {
            continue;
        }

        const std::string &name = (*it)->getName()->getId();
        int32_t id = func_sym->getPlist()->getChildren().size();

        if (func_sym->getPlist()->getSymtab().find(name)
            != func_sym->getPlist()->getSymtab().end()) {
            // Already registered -- a repeated prototype, or a duplicate
            // parameter name, which reportDuplicateParams() above has
            // already reported.
            continue;
        }

        (*it)->setIndex(id);
        func_sym->getPlist()->getSymtab().insert({name, id});
        func_sym->getPlist()->getChildren().push_back(
            ast::IScopeChildUP(it->get(), false));
    }

    func_sym->getPrototypes().push_back(i);
    DEBUG_LEAVE("visitFunctionPrototype %s", i->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitGlobalScope(ast::IGlobalScope *i) {
    DEBUG_ENTER("visitGlobalScope");
    addChild(i, false);
    DEBUG_ENTER("visitGlobalScope");
}

void TaskBuildSymbolTree::visitPackageImportStmt(ast::IPackageImportStmt *i) {
    DEBUG_ENTER("visitPackageImportStmt");
    ast::ISymbolScope *scope = symbolScope();

    if (!scope->getImports()) {
        DEBUG("Create new ImportSpec");
        scope->setImports(m_factory->mkSymbolImportSpec());
    }

    DEBUG("Add import to scope %s", scope->getName().c_str());

    // See if this import already exists
    bool exists = false;
    for (std::vector<ast::IPackageImportStmt *>::const_iterator
        it=scope->getImports()->getImports().begin();
        it!=scope->getImports()->getImports().end(); it++) {
        if (i->getWildcard() == (*it)->getWildcard()) {
            // Compare the paths
            if (i->getPath()->getElems().size() == (*it)->getPath()->getElems().size()) {
                uint32_t ii;
                for (ii=0; ii<i->getPath()->getElems().size(); ii++) {
                    if (i->getPath()->getElems().at(ii)->getId()->getId() !=
                        (*it)->getPath()->getElems().at(ii)->getId()->getId()) {
                        break;
                    }
                }
                exists = (ii == i->getPath()->getElems().size());
            }
        }
        if (exists) {
            break;
        }
    }

    if (!exists) {
        scope->getImports()->getImports().push_back(i);
    } else {
        DEBUG("Skip duplicate import");
    }

    DEBUG_LEAVE("visitPackageImportStmt");
}

void TaskBuildSymbolTree::visitPyImportStmt(ast::IPyImportStmt *i) {
    DEBUG_ENTER("visitPyImportStmt");
    ast::ISymbolScope *scope = symbolScope();
    std::unordered_map<std::string, int32_t>::const_iterator it;

    if (i->getAlias()) {
        // Register the alias name
        if ((it=scope->getSymtab().find(i->getAlias()->getId())) != scope->getSymtab().end()) {
            // Error: 
            DEBUG_ERROR("TODO: symbol collision with pyimport %s", i->getAlias()->getId().c_str());
        } else {
            int32_t id = scope->getChildren().size();
            scope->getChildren().push_back(ast::IScopeChildUP(i, false));
            scope->getSymtab().insert({
                i->getAlias()->getId(),
                id
            });
        }
    } else {
        // Register the basename
        if ((it=scope->getSymtab().find(i->getPath().front()->getId())) != scope->getSymtab().end()) {
            // Error: 
            DEBUG_ERROR("TODO: symbol collision with pyimport %s", i->getPath().front()->getId().c_str());
        } else {
            int32_t id = scope->getChildren().size();
            scope->getChildren().push_back(ast::IScopeChildUP(i, false));
            scope->getSymtab().insert({
                i->getPath().front()->getId(),
                id
            });
        }
    }
    DEBUG_LEAVE("visitPyImportStmt");
}

void TaskBuildSymbolTree::visitPyImportFromStmt(ast::IPyImportFromStmt *i) {
    DEBUG_ENTER("visitPyImportFromStmt");
    DEBUG("TODO: visitPyImportFromStmt");
    DEBUG_LEAVE("visitPyImportFromStmt");
}

void TaskBuildSymbolTree::visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) {
    DEBUG_ENTER("visitProceduralStmtDataDeclaration %s", i->getName()->getId().c_str());
#ifdef UNDEFINED
    ast::ISymbolScope *scope = symbolScope();

    std::unordered_map<std::string, int32_t>::const_iterator it =
        scope->getSymtab().find(i->getName()->getId());
    
    if (it != scope->getSymtab().end()) {
        reportDuplicateSymbol(
            scope,
            scope->getChildren().at(it->second).get(),
            i
        );
    } else {
        int32_t id = -1;
        if (scope->getSynthetic()) {
            id = scope->getChildren().size();
            DEBUG("DataDeclaration %s: %d", i->getName()->getId().c_str(), id);
            scope->getChildren().push_back(ast::IScopeChildUP(i, false));
        } else {
            id = i->getIndex();
        }
        scope->getSymtab().insert({i->getName()->getId(), id});
    }
#endif // UNDEFINED

    DEBUG_LEAVE("visitProceduralStmtDataDeclaration");
}

void TaskBuildSymbolTree::visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) {
    DEBUG_ENTER("visitProceduralStmtIfElse");
    addChild(i, false);
//     ast::ISymbolScope *scope = symbolScope();

//     int32_t id = scope->getChildren().size();
// //    ast::ISymbolChildrenScope *if_scope = m_factory->mkSymbolChildrenScope("<if>");
//     ast::ISymbolScope *if_scope = m_factory->mkSymbolScope("<if>");
//     if_scope->setLocation(i->getLocation());
//     if_scope->setTarget(i);
//     addChild(if_scope, true);
//     pushSymbolScope(if_scope);
//     for (std::vector<ast::IProceduralStmtIfClauseUP>::const_iterator
//         it=i->getIf_then().begin();
//         it!=i->getIf_then().end(); it++) {
//         ast::ISymbolCondConnector *cc = m_factory->mkSymbolCondConnector((*it)->getCond(), 0);
//         addChild(cc, true);
//         pushSymbolScope(cc);
//         (*it)->accept(m_this);
//         popSymbolScope();
//     }
//     if (i->getElse_then()) {
//         i->getElse_then()->accept(m_this);
//     }
//     popSymbolScope();

    DEBUG_LEAVE("visitProceduralStmtIfElse");
}

void TaskBuildSymbolTree::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    DEBUG_ENTER("visitProceduralStmtRepeat symtab-sz: %d", i->getSymtab().size());
    DEBUG_LEAVE("visitProceduralStmtRepeat");
}

void TaskBuildSymbolTree::visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) {
    // The iterator/index variables were registered on the node's symtab by the
    // AST builder; do not let the base visitor re-home them (mirrors repeat).
    DEBUG_ENTER("visitProceduralStmtForeach symtab-sz: %d", i->getSymtab().size());
    DEBUG_LEAVE("visitProceduralStmtForeach");
}

void TaskBuildSymbolTree::visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) {
    DEBUG_ENTER("visitProceduralStmtMatch");
    DEBUG_LEAVE("visitProceduralStmtMatch");
}

void TaskBuildSymbolTree::visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) {
    DEBUG_ENTER("visitProceduralStmtRepeatWhile");
    DEBUG_LEAVE("visitProceduralStmtRepeatWhile");
}

void TaskBuildSymbolTree::visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) {
    DEBUG_ENTER("visitProceduralStmtWhile");
    DEBUG_LEAVE("visitProceduralStmtWhile");
}

/*
void TaskBuildSymbolTree::visitProceduralStmtIfClause(ast::IProceduralStmtIfClause *i) {
    DEBUG_ENTER("visitProceduralStmtIfClause");
    DEBUG_LEAVE("visitProceduralStmtIfClause");
}
 */

void TaskBuildSymbolTree::visitScope(ast::IScope *i) {
    DEBUG_ENTER("visitScope");
    addChild(i, false);
    DEBUG_LEAVE("visitScope");
}

void TaskBuildSymbolTree::visitScopeChild(ast::IScopeChild *i) {
    DEBUG_ENTER("visitScopeChild");
    addChild(i, false);
    DEBUG_LEAVE("visitScopeChild");
}

void TaskBuildSymbolTree::visitTypeScope(ast::ITypeScope *i) {
    DEBUG_ENTER("visitTypeScope %s %d children", 
        (i->getName() ? i->getName()->getId().c_str() : "<unnamed>"),
        i->getChildren().size());
    ast::ISymbolScope *scope = symbolScope();

    ast::ISymbolScope *plist = 0;
    if (i->getParams()) {
        DEBUG("Build out plist %d", i->getParams()->getParams().size());
        plist = m_factory->mkSymbolScope("<plist>");
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=i->getParams()->getParams().begin();
            it!=i->getParams()->getParams().end(); it++) {
            int32_t id = plist->getChildren().size();
            std::unordered_map<std::string, int32_t>::const_iterator s_it;
            DEBUG("  Param: %", ((*it)->getName())?(*it)->getName()->getId().c_str():"<unknown>");
            
            s_it = plist->getSymtab().find((*it)->getName()->getId());
            if (s_it == plist->getSymtab().end()) {
                plist->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
                plist->getSymtab().insert({(*it)->getName()->getId(), id});
            } else {
                Marker m(
                    "duplicate parameter name '" + (*it)->getName()->getId() + "'",
                    MarkerSeverityE::Error,
                    (*it)->getLocation());
                if (m_marker_l) m_marker_l->marker(&m);
            }
        }
    } else {
        DEBUG("No plist");
    }
    ast::ISymbolTypeScope *ts = m_factory->mkSymbolTypeScope(i->getName() ? i->getName()->getId() : "<unnamed>", plist);
    ts->setSynthetic(true);
    ts->setLocation(i->getLocation());
    ts->setTarget(i);
    ts->setParent(i->getParent());

    // pyobj fields are opaque, since Python is a dynamically-typed library
    if (i->getName()->getId() == "pyobj") {
        ts->setOpaque(true);
    }

    if (addChild(ts, i->getName()->getId(), false)) {
        pushSymbolScope(ts);

        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            (*it)->accept(m_this);
        }
        popSymbolScope();
    }

    DEBUG_LEAVE("visitTypeScope %s %d children", 
        i->getName()->getId().c_str(),
        ts->getChildren().size());
}

void TaskBuildSymbolTree::reportDuplicateSymbol(
        ast::ISymbolScope       *scope,
        ast::IScopeChild        *orig,
        ast::IScopeChild        *dup) {
    std::string name = TaskGetName().get(orig);

    // DEBUG rather than DEBUG_ERROR: with no debug manager installed --
    // i.e. in every ordinary run -- DEBUG_ERROR prints straight to stdout,
    // so this produced a bare `Error: TaskBuildSymbolTree: Duplicate
    // declaration: A` line with no file, no location, and no bearing on the
    // exit code, above a summary that said `0 errors`. The marker below is
    // the report.
    DEBUG("Duplicate declaration: %s", name.c_str());

    ast::Location loc = dup->getLocation();
    if (loc.lineno < 0 && orig) {
        loc = orig->getLocation();
    }

    // Error, not Warn. Two declarations of one name in one scope is illegal
    // PSS, and the second silently wins the symbol table -- so a reference
    // that names the first resolves to the second, and every diagnostic that
    // follows is measured against a declaration the user did not write.
    // `checkers/core_checker.py` has always classified PSS003 as an error;
    // only the marker disagreed. Extensions that collide with a declaration
    // (`Type extension of A conflicts...`) were already errors, so this also
    // makes the two paths agree.
    Marker m(
        "duplicate declaration of '" + name + "'",
        MarkerSeverityE::Error,
        loc);
    m_marker_l->marker(&m);
}

void TaskBuildSymbolTree::reportDuplicateParams(ast::IFunctionPrototype *proto) {
    if (!proto) {
        return;
    }

    std::set<std::string> seen;

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=proto->getParameters().begin();
        it!=proto->getParameters().end(); it++) {
        if (!(*it)->getName()) {
            continue;
        }

        const std::string &name = (*it)->getName()->getId();

        if (!seen.insert(name).second) {
            Marker m(
                "duplicate parameter name '" + name + "'",
                MarkerSeverityE::Error,
                (*it)->getName()->getLocation());
            m_marker_l->marker(&m);
        }
    }

    checkParamDefaultOrder(proto);
    checkPureQualifier(proto);
}

void TaskBuildSymbolTree::checkPureQualifier(ast::IFunctionPrototype *proto) {
    // LRM 20.2.6 rule (a): "Only non-void functions with no output or inout
    // parameters may be declared pure."
    //
    // Both halves follow from what `pure` means -- the return value depends
    // only on the parameters, and evaluation has no side effects. A void pure
    // function can have no observable effect at all, and an output parameter
    // *is* a side effect. The LRM notes that a wrongly-declared pure function
    // "may lead to unexpected behavior", because implementations are entitled
    // to optimize on the strength of the modifier: the call may be hoisted,
    // reordered, or evaluated once and reused. Neither of these is a style
    // question.
    if (!proto->getIs_pure()) {
        return;
    }

    if (!proto->getRtype()) {
        Marker m(
            "'" + proto->getName()->getId()
                + "' is declared pure, so it cannot return void",
            MarkerSeverityE::Error,
            proto->getName()->getLocation());
        m_marker_l->marker(&m);
    }

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=proto->getParameters().begin();
        it!=proto->getParameters().end(); it++) {
        ast::ParamDir dir = (*it)->getDir();
        if (dir != ast::ParamDir::ParamDir_Out
            && dir != ast::ParamDir::ParamDir_InOut) {
            continue;
        }
        if (!(*it)->getName()) {
            continue;
        }
        Marker m(
            "'" + proto->getName()->getId() + "' is declared pure, so parameter '"
                + (*it)->getName()->getId() + "' cannot be "
                + ((dir == ast::ParamDir::ParamDir_Out)?"output":"inout"),
            MarkerSeverityE::Error,
            (*it)->getName()->getLocation());
        m_marker_l->marker(&m);
        // One report per prototype: a pure function with three output
        // parameters has one thing wrong with it, not three.
        break;
    }
}

bool TaskBuildSymbolTree::checkNativeParamDir(ast::IFunctionPrototype *proto) {
    // LRM 20.2.2: "Parameter direction modifiers (input, output, or inout) are
    // optional in the function declaration. However, if they are specified in
    // the function declaration, such a function may only be imported." And
    // 20.3.2, for native functions: "Parameter direction shall be unspecified
    // ... If the function declaration contains directions for parameters, this
    // function shall not have a native implementation."
    //
    // Called only from visitFunctionDefinition -- that is the whole of the
    // rule. A direction on a prototype is legal on its own; it becomes illegal
    // when a PSS body turns up for it.
    //
    // `is_core` is the exemption the LRM grants itself: "Functions whose
    // definition is built into implementations, such as functions included in
    // the PSS core library, may also have output or inout parameters."
    if (!proto || proto->getIs_core()) {
        return false;
    }

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=proto->getParameters().begin();
        it!=proto->getParameters().end(); it++) {
        ast::ParamDir dir = (*it)->getDir();
        if (dir == ast::ParamDir::ParamDir_Default || !(*it)->getName()) {
            continue;
        }
        const char *dir_s = (dir == ast::ParamDir::ParamDir_In)?"input":
                            (dir == ast::ParamDir::ParamDir_Out)?"output":"inout";
        Marker m(
            std::string("parameter '") + (*it)->getName()->getId() + "' of '"
                + proto->getName()->getId() + "' is declared " + dir_s
                + ", so '" + proto->getName()->getId()
                + "' may only be imported, not defined in PSS",
            MarkerSeverityE::Error,
            (*it)->getName()->getLocation());
        m_marker_l->marker(&m);
        return true;
    }

    return false;
}

void TaskBuildSymbolTree::checkParamDefaultOrder(ast::IFunctionPrototype *proto) {
    // Parameters with a default shall be trailing. Otherwise the default is
    // unreachable -- there is no call that omits it while supplying the ones
    // after it -- and the arity check computes its minimum by taking the index
    // of the last parameter without a default, which quietly treats the
    // earlier default as required.
    bool seen_dflt = false;
    ast::IFunctionParamDecl *first_dflt = 0;

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=proto->getParameters().begin();
        it!=proto->getParameters().end(); it++) {
        if ((*it)->getIs_varargs()) {
            // Always last, and never carries a default.
            break;
        }

        if ((*it)->getDflt()) {
            seen_dflt = true;
            if (!first_dflt) {
                first_dflt = it->get();
            }
        } else if (seen_dflt && (*it)->getName()) {
            Marker m(
                "parameter '" + (*it)->getName()->getId()
                    + "' has no default, but follows '"
                    + first_dflt->getName()->getId() + "' which does",
                MarkerSeverityE::Error,
                (*it)->getName()->getLocation());
            m_marker_l->marker(&m);
            // One report per prototype: every later non-defaulted parameter
            // is the same mistake, and naming the first default each time
            // would repeat the same advice.
            break;
        }
    }
}

ast::IScopeChild *TaskBuildSymbolTree::findSymbol(const std::string &name) {
    ast::ISymbolScope *scope = symbolScope();
    if (scope) {
        std::unordered_map<std::string, int32_t>::const_iterator it =
            scope->getSymtab().find(name);
        if (it != scope->getSymtab().end()) {
            return scope->getChildren().at(it->second).get();
        } else {
            return 0;
        }
    } else {
        return 0;
    }
}

void TaskBuildSymbolTree::pushSymbolScope(ast::ISymbolChild *s) {
    m_scope_s.push_back(s);
}

ast::ISymbolScope *TaskBuildSymbolTree::symbolScope() {
    if (m_scope_s.size()) {
        return dynamic_cast<ast::ISymbolScope *>(m_scope_s.back());
    } else {
        return 0;
    }
}

void TaskBuildSymbolTree::popSymbolScope() {
    m_scope_s.pop_back();
}

void TaskBuildSymbolTree::addChild(
    ast::IScopeChild    *c,
    bool                owned) {
    DEBUG_ENTER("addChild(ScopeChild)");
    if (dynamic_cast<ast::ISymbolScope *>(m_scope_s.back())) {
        ast::ISymbolScope *scope = dynamic_cast<ast::ISymbolScope *>(m_scope_s.back());
        DEBUG("Scope: isSynth=%d", scope->getSynthetic());
        if (scope->getSynthetic()) {
            scope->getChildren().push_back(ast::IScopeChildUP(c, owned));
        }
//        dynamic_cast<ast::ISymbolChildrenScope *>(m_scope_s.back())->getChildren().push_back(
//            ast::IScopeChildUP(c, owned));
    }/* else {
        ast::ISymbolCondConnector *cond = dynamic_cast<ast::ISymbolCondConnector *>(m_scope_s.back());
        DEBUG("Setting cond-connector target");
        cond->setStmt(c);
    } */
    DEBUG_LEAVE("addChild(ScopeChild)");
}

void TaskBuildSymbolTree::addChild(
    ast::ISymbolScope   *c,
    bool                owned) {
    DEBUG_ENTER("addChild(ScopeChild)");
    owned = false;
    if (dynamic_cast<ast::ISymbolChildrenScope *>(m_scope_s.back())) {
        ast::ISymbolChildrenScope *scs = dynamic_cast<ast::ISymbolChildrenScope *>(m_scope_s.back());
        c->setId(scs->getChildren().size());
        scs->getChildren().push_back(ast::IScopeChildUP(c, owned));
    } /*else {
        ast::ISymbolCondConnector *cond = dynamic_cast<ast::ISymbolCondConnector *>(m_scope_s.back());
        DEBUG("Setting cond-connector target");
        cond->setStmt(c);
    }*/
    DEBUG_LEAVE("addChild(ScopeChild)");
}

bool TaskBuildSymbolTree::addChild(
    ast::IScopeChild    *c, 
    const std::string   &name,
    bool                owned) {
    ast::ISymbolScope *scope = symbolScope();
    owned = false;
    if (c == scope) {
        DEBUG_ERROR("recursive");
    }
    std::unordered_map<std::string, int32_t>::const_iterator it =
        scope->getSymtab().find(name);
    
    if (it == scope->getSymtab().end()) {
        int32_t id = -1;
        if (scope->getSynthetic()) {
            id = scope->getChildren().size();
            scope->getChildren().push_back(ast::IScopeChildUP(c, owned));
        } else {
            id = c->getIndex();
        }
        scope->getSymtab().insert({name, id});
        return true;
    } else {
        reportDuplicateSymbol(
            scope,
            scope->getChildren().at(it->second).get(),
            c);
        return false;
    }
}

bool TaskBuildSymbolTree::addChild(
    ast::ISymbolChild   *c, 
    const std::string   &name,
    bool                owned) {
    DEBUG_ENTER("addChild(SymbolChild) %s", name.c_str());
    ast::ISymbolScope *scope = symbolScope();
    owned = false;

    DEBUG("scope: %s %d (%p)", scope->getName().c_str(), scope->getSymtab().size(), scope);

    if (c == scope) {
        DEBUG_ERROR("recursive");
    }
    if (name != "") {
        std::unordered_map<std::string, int32_t>::const_iterator it =
            scope->getSymtab().find(name);
        
        if (it != scope->getSymtab().end()) {
            reportDuplicateSymbol(
                scope,
                scope->getChildren().at(it->second).get(),
                c);
            return false;
        } else {
            int32_t id = -1;
            if (scope->getSynthetic()) {
                id = scope->getChildren().size();
                scope->getChildren().push_back(ast::IScopeChildUP(c, owned));
            } else {
                id = c->getIndex();
                scope->getChildren().push_back(ast::IScopeChildUP(c, owned));
            }
            c->setId(id);
            scope->getSymtab().insert({name, id});
        }
    }
    c->setUpper(scope);
    DEBUG_LEAVE("addChild(SymbolChild)");
    return true;
}

// Recursively scan an activity scope and register labeled activity stmts
// (e.g. T1: do tx_data_a) as named children in the CURRENT symbol scope.
// This gives them valid getId() entries so path resolution through the
// symbol tree works correctly for cross-traversal references (T1.tx_byte).
void TaskBuildSymbolTree::registerActivityLabels(ast::ISymbolScope *scope) {
    if (!scope) return;
    for (auto &child : scope->getChildren()) {
        auto *labeled = dynamic_cast<ast::IActivityLabeledStmt*>(child.get());
        if (labeled && labeled->getLabel()) {
            const std::string &lname = labeled->getLabel()->getId();
            // Register in the CURRENT symbol scope (the action's type scope)
            // using the addChild that properly sets getId() via setId().
            addChild(dynamic_cast<ast::IScopeChild*>(labeled), lname, false);
        }
        // Recurse into compound activity scopes (parallel, schedule, sequence)
        auto *nested_scope = dynamic_cast<ast::ISymbolScope*>(child.get());
        if (nested_scope) {
            registerActivityLabels(nested_scope);
        }
    }
}

dmgr::IDebug *TaskBuildSymbolTree::m_dbg = 0;

}
