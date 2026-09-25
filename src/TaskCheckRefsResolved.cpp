/**
 * TaskCheckRefsResolved.cpp
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
#include "TaskCheckRefsResolved.h"
#include "pssp/ast/IAnnotation.h"
#include "pssp/ast/IAnnotationParam.h"
#include "pssp/ast/IDataTypeUserDefined.h"
#include "pssp/ast/IExtendType.h"
#include "pssp/ast/ICovergroupType.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IGenericConstraintDeclBool.h"
#include "pssp/ast/IGenericConstraintDeclValue.h"
#include "pssp/ast/IGenericConstraintParam.h"
#include "pssp/ast/ITypeScope.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ISymbolChildrenScope.h"
#include "pssp/ast/ISymbolScope.h"

namespace pssp {

namespace {

/**
 * Every name declared in the units, the core library's included: the name of
 * each scope child (types, fields, functions, parameters, enum items,
 * labels...).
 */
class NameCollector : public ast::VisitorBase {
public:
    NameCollector(OccurrenceCollector *coll, std::set<std::string> &names) :
        m_coll(coll), m_names(names) { }

    virtual void visitScopeChild(ast::IScopeChild *i) override {
        ast::IExprId *n = m_coll->nameOf(i);
        if (n) {
            m_names.insert(n->getId());
        }
        ast::VisitorBase::visitScopeChild(i);
    }

private:
    OccurrenceCollector         *m_coll;
    std::set<std::string>       &m_names;
};

}

TaskCheckRefsResolved::TaskCheckRefsResolved(ResolveContext *ctxt) :
    m_ctxt(ctxt), m_coll(ctxt->getDebugMgr()), m_had_errors(false) {
    DEBUG_INIT("pssp::TaskCheckRefsResolved", ctxt->getDebugMgr());
}

TaskCheckRefsResolved::~TaskCheckRefsResolved() { }

void TaskCheckRefsResolved::check(
        ast::IRootSymbolScope   *root,
        uint32_t                n_builtin_units) {
    DEBUG_ENTER("check");
    m_occ.clear();
    m_names.clear();
    m_checked.clear();
    m_had_errors = m_ctxt->hasErrors();

    std::vector<Occurrence> occs;
    m_coll.collect(root, occs);
    for (std::vector<Occurrence>::const_iterator
        it=occs.begin(); it!=occs.end(); it++) {
        m_occ.emplace(OccurrenceCollector::key(it->id->getLocation()), *it);
    }

    collectNames(root);

    for (uint32_t i=n_builtin_units; i<root->getUnits().size(); i++) {
        ast::IGlobalScope *unit = root->getUnits().at(i).get();
        if (unit->getFileid() >= 1) {
            unit->accept(m_this);
        }
    }

    DEBUG_LEAVE("check");
}

void TaskCheckRefsResolved::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    std::vector<ast::IExprId *> ids;
    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
        it=i->getElems().begin(); it!=i->getElems().end(); it++) {
        ids.push_back((*it)->getId());
    }
    checkRef(ids, true);
    // On into the template arguments, which are references of their own.
    ast::VisitorBase::visitTypeIdentifier(i);
}

void TaskCheckRefsResolved::visitExprRefName(ast::IExprRefName *i) {
    checkRef({i->getId()}, false);
}

void TaskCheckRefsResolved::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    std::vector<ast::IExprId *> ids;
    if (i->getHier_id()) {
        for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
            it=i->getHier_id()->getElems().begin();
            it!=i->getHier_id()->getElems().end(); it++) {
            ids.push_back((*it)->getId());
        }
    }
    checkRef(ids, false);
    // On into subscripts and call arguments.
    ast::VisitorBase::visitExprRefPathContext(i);
}

void TaskCheckRefsResolved::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    if (m_checked.find(i) == m_checked.end()) {
        std::vector<ast::IExprId *> ids;
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin(); it!=i->getBase().end(); it++) {
            ids.push_back((*it)->getId());
        }
        checkRef(ids, false);
    }
    ast::VisitorBase::visitExprRefPathStatic(i);
}

void TaskCheckRefsResolved::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    // One reference, `p::T::f(1).x`: the root and the leaf are its two
    // halves, and a miss in the root means the leaf was never looked up.
    std::vector<ast::IExprId *> ids;
    if (i->getRoot()) {
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getRoot()->getBase().begin();
            it!=i->getRoot()->getBase().end(); it++) {
            ids.push_back((*it)->getId());
        }
        m_checked.insert(i->getRoot());
    }
    if (i->getLeaf()) {
        for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
            it=i->getLeaf()->getElems().begin();
            it!=i->getLeaf()->getElems().end(); it++) {
            ids.push_back((*it)->getId());
        }
    }
    checkRef(ids, false);
    ast::VisitorBase::visitExprRefPathStaticRooted(i);
}

