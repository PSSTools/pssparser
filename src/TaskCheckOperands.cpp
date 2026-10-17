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
#include <map>
#include "pssp/IValInt.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "pssp/ast/IDataTypeInt.h"
#include "pssp/ast/IEnumDecl.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/IExportFunction.h"
#include "pssp/ast/IExprRefName.h"
#include "pssp/ast/IFunctionImportProto.h"
#include "pssp/ast/IFunctionImportType.h"
#include "pssp/ast/ITypeIdentifier.h"
#include "pssp/ast/ITypeIdentifierElem.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/ICompileCond.h"
#include "pssp/ast/IExtendType.h"
#include "pssp/ast/IProceduralStmtRandomize.h"
#include "pssp/ast/ITemplateGenericTypeParamDecl.h"
#include "pssp/ast/ITemplateParamDeclList.h"
#include "pssp/ast/ITemplateValueParamDecl.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IActivityDecl.h"
#include "pssp/ast/IConstraintBlock.h"
#include "pssp/ast/IDataTypeRef.h"
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

    if (i->getCollection()) {
        ExprType ct = m_typer.typeOf(i->getCollection());
        if (ct.kind == TypeKindE::Map) {
            // 7.9.4 (and 8.5.9.1): "The set membership operator (in) cannot
            // be applied directly to a map".
            m_ctxt->addErrorMarker(locOf(i->getCollection()),
                "'in' cannot be applied directly to a map: use its keys() or "
                "values() (LRM 7.9.4)");
            return;
        }
    }

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

    // 8.5.1: "Division or modulus by zero shall be considered illegal";
    // 8.5.7: "The right operand shall be a non-negative number". Only a
    // constant right operand is judged here (ruling R14 leaves the run-time
    // forms undefined).
    {
        ast::ExprBinOp op = i->getOp();
        bool divmod = (op == ast::ExprBinOp::BinOp_Div || op == ast::ExprBinOp::BinOp_Mod);
        bool shift = (op == ast::ExprBinOp::BinOp_Shl || op == ast::ExprBinOp::BinOp_Shr);
        if ((divmod || shift) && isConstExpr(i->getRhs())) {
            std::unique_ptr<IVal> v(TaskEvalExpr(
                m_ctxt->getFactory(), m_ctxt->root()).eval(i->getRhs()));
            IValInt *vi = dynamic_cast<IValInt *>(v.get());
            if (vi && divmod && vi->getValU() == 0) {
                m_ctxt->addErrorMarker(locOf(i),
                    "%s by a constant zero is illegal (LRM 8.5.1)",
                    (op == ast::ExprBinOp::BinOp_Div) ? "division" : "modulus");
                return;
            }
            if (vi && shift && vi->isSigned() && vi->getValS() < 0) {
                m_ctxt->addErrorMarker(locOf(i),
                    "a shift by the constant %lld: the right operand shall be "
                    "non-negative (LRM 8.5.7)", (long long)vi->getValS());
                return;
            }
        }
    }

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
    if (i->getName() && i->getName()->getLocation().lineno > 0) {
        m_stmt_loc = i->getName()->getLocation();
    }
    ast::VisitorBase::visitProceduralStmtDataDeclaration(i);
    checkItemlessEnum(i->getName(), i->getDatatype());
    if (i->getName() && i->getName()->getLocation().lineno > 0) {
        m_stmt_loc = i->getName()->getLocation();
    }
    checkNullInit(m_typer.typeOfDataType(i->getDatatype()), i->getInit());
}

