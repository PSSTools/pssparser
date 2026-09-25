/*
 * TaskSpecializeParameterizedRef.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
#include "TaskSpecializeParameterizedRef.h"
#include "TaskGetSpecializedTemplateType.h"
#include "TaskBuildParamValList.h"
#include "TaskResolveRefs.h"
#include "TaskResolveRef.h"
#include "ExprTypeOf.h"


namespace pssp {



TaskSpecializeParameterizedRef::TaskSpecializeParameterizedRef(ResolveContext *ctxt) :
    m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskSpecializeParameterizedRef", ctxt->getDebugMgr());
}

TaskSpecializeParameterizedRef::~TaskSpecializeParameterizedRef() {

}

ast::ISymbolRefPath *TaskSpecializeParameterizedRef::specialize(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateParamValueList        *pvals,
        const ast::Location                 &use_loc) {
    DEBUG_ENTER("specialize");
    // Find the base type
    ast::IScopeChild *target_sc = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), 
        m_ctxt->root()).resolve(target);
    ast::ISymbolTypeScope *target_c = 
        TaskResolveSymbolPathRef(
            m_ctxt->getDebugMgr(), 
            m_ctxt->root()).resolveT<ast::ISymbolTypeScope>(target);

    if (!target_c) {
        DEBUG("TODO: Flag error about templated type");
        return 0;
    }

    if (!target_c->getPlist()) {
        m_ctxt->addErrorMarker(
            use_loc,
            "Type %s is not templated",
            target_c->getName().c_str());
        return 0;
    }

    DEBUG("target: %s", target_c->getName().c_str());

    bindDefaults(target, target_c);

    // Form parameter list 
    ast::ITemplateParamDeclList *pdecl_list = TaskBuildParamValList(m_ctxt).build(
            target_c->getPlist(),
            pvals,
            use_loc);
    TaskGetSpecializedTemplateType typespec_getter(m_ctxt);

    if (!pdecl_list) {
        // Encountered an error while building out the param list
        return 0;
    }

    ast::ISymbolRefPath *target_t = typespec_getter.find(
        target, 
        pdecl_list);

    if (target_t) {
        // The new parameter list that we created is no longer needed
        DEBUG("Specialization already exists");
        delete pdecl_list;
    } else {
        DEBUG("Must create new specialization");
        target_t = typespec_getter.mk(
            target, 
            pdecl_list);
    }
    

    DEBUG_LEAVE("specialize %p", target_t);
    return target_t;
}

namespace {

/** Finds template or call arguments anywhere under a node. */
class HasArgs : public virtual ast::VisitorBase {
public:
    HasArgs() : m_ret(false) { }

    bool check(ast::IScopeChild *c) {
        c->accept(m_this);
        return m_ret;
    }

    virtual void visitTypeIdentifierElem(ast::ITypeIdentifierElem *i) override {
        m_ret |= (i->getParams() != 0);
    }

    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) override {
        m_ret |= (i->getParams() != 0);
        ast::VisitorBase::visitExprMemberPathElem(i);
    }

private:
    bool                    m_ret;
};

}

/**
 * Bind the references in the generic's value-parameter defaults, in its
 * declaring scope, before the first use that falls back on one. The copy
 * TaskBuildParamValList makes of a default then carries its targets, so
 * `packed_s<>` is found to be the same specialization as
 * `packed_s<LITTLE_ENDIAN>` (8.3), and never resolves the default at the use
 * site. A generic declared after its first use -- the core library is linked
 * after the user's files -- has not been visited yet at that point.
 *
 * Quiet: the generic's own visit reports anything wrong with a default.
 *
 * Only a generic whose defaults hold no template or call arguments: a type
 * identifier keeps its target when copied, so binding `sizeof_s<R>` here
 * would tie every specialization to the generic's own R.
 */
void TaskSpecializeParameterizedRef::bindDefaults(
        ast::ISymbolRefPath                 *target,
        ast::ISymbolTypeScope               *target_c) {
    bool any = false;
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=target_c->getPlist()->getChildren().begin();
            it!=target_c->getPlist()->getChildren().end() && !any; it++) {
        ast::ITemplateValueParamDecl *v =
            dynamic_cast<ast::ITemplateValueParamDecl *>(it->get());
        any = (v && v->getDflt());
    }
    if (!any || !m_ctxt->firstDefaultsBinding(target_c)) {
        return;
    }
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=target_c->getPlist()->getChildren().begin();
            it!=target_c->getPlist()->getChildren().end(); it++) {
        if (HasArgs().check(it->get())) {
            return;
        }
    }
    DEBUG_ENTER("bindDefaults %s", target_c->getName().c_str());

    inDeclScope(target, [&]() {
        TaskResolveRefs resolver(m_ctxt);
        target_c->getPlist()->accept(&resolver);
    });

    DEBUG_LEAVE("bindDefaults");
}

ast::ISymbolEnumScope *TaskSpecializeParameterizedRef::paramEnum(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateValueParamDecl        *p) {
    ast::IDataTypeUserDefined *udt =
        dynamic_cast<ast::IDataTypeUserDefined *>(p->getType());
    if (!udt || !udt->getType_id()) {
        return 0;
    }
    ast::ITypeIdentifier *tid = udt->getType_id();
    if (!tid->getTarget()) {
        // An enum takes no template arguments; a type that does is none of
        // this function's business, and binding it here would specialize.
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
                it=tid->getElems().begin(); it!=tid->getElems().end(); it++) {
            if ((*it)->getParams()) {
                return 0;
            }
        }
        inDeclScope(target, [&]() {
            ast::ISymbolRefPath *t = TaskResolveRef(m_ctxt, true, false).resolve(tid);
            if (t) {
                tid->setTarget(t);
            }
        });
    }
    return ExprTypeOf(m_ctxt).enumOfType(udt);
}

void TaskSpecializeParameterizedRef::inDeclScope(
        ast::ISymbolRefPath                 *target,
        const std::function<void()>         &f) {
    // As TaskResolveRefs::resolve(ISymbolTypeScope *) does for the generic
    // itself: the parameter list, from the scope that declares the type.
    // Quiet: the generic's own visit reports anything wrong in it.
    ISymbolTableIterator *it = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), m_ctxt->root()).mkIterator(
            m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
            target);
    it->popScope();
    m_ctxt->pushSymtab(it);
    m_ctxt->pushQuiet();
    f();
    m_ctxt->popQuiet();
    m_ctxt->popSymtab();
}

dmgr::IDebug *TaskSpecializeParameterizedRef::m_dbg = 0;

}