void TaskCheckRefsResolved::visitExtendType(ast::IExtendType *i) {
    if (i->getTarget() && !i->getTarget()->getTarget()) {
        i->getTarget()->accept(m_this);
        return;
    }
    ast::VisitorBase::visitExtendType(i);
}

void TaskCheckRefsResolved::visitTypeScope(ast::ITypeScope *i) {
    m_type_s.push_back(i);
    ast::VisitorBase::visitTypeScope(i);
    m_type_s.pop_back();
}

void TaskCheckRefsResolved::visitAnnotation(ast::IAnnotation *i) {
    if (i->getType() && !i->getType()->getTarget()
            && m_ctxt->wasNoted(i->getLocation())) {
        return;
    }
    ast::VisitorBase::visitAnnotation(i);
}

void TaskCheckRefsResolved::visitAnnotationParam(ast::IAnnotationParam *i) {
    if (i->getName() && !m_ctxt->wasReported(i->getLocation())) {
        i->getName()->accept(m_this);
    }
    if (i->getValue()) {
        i->getValue()->accept(m_this);
    }
}

void TaskCheckRefsResolved::visitCovergroupInstantiation(ast::ICovergroupInstantiation *i) {
    // The covergroup type is an ordinary type reference; the port map and
    // options are not bound yet (WS10).
    if (i->getType()) {
        i->getType()->accept(m_this);
    }
}

void TaskCheckRefsResolved::visitExprAggrStructElem(ast::IExprAggrStructElem *i) {
    if (i->getValue()) {
        i->getValue()->accept(m_this);
    }
}

void TaskCheckRefsResolved::checkRef(
        const std::vector<ast::IExprId *>   &ids,
        bool                                is_type) {
    for (std::vector<ast::IExprId *>::const_iterator
        it=ids.begin(); it!=ids.end(); it++) {
        if (*it && m_ctxt->wasReported((*it)->getLocation())) {
            // Already diagnosed, and better than this can: "unknown type
            // 'x'; did you mean 'y'?". Repeating it would turn one mistake
            // into two errors.
            return;
        }
    }

    ast::IScopeChild *prev = 0;
    for (uint32_t ii=0; ii<ids.size(); ii++) {
        ast::IExprId *id = ids.at(ii);
        if (!id || !OccurrenceCollector::isKeyable(id)) {
            // Synthetic: built by the front end, not written by the user.
            return;
        }
        std::map<OccurrenceCollector::LocKey, Occurrence>::const_iterator it =
            m_occ.find(OccurrenceCollector::key(id->getLocation()));
        if (it == m_occ.end()) {
            return;
        }
        const Occurrence &occ = it->second;

        if (occ.resolution != OccurrenceResolution::Unresolved) {
            if (occ.resolution == OccurrenceResolution::Dependent) {
                // Depends on a template parameter; checked, if anywhere, in
                // the specializations.
                return;
            }
            prev = occ.decl;
            continue;
        }

        const std::string &name = id->getId();
        bool declared = (m_names.find(name) != m_names.end());

        if (is_type && ii > 0 && dynamic_cast<ast::IField *>(prev)) {
            // `tx::send_pkt s;` in an activity, where `tx` is a component
            // *instance*: the path is resolved by instance, not by scope, and
            // this node never receives a target. pssc resolves it the same
            // way (targets/sv/context.py).
            DEBUG("Note: '%s' is qualified by an instance", name.c_str());
            return;
        }

        if (ii > 0 && hasUnboundType(prev)) {
            // `x.f` where x's own type failed to resolve: that failure has
            // its own report, and f was never looked up.
            DEBUG("Note: '%s' follows an element of unresolved type", name.c_str());
            return;
        }

        if ((ii > 0 && prev)?reachesUnknownBase(prev):false) {
            // `x.f` where f may be declared by a base type of x's type that
            // failed to resolve, and was reported where it is named.
            DEBUG("Note: '%s' may be inherited from an unknown type", name.c_str());
            return;
        }

        if (ii == 0 || !prev) {
            // `f`, `super.f`, `this.f`: f may be inherited from an unknown
            // base of an enclosing type.
            for (std::vector<ast::ITypeScope *>::const_iterator
                t_it=m_type_s.begin(); t_it!=m_type_s.end(); t_it++) {
                if (hasUnknownBase(*t_it)) {
                    DEBUG("Note: '%s' may be inherited from an unknown type",
                        name.c_str());
                    return;
                }
            }
        }

        if (!declared) {
            if (ii == 0) {
                m_ctxt->addErrorMarker(
                    id->getLocation(),
                    "unknown %s '%s'",
                    (is_type)?"type":"identifier",
                    name.c_str());
            } else {
                m_ctxt->addErrorMarker(
                    id->getLocation(),
                    "'%s' has no member named '%s'",
                    ids.at(ii-1)->getId().c_str(),
                    name.c_str());
            }
        } else if (!m_had_errors) {
            m_ctxt->addErrorMarker(
                id->getLocation(),
                "'%s' was left unbound by pssparser, although the model "
                "declares it: a pssparser defect, please report it",
                name.c_str());
        } else {
            DEBUG("Note: '%s' unbound in a model with errors", name.c_str());
        }
        return;
    }
}

