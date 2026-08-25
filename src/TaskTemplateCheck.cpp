/*
 * TaskTemplateCheck.cpp
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
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/IExprRefPath.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprRefPathId.h"
#include "pssp/ast/IExprRefPathStaticFunc.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ISymbolChild.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/ITemplateAssign.h"
#include "pssp/ast/ITemplateBlock.h"
#include "pssp/ast/ITemplateExpr.h"
#include "pssp/ast/ITemplateForeach.h"
#include "pssp/ast/ITemplateIf.h"
#include "pssp/ast/ITemplateIfClause.h"
#include "pssp/ast/ITemplateRepeat.h"
#include "pssp/ast/ITemplateVarDecl.h"
#include "pssp/ast/ITemplateValueParamDecl.h"
#include "TaskCheckCallArgs.h"
#include "TaskExprTypeCat.h"
#include "TaskTemplateCheck.h"

namespace pssp {

dmgr::IDebug *TaskTemplateCheck::m_dbg = 0;

namespace {

/**
 * Walks one expression, deciding whether it references only constants.
 *
 * Overriding `visitExprRefPath` alone catches every path form: the generated
 * visitors for the concrete subclasses chain up to it before descending, so
 * subscripts and call arguments are still walked and still counted.
 */
class ConstScan : public ast::VisitorBase {
public:
    ConstScan(
        ResolveContext                                      *ctxt,
        const std::map<std::string, ast::IScopeChild *>     &locals,
        const std::set<ast::IScopeChild *>                  &nonconst) :
        m_ctxt(ctxt), m_locals(locals), m_nonconst(nonconst),
        is_const(true) { }

    virtual void visitExprRefPath(ast::IExprRefPath *i) override {
        if (isCall(i)) {
            // A call is never a constant expression here. Even a `pure`
            // function is only constant-foldable given constant arguments and
            // a body this front end does not evaluate.
            is_const = false;
        } else if (ast::IScopeChild *local = localFor(i)) {
            if (m_nonconst.find(local) != m_nonconst.end()) {
                is_const = false;
            }
        } else {
            ast::IScopeChild *c = i->getTarget()
                ? m_ctxt->resolveSymbolPathRef(i->getTarget()) : 0;
            if (!declConst(c)) {
                is_const = false;
            }
        }

        ast::VisitorBase::visitExprRefPath(i);
    }

