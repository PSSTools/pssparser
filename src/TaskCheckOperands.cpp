/**
 * TaskCheckOperands.cpp
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
 */
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/IConstraintStmt.h"
#include "pssp/ast/IExecStmt.h"
#include "pssp/ast/IExprBin.h"
#include "pssp/ast/IExprCast.h"
#include "pssp/ast/IExprHierarchicalId.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IExprIn.h"
#include "pssp/ast/IExprOpenRangeList.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprRefPathStaticRooted.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IMethodParameterList.h"
#include "pssp/ast/IProceduralStmtAssignment.h"
#include "pssp/ast/IStruct.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/impl/NodeKind.h"
#include "TaskCheckOperands.h"

namespace pssp {

namespace {

/** The first identifier under an expression that has a source position. */
class FirstLocated : public virtual ast::VisitorBase {
public:
    FirstLocated() : m_found(false) { }

    bool find(ast::IExpr *n, ast::Location &loc) {
        m_found = false;
        n->accept(m_this);
        if (m_found) {
            loc = m_loc;
        }
        return m_found;
    }

    virtual void visitExprId(ast::IExprId *i) override {
        if (!m_found && i->getLocation().lineno > 0) {
            m_found = true;
            m_loc = i->getLocation();
        }
    }

private:
    bool            m_found;
    ast::Location   m_loc;
};

}

dmgr::IDebug *TaskCheckOperands::m_dbg = 0;

TaskCheckOperands::TaskCheckOperands(ResolveContext *ctxt) :
        m_ctxt(ctxt), m_typer(ctxt) {
    DEBUG_INIT("pssp::TaskCheckOperands", ctxt->getDebugMgr());
}

TaskCheckOperands::~TaskCheckOperands() {

}

void TaskCheckOperands::check(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("check");
    for (uint32_t i=0; i<root->getUnits().size(); i++) {
        ast::IGlobalScope *unit = root->getUnits().at(i).get();
        if (unit->getFileid() >= 1) {
            unit->accept(m_this);
        }
    }
    DEBUG_LEAVE("check");
}

ast::Location TaskCheckOperands::locOf(ast::IExpr *e) {
    ast::Location loc = m_stmt_loc;
    if (e) {
        FirstLocated().find(e, loc);
    }
    return loc;
}

void TaskCheckOperands::visitExecStmt(ast::IExecStmt *i) {
    if (i->getLocation().lineno > 0) {
        m_stmt_loc = i->getLocation();
    }
    ast::VisitorBase::visitExecStmt(i);
}

void TaskCheckOperands::visitConstraintStmt(ast::IConstraintStmt *i) {
    if (i->getLocation().lineno > 0) {
        m_stmt_loc = i->getLocation();
    }
    ast::VisitorBase::visitConstraintStmt(i);
}

// ---------------------------------------------------------------------------
// Casts (7.12, 7.12.1)
// ---------------------------------------------------------------------------

void TaskCheckOperands::visitExprCast(ast::IExprCast *i) {
    ast::VisitorBase::visitExprCast(i);

    ExprType to = m_typer.typeOfDataType(i->getCasting_type());
    bool bad_to = !to.is_ref && (to.kind == TypeKindE::Struct || to.isCollection()
        || to.kind == TypeKindE::String || to.kind == TypeKindE::Chandle);
    if (bad_to) {
        // 7.12.1: "A type_identifier specified as a casting_type shall refer
        // to a numeric, Boolean, enumeration, or reference type."
        m_ctxt->addErrorMarker(locOf(i),
            "a cast to %s: a casting type shall be a numeric, Boolean, "
            "enumeration or reference type (LRM 7.12.1)",
            to.describe().c_str());
        return;
    }

    ExprType from = m_typer.typeOf(i->getExpr());
    bool bad_from = !from.is_ref && (from.kind == TypeKindE::Struct
        || from.isCollection() || from.kind == TypeKindE::String
        || from.kind == TypeKindE::Chandle);
    if (bad_from) {
        // 7.12 lists what may be cast; anything else may not be (7.12.1 a:
        // "can only be cast").
        m_ctxt->addErrorMarker(locOf(i->getExpr()),
            "a cast from %s: only a numeric, Boolean or enumeration value, or "
            "a reference, can be cast (LRM 7.12)",
            from.describe().c_str());
    }
}

// ---------------------------------------------------------------------------
// in (8.5.9.1)
// ---------------------------------------------------------------------------

void TaskCheckOperands::visitExprIn(ast::IExprIn *i) {
    ast::VisitorBase::visitExprIn(i);

    if (i->getCollection() || !i->getRhs() || !i->getRhs()->getValues().size()) {
        return;
    }
    ExprType lhs = m_typer.typeOf(i->getLhs());
    if (lhs.kind == TypeKindE::Aggregate) {
        m_ctxt->addErrorMarker(locOf(i),
            "the left side of 'in' shall not be an aggregate literal "
            "(LRM 8.5.9.1)");
    } else if (lhs.kind == TypeKindE::Struct || lhs.isCollection()
            || lhs.kind == TypeKindE::Component || lhs.kind == TypeKindE::Action) {
        m_ctxt->addErrorMarker(locOf(i->getLhs()),
            "the left side of 'in' is %s, not a scalar, so the right side shall be "
            "a collection, not a range list (LRM 8.5.9.1)",
            lhs.describe().c_str());
    }
}

// ---------------------------------------------------------------------------
// Arrays of modeling elements (7.9.2)
// ---------------------------------------------------------------------------

bool TaskCheckOperands::isModelingArray(const ExprType &t) {
    if (t.kind != TypeKindE::Array) {
        return false;
    }
    ExprType e = m_typer.elemType(t);
    return (e.kind == TypeKindE::Component || e.kind == TypeKindE::Action);
}

void TaskCheckOperands::visitExprBin(ast::IExprBin *i) {
    ast::VisitorBase::visitExprBin(i);

    if (i->getOp() != ast::ExprBinOp::BinOp_Eq && i->getOp() != ast::ExprBinOp::BinOp_Ne) {
        return;
    }
    if (isModelingArray(m_typer.typeOf(i->getLhs()))
            || isModelingArray(m_typer.typeOf(i->getRhs()))) {
        m_ctxt->addErrorMarker(locOf(i),
            "'%s' does not apply to an array of components or actions: only [], "
            "size(), foreach and 'in' do (LRM 7.9.2)",
            (i->getOp() == ast::ExprBinOp::BinOp_Eq) ? "==" : "!=");
    }
}

void TaskCheckOperands::visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) {
    ast::VisitorBase::visitProceduralStmtAssignment(i);

    if (isModelingArray(m_typer.typeOf(i->getLhs()))) {
        m_ctxt->addErrorMarker(locOf(i->getLhs()),
            "an array of components or actions cannot be assigned: only [], "
            "size(), foreach and 'in' apply to one (LRM 7.9.2)");
    }
}

