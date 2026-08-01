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
#include "pssp/impl/TaskCopyAst.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "AssocDataTypeScope.h"
#include "TaskBuildSymbolTree.h"
#include "TaskCompareParamLists.h"
#include "TaskResolveRefs.h"


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
        ast::ITypeScope *type_s_t = dynamic_cast<ast::ITypeScope  *>(sym_type_s_t->getTarget());

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
    ast::ITemplateParamDeclList         *params) {
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

    if (!type_s) {
        // The copier hit a construct it does not handle.  It has already named
        // the construct on stderr; report the failure against the declaration
        // and give up on this specialization rather than dereferencing null.
        m_ctxt->addErrorMarker(
            type_up->getTarget()->getLocation(),
            "failed to specialize type '%s': it contains a construct the "
            "AST copier does not support",
            type_up->getName().c_str());
        DEBUG_LEAVE("mk (copy failed)");
        return 0;
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

    // Have the specialized type point to the unspecialized
    // parameterized type as its super type
    ast::ITypeIdentifier *super_t = m_ctxt->getFactory()->getAstFactory()->mkTypeIdentifier();
    super_t->setTarget(copier.copy(type));

    // We must now build a symbol-scope node for the type scope
    ast::ISymbolTypeScope *type_ss = TaskBuildSymbolTree(
        m_ctxt->getDebugMgr(),
        m_ctxt->getFactory()->getAstFactory(),
        0).build(type_s);

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
                dynamic_cast<ast::ITypeScope *>(type_ss->getTarget()));
        }
    }

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
            dynamic_cast<ast::IDataTypeUserDefined *>(dt)) {
        if (ud->getType_id()) {
            ast::IScopeChild *sc = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(),
                m_ctxt->root()).resolve(ud->getType_id()->getTarget());
            if (ast::ISymbolChildrenScope *ss =
                    dynamic_cast<ast::ISymbolChildrenScope *>(sc)) {
                return ss->getName();
            }
            // Unresolved: fall back to what was written.
            if (ud->getType_id()->getElems().size() &&
                ud->getType_id()->getElems().back()->getId()) {
                return ud->getType_id()->getElems().back()->getId()->getId();
            }
        }
    } else if (ast::IDataTypeInt *i = dynamic_cast<ast::IDataTypeInt *>(dt)) {
        std::string base = (i->getIs_signed())?"int":"bit";
        if (ast::IExprUnsignedNumber *w =
                dynamic_cast<ast::IExprUnsignedNumber *>(i->getWidth())) {
            return base + "[" + std::to_string(w->getValue()) + "]";
        }
        return base;
    } else if (dynamic_cast<ast::IDataTypeBool *>(dt)) {
        return "bool";
    } else if (dynamic_cast<ast::IDataTypeString *>(dt)) {
        return "string";
    } else if (dynamic_cast<ast::IDataTypeChandle *>(dt)) {
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
            dynamic_cast<ast::IExprUnsignedNumber *>(e)) {
        return std::to_string(n->getValue());
    } else if (ast::IExprSignedNumber *n =
            dynamic_cast<ast::IExprSignedNumber *>(e)) {
        return std::to_string(n->getValue());
    } else if (ast::IExprId *id = dynamic_cast<ast::IExprId *>(e)) {
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
                    dynamic_cast<ast::ITemplateValueParamDecl *>(it->get())) {
                name += argName(v->getDflt());
            } else if (ast::ITemplateGenericTypeParamDecl *g =
                    dynamic_cast<ast::ITemplateGenericTypeParamDecl *>(it->get())) {
                name += argName(g->getDflt());
            } else if (ast::ITemplateCategoryTypeParamDecl *c =
                    dynamic_cast<ast::ITemplateCategoryTypeParamDecl *>(it->get())) {
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