void TaskCheckOperands::visitField(ast::IField *i) {
    if (i->getName() && i->getName()->getLocation().lineno > 0) {
        m_stmt_loc = i->getName()->getLocation();
    }
    ast::VisitorBase::visitField(i);
    checkItemlessEnum(i->getName(), i->getType());
    checkFieldType(i);
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
        checkAccess(i->getHier_id()->getElems());
        checkCollectionUse(i->getHier_id()->getElems(),
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

    // 20.2.5: generic and varargs parameters "are used for the declaration
    // of functions whose definition is built into implementations"; ruling
    // R23 reserves them for the core library. This walk sees only user
    // files, so any one here is a user-written function's.
    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getParameters().begin(); it!=i->getParameters().end(); it++) {
        ast::IFunctionParamDecl *p = it->get();
        bool varargs = p->getIs_varargs();
        bool generic = (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType);
        bool ref_kind = (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType
                && p->getKind() != ast::FunctionParamDeclKind::ParamKind_Type
                && p->getKind() != ast::FunctionParamDeclKind::ParamKind_Struct)
            || (p->getKind() == ast::FunctionParamDeclKind::ParamKind_DataType
                && p->getType() && m_typer.typeOfDataType(p->getType()).is_ref);
        if (p->getIs_const() && ref_kind && p->getName() && i->getName()) {
            // 20.2.3 b: "It shall not be allowed to add the const qualifier
            // on reference types or collections thereof."
            m_ctxt->addErrorMarker(p->getName()->getLocation(),
                "parameter '%s' of '%s' is a reference, which cannot be const "
                "(LRM 20.2.3 b)",
                p->getName()->getId().c_str(), i->getName()->getId().c_str());
        }
        if ((varargs || generic) && p->getName() && i->getName()) {
            m_ctxt->addErrorMarker(p->getName()->getLocation(),
                "parameter '%s' of '%s' is %s, which only a core-library function may "
                "have (LRM 20.2.5, ruling R23)",
                p->getName()->getId().c_str(), i->getName()->getId().c_str(),
                (varargs) ? "varargs" : "generic");
        }
    }

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


// ---------------------------------------------------------------------------
// Enum values (7.5.1)
// ---------------------------------------------------------------------------

void TaskCheckOperands::checkItemlessEnum(ast::IExprId *name, ast::IDataType *dt) {
    if (!name || !dt || name->getLocation().lineno <= 0) {
        return;
    }
    ExprType t = m_typer.typeOfDataType(dt);
    ast::ISymbolEnumScope *es = NodeKind::cast<ast::ISymbolEnumScope>(t.scope);
    if (t.kind != TypeKindE::Enum || !es || es->getChildren().size()) {
        return;
    }
    // 7.5.1 j: "It shall be illegal to declare an enumeration variable whose
    // type contains no enum_items across its initial definition and
    // extensions." Extensions are merged into the scope by now.
    m_ctxt->addErrorMarker(name->getLocation(),
        "'%s' is a variable of enum '%s', which has no items in its declaration or "
        "any extension (LRM 7.5.1 j)",
        name->getId().c_str(), es->getName().c_str());
}

void TaskCheckOperands::visitEnumDecl(ast::IEnumDecl *i) {
    ast::VisitorBase::visitEnumDecl(i);

    const char *ename = (i->getName()) ? i->getName()->getId().c_str() : "?";

    // The base type: an integer type with no domain (7.5.1).
    bool bounded = false;
    int64_t lo = 0, hi = 0;
    std::string base_name;
    if (i->getBase_type()) {
        ExprType bt = m_typer.typeOfDataType(i->getBase_type());
        ast::IDataTypeInt *it = NodeKind::cast<ast::IDataTypeInt>(bt.dt);
        if (it && it->getIn_range()) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "the base type of enum '%s' shall not have a value domain (LRM 7.5.1)",
                ename);
        }
        if (it) {
            int64_t width = (it->getIs_signed()) ? 32 : 1;
            bool known = true;
            if (it->getWidth()) {
                std::unique_ptr<IVal> w(TaskEvalExpr(
                    m_ctxt->getFactory(), m_ctxt->root()).eval(it->getWidth()));
                IValInt *wi = dynamic_cast<IValInt *>(w.get());
                known = (wi != 0);
                width = (wi) ? wi->getValS() : 0;
            }
            if (known && width > 0 && width < 63) {
                bounded = true;
                if (it->getIs_signed()) {
                    lo = -(int64_t(1) << (width-1));
                    hi = (int64_t(1) << (width-1)) - 1;
                } else {
                    lo = 0;
                    hi = (int64_t(1) << width) - 1;
                }
                base_name = std::string((it->getIs_signed()) ? "int" : "bit")
                    + "[" + std::to_string(width) + "]";
            }
        }
    }

    // The items, the declaration's then each extension's, in merge order:
    // the enum scope holds them all.
    if (!i->getItems().size() || !i->getItems().front()->getUpper()) {
        return;
    }
    ast::ISymbolEnumScope *es = i->getItems().front()->getUpper();
    std::map<int64_t, ast::IEnumItem *> seen;
    bool have_prev = false;
    int64_t prev = 0;
    for (std::vector<ast::IScopeChildUP>::const_iterator
            it=es->getChildren().begin(); it!=es->getChildren().end(); it++) {
        ast::IEnumItem *item = NodeKind::cast<ast::IEnumItem>(it->get());
        if (!item) {
            continue;
        }
        bool user = (item->getName()->getLocation().fileid >= 1);
        int64_t v;
        if (item->getValue()) {
            std::unique_ptr<IVal> val(TaskEvalExpr(
                m_ctxt->getFactory(), m_ctxt->root()).eval(item->getValue()));
            IValInt *vi = dynamic_cast<IValInt *>(val.get());
            if (!vi) {
                // Not foldable here (an item defined by another, say): the
                // values from here on are not known.
                return;
            }
            v = vi->getValS();
            if (bounded && user && (v < lo || v > hi)) {
                m_ctxt->addErrorMarker(item->getName()->getLocation(),
                    "enum item '%s' has the value %lld, which is not a value of the "
                    "base type %s (LRM 7.5.1 c)",
                    item->getName()->getId().c_str(), (long long)v, base_name.c_str());
            }
        } else {
            if (have_prev && bounded && user && prev == hi) {
                m_ctxt->addErrorMarker(item->getName()->getLocation(),
                    "enum item '%s' has no value of its own, and the item before it "
                    "has the greatest value of the base type %s (LRM 7.5.1 c)",
                    item->getName()->getId().c_str(), base_name.c_str());
            }
            v = (have_prev) ? prev+1 : 0;
        }
        std::map<int64_t, ast::IEnumItem *>::const_iterator d = seen.find(v);
        if (d != seen.end() && user) {
            m_ctxt->addErrorMarker(item->getName()->getLocation(),
                "enum item '%s' has the value %lld, as '%s' does: each enum item "
                "shall have a distinct value (LRM 7.5.1 e)",
                item->getName()->getId().c_str(), (long long)v,
                d->second->getName()->getId().c_str());
        } else if (d == seen.end()) {
            seen.insert({v, item});
        }
        prev = v;
        have_prev = true;
    }
}


