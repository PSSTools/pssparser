/*
 * TaskGetSpecializedTemplateType.cpp
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
#include "TaskGetSpecializedTemplateType.h"
#include <memory>
#include <map>
#include <set>
#include "pssp/impl/TaskCopyAst.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "AssocDataTypeScope.h"
#include "TaskBuildSymbolTree.h"
#include "TaskCompareParamLists.h"
#include "TaskResolveRefs.h"
#include "TaskResolveRootRef.h"
#include "pssp/impl/TaskGetName.h"
#include "pssp/ast/IExtendEnum.h"
#include "pssp/ast/IExtendType.h"
#include "pssp/impl/NodeKind.h"


namespace pssp {



TaskGetSpecializedTemplateType::TaskGetSpecializedTemplateType(
    ResolveContext          *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("TaskGetSpecializedTemplateType", ctxt->getDebugMgr());

}

TaskGetSpecializedTemplateType::~TaskGetSpecializedTemplateType() {

}

ast::ISymbolRefPath *TaskGetSpecializedTemplateType::find(
    const ast::ISymbolRefPath           *type,
    const ast::ITemplateParamDeclList   *params) {
    DEBUG_ENTER("find");
    ast::ISymbolTypeScope *type_up = 
        TaskResolveSymbolPathRef(
            m_ctxt->getDebugMgr(), 
            m_ctxt->root()).resolveT<ast::ISymbolTypeScope>(type);
    
    DEBUG(" (find) type_up=%s", type_up->getName().c_str());

    ast::ISymbolRefPath *ret = 0;

    // Search through the list of available specializations for
    // a matching one
    TaskCompareParamLists p_comp(m_ctxt->getFactory(), m_ctxt->root());
    DEBUG("There are %d existing specializations", type_up->getSpec_types().size());
    for (int32_t i=0; i<type_up->getSpec_types().size(); i++) {
        ast::ISymbolTypeScope *sym_type_s_t = type_up->getSpec_types().at(i).get();
        ast::ITypeScope *type_s_t = NodeKind::cast<ast::ITypeScope>(sym_type_s_t->getTarget());

        if (p_comp.equal(params, type_s_t->getParams())) {
            // Have a match!
            DEBUG("Found plist match");
            ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();

            // Copy over initial path
            ret->getPath().insert(
                ret->getPath().begin(),
                type->getPath().begin(),
                type->getPath().end());
            
            // Now, add on a directive to get a specialization
            ret->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_TypeSpec,
                i
            });
            break;
        }
    }

    DEBUG_LEAVE("find %p", ret);
    return ret;
}

ast::ISymbolRefPath *TaskGetSpecializedTemplateType::mk(
    const ast::ISymbolRefPath           *type,
    ast::ITemplateParamDeclList         *params,
    const ast::Location                 &use_loc) {
    DEBUG_ENTER("mk params=%p (%d)", params, (params)?params->getParams().size():-1);
    ast::ISymbolTypeScope *type_up = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolveT<ast::ISymbolTypeScope>(type);
    DEBUG("type_up=%s", type_up->getName().c_str());

    if (m_ctxt->specializationDepth() >= MAX_SPECIALIZATION_DEPTH) {
        // Specializing a type resolves its body, which may specialize again.
        // Most such chains terminate because the argument list repeats and the
        // existing specialization is reused, but some do not: `struct S<type T>
        // { S<S<T>> next; }` names a strictly larger argument at every step and
        // has no fixed point. Diagnose it rather than running out of stack.
        m_ctxt->addErrorMarker(
            type_up->getTarget()->getLocation(),
            "recursive specialization of '%s' exceeded the maximum depth of "
            "%d: each step specializes on a larger argument than the last, so "
            "the chain does not terminate",
            type_up->getName().c_str(),
            MAX_SPECIALIZATION_DEPTH);
        DEBUG_LEAVE("mk (depth limit)");
        return 0;
    }

    TaskCopyAst copier(m_ctxt->getFactory());

    ast::ITypeScope *type_s =
        copier.copyT<ast::ITypeScope>(type_up->getTarget());

    if (!type_s || !copier.failure().empty()) {
        // The copier hit a construct it does not handle -- a gap in pssparser,
        // not a fault in the model. Name the construct in the diagnostic (it
        // used to go to stdout, uncounted) and, when the copy as a whole
        // failed, give up on this specialization rather than dereference null.
        // A copy that succeeded around a gap is kept: the gap is reported, and
        // the rest of the specialization is still usable.
        m_ctxt->internalError(
            type_up->getTarget()->getLocation(),
            "failed to specialize type '%s': the AST copier does not support "
            "a construct it contains (%s)",
            type_up->getName().c_str(),
            copier.failure().empty() ? "unknown" : copier.failure().c_str());
        if (!type_s) {
            DEBUG_LEAVE("mk (copy failed)");
            return 0;
        }
    }

    type_s->setParent(type_up->getTarget()->getParent());

    if (DEBUG_EN) {
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=params->getParams().begin();
            it!=params->getParams().end(); it++) {
            DEBUG("Param: %s", ((*it)->getName())?(*it)->getName()->getId().c_str():"<unnamed>");
        }
    }

    params->setSpecialized(true);

    // Replace the declaration parameter list with the properly-parameterized one
    // Note: UP takes care of freeing previous
    type_s->setParams(params);

    std::map<ast::IScopeChild *, ast::ISymbolScope *> inst_members;
    applyInstanceExtensions(
        type_up, type_s, params, inst_members);

    // Have the specialized type point to the unspecialized
    // parameterized type as its super type
    ast::ITypeIdentifier *super_t = m_ctxt->getFactory()->getAstFactory()->mkTypeIdentifier();
    super_t->setTarget(copier.copy(type));

    // We must now build a symbol-scope node for the type scope
    ast::ISymbolTypeScope *type_ss = TaskBuildSymbolTree(
        m_ctxt->getDebugMgr(),
        m_ctxt->getFactory()->getAstFactory(),
        0).build(type_s);

    if (inst_members.size()) {
        // A member an instance extension added resolves with the extension's
        // package in scope too (17.2, CL-N1), as a generic extension's does.
        for (std::vector<ast::IScopeChildUP>::const_iterator
                it=type_ss->getChildren().begin();
                it!=type_ss->getChildren().end(); it++) {
            ast::ISymbolScope *ss = NodeKind::cast<ast::ISymbolScope>(it->get());
            std::map<ast::IScopeChild *, ast::ISymbolScope *>::const_iterator
                m_it = inst_members.find((ss)?ss->getTarget():it->get());
            if (m_it != inst_members.end() && m_it->second) {
                m_ctxt->addExtensionDeclScope(it->get(), m_it->second);
            }
        }
    }

    // Give the new type an appropriate name

    // Store the specialized AST under the symbol table
    type_ss->setName(mkTypename(type, params));

    int32_t id = type_up->getSpec_types().size();

    // Record where this specialization lives in the generic's spec_types
    // vector. Everything that later builds a reference path *into* this
    // specialization -- the symbol-table iterator by way of TaskGetItemIndex,
    // and TaskGetSymbolRefPath -- reads the index from here. The copier had
    // carried over the declaration's own child index instead, so every
    // specialization claimed to be specialization 0 and references to a
    // parameter from inside the second and later specializations resolved to
    // the first one's binding.
    type_s->setIndex(id);

    DEBUG("Adding \"%s\" to specialization %s (%p)",
        type_ss->getName().c_str(),
        type_up->getName().c_str(),
        type_up);
    type_up->getSpec_types().push_back(ast::ISymbolTypeScopeUP(type_ss));
    type_ss->setUpper(type_up);

    if (!m_ctxt->specializationDepth()) {
        DEBUG("Change symbol-lookup scope");
        ISymbolTableIterator *it = TaskResolveSymbolPathRef(
            m_ctxt->getDebugMgr(), m_ctxt->root()).mkIterator(
                m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
                type);
        /*
        it->popScope();
         */
        it->pushScope(type_ss, ast::SymbolRefPathElemKind::ElemKind_TypeSpec);

        ISymbolTableIteratorUP tmp(it->clone());
        while (tmp->hasScopes()) {
            DEBUG("Scope: %s %d", tmp->getScope()->getName().c_str(), tmp->getScope()->getId());
            tmp->popScope();
        }
        m_ctxt->pushSymtab(it);
    } else {
        DEBUG("Leaving symbol-lookup scope %d", m_ctxt->specializationDepth());
    }

    m_ctxt->incSpecializationDepth();

    // Need to remove the leaf node in this case, since
    // the symbol resolver will attempt to push it on again