// ---------------------------------------------------------------------------
// Calls: an array argument's size (8.3, 20.3.2)
// ---------------------------------------------------------------------------

void TaskCheckOperands::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    if (i->getHier_id() && i->getTarget()) {
        checkCalls(i->getHier_id()->getElems(),
            m_ctxt->resolveSymbolPathRef(i->getTarget()));
    }
    ast::VisitorBase::visitExprRefPathContext(i);
}

void TaskCheckOperands::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    if (i->getLeaf()) {
        checkCalls(i->getLeaf()->getElems(), 0);
    }
    ast::VisitorBase::visitExprRefPathStaticRooted(i);
}

void TaskCheckOperands::checkCalls(
        const std::vector<ast::IExprMemberPathElemUP>   &elems,
        ast::IScopeChild                                *first_decl) {
    for (uint32_t k=0; k<elems.size(); k++) {
        ast::IExprMemberPathElem *elem = elems.at(k).get();
        if (!elem->getParams()) {
            continue;
        }
        ast::IScopeChild *decl = elem->getId()->getDecl();
        if (!decl && k == 0) {
            decl = first_decl;
        }
        if (ast::ISymbolFunctionScope *fn = NodeKind::cast<ast::ISymbolFunctionScope>(decl)) {
            checkArraySizes(elem, fn);
        }
    }
}