// ---------------------------------------------------------------------------
// Import and export types (20.4.1 c, 20.4.2.1)
// ---------------------------------------------------------------------------

int64_t TaskCheckOperands::intWidth(const ExprType &t) {
    ast::IDataTypeInt *it = NodeKind::cast<ast::IDataTypeInt>(t.dt);
    if (t.kind != TypeKindE::Int || !it) {
        return -1;
    }
    if (!it->getWidth()) {
        return (it->getIs_signed()) ? 32 : 1;
    }
    std::unique_ptr<IVal> w(TaskEvalExpr(
        m_ctxt->getFactory(), m_ctxt->root()).eval(it->getWidth()));
    IValInt *wi = dynamic_cast<IValInt *>(w.get());
    return (wi) ? wi->getValS() : -1;
}

std::string TaskCheckOperands::typeName(const ExprType &t) {
    int64_t w = intWidth(t);
    if (w > 0) {
        return t.describe() + "[" + std::to_string(w) + "]";
    }
    if (t.isCollection()) {
        ExprType e = m_typer.elemType(t);
        if (e.known()) {
            return t.describe() + " of " + typeName(e);
        }
    }
    return t.describe();
}

bool TaskCheckOperands::importTypeOk(const ExprType &t, int32_t depth) {
    switch (t.kind) {
        case TypeKindE::Unknown:
        case TypeKindE::Other:
        case TypeKindE::Void:
            return true;
        case TypeKindE::Int:
            return intWidth(t) <= 64;
        case TypeKindE::Bool:
        case TypeKindE::Enum:
        case TypeKindE::String:
        case TypeKindE::Chandle:
        case TypeKindE::Struct:
            return !t.is_ref;
        case TypeKindE::Array: {
            // 7) an array of 1-6, a sub-array included
            ExprType e = m_typer.elemType(t);
            return (depth > 8) || (e.kind != TypeKindE::List && importTypeOk(e, depth+1)
                && e.kind != TypeKindE::Map && e.kind != TypeKindE::Set);
        }
        case TypeKindE::List: {
            // 8) a list of 1-6, but not of strings or chandles
            ExprType e = m_typer.elemType(t);
            if (!e.known()) {
                return true;
            }
            return (e.kind == TypeKindE::Int || e.kind == TypeKindE::Bool
                || e.kind == TypeKindE::Enum || e.kind == TypeKindE::Struct)
                && importTypeOk(e, depth+1);
        }
        default:
            return false;
    }
}

bool TaskCheckOperands::exportTypeOk(const ExprType &t, int32_t depth) {
    switch (t.kind) {
        case TypeKindE::Unknown:
        case TypeKindE::Other:
        case TypeKindE::Void:
            return true;
        case TypeKindE::Int:
            return intWidth(t) <= 64;
        case TypeKindE::Bool:
        case TypeKindE::Enum:
        case TypeKindE::Float:
        case TypeKindE::String:
        case TypeKindE::Chandle:
        case TypeKindE::Struct:
            return !t.is_ref;
        default:
            return false;
    }
}

void TaskCheckOperands::checkImport(
        ast::IFunctionPrototype     *proto,
        const ast::Location         &at,
        bool                        use_at) {
    if (!proto || !proto->getName()) {
        return;
    }
    const char *fname = proto->getName()->getId().c_str();
    if (proto->getRtype()) {
        ExprType rt = m_typer.typeOfDataType(proto->getRtype());
        if (!importTypeOk(rt)) {
            m_ctxt->addErrorMarker((use_at) ? at : proto->getName()->getLocation(),
                "imported function '%s' returns %s, which an import cannot "
                "(LRM 20.4.1 c)", fname, typeName(rt).c_str());
            return;
        }
    }
    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=proto->getParameters().begin(); it!=proto->getParameters().end(); it++) {
        ast::IFunctionParamDecl *p = it->get();
        if (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType
                || p->getIs_varargs() || !p->getName()) {
            continue;
        }
        ExprType pt = m_typer.typeOfDataType(p->getType());
        if (!importTypeOk(pt)) {
            m_ctxt->addErrorMarker((use_at) ? at : p->getName()->getLocation(),
                "parameter '%s' of imported function '%s' has type %s, which an "
                "import cannot take (LRM 20.4.1 c)",
                p->getName()->getId().c_str(), fname, typeName(pt).c_str());
            return;
        }
    }
}