//    root_it->popScope();

    // Resolution must be relative to the declaration 
    // scope of the specialized type
    DEBUG_ENTER("Resolve Specialized Type %s", type_ss->getName().c_str());
    TaskResolveRefs(m_ctxt).resolve(type_ss);
    DEBUG_LEAVE("Resolve Specialized Type %s", type_ss->getName().c_str());

    if (type_ss->getTarget()->getAssocData()) {
        DEBUG("Type has associated data");
        AssocDataTypeScope *ad = dynamic_cast<AssocDataTypeScope *>(
            type_ss->getTarget()->getAssocData());
        if (ad) {
            ad->postSpecialize(
                m_ctxt, 
                NodeKind::cast<ast::ITypeScope>(type_ss->getTarget()));
        }
    }

    queueAsserts(type, type_up, type_ss, use_loc);

    ast::ISymbolRefPath *ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();

    // Copy over initial path
    ret->getPath().insert(
        ret->getPath().begin(),
        type->getPath().begin(),
        type->getPath().end());
            
    // Now, add on a directive to get the new specialization
    ret->getPath().push_back({
        ast::SymbolRefPathElemKind::ElemKind_TypeSpec,
        id
    });

    m_ctxt->decSpecializationDepth();

    if (!m_ctxt->specializationDepth()) {
        m_ctxt->popSymtab();
    }
    
    DEBUG_LEAVE("mk %p", ret);

    return ret;
}