    bool is_const;

private:
    static bool isCall(ast::IExprRefPath *i) {
        if (dynamic_cast<ast::IExprRefPathStaticFunc *>(i)) {
            return true;
        }
        ast::IExprRefPathContext *rc =
            dynamic_cast<ast::IExprRefPathContext *>(i);
        if (rc && rc->getHier_id()) {
            for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
                it=rc->getHier_id()->getElems().begin();
                it!=rc->getHier_id()->getElems().end(); it++) {
                if ((*it)->getParams()) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * The template-local declaration `i` names, or null.
     *
     * Matched **by name** rather than through the resolved symbol path. The
     * path now reaches the same declaration (P5-X2), but not the same *state*:
     * this pass walks the template in source order and needs the declaration in
     * effect at the point of the reference, so that a later declaration of the
     * same name shadows an earlier one and an assignment made after a reference
     * does not retroactively make it non-constant. A symbol path names the
     * scope's final contents and cannot express either.
     */
    ast::IScopeChild *localFor(ast::IExprRefPath *i) {
        const std::string *name = 0;

        if (ast::IExprRefPathId *ri = dynamic_cast<ast::IExprRefPathId *>(i)) {
            if (ri->getId()) {
                name = &ri->getId()->getId();
            }
        } else if (ast::IExprRefPathContext *rc =
            dynamic_cast<ast::IExprRefPathContext *>(i)) {
            // Only a bare `x`. `x.a` is a member of something a template local
            // cannot be -- a local is scalar -- so it is not one of these.
            if (!rc->getIs_super() && rc->getHier_id() &&
                rc->getHier_id()->getElems().size() == 1) {
                name = &rc->getHier_id()->getElems().at(0)->getId()->getId();
            }
        }

        if (!name) {
            return 0;
        }

        std::map<std::string, ast::IScopeChild *>::const_iterator it =
            m_locals.find(*name);
        return (it != m_locals.end())?it->second:0;
    }

    bool declConst(ast::IScopeChild *c) {
        if (!c) {
            // Unresolved. Something else has already reported that; treating
            // it as non-constant keeps this pass from *also* claiming the
            // template is constant on the strength of a reference that is not.
            return false;
        }
        if (dynamic_cast<ast::IEnumItem *>(c)) {
            return true;
        }
        if (dynamic_cast<ast::ITemplateValueParamDecl *>(c)) {
            // A type template's value parameter is fixed at specialization.
            return true;
        }
        if (ast::IField *f = dynamic_cast<ast::IField *>(c)) {
            return (f->getAttr() & ast::FieldAttr::Const) !=
                ast::FieldAttr::NoFlags;
        }
        // An ordinary procedural variable -- reached from a template inside an
        // exec body -- is a run-time value. Template locals never arrive here;
        // they are matched by name in localFor().
        return false;
    }

private:
    ResolveContext                                      *m_ctxt;
    const std::map<std::string, ast::IScopeChild *>     &m_locals;
    const std::set<ast::IScopeChild *>                  &m_nonconst;
};

}

TaskTemplateCheck::TaskTemplateCheck(ResolveContext *ctxt) :
    m_ctxt(ctxt), m_is_const(true) {
    DEBUG_INIT("pssp::TaskTemplateCheck", ctxt->getDebugMgr());
}

TaskTemplateCheck::~TaskTemplateCheck() {

}

void TaskTemplateCheck::check(ast::ITemplateString *t) {
    DEBUG_ENTER("check");
    m_is_const = true;
    m_nonconst.clear();
    m_locals.clear();

    elems(t->getElems());

    t->setIs_const(m_is_const);
    DEBUG_LEAVE("check is_const=%d", m_is_const);
}

void TaskTemplateCheck::elems(const std::vector<ast::ITemplateElemUP> &el) {
    for (std::vector<ast::ITemplateElemUP>::const_iterator
        it=el.begin(); it!=el.end(); it++) {
        elem(it->get());
    }
}

void TaskTemplateCheck::elem(ast::ITemplateElem *e) {
    // Ordered most-derived first: TemplateIfClause, TemplateForeach and
    // TemplateRepeat are all TemplateBlocks, and the block arm is the
    // catch-all.
    if (ast::ITemplateExpr *x = dynamic_cast<ast::ITemplateExpr *>(e)) {
        // The element carries the location, not the expression: ast::IExpr has
        // none, and the mustache's own span is the more useful thing to point
        // at anyway.
        expr(x->getExpr(), &x->getLocation());
        return;
    }
    if (ast::ITemplateIf *x = dynamic_cast<ast::ITemplateIf *>(e)) {
        for (std::vector<ast::ITemplateIfClauseUP>::const_iterator
            it=x->getClauses().begin(); it!=x->getClauses().end(); it++) {
            elem(it->get());
        }
        return;
    }
    if (ast::ITemplateIfClause *x = dynamic_cast<ast::ITemplateIfClause *>(e)) {
        expr(x->getCond(), 0);
        elems(x->getBody());
        return;
    }
    if (ast::ITemplateForeach *x = dynamic_cast<ast::ITemplateForeach *>(e)) {
        bool c = expr(x->getExpr(), 0);
        // The iterator and index take their values from the collection, so
        // they are constant exactly when it is.
        loopVars(x, c);
        elems(x->getBody());
        return;
    }
    if (ast::ITemplateRepeat *x = dynamic_cast<ast::ITemplateRepeat *>(e)) {
        bool c = expr(x->getExpr(), 0);
        loopVars(x, c);
        elems(x->getBody());
        return;
    }
    if (ast::ITemplateVarDecl *x = dynamic_cast<ast::ITemplateVarDecl *>(e)) {
        for (std::vector<ast::IProceduralStmtDataDeclarationUP>::const_iterator
            it=x->getDecls().begin(); it!=x->getDecls().end(); it++) {
            addLocal(it->get());
            // An uninitialized local is constant until something non-constant
            // is assigned to it -- `{% int i; %}{% i = 2; %}` is constant.
            if ((*it)->getInit() && !expr((*it)->getInit(), 0)) {
                markNonConst(it->get());
            }
        }
        return;
    }
    if (ast::ITemplateAssign *x = dynamic_cast<ast::ITemplateAssign *>(e)) {
        if (!expr(x->getRhs(), 0)) {
            // PSS112 has already reported an assignment to anything that is
            // not a template local, so an unresolved target needs no second
            // diagnostic -- but the template stops being constant either way.
            markNonConst(assignTarget(x));
            m_is_const = false;
        }
        return;
    }
    if (ast::ITemplateBlock *x = dynamic_cast<ast::ITemplateBlock *>(e)) {
        elems(x->getBody());
        return;
    }
    // TemplateText and TemplateComment contribute nothing.
}

void TaskTemplateCheck::loopVars(ast::ITemplateBlock *b, bool is_const) {
    // The iterator/index declarations are synthesized into the block's own
    // scope by the builder; they are not reachable from the directive node.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=b->getChildren().begin(); it!=b->getChildren().end(); it++) {
        addLocal(it->get());
        if (!is_const) {
            markNonConst(it->get());
        }
    }
}