void TaskCheckOperands::visitFunctionImportProto(ast::IFunctionImportProto *i) {
    ast::VisitorBase::visitFunctionImportProto(i);
    checkImport(i->getProto(), ast::Location(), false);
}

void TaskCheckOperands::visitFunctionImportType(ast::IFunctionImportType *i) {
    ast::VisitorBase::visitFunctionImportType(i);
    ast::ITypeIdentifier *tid = i->getType();
    if (!tid || !tid->getTarget() || !tid->getElems().size()) {
        return;
    }
    ast::ISymbolFunctionScope *fn = NodeKind::cast<ast::ISymbolFunctionScope>(
        m_ctxt->resolveSymbolPathRef(tid->getTarget()));
    if (!fn || !fn->getPrototypes().size()) {
        return;
    }
    checkImport(fn->getPrototypes().front(),
        tid->getElems().back()->getId()->getLocation(), true);
}

void TaskCheckOperands::visitExportFunction(ast::IExportFunction *i) {
    ast::VisitorBase::visitExportFunction(i);
    if (!i->getName() || !i->getName()->getTarget()) {
        return;
    }
    ast::ISymbolFunctionScope *fn = NodeKind::cast<ast::ISymbolFunctionScope>(
        m_ctxt->resolveSymbolPathRef(i->getName()->getTarget()));
    if (!fn || !fn->getPrototypes().size()) {
        return;
    }
    ast::IFunctionPrototype *proto = fn->getPrototypes().front();
    // 20.4.2 exports a static function -- a package function or a
    // component's `static` one. Exporting an instance function is an
    // extension (LINT301), whose signature 20.4.2.1 does not govern.
    if (NodeKind::cast<ast::ISymbolTypeScope>(fn->getUpper()) && !proto->getIs_static()) {
        return;
    }
    const ast::Location &at = i->getName()->getId()->getLocation();
    const char *fname = proto->getName()->getId().c_str();
    if (proto->getRtype()) {
        ExprType rt = m_typer.typeOfDataType(proto->getRtype());
        if (!exportTypeOk(rt)) {
            m_ctxt->addErrorMarker(at,
                "exported function '%s' returns %s, which an export cannot "
                "(LRM 20.4.2.1)", fname, typeName(rt).c_str());
            return;
        }
    }
    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=proto->getParameters().begin(); it!=proto->getParameters().end(); it++) {
        ast::IFunctionParamDecl *p = it->get();
        if (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType
                || p->getIs_varargs() || !p->getName()) {
            continue;
        }
        ExprType pt = m_typer.typeOfDataType(p->getType());
        if (!exportTypeOk(pt)) {
            m_ctxt->addErrorMarker(at,
                "parameter '%s' of exported function '%s' has type %s, which an "
                "export cannot take (LRM 20.4.2.1)",
                p->getName()->getId().c_str(), fname, typeName(pt).c_str());
            return;
        }
        if (pt.kind == TypeKindE::Struct && !p->getIs_const()) {
            m_ctxt->addErrorMarker(at,
                "parameter '%s' of exported function '%s' is a struct, so it shall "
                "be declared const (LRM 20.4.2.1 g)",
                p->getName()->getId().c_str(), fname);
            return;
        }
    }
}


// ---------------------------------------------------------------------------
// Group 6: widths, constants, channels, registers, rand, access, compile if
// ---------------------------------------------------------------------------

void TaskCheckOperands::visitDataTypeInt(ast::IDataTypeInt *i) {
    ast::VisitorBase::visitDataTypeInt(i);
    if (!i->getWidth() || !isConstExpr(i->getWidth())) {
        return;
    }
    std::unique_ptr<IVal> w(TaskEvalExpr(
        m_ctxt->getFactory(), m_ctxt->root()).eval(i->getWidth()));
    IValInt *wi = dynamic_cast<IValInt *>(w.get());
    if (wi && wi->getValS() <= 0) {
        // 7.2.1 c says only "should"; ruling R19 makes it an error.
        ast::Location loc = locOf(i->getWidth());
        if (loc.lineno <= 0 && i->getLocation().lineno > 0) {
            loc = i->getLocation();
        }
        m_ctxt->addErrorMarker(loc,
            "integer width %lld is not positive (LRM 7.2.1 c, ruling R19)",
            (long long)wi->getValS());
    }
}