/**
 * Add the members of each instance extension of the generic whose parameter
 * list equals `params` (17.2.6b) to `type_s`, the new specialization's AST,
 * before its symbol tree is built. They are the extension's own nodes, not
 * copies: specializations with equal lists are one (8.3), so this is the only
 * one the extension applies to, and the statement is then bound where it is
 * written, as a generic extension's body is. A second match would be a
 * defect in that identity; it gets copies rather than a share.
 *
 * `members` maps each member to the scope that declares its extension. More
 * than one extension of the same instance is applied, in the order they were
 * registered.
 */
void TaskGetSpecializedTemplateType::applyInstanceExtensions(
        ast::ISymbolTypeScope               *type_up,
        ast::ITypeScope                     *type_s,
        ast::ITemplateParamDeclList         *params,
        std::map<ast::IScopeChild *, ast::ISymbolScope *> &members) {
    const std::vector<InstanceExtension> *exts =
        m_ctxt->instanceExtensions(type_up);
    if (!exts) {
        return;
    }
    TaskCompareParamLists p_comp(m_ctxt->getFactory(), m_ctxt->root());
    // What the type declares, its generic extensions included (they are in
    // the generic's AST): 17.2.3 makes a second declaration of one an error.
    std::map<std::string, ast::IScopeChild *> names;
    bool have_names = false;
    for (std::vector<InstanceExtension>::const_iterator
            it=exts->begin(); it!=exts->end(); it++) {
        if (!p_comp.equal(it->params.get(), params)) {
            continue;
        }
        DEBUG("Apply instance extension to %s", type_up->getName().c_str());
        if (!have_names) {
            for (std::vector<ast::IScopeChildUP>::const_iterator
                    c_it=type_s->getChildren().begin();
                    c_it!=type_s->getChildren().end(); c_it++) {
                std::string name = TaskGetName().get(c_it->get());
                if (name.size()) {
                    names.insert({name, c_it->get()});
                }
            }
            have_names = true;
        }
        bool share = m_ctxt->applyInstanceExtension(it->ext);
        for (std::vector<ast::IScopeChildUP>::const_iterator
                c_it=it->ext->getChildren().begin();
                c_it!=it->ext->getChildren().end(); c_it++) {
            ast::IScopeChild *c = c_it->get();
            if (NodeKind::cast<ast::IExtendType>(c)
                    || NodeKind::cast<ast::IExtendEnum>(c)) {
                // Reported by TaskApplyTypeExtensions::applyInstanceExtension.
                continue;
            }
            // A constraint of a name the type has conjoins with it, as in a
            // generic extension (TaskApplyTypeExtensions::mergeChild).
            std::string name = TaskGetName().get(c);
            if (name.size() && !NodeKind::cast<ast::IConstraintBlock>(c)) {
                std::map<std::string, ast::IScopeChild *>::const_iterator n_it =
                    names.find(name);
                if (n_it != names.end()) {
                    if (share) {
                        std::vector<std::pair<ast::Location, std::string>> related;
                        related.push_back({
                            TaskResolveRootRef::declLocation(n_it->second),
                            "first declared here"});
                        m_ctxt->addMarker(
                            MarkerSeverityE::Error,
                            TaskResolveRootRef::declLocation(c),
                            "duplicate declaration of '" + name + "' in an "
                                "extension of an instance of '" + type_up->getName()
                                + "': the type already declares it (17.2.3)",
                            related);
                    }
                    continue;
                }
                names.insert({name, c});
            }
            if (share) {
                // Non-owning: the `extend` statement owns its members
                // (TaskApplyTypeExtensions::mergeIntoGenericAst).
                type_s->getChildren().push_back(ast::IScopeChildUP(c, false));
            } else {
                TaskCopyAst copier(m_ctxt->getFactory());
                c = copier.copy(c_it->get());
                if (!c) {
                    continue;
                }
                c->setParent(type_s);
                type_s->getChildren().push_back(ast::IScopeChildUP(c));
            }
            // Its index is its place in the type: a path into a constraint's
            // body steps through it (TaskGetItemIndex), and the builder
            // numbered it in the `extend` statement.
            c->setIndex(type_s->getChildren().size()-1);
            members[c] = it->decl_s;
        }
    }
}

