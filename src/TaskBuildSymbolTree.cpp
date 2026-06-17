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

void TaskBuildSymbolTree::visitFunctionDefinition(ast::IFunctionDefinition *i) { 
    DEBUG_ENTER("visitFunctionDefinition %s", i->getProto()->getName()->getId().c_str());

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

        // Add parameters to the function symbol scope
        for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getProto()->getParameters().begin();
            it!=i->getProto()->getParameters().end(); it++) {
            int32_t id = func_sym->getChildren().size();
            std::unordered_map<std::string, int32_t>::const_iterator sym_it =
                func_sym->getPlist()->getSymtab().find((*it)->getName()->getId());
            
            if (sym_it != func_sym->getSymtab().end()) {
                // Duplicate
                reportDuplicateSymbol(
                    func_sym,
                    func_sym->getChildren().at(sym_it->second).get(),
                    it->get());
            } else {
                DEBUG("Add parameter %s to function symtab", (*it)->getName()->getId().c_str());
                (*it)->setIndex(id);
                func_sym->getSymtab().insert({(*it)->getName()->getId(), id});
                func_sym->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
            }
        }
    }

    if (func_sym->getBody()) {
        // TODO: Report duplicate function error
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

    DEBUG_LEAVE("visitFunctionDefinition %s", i->getProto()->getName()->getId().c_str());
}

void TaskBuildSymbolTree::visitFunctionImportProto(ast::IFunctionImportProto *i) { 
    DEBUG_ENTER("visitFunctionImportProto %s", i->getProto()->getName()->getId().c_str());

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
                // Duplicate
                reportDuplicateSymbol(
                    func_sym,
                    func_sym->getPlist()->getChildren().at(sym_it->second).get(),
                    it->get());
            } else {
                func_sym->getPlist()->getSymtab().insert({(*it)->getName()->getId(), id});
                func_sym->getPlist()->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
            }
        }
    }

    if (func_sym->getBody()) {
        // TODO: Cannot both define and import an implementation
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
    DEBUG_ERROR("Duplicate declaration: %s", name.c_str());
    ast::Location loc = dup->getLocation();
    if (loc.lineno < 0 && orig) {
        loc = orig->getLocation();
    }
    Marker m(
        "duplicate declaration of '" + name + "'",
        MarkerSeverityE::Warn,
        loc);
    m_marker_l->marker(&m);
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