bool TaskCheckOperands::isConstExpr(ast::IExpr *e, int32_t depth) {
    if (!e || depth > 16) {
        return false;
    }
    NodeKind nk(e);
    if (nk.is<ast::IExprNumber>() || nk.is<ast::IExprBool>()) {
        return true;
    } else if (ast::IExprUnary *u = nk.as<ast::IExprUnary>()) {
        return isConstExpr(u->getRhs(), depth+1);
    } else if (ast::IExprBin *b = nk.as<ast::IExprBin>()) {
        return isConstExpr(b->getLhs(), depth+1) && isConstExpr(b->getRhs(), depth+1);
    } else if (ast::IExprCond *c = nk.as<ast::IExprCond>()) {
        return isConstExpr(c->getCond_e(), depth+1) && isConstExpr(c->getTrue_e(), depth+1)
            && isConstExpr(c->getFalse_e(), depth+1);
    }
    ast::IScopeChild *decl = 0;
    if (ast::IExprRefPathStatic *r = nk.as<ast::IExprRefPathStatic>()) {
        decl = (r->getTarget() && !r->getSlice())
            ? m_ctxt->resolveSymbolPathRef(r->getTarget()) : 0;
    } else if (ast::IExprRefPathContext *r = nk.as<ast::IExprRefPathContext>()) {
        if (r->getTarget() && !r->getSlice() && r->getHier_id()
                && r->getHier_id()->getElems().size() == 1
                && !r->getHier_id()->getElems().at(0)->getParams()
                && !r->getHier_id()->getElems().at(0)->getSubscript().size()) {
            decl = m_ctxt->resolveSymbolPathRef(r->getTarget());
        }
    }
    if (NodeKind::cast<ast::IEnumItem>(decl)) {
        return true;
    }
    if (ast::IField *f = NodeKind::cast<ast::IField>(decl)) {
        return (f->getAttr() & ast::FieldAttr::Const) != ast::FieldAttr::NoFlags;
    }
    if (NodeKind::cast<ast::ITemplateValueParamDecl>(decl)) {
        // Bound only in a specialization; the generic's default says nothing.
        return false;
    }
    return false;
}

ast::ITypeScope *TaskCheckOperands::typeScopeOf(const ExprType &t) {
    ast::ISymbolTypeScope *sts = NodeKind::cast<ast::ISymbolTypeScope>(t.scope);
    return (sts) ? NodeKind::cast<ast::ITypeScope>(sts->getTarget()) : 0;
}

bool TaskCheckOperands::derivesFromCore(ast::ITypeScope *ts, const char *name) {
    for (int32_t depth=0; ts && depth<64; depth++) {
        if (ts->getName() && ts->getName()->getId() == name
                && ts->getLocation().fileid < 1) {
            return true;
        }
        if (!ts->getSuper_t() || !ts->getSuper_t()->getTarget() || ts->getSuper_cyclic()) {
            return false;
        }
        ast::ISymbolTypeScope *b = NodeKind::cast<ast::ISymbolTypeScope>(
            m_ctxt->resolveSymbolPathRef(ts->getSuper_t()->getTarget()));
        ts = (b) ? NodeKind::cast<ast::ITypeScope>(b->getTarget()) : 0;
    }
    return false;
}