void TaskGetSpecializedTemplateType::queueAsserts(
        const ast::ISymbolRefPath           *type,
        ast::ISymbolTypeScope               *type_up,
        ast::ISymbolTypeScope               *type_ss,
        const ast::Location                 &use_loc) {
    ast::IScope *generic = NodeKind::cast<ast::IScope>(type_up->getTarget());
    if (!generic) {
        return;
    }
    std::shared_ptr<ast::ISymbolRefPath> path;
    for (std::vector<ast::ICompileCondUP>::const_iterator
            it=generic->getCompile_conds().begin();
            it!=generic->getCompile_conds().end(); it++) {
        ast::ICompileCond *cc = it->get();
        if (!cc->getDeferred() || !cc->getCond()) {
            continue;
        }
        if (!path) {
            // The caller's path may not outlive this call.
            path.reset(m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath());
            path->getPath() = type->getPath();
        }
        ResolveContext *ctxt = m_ctxt;
        ast::Location loc = (use_loc.fileid >= 0)?use_loc:cc->getLocation();
        m_ctxt->addPostResolveAction([ctxt, path, type_ss, cc, loc]() {
            checkAssert(ctxt, path.get(), type_ss, cc, loc);
        });
    }
}

void TaskGetSpecializedTemplateType::checkAssert(
        ResolveContext                      *ctxt,
        const ast::ISymbolRefPath           *type,
        ast::ISymbolTypeScope               *type_ss,
        ast::ICompileCond                   *cc,
        const ast::Location                 &use_loc) {
    DEBUG_ENTER("checkAssert %s", type_ss->getName().c_str());
    // The generic's condition is bound to the generic's parameters; a copy
    // (which drops the bindings) is bound to this specialization's, as its
    // body was in mk().
    TaskCopyAst copier(ctxt->getFactory());
    std::unique_ptr<ast::IExpr> cond(copier.copy(cc->getCond()));

    IValInt *val = 0;
    std::unique_ptr<IVal> val_h;
    if (cond && copier.failure().empty()) {
        ISymbolTableIterator *it = TaskResolveSymbolPathRef(
            ctxt->getDebugMgr(), ctxt->root()).mkIterator(
                ctxt->getFactory()->mkAstSymbolTableIterator(ctxt->root()),
                type);
        it->pushScope(type_ss, ast::SymbolRefPathElemKind::ElemKind_TypeSpec);
        ctxt->pushSymtab(it);
        ctxt->pushQuiet();
        TaskResolveRefs resolver(ctxt);
        cond->accept(&resolver);
        ctxt->popQuiet();
        ctxt->popSymtab();

        val_h.reset(TaskEvalExpr(ctxt->getFactory(), ctxt->root()).eval(cond.get()));
        val = dynamic_cast<IValInt *>(val_h.get());
    }

    // The specialization's name leaves a default that depends on another
    // parameter as '?' (`a<0,?>`); every value is known by now.
    std::string name = type_ss->getName();
    ast::ITypeScope *spec = NodeKind::cast<ast::ITypeScope>(type_ss->getTarget());
    if (spec && spec->getParams() && name.find('?') != std::string::npos) {
        std::string args;
        bool ok = true;
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
                it=spec->getParams()->getParams().begin();
                ok && it!=spec->getParams()->getParams().end(); it++) {
            std::string arg = "?";
            if (ast::ITemplateValueParamDecl *v =
                    NodeKind::cast<ast::ITemplateValueParamDecl>(it->get())) {
                std::unique_ptr<IVal> pv(v->getDflt()
                    ? TaskEvalExpr(ctxt->getFactory(), ctxt->root()).eval(v->getDflt()) : 0);
                if (IValInt *iv = dynamic_cast<IValInt *>(pv.get())) {
                    arg = std::to_string(iv->getValS());
                } else {
                    ok = false;
                }
            } else {
                ok = false;
            }
            args += ((args.size())?",":"") + arg;
        }
        if (ok) {
            name = name.substr(0, name.find('<')) + "<" + args + ">";
        }
    }

    std::vector<std::pair<ast::Location, std::string>> related;
    related.push_back({cc->getLocation(), "the assertion"});
    if (!val) {
        ctxt->addMarker(
            MarkerSeverityE::Error,
            use_loc,
            "compile assert condition cannot be evaluated for '" + name
                + "': a compile-time expression may reference only constants and "
                "template parameters (19.4)",
            related);
    } else if (!val->getValS()) {
        ctxt->addMarker(
            MarkerSeverityE::Error,
            use_loc,
            "compile assert failed for '" + name + "'"
                + ((cc->getMsg().size())?": " + cc->getMsg():std::string()),
            related);
    }
    DEBUG_LEAVE("checkAssert");
}

