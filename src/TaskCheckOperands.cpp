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
#include "pssp/ast/IExprCond.h"
#include "pssp/ast/IExprNull.h"
#include "pssp/ast/IExprNumber.h"
#include "pssp/ast/IExprSignedNumber.h"
#include "pssp/ast/IExprUnsignedNumber.h"
#include "pssp/ast/IExprUnary.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/IProceduralStmtIfClause.h"
#include "pssp/ast/IProceduralStmtRepeatWhile.h"
#include "pssp/ast/IProceduralStmtWhile.h"
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

static bool isZeroLiteral(ast::IExpr *e) {
    if (ast::IExprSignedNumber *n = NodeKind::cast<ast::IExprSignedNumber>(e)) {
        return n->getValue() == 0;
    } else if (ast::IExprUnsignedNumber *n = NodeKind::cast<ast::IExprUnsignedNumber>(e)) {
        return n->getValue() == 0;
    }
    return false;
}

void TaskCheckOperands::visitExprBin(ast::IExprBin *i) {
    ast::VisitorBase::visitExprBin(i);

    switch (i->getOp()) {
        case ast::ExprBinOp::BinOp_Lt:
            checkOperands("<", Opd::Numeric, "8.4 Table 10, 8.5.2", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Le:
            checkOperands("<=", Opd::Numeric, "8.4 Table 10, 8.5.2", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Gt:
            checkOperands(">", Opd::Numeric, "8.4 Table 10, 8.5.2", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Ge:
            checkOperands(">=", Opd::Numeric, "8.4 Table 10, 8.5.2", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Add:
            checkOperands("+", Opd::Numeric, "8.4 Table 10, 8.5.1", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Sub:
            checkOperands("-", Opd::Numeric, "8.4 Table 10, 8.5.1", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Mul:
            checkOperands("*", Opd::Numeric, "8.4 Table 10, 8.5.1", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Div:
            checkOperands("/", Opd::Numeric, "8.4 Table 10, 8.5.1", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Exp:
            checkOperands("**", Opd::Numeric, "8.4 Table 10, 8.5.1", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Mod:
            checkOperands("%", Opd::Integer, "8.4 Table 10, 8.5.1", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_BitAnd:
            checkOperands("&", Opd::Integer, "8.4 Table 10, 8.5.5", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_BitOr:
            checkOperands("|", Opd::Integer, "8.4 Table 10, 8.5.5", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_BitXor:
            checkOperands("^", Opd::Integer, "8.4 Table 10, 8.5.5", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Shl:
            checkOperands("<<", Opd::Integer, "8.4 Table 10, 8.5.7", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_Shr:
            checkOperands(">>", Opd::Integer, "8.4 Table 10, 8.5.7", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_LogAnd:
            checkOperands("&&", Opd::Boolean, "8.4 Table 10, 8.5.4", i->getLhs(), i->getRhs());
            return;
        case ast::ExprBinOp::BinOp_LogOr:
            checkOperands("||", Opd::Boolean, "8.4 Table 10, 8.5.4", i->getLhs(), i->getRhs());
            return;
        default:
            break;
    }

    // == and !=
    const char *op = (i->getOp() == ast::ExprBinOp::BinOp_Eq) ? "==" : "!=";
    ExprType l = m_typer.typeOf(i->getLhs());
    ExprType r = m_typer.typeOf(i->getRhs());
    if (isModelingArray(l) || isModelingArray(r)) {
        m_ctxt->addErrorMarker(locOf(i),
            "'%s' does not apply to an array of components or actions: only [], "
            "size(), foreach and 'in' do (LRM 7.9.2)", op);
        return;
    }
    // 7.7: a chandle is compared only with a chandle, and "the only literal
    // value with which it may be compared is 0". (null is left alone: 7.10
    // gives it to references, and whether a chandle is one is not settled.)
    for (int side=0; side<2; side++) {
        const ExprType &c = (side) ? r : l;
        const ExprType &o = (side) ? l : r;
        ast::IExpr *oe = (side) ? i->getLhs() : i->getRhs();
        if (c.kind == TypeKindE::Chandle && o.known() && o.kind != TypeKindE::Chandle
                && o.kind != TypeKindE::Null && o.kind != TypeKindE::Other
                && !isZeroLiteral(oe)) {
            m_ctxt->addErrorMarker(locOf(i),
                "a chandle can be compared only with a chandle or the literal 0, "
                "not %s (LRM 7.7)", o.describe().c_str());
            return;
        }
    }
}

bool TaskCheckOperands::badOperand(const ExprType &t, Opd c) {
    switch (t.kind) {
        case TypeKindE::Unknown:
        case TypeKindE::Other:
        case TypeKindE::Void:       // a void call used as a value is PSS007
            return false;
        case TypeKindE::Enum:
            // 7.5.1 permits an enum in assignment and equality ("may be
            // used"), and forbids nothing in so many words: not judged as a
            // number. It is not a Boolean, though.
            return (c == Opd::Boolean);
        case TypeKindE::Int:
            return (c == Opd::Boolean);
        case TypeKindE::Float:
            return (c != Opd::Numeric);
        case TypeKindE::Bool:
            return (c != Opd::Boolean);
        default:
            return true;
    }
}

bool TaskCheckOperands::checkOperands(
        const char      *op,
        Opd             c,
        const char      *clause,
        ast::IExpr      *a,
        ast::IExpr      *b) {
    ast::IExpr *opds[] = {a, b};
    for (ast::IExpr *e : opds) {
        if (!e) {
            continue;
        }
        ExprType t = m_typer.typeOf(e);
        if (!badOperand(t, c)) {
            continue;
        }
        const char *want = (c == Opd::Numeric) ? "numeric"
            : (c == Opd::Integer) ? "integer" : "Boolean";
        m_ctxt->addErrorMarker(locOf(e),
            "operator '%s' takes %s operands, not %s (LRM %s)",
            op, want, t.describe().c_str(), clause);
        return true;
    }
    return false;
}

void TaskCheckOperands::visitExprUnary(ast::IExprUnary *i) {
    ast::VisitorBase::visitExprUnary(i);
    switch (i->getOp()) {
        case ast::ExprUnaryOp::UnaryOp_Minus:
            checkOperands("-", Opd::Numeric, "8.4 Table 10, 8.5.1", i->getRhs());
            break;
        case ast::ExprUnaryOp::UnaryOp_BitNeg:
            checkOperands("~", Opd::Integer, "8.4 Table 10, 8.5.5", i->getRhs());
            break;
        case ast::ExprUnaryOp::UnaryOp_BitAnd:
            checkOperands("&", Opd::Integer, "8.4 Table 10, 8.5.6", i->getRhs());
            break;
        case ast::ExprUnaryOp::UnaryOp_BitOr:
            checkOperands("|", Opd::Integer, "8.4 Table 10, 8.5.6", i->getRhs());
            break;
        case ast::ExprUnaryOp::UnaryOp_BitXor:
            checkOperands("^", Opd::Integer, "8.4 Table 10, 8.5.6", i->getRhs());
            break;
        case ast::ExprUnaryOp::UnaryOp_LogNot:
            checkOperands("!", Opd::Boolean, "8.4 Table 10, 8.5.4", i->getRhs());
            break;
        default:
            break;
    }
}

// ---------------------------------------------------------------------------
// Conditions (20.7.9, 20.7.7 a, 8.5.8)
// ---------------------------------------------------------------------------

void TaskCheckOperands::checkCondition(
        const char  *what,
        const char  *clause,
        ast::IExpr  *cond) {
    ExprType t = m_typer.typeOf(cond);
    if (!t.known() || t.kind == TypeKindE::Bool || t.kind == TypeKindE::Other
            || t.kind == TypeKindE::Void) {
        return;
    }
    m_ctxt->addErrorMarker(locOf(cond),
        "the condition of %s shall be of Boolean type, not %s (LRM %s)",
        what, t.describe().c_str(), clause);
}

void TaskCheckOperands::visitExprCond(ast::IExprCond *i) {
    ast::VisitorBase::visitExprCond(i);
    checkCondition("'?:'", "8.5.8", i->getCond_e());
}

void TaskCheckOperands::visitProceduralStmtIfClause(ast::IProceduralStmtIfClause *i) {
    if (i->getLocation().lineno > 0) {
        m_stmt_loc = i->getLocation();
    }
    ast::VisitorBase::visitProceduralStmtIfClause(i);
    checkCondition("'if'", "20.7.9", i->getCond());
}

void TaskCheckOperands::visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) {
    ast::VisitorBase::visitProceduralStmtWhile(i);
    checkCondition("'while'", "20.7.7 a", i->getExpr());
}

void TaskCheckOperands::visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) {
    ast::VisitorBase::visitProceduralStmtRepeatWhile(i);
    checkCondition("'repeat ... while'", "20.7.7 a", i->getExpr());
}

// ---------------------------------------------------------------------------
// null (8.3)
// ---------------------------------------------------------------------------

void TaskCheckOperands::checkNullInit(const ExprType &target, ast::IExpr *value) {
    if (!value || !NodeKind::cast<ast::IExprNull>(value)) {
        return;
    }
    switch (target.kind) {
        case TypeKindE::Int:
        case TypeKindE::Bool:
        case TypeKindE::Float:
        case TypeKindE::String:
        case TypeKindE::Enum:
        case TypeKindE::Struct:
        case TypeKindE::Array:
        case TypeKindE::List:
        case TypeKindE::Map:
        case TypeKindE::Set:
            if (target.is_ref) {
                return;
            }
            m_ctxt->addErrorMarker(m_stmt_loc,
                "null cannot be assigned to %s: only a reference takes null "
                "(LRM 8.3)", target.describe().c_str());
            break;
        default:
            break;
    }
}

void TaskCheckOperands::visitProceduralStmtDataDeclaration(
        ast::IProceduralStmtDataDeclaration *i) {
    ast::VisitorBase::visitProceduralStmtDataDeclaration(i);
    if (i->getName() && i->getName()->getLocation().lineno > 0) {
        m_stmt_loc = i->getName()->getLocation();
    }
    checkNullInit(m_typer.typeOfDataType(i->getDatatype()), i->getInit());
}

void TaskCheckOperands::visitField(ast::IField *i) {
    ast::VisitorBase::visitField(i);
    if (i->getInit() && i->getName() && i->getName()->getLocation().lineno > 0) {
        m_stmt_loc = i->getName()->getLocation();
        checkNullInit(m_typer.typeOfDataType(i->getType()), i->getInit());
    }
}

void TaskCheckOperands::visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) {
    ast::VisitorBase::visitProceduralStmtAssignment(i);

    // Table 9: the compound assignments' operand types.
    switch (i->getOp()) {
        case ast::AssignOp::AssignOp_PlusEq:
            checkOperands("+=", Opd::Numeric, "8.3 Table 9", i->getLhs(), i->getRhs());
            break;
        case ast::AssignOp::AssignOp_MinusEq:
            checkOperands("-=", Opd::Numeric, "8.3 Table 9", i->getLhs(), i->getRhs());
            break;
        case ast::AssignOp::AssignOp_ShlEq:
            checkOperands("<<=", Opd::Integer, "8.3 Table 9", i->getLhs(), i->getRhs());
            break;
        case ast::AssignOp::AssignOp_ShrEq:
            checkOperands(">>=", Opd::Integer, "8.3 Table 9", i->getLhs(), i->getRhs());
            break;
        case ast::AssignOp::AssignOp_OrEq:
            checkOperands("|=", Opd::Integer, "8.3 Table 9", i->getLhs(), i->getRhs());
            break;
        case ast::AssignOp::AssignOp_AndEq:
            checkOperands("&=", Opd::Integer, "8.3 Table 9", i->getLhs(), i->getRhs());
            break;
        default:
            if (i->getLocation().lineno > 0) {
                m_stmt_loc = i->getLocation();
            }
            checkNullInit(m_typer.typeOf(i->getLhs()), i->getRhs());
            break;
    }

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