void TaskCheckOperands::checkFieldType(ast::IField *i) {
    if (!i->getName() || i->getName()->getLocation().fileid < 1) {
        return;
    }
    const char *fname = i->getName()->getId().c_str();
    ExprType t = m_typer.typeOfDataType(i->getType());
    ExprType elem = t;
    while (elem.kind == TypeKindE::Array) {
        ExprType e = m_typer.elemType(elem);
        if (!e.known()) {
            break;
        }
        elem = e;
    }

    // PSS142 -- 7.1: "rand ... may be applied only to randomizable types".
    if ((i->getAttr() & ast::FieldAttr::Rand) != ast::FieldAttr::NoFlags) {
        if (t.kind == TypeKindE::Map || t.kind == TypeKindE::Set) {
            // 7.1: "the map and set collection types are not randomizable".
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "rand field '%s' is a %s, which is not randomizable (LRM 7.1)",
                fname, t.describe().c_str());
            return;
        }
        ExprType r = (t.kind == TypeKindE::List) ? m_typer.elemType(t) : elem;
        if (r.kind == TypeKindE::Chandle || r.kind == TypeKindE::Float
                || r.kind == TypeKindE::String) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "rand field '%s' is of type %s, which is not randomizable (LRM 7.1)",
                fname, r.describe().c_str());
            return;
        }
    }

    // PSS149 -- 7.10 a: "Reference types shall not be used to declare
    // fields in the scope of flow/resource objects or structs."
    if (t.is_ref || elem.is_ref) {
        ast::IStruct *st = NodeKind::cast<ast::IStruct>(i->getParent());
        if (st) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "'%s' is a reference field, which a struct or object cannot declare "
                "(LRM 7.10 a)", fname);
            return;
        }
    }
    // PSS149 -- 9.1.5.3 a: "The instance qualifier may only be applied to
    // component fields whose type is a component reference or a list or array
    // of component references."
    if ((i->getAttr() & ast::FieldAttr::Instance) != ast::FieldAttr::NoFlags) {
        ExprType e2 = (t.isCollection()) ? m_typer.elemType(t) : t;
        if (t.known() && !(e2.is_ref || !e2.known())) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "'%s' is declared instance, but its type is not a component reference "
                "(LRM 9.1.5.3 a)", fname);
            return;
        }
    }

    ast::ITypeScope *ts = typeScopeOf(elem);
    if (!ts || elem.kind != TypeKindE::Component) {
        return;
    }

    // PSS141 -- 21.14.1: a register "can be instantiated only in a register
    // group".
    if (derivesFromCore(ts, "reg_base_c")) {
        ast::ITypeScope *owner = NodeKind::cast<ast::ITypeScope>(i->getParent());
        ast::IExtendType *ext = NodeKind::cast<ast::IExtendType>(i->getParent());
        if (ext && ext->getTarget() && ext->getTarget()->getTarget()) {
            ast::ISymbolTypeScope *es = NodeKind::cast<ast::ISymbolTypeScope>(
                m_ctxt->resolveSymbolPathRef(ext->getTarget()->getTarget()));
            owner = (es) ? NodeKind::cast<ast::ITypeScope>(es->getTarget()) : 0;
        }
        if (owner && !derivesFromCore(owner, "reg_group_c")) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "register '%s' is in '%s', which is not a register group (LRM 21.14.1)",
                fname, (owner->getName()) ? owner->getName()->getId().c_str() : "?");
        }
        return;
    }

    // PSS140 -- 21.9.1 a/b: what a channel holds, and its depth.
    if (ts->getName() && ts->getName()->getId() == "channel_c"
            && ts->getLocation().fileid < 1 && ts->getParams()
            && ts->getParams()->getSpecialized() && ts->getParams()->getParams().size() > 0) {
        ast::ITemplateGenericTypeParamDecl *tp = NodeKind::cast<ast::ITemplateGenericTypeParamDecl>(
            ts->getParams()->getParams().at(0).get());
        ExprType et = (tp) ? m_typer.typeOfDataType(tp->getDflt()) : ExprType();
        while (et.kind == TypeKindE::Array) {
            ExprType e = m_typer.elemType(et);
            if (!e.known()) {
                break;
            }
            et = e;
        }
        bool bad = false;
        switch (et.kind) {
            case TypeKindE::String:
            case TypeKindE::Chandle:
            case TypeKindE::List:
            case TypeKindE::Map:
            case TypeKindE::Set:
            case TypeKindE::Component:
            case TypeKindE::Action:
                bad = true;
                break;
            case TypeKindE::Enum: {
                // "enumerated types that have a base type"
                ast::ISymbolEnumScope *es = NodeKind::cast<ast::ISymbolEnumScope>(et.scope);
                bad = (es && es->getDecl() && !es->getDecl()->getBase_type());
            } break;
            default:
                break;
        }
        if (bad) {
            m_ctxt->addErrorMarker(i->getName()->getLocation(),
                "channel '%s' cannot hold %s (LRM 21.9.1 a)",
                fname, typeName(et).c_str());
            return;
        }
        if (ts->getParams()->getParams().size() > 1) {
            ast::ITemplateValueParamDecl *dp = NodeKind::cast<ast::ITemplateValueParamDecl>(
                ts->getParams()->getParams().at(1).get());
            if (dp && dp->getDflt()) {
                std::unique_ptr<IVal> v(TaskEvalExpr(
                    m_ctxt->getFactory(), m_ctxt->root()).eval(dp->getDflt()));
                IValInt *vi = dynamic_cast<IValInt *>(v.get());
                if (vi && vi->getValS() <= 0) {
                    m_ctxt->addErrorMarker(i->getName()->getLocation(),
                        "channel '%s' has DEPTH %lld: it shall be positive (LRM 21.9.1 b)",
                        fname, (long long)vi->getValS());
                }
            }
        }
    }
}