/**
 * Render one bound *type* argument.
 *
 * Prefers the resolved declaration's name over the spelling, so an argument
 * that is itself a specialization reads as what it is: specializations are
 * created innermost-first, so `Q<int>` already carries that name by the time
 * an enclosing `S<Q<int>>` is named.
 */
std::string TaskGetSpecializedTemplateType::argName(ast::IDataType *dt) {
    if (!dt) {
        return "?";
    }

    if (ast::IDataTypeUserDefined *ud =
            NodeKind::cast<ast::IDataTypeUserDefined>(dt)) {
        if (ud->getType_id()) {
            ast::IScopeChild *sc = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(),
                m_ctxt->root()).resolve(ud->getType_id()->getTarget());
            if (ast::ISymbolChildrenScope *ss =
                    NodeKind::cast<ast::ISymbolChildrenScope>(sc)) {
                return ss->getName();
            }
            // Unresolved: fall back to what was written.
            if (ud->getType_id()->getElems().size() &&
                ud->getType_id()->getElems().back()->getId()) {
                return ud->getType_id()->getElems().back()->getId()->getId();
            }
        }
    } else if (ast::IDataTypeInt *i = NodeKind::cast<ast::IDataTypeInt>(dt)) {
        std::string base = (i->getIs_signed())?"int":"bit";
        if (ast::IExprUnsignedNumber *w =
                NodeKind::cast<ast::IExprUnsignedNumber>(i->getWidth())) {
            return base + "[" + std::to_string(w->getValue()) + "]";
        }
        return base;
    } else if (NodeKind::cast<ast::IDataTypeBool>(dt)) {
        return "bool";
    } else if (NodeKind::cast<ast::IDataTypeString>(dt)) {
        return "string";
    } else if (NodeKind::cast<ast::IDataTypeChandle>(dt)) {
        return "chandle";
    }

    // Deliberately not silent. A name that says "there is an argument here I
    // cannot render" is still a name that distinguishes two specializations
    // less well than it should -- but it says so, where `<>` did not.
    return "?";
}

