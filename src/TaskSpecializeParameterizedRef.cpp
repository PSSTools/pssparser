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
#include "pssp/impl/NodeKind.h"
#include "pssp/ast/ITemplateCategoryTypeParamDecl.h"
#include "pssp/ast/ITemplateGenericTypeParamDecl.h"
#include <set>


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
    ast::ITemplateParamDeclList *pdecl_list = buildParams(target, pvals, use_loc);

    if (!pdecl_list) {
        // Encountered an error while building out the param list
        DEBUG_LEAVE("specialize (no params)");
        return 0;
    }

    TaskGetSpecializedTemplateType typespec_getter(m_ctxt);
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
            pdecl_list,
            use_loc);
    }
    

    DEBUG_LEAVE("specialize %p", target_t);
    return target_t;
}

ast::ITemplateParamDeclList *TaskSpecializeParameterizedRef::buildParams(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateParamValueList        *pvals,
        const ast::Location                 &use_loc) {
    // Find the base type
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
            "'%s' is not a generic type, so it takes no template arguments",
            target_c->getName().c_str());
        return 0;
    }

    DEBUG("target: %s", target_c->getName().c_str());

    bindDefaults(target, target_c);

    // Form parameter list 
    return TaskBuildParamValList(m_ctxt).build(
            target_c->getPlist(),
            pvals,
            use_loc,
            target_c->getName());
}

namespace {

/**
 * Finds whether a default may depend on the generic's own parameter list:
 * an identifier under it spelled like one of its parameters, or template or
 * call arguments anywhere under it. Conservative -- a member or a qualified
 * name spelled like a parameter counts too -- which only leaves that default
 * to be resolved in the specialization, as it always was.
 *
 * Arguments count whatever they name: binding `S<int>` in S's own default
 * would specialize S from inside its own defaults binding, where the depth
 * limit's diagnostic is quiet.
 */
class MayDependOnList : public virtual ast::VisitorBase {
public:
    MayDependOnList(const std::set<std::string> &names) :
        m_names(names), m_ret(false) { }

    bool check(const std::function<void(ast::IVisitor *)> &piece) {
        m_ret = false;
        piece(m_this);
        return m_ret;
    }

    virtual void visitExprId(ast::IExprId *i) override {
        m_ret |= (m_names.find(i->getId()) != m_names.end());
    }

    virtual void visitTypeIdentifierElem(ast::ITypeIdentifierElem *i) override {
        m_ret |= (i->getParams() != 0);
        ast::VisitorBase::visitTypeIdentifierElem(i);
    }

    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) override {
        m_ret |= (i->getParams() != 0);
        ast::VisitorBase::visitExprMemberPathElem(i);
    }

private:
    const std::set<std::string>     &m_names;
    bool                            m_ret;
};

typedef std::function<void(ast::IVisitor *)> VisitFn;

template <class T> void addPiece(std::vector<VisitFn> &pieces, T *n) {
    if (n) {
        pieces.push_back([n](ast::IVisitor *v) { n->accept(v); });
    }
}

/**
 * What of a template parameter declaration names something in the generic's
 * declaring scope: its default, and a value parameter's type, which the copy
 * of a default carries along.
 */
void paramPieces(ast::IScopeChild *c, std::vector<VisitFn> &pieces) {
    NodeKind nk(c);
    if (ast::ITemplateValueParamDecl *v = nk.as<ast::ITemplateValueParamDecl>()) {
        addPiece(pieces, v->getType());
        addPiece(pieces, v->getDflt());
    } else if (ast::ITemplateCategoryTypeParamDecl *ct =
            nk.as<ast::ITemplateCategoryTypeParamDecl>()) {
        // Not the restriction: checkCategoryArg skips one still unbound, and
        // an instance extension specializes before super types are resolved,
        // when no argument can yet be shown to derive from it.
        addPiece(pieces, ct->getDflt());
    } else if (ast::ITemplateGenericTypeParamDecl *gt =
            nk.as<ast::ITemplateGenericTypeParamDecl>()) {
        addPiece(pieces, gt->getDflt());
    }
}

bool hasDflt(ast::IScopeChild *c) {
    NodeKind nk(c);
    if (ast::ITemplateValueParamDecl *v = nk.as<ast::ITemplateValueParamDecl>()) {
        return v->getDflt();
    } else if (ast::ITemplateCategoryTypeParamDecl *ct =
            nk.as<ast::ITemplateCategoryTypeParamDecl>()) {
        return ct->getDflt();
    } else if (ast::ITemplateGenericTypeParamDecl *gt =
            nk.as<ast::ITemplateGenericTypeParamDecl>()) {
        return gt->getDflt();
    }
    return false;
}

}

/**
 * Bind the references in the generic's parameter defaults (and in the value
 * parameters' types their copies carry), in its declaring scope, before
 * the first use that falls back on one. A default means what
 * it means where the generic is written. The copy TaskBuildParamValList makes
 * of a default then carries its targets: `packed_s<>` is found to be the same
 * specialization as `packed_s<LITTLE_ENDIAN>` (8.3), and a type default is
 * never looked up from the use site.
 *
 * A generic not visited yet has unbound defaults: the core library is linked
 * after the user's files, and an instance extension specializes while
 * extensions are applied, before any body is visited. Left unbound, a default
 * was resolved with the specialization's parameter list, in whatever scope
 * the caller had on top -- for a nested specialization, the enclosing
 * specialization's body, where `struct g_s<struct T, struct A=d_s>`'s d_s
 * may be invisible (an import of the enclosing package does not reach it) or
 * mean something else.
 *
 * Quiet: the generic's own visit reports anything wrong with a default.
 *
 * Not a default that may depend on the list (MayDependOnList): a type
 * identifier keeps its target when copied, so binding `sizeof_s<R>` here
 * would tie every specialization to the generic's own R. Such a default is
 * resolved in the specialization, where R is bound. Each default is judged
 * on its own; one that depends no longer keeps the others unbound.
 */
void TaskSpecializeParameterizedRef::bindDefaults(
        ast::ISymbolRefPath                 *target,
        ast::ISymbolTypeScope               *target_c) {
    std::set<std::string> names;
    std::vector<VisitFn> pieces;
    bool any = false;
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=target_c->getPlist()->getChildren().begin();
            it!=target_c->getPlist()->getChildren().end(); it++) {
        ast::ITemplateParamDecl *pd =
            NodeKind::cast<ast::ITemplateParamDecl>(it->get());
        if (pd && pd->getName()) {
            names.insert(pd->getName()->getId());
        }
        any |= hasDflt(it->get());
        paramPieces(it->get(), pieces);
    }
    if (!any || !m_ctxt->firstDefaultsBinding(target_c)) {
        return;
    }
    DEBUG_ENTER("bindDefaults %s", target_c->getName().c_str());

    MayDependOnList may_depend(names);
    inDeclScope(target, [&]() {
        TaskResolveRefs resolver(m_ctxt);
        for (std::vector<VisitFn>::const_iterator
                it=pieces.begin(); it!=pieces.end(); it++) {
            if (!may_depend.check(*it)) {
                (*it)(&resolver);
            }
        }
    });

    DEBUG_LEAVE("bindDefaults");
}

ast::ISymbolEnumScope *TaskSpecializeParameterizedRef::paramEnum(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateValueParamDecl        *p) {
    ast::IDataTypeUserDefined *udt =
        NodeKind::cast<ast::IDataTypeUserDefined>(p->getType());
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