void TaskCheckOperands::visitExtendType(ast::IExtendType *i) {
    // 21.14.1: "It shall be illegal to extend the reg_c component and its
    // base components"; 21.14.2: "It shall be illegal to extend the
    // reg_group_c class."
    ast::ITypeScope *ts = 0;
    if (i->getTarget() && i->getTarget()->getTarget()) {
        ast::ISymbolTypeScope *es = NodeKind::cast<ast::ISymbolTypeScope>(
            m_ctxt->resolveSymbolPathRef(i->getTarget()->getTarget()));
        ts = (es) ? NodeKind::cast<ast::ITypeScope>(es->getTarget()) : 0;
    }
    if (ts && ts->getName() && ts->getLocation().fileid < 1) {
        const std::string &n = ts->getName()->getId();
        if (n == "reg_c" || n == "reg_sized_c" || n == "reg_base_c" || n == "reg_group_c") {
            const ast::Location &loc = i->getTarget()->getElems().back()->getId()->getLocation();
            m_ctxt->addErrorMarker(loc,
                "'%s' cannot be extended (LRM %s)", n.c_str(),
                (n == "reg_group_c") ? "21.14.2" : "21.14.1");
        }
    }
    m_type_s.push_back(ts);
    ast::VisitorBase::visitExtendType(i);
    m_type_s.pop_back();
}

void TaskCheckOperands::visitProceduralStmtRandomize(ast::IProceduralStmtRandomize *i) {
    ast::VisitorBase::visitProceduralStmtRandomize(i);
    // 7.1 and 13.4.6 ("plain-data"); ruling R18 reads it as randomizable.
    for (std::vector<ast::IExprUP>::const_iterator
            it=i->getTargets().begin(); it!=i->getTargets().end(); it++) {
        ExprType t = m_typer.typeOf(it->get());
        if (t.kind == TypeKindE::Chandle || t.kind == TypeKindE::Float
                || t.kind == TypeKindE::String) {
            m_ctxt->addErrorMarker(locOf(it->get()),
                "a randomize target of type %s, which is not randomizable "
                "(LRM 7.1, 13.4.6, ruling R18)", t.describe().c_str());
        }
    }
}

void TaskCheckOperands::visitComponent(ast::IComponent *i) {
    m_type_s.push_back(i);
    ast::VisitorBase::visitComponent(i);
    m_type_s.pop_back();
}

void TaskCheckOperands::visitAction(ast::IAction *i) {
    m_type_s.push_back(i);
    ast::VisitorBase::visitAction(i);
    m_type_s.pop_back();
}

void TaskCheckOperands::visitStruct(ast::IStruct *i) {
    m_type_s.push_back(i);
    ast::VisitorBase::visitStruct(i);
    m_type_s.pop_back();
}

void TaskCheckOperands::checkAccess(const std::vector<ast::IExprMemberPathElemUP> &elems) {
    // 17.4 b: a private attribute "is accessible only from the element in
    // which the attribute is declared"; c: a protected one also from
    // sub-elements that inherit from it, and their extensions. A member
    // reached by a bare name is in scope by definition: only `x.m` is judged.
    for (uint32_t k=1; k<elems.size(); k++) {
        ast::IField *f = NodeKind::cast<ast::IField>(elems.at(k)->getId()->getDecl());
        if (!f) {
            continue;
        }
        bool priv = (f->getAttr() & ast::FieldAttr::Private) != ast::FieldAttr::NoFlags;
        bool prot = (f->getAttr() & ast::FieldAttr::Protected) != ast::FieldAttr::NoFlags;
        if (!priv && !prot) {
            continue;
        }
        ast::ITypeScope *decl_t = NodeKind::cast<ast::ITypeScope>(f->getParent());
        if (!decl_t || !decl_t->getName()) {
            continue;
        }
        const std::string &dname = decl_t->getName()->getId();
        bool ok = false;
        for (std::vector<ast::ITypeScope *>::const_iterator
                it=m_type_s.begin(); !ok && it!=m_type_s.end(); it++) {
            ast::ITypeScope *t = *it;
            if (!t) {
                // An extension whose type is not known: say nothing.
                ok = true;
            } else if (t == decl_t || (t->getName() && t->getName()->getId() == dname
                    && t->getLocation().fileid == decl_t->getLocation().fileid
                    && t->getLocation().lineno == decl_t->getLocation().lineno)) {
                // The element itself (a specialization is its copy), or a
                // type nested in it.
                ok = true;
            } else if (prot) {
                // A sub-element: walk its bases for the declaring type.
                ast::ITypeScope *b = t;
                for (int32_t d=0; !ok && b && d<64; d++) {
                    if (b == decl_t || (b->getName() && b->getName()->getId() == dname
                            && b->getLocation().lineno == decl_t->getLocation().lineno)) {
                        ok = true;
                        break;
                    }
                    if (!b->getSuper_t() || !b->getSuper_t()->getTarget() || b->getSuper_cyclic()) {
                        break;
                    }
                    ast::ISymbolTypeScope *bs = NodeKind::cast<ast::ISymbolTypeScope>(
                        m_ctxt->resolveSymbolPathRef(b->getSuper_t()->getTarget()));
                    b = (bs) ? NodeKind::cast<ast::ITypeScope>(bs->getTarget()) : 0;
                }
            }
        }
        if (!ok) {
            m_ctxt->addErrorMarker(elems.at(k)->getId()->getLocation(),
                "'%s' is %s to '%s' and cannot be reached from here (LRM 17.4 %s)",
                f->getName()->getId().c_str(), (priv) ? "private" : "protected",
                dname.c_str(), (priv) ? "b" : "c");
        }
    }
}