void TaskCheckOperands::checkArraySizes(
        ast::IExprMemberPathElem    *elem,
        ast::ISymbolFunctionScope   *fn) {
    if (!fn->getPrototypes().size()) {
        return;
    }
    ast::IFunctionPrototype *proto = fn->getPrototypes().front();
    const std::vector<ast::IExprUP> &args = elem->getParams()->getParameters();
    const std::vector<ast::IFunctionParamDeclUP> &params = proto->getParameters();
    for (uint32_t ii=0; ii<args.size() && ii<params.size(); ii++) {
        ast::IFunctionParamDecl *p = params.at(ii).get();
        if (p->getIs_varargs()
                || p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType) {
            continue;
        }
        ExprType formal = m_typer.typeOfDataType(p->getType());
        if (formal.kind != TypeKindE::Array || formal.size < 0) {
            continue;
        }
        ExprType actual = m_typer.typeOf(args.at(ii).get());
        if (actual.kind != TypeKindE::Array || actual.size < 0
                || actual.size == formal.size) {
            continue;
        }
        m_ctxt->addErrorMarker(elem->getId()->getLocation(),
            "argument %d of '%s' is an array of %lld elements, but parameter '%s' "
            "is an array of %lld (LRM 8.3)",
            ii+1,
            elem->getId()->getId().c_str(),
            (long long)actual.size,
            p->getName() ? p->getName()->getId().c_str() : "?",
            (long long)formal.size);
    }
}

// ---------------------------------------------------------------------------
// Function signatures (20.2.2)
// ---------------------------------------------------------------------------

const char *TaskCheckOperands::needsRef(const ExprType &t) {
    if (t.is_ref) {
        return 0;
    }
    switch (t.kind) {
        case TypeKindE::Component: return "component";
        case TypeKindE::Action: return "action";
        case TypeKindE::Struct: {
            ast::ISymbolTypeScope *sts = NodeKind::cast<ast::ISymbolTypeScope>(t.scope);
            ast::IStruct *s = (sts) ? NodeKind::cast<ast::IStruct>(sts->getTarget()) : 0;
            if (!s) {
                return 0;
            }
            switch (s->getKind()) {
                case ast::StructKind::Buffer:
                case ast::StructKind::Stream:
                case ast::StructKind::State: return "flow object";
                case ast::StructKind::Resource: return "resource object";
                default: return 0;
            }
        }
        default:
            return 0;
    }
}

void TaskCheckOperands::visitFunctionPrototype(ast::IFunctionPrototype *i) {
    ast::VisitorBase::visitFunctionPrototype(i);

    if (i->getRtype()) {
        ExprType rt = m_typer.typeOfDataType(i->getRtype());
        if (const char *what = needsRef(rt)) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "function '%s' returns %s type '%s' without 'ref': a function shall "
                "not (LRM 20.2.2)",
                i->getName()->getId().c_str(), what, rt.scope->getName().c_str());
        }
    }
    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getParameters().begin(); it!=i->getParameters().end(); it++) {
        ast::IFunctionParamDecl *p = it->get();
        if (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType
                || !p->getType() || !p->getName()) {
            continue;
        }
        ExprType pt = m_typer.typeOfDataType(p->getType());
        if (const char *what = needsRef(pt)) {
            m_ctxt->addErrorMarker(p->getName()->getLocation(),
                "parameter '%s' of '%s' has %s type '%s' without 'ref': a function "
                "shall not (LRM 20.2.2)",
                p->getName()->getId().c_str(), i->getName()->getId().c_str(),
                what, pt.scope->getName().c_str());
        }
    }
}

}