bool TaskCheckRefsResolved::hasUnboundType(ast::IScopeChild *decl) {
    if (!decl) {
        return false;
    }
    ast::IDataType *t = 0;
    if (ast::IField *f = dynamic_cast<ast::IField *>(decl)) {
        t = f->getType();
    } else if (ast::IProceduralStmtDataDeclaration *d =
            dynamic_cast<ast::IProceduralStmtDataDeclaration *>(decl)) {
        t = d->getDatatype();
    } else if (ast::IFunctionParamDecl *p =
            dynamic_cast<ast::IFunctionParamDecl *>(decl)) {
        t = p->getType();
    } else if (ast::IGenericConstraintParam *p =
            dynamic_cast<ast::IGenericConstraintParam *>(decl)) {
        t = p->getType();
    }
    ast::IDataTypeUserDefined *ut = dynamic_cast<ast::IDataTypeUserDefined *>(t);
    return ut && ut->getType_id() && !ut->getType_id()->getTarget();
}

bool TaskCheckRefsResolved::reachesUnknownBase(ast::IScopeChild *decl) {
    ast::IScopeChild *t = decl;
    ast::IDataType *dt = 0;
    if (ast::IField *f = dynamic_cast<ast::IField *>(decl)) {
        dt = f->getType();
    } else if (ast::IProceduralStmtDataDeclaration *d =
            dynamic_cast<ast::IProceduralStmtDataDeclaration *>(decl)) {
        dt = d->getDatatype();
    } else if (ast::IFunctionParamDecl *p =
            dynamic_cast<ast::IFunctionParamDecl *>(decl)) {
        dt = p->getType();
    } else if (ast::IGenericConstraintParam *p =
            dynamic_cast<ast::IGenericConstraintParam *>(decl)) {
        dt = p->getType();
    }
    if (dt) {
        ast::IDataTypeUserDefined *ut = dynamic_cast<ast::IDataTypeUserDefined *>(dt);
        if (!ut || !ut->getType_id() || !ut->getType_id()->getTarget()) {
            return false;
        }
        t = m_coll.unwrap(m_ctxt->resolveSymbolPathRef(ut->getType_id()->getTarget()));
    }
    return hasUnknownBase(dynamic_cast<ast::ITypeScope *>(t));
}

bool TaskCheckRefsResolved::hasUnknownBase(ast::ITypeScope *ts) {
    std::set<ast::ITypeScope *> seen;
    while (ts && seen.insert(ts).second && !ts->getSuper_cyclic()) {
        if (!ts->getSuper_t()) {
            return false;
        }
        if (!ts->getSuper_t()->getTarget()) {
            return true;
        }
        ts = dynamic_cast<ast::ITypeScope *>(m_coll.unwrap(
            m_ctxt->resolveSymbolPathRef(ts->getSuper_t()->getTarget())));
    }
    return false;
}

void TaskCheckRefsResolved::collectNames(ast::IRootSymbolScope *root) {
    NameCollector names(&m_coll, m_names);
    for (std::vector<ast::IGlobalScopeUP>::const_iterator
        it=root->getUnits().begin(); it!=root->getUnits().end(); it++) {
        (*it)->accept(&names);
    }
    // And whatever the linker declared without a source declaration: the
    // built-in members (`uid`, `prev`, ...), the synthesized `comp` field.
    std::set<ast::IScopeChild *> seen;
    collectSymtabNames(root, seen);
}

void TaskCheckRefsResolved::collectSymtabNames(
        ast::IScopeChild                *c,
        std::set<ast::IScopeChild *>    &seen) {
    if (!c || !seen.insert(c).second) {
        return;
    }
    if (ast::ISymbolScope *s = dynamic_cast<ast::ISymbolScope *>(c)) {
        for (std::unordered_map<std::string,int32_t>::const_iterator
            it=s->getSymtab().begin(); it!=s->getSymtab().end(); it++) {
            m_names.insert(it->first);
        }
    }
    if (ast::ISymbolChildrenScope *s = dynamic_cast<ast::ISymbolChildrenScope *>(c)) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin(); it!=s->getChildren().end(); it++) {
            if (dynamic_cast<ast::ISymbolChildrenScope *>(it->get())) {
                collectSymtabNames(it->get(), seen);
            }
        }
    }
}

dmgr::IDebug *TaskCheckRefsResolved::m_dbg = 0;

}