namespace {

/** Every reference in an expression. */
class RefCollector : public virtual ast::VisitorBase {
public:
    std::vector<ast::IExpr *> refs;
    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override {
        refs.push_back(i);
    }
    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override {
        refs.push_back(i);
        ast::VisitorBase::visitExprRefPathContext(i);
    }
    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override {
        refs.push_back(i);
    }
};

}

void TaskCheckOperands::checkCompileCond(ast::IExpr *cond) {
    if (!cond) {
        return;
    }
    RefCollector rc;
    cond->accept(&rc);
    for (std::vector<ast::IExpr *>::const_iterator
            it=rc.refs.begin(); it!=rc.refs.end(); it++) {
        ast::IExprRefPath *r = NodeKind::cast<ast::IExprRefPath>(*it);
        ast::IScopeChild *decl = (r && r->getTarget())
            ? m_ctxt->resolveSymbolPathRef(r->getTarget()) : 0;
        ast::IField *f = NodeKind::cast<ast::IField>(decl);
        if (!f || !f->getName()) {
            continue;
        }
        ast::ITypeScope *owner = NodeKind::cast<ast::ITypeScope>(f->getParent());
        if (!owner || !owner->getName()) {
            continue;
        }
        // 19.1.3 b: "Conditional compilation directives may not reference
        // inner members of types."
        m_ctxt->addErrorMarker(locOf(*it),
            "a compile if condition may not reference '%s', a member of type '%s' "
            "(LRM 19.1.3 b)",
            f->getName()->getId().c_str(), owner->getName()->getId().c_str());
        return;
    }
}

void TaskCheckOperands::visitScope(ast::IScope *i) {
    ast::VisitorBase::visitScope(i);
    for (std::vector<ast::ICompileCondUP>::const_iterator
            it=i->getCompile_conds().begin(); it!=i->getCompile_conds().end(); it++) {
        // 19.1.3 speaks of compile if expressions; compile assert (19.4) is
        // not judged.
        if ((*it)->getKind() == ast::CompileCondKind::CompileCondKind_If) {
            checkCompileCond((*it)->getCond());
        }
    }
}


// ---------------------------------------------------------------------------
// Collections where an operator does not apply (F23)
// ---------------------------------------------------------------------------

void TaskCheckOperands::visitConstraintBlock(ast::IConstraintBlock *i) {
    m_decl_ctx++;
    ast::VisitorBase::visitConstraintBlock(i);
    m_decl_ctx--;
}

void TaskCheckOperands::visitActivityDecl(ast::IActivityDecl *i) {
    m_decl_ctx++;
    ast::VisitorBase::visitActivityDecl(i);
    m_decl_ctx--;
}

static bool changesCollectionM(const std::string &name) {
    return name == "push_back" || name == "push_front" || name == "pop_back"
        || name == "pop_front" || name == "insert" || name == "delete"
        || name == "clear";
}

void TaskCheckOperands::checkCollectionUse(
        const std::vector<ast::IExprMemberPathElemUP>   &elems,
        ast::IScopeChild                                *first_decl) {
    ExprType recv;
    for (uint32_t k=0; k<elems.size(); k++) {
        ast::IExprMemberPathElem *elem = elems.at(k).get();
        ast::IScopeChild *decl = elem->getId()->getDecl();
        if (!decl && k == 0) {
            decl = first_decl;
        }
        if (elem->getParams()) {
            if (k > 0 && m_decl_ctx && recv.isCollection()
                    && changesCollectionM(elem->getId()->getId())) {
                // 7.9: "Operators and methods that modify the contents of a
                // collection shall not be used in activities, constraints,
                // or covergroups."
                m_ctxt->addErrorMarker(elem->getId()->getLocation(),
                    "'%s' changes its collection, so it shall not be used in a "
                    "constraint or activity (LRM 7.9)", elem->getId()->getId().c_str());
            }
            return;
        }
        ExprType t = m_typer.typeOfDecl(decl);
        for (std::vector<ast::IExprUP>::const_iterator
                it=elem->getSubscript().begin();
                t.known() && it!=elem->getSubscript().end(); it++) {
            if (t.kind == TypeKindE::Set) {
                // Table 10: the index operator applies to an array, a list or
                // a map; 8.5.9.1's array_slice to an array or a list.
                m_ctxt->addErrorMarker(elem->getId()->getLocation(),
                    "'%s' is a set, which cannot be indexed or sliced "
                    "(LRM 8.4 Table 10, 7.9.5)", elem->getId()->getId().c_str());
                return;
            }
            t = m_typer.subscript(t, it->get());
        }
        recv = t;
        if (!decl) {
            return;
        }
    }
}

}