void TaskTemplateCheck::addLocal(ast::IScopeChild *decl) {
    ast::IProceduralStmtDataDeclaration *d =
        dynamic_cast<ast::IProceduralStmtDataDeclaration *>(decl);
    if (d && d->getName()) {
        // A later declaration of the same name shadows an earlier one, which
        // is also the order a reference resolves in.
        m_locals[d->getName()->getId()] = decl;
    }
}

ast::IScopeChild *TaskTemplateCheck::assignTarget(ast::ITemplateAssign *a) {
    if (!a->getLhs()) {
        return 0;
    }
    // The target was resolved through the template's own symtab (PSS112), so
    // the declaration is one of the locals this pass has already recorded.
    std::map<std::string, ast::IScopeChild *>::const_iterator it =
        m_locals.find(a->getLhs()->getId());
    return (it != m_locals.end())?it->second:0;
}

void TaskTemplateCheck::markNonConst(ast::IScopeChild *decl) {
    if (decl) {
        m_nonconst.insert(decl);
    }
    m_is_const = false;
}

bool TaskTemplateCheck::expr(ast::IExpr *e, const ast::Location *loc) {
    if (!e) {
        return true;
    }

    ConstScan scan(m_ctxt, m_locals, m_nonconst);
    e->accept(&scan);

    if (!scan.is_const) {
        m_is_const = false;
    }

    if (loc) {
        // PSS113. §4.7.1.1 requires the substituted value to be of scalar
        // type; an aggregate is the one thing this classifier can say is
        // definitely not. Everything it cannot classify stays silent, which
        // is the same posture PSS007 takes.
        TypeCatE cat = TaskExprTypeCat(m_ctxt).expr(e);
        if (cat == TypeCatE::Aggregate) {
            m_ctxt->addErrorMarker(
                *loc,
                "template expression is not of scalar type");
        }
    }

    return scan.is_const;
}

bool TaskTemplateCheck::inPureComponent(ast::IScopeChild *target) {
    ast::ISymbolChild *sc = dynamic_cast<ast::ISymbolChild *>(target);

    if (!sc) {
        return false;
    }

    // One level, not the whole chain. `pure component` says every function *of
    // the component* is pure; it says nothing about a function of an action
    // declared inside it, which is a type of its own.
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(sc->getUpper());

    if (!ts) {
        return false;
    }

    ast::IComponent *comp = dynamic_cast<ast::IComponent *>(ts->getTarget());

    // Deliberately the *enclosing* type rather than the one the call was
    // written against. A function inherited from a pure component is pure
    // because of where it is declared, so a plain `component D : PC` does not
    // make D's own functions pure -- and a function added by
    // `extend component PC` is pure, because applying the extension re-homes it
    // into PC (see known-issues P2-A5b).
    return comp && comp->getIs_pure();
}

void TaskTemplateCheck::checkPure(
    ast::IScopeChild            *target,
    ast::IExprMemberPathElem    *elem) {
    if (!target || !elem || !elem->getParams()) {
        return;
    }

    std::vector<ast::IFunctionPrototype *> protos;
    TaskCheckCallArgs::collectPrototypes(target, protos);

    if (protos.empty()) {
        // Not something with a signature. Either it is not callable -- already
        // reported as PSS008 -- or it is something the resolver models
        // loosely, and guessing beats nothing only if the guess is right.
        return;
    }

    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=protos.begin(); it!=protos.end(); it++) {
        if ((*it)->getIs_pure()) {
            return;
        }
    }

    if (inPureComponent(target)) {
        return;
    }

    m_ctxt->addErrorMarker(
        elem->getId()->getLocation(),
        "call to non-pure function '%s' in a template string",
        elem->getId()->getId().c_str());
}

}