/** Render one bound *value* argument. */
std::string TaskGetSpecializedTemplateType::argName(ast::IExpr *e) {
    if (!e) {
        return "?";
    }
    if (ast::IExprUnsignedNumber *n =
            NodeKind::cast<ast::IExprUnsignedNumber>(e)) {
        return std::to_string(n->getValue());
    } else if (ast::IExprSignedNumber *n =
            NodeKind::cast<ast::IExprSignedNumber>(e)) {
        return std::to_string(n->getValue());
    } else if (ast::IExprId *id = NodeKind::cast<ast::IExprId>(e)) {
        return id->getId();
    }
    return "?";
}

/**
 * The name a specialization is known by.
 *
 * This used to emit `name<>` -- the angle brackets with nothing between them --
 * so every specialization of a generic had the *same* name. Identity was never
 * affected (specializations are matched by comparing parameter lists, not
 * names), but everything a human or a tool reads was: a diagnostic naming
 * `S<>` cannot say which use it means, and an outline built on the API showed
 * one entry repeated.
 *
 * It also made a name test on a specialization scope meaningless, which is
 * what several collection checks were doing -- see BuiltinCollectionUtil.
 */
std::string TaskGetSpecializedTemplateType::mkTypename(
        const ast::ISymbolRefPath           *type,
        ast::ITemplateParamDeclList         *params) {
    std::string name = TaskResolveSymbolPathRef(m_ctxt->getDebugMgr(), m_ctxt->root()).mkName(type);

    name += "<";

    if (params) {
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=params->getParams().begin();
            it!=params->getParams().end(); it++) {
            if (it != params->getParams().begin()) {
                name += ",";
            }
            // On a specialized list the dflt slot holds the bound argument.
            if (ast::ITemplateValueParamDecl *v =
                    NodeKind::cast<ast::ITemplateValueParamDecl>(it->get())) {
                name += argName(v->getDflt());
            } else if (ast::ITemplateGenericTypeParamDecl *g =
                    NodeKind::cast<ast::ITemplateGenericTypeParamDecl>(it->get())) {
                name += argName(g->getDflt());
            } else if (ast::ITemplateCategoryTypeParamDecl *c =
                    NodeKind::cast<ast::ITemplateCategoryTypeParamDecl>(it->get())) {
                name += argName(c->getDflt());
            } else {
                name += "?";
            }
        }
    }

    name += ">";

    return name;
}


dmgr::IDebug *TaskGetSpecializedTemplateType::m_dbg = 0;

}
