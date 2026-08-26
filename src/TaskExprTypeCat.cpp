/*
 * TaskExprTypeCat.cpp
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
#include "pssp/ast/IDataTypeUserDefined.h"
#include "pssp/ast/IEnumDecl.h"
#include "pssp/ast/IStruct.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/ITypeScope.h"
#include "pssp/impl/BuiltinCollectionUtil.h"
#include "pssp/ast/IDataTypeBool.h"
#include "pssp/ast/IDataTypeChandle.h"
#include "pssp/ast/IDataTypeEnum.h"
#include "pssp/ast/IDataTypeFloat.h"
#include "pssp/ast/IDataTypeInt.h"
#include "pssp/ast/IDataTypeString.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/IExprAggrLiteral.h"
#include "pssp/ast/IExprBin.h"
#include "pssp/ast/IExprBool.h"
#include "pssp/ast/IExprCast.h"
#include "pssp/ast/IExprCond.h"
#include "pssp/ast/IExprFloatLiteral.h"
#include "pssp/ast/IExprHierarchicalId.h"
#include "pssp/ast/IExprIn.h"
#include "pssp/ast/IExprListLiteral.h"
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IExprNull.h"
#include "pssp/ast/IExprNumber.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprString.h"
#include "pssp/ast/IExprStructLiteral.h"
#include "pssp/ast/IExprSubstring.h"
#include "pssp/ast/IExprUnary.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ITypedefDeclaration.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskExprTypeCat.h"


namespace pssp {

dmgr::IDebug *TaskExprTypeCat::m_dbg = 0;

TaskExprTypeCat::TaskExprTypeCat(ResolveContext *ctxt) :
    m_ctxt(ctxt), m_depth(0) {
    DEBUG_INIT("pssp::TaskExprTypeCat", ctxt->getDebugMgr());
}

TaskExprTypeCat::~TaskExprTypeCat() {

}

TypeCatE TaskExprTypeCat::expr(ast::IExpr *e) {
    if (!e || m_depth > 32) {
        return TypeCatE::Unknown;
    }

    // Literals -- the cases that motivated this in the first place.
    if (dynamic_cast<ast::IExprString *>(e)) {
        return TypeCatE::String;
    } else if (dynamic_cast<ast::IExprSubstring *>(e)) {
        return TypeCatE::String;
    } else if (dynamic_cast<ast::IExprBool *>(e)) {
        return TypeCatE::Bool;
    } else if (dynamic_cast<ast::IExprFloatLiteral *>(e)) {
        return TypeCatE::Float;
    } else if (dynamic_cast<ast::IExprNumber *>(e)) {
        return TypeCatE::Int;
    } else if (dynamic_cast<ast::IExprNull *>(e)) {
        return TypeCatE::Null;
    } else if (dynamic_cast<ast::IExprAggrLiteral *>(e) ||
               dynamic_cast<ast::IExprListLiteral *>(e) ||
               dynamic_cast<ast::IExprStructLiteral *>(e)) {
        return TypeCatE::Aggregate;
    }

    // A cast states the category outright.
    if (ast::IExprCast *c = dynamic_cast<ast::IExprCast *>(e)) {
        return dataType(c->getCasting_type());
    }

    if (ast::IExprUnary *u = dynamic_cast<ast::IExprUnary *>(e)) {
        m_depth++;
        TypeCatE ret;
        switch (u->getOp()) {
            case ast::ExprUnaryOp::UnaryOp_LogNot:
                ret = TypeCatE::Bool;
                break;
            case ast::ExprUnaryOp::UnaryOp_BitAnd:
            case ast::ExprUnaryOp::UnaryOp_BitOr:
            case ast::ExprUnaryOp::UnaryOp_BitXor:
                // Reduction operators -- always a single bit.
                ret = TypeCatE::Int;
                break;
            default:
                ret = expr(u->getRhs());
                break;
        }
        m_depth--;
        return ret;
    }

    if (ast::IExprBin *b = dynamic_cast<ast::IExprBin *>(e)) {
        switch (b->getOp()) {
            case ast::ExprBinOp::BinOp_LogOr:
            case ast::ExprBinOp::BinOp_LogAnd:
            case ast::ExprBinOp::BinOp_Lt:
            case ast::ExprBinOp::BinOp_Le:
            case ast::ExprBinOp::BinOp_Gt:
            case ast::ExprBinOp::BinOp_Ge:
            case ast::ExprBinOp::BinOp_Eq:
            case ast::ExprBinOp::BinOp_Ne:
                return TypeCatE::Bool;
            case ast::ExprBinOp::BinOp_Shl:
            case ast::ExprBinOp::BinOp_Shr:
                // The shift amount says nothing about the result.
                m_depth++;
                { TypeCatE ret = expr(b->getLhs()); m_depth--; return ret; }
            default: {
                m_depth++;
                TypeCatE ret = merge(expr(b->getLhs()), expr(b->getRhs()));
                m_depth--;
                return ret;
            }
        }
    }

    if (ast::IExprCond *c = dynamic_cast<ast::IExprCond *>(e)) {
        m_depth++;
        TypeCatE ret = merge(expr(c->getTrue_e()), expr(c->getFalse_e()));
        m_depth--;
        return ret;
    }

    if (dynamic_cast<ast::IExprIn *>(e)) {
        return TypeCatE::Bool;
    }

    return refPath(e);
}

TypeCatE TaskExprTypeCat::refPath(ast::IExpr *e) {
    ast::IExprRefPathContext *rp = dynamic_cast<ast::IExprRefPathContext *>(e);

    if (!rp || !rp->getTarget() || rp->getIs_super() || !rp->getHier_id()) {
        return TypeCatE::Unknown;
    }

    // Only a bare `x` is followed. `a.b`, `a[i]`, `a[7:0]` and `f()` each need
    // a step this pass cannot take: member lookup, element type, slice width,
    // or a return type. Those all fall out of the same missing type-inference
    // pass (P3-X6c), so they stay Unknown rather than guessing.
    if (rp->getSlice() || rp->getHier_id()->getElems().size() != 1) {
        return TypeCatE::Unknown;
    }

    ast::IExprMemberPathElem *elem = rp->getHier_id()->getElems().at(0).get();
    if (elem->getParams() || elem->getSubscript().size()) {
        return TypeCatE::Unknown;
    }

    ast::IScopeChild *c = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(),
        m_ctxt->root(),
        m_ctxt->inlineCtxt()).resolve(rp->getTarget());

    return declared(c, this);
}

TypeCatE TaskExprTypeCat::declared(ast::IScopeChild *c, TaskExprTypeCat *self) {
    if (!c) {
        return TypeCatE::Unknown;
    }

    if (dynamic_cast<ast::IEnumItem *>(c)) {
        return TypeCatE::Enum;
    } else if (ast::IField *f = dynamic_cast<ast::IField *>(c)) {
        return self->dataType(f->getType());
    } else if (ast::IProceduralStmtDataDeclaration *d =
        dynamic_cast<ast::IProceduralStmtDataDeclaration *>(c)) {
        return self->dataType(d->getDatatype());
    } else if (ast::IFunctionParamDecl *p =
        dynamic_cast<ast::IFunctionParamDecl *>(c)) {
        return self->dataType(p->getType());
    }

    return TypeCatE::Unknown;
}

TypeCatE TaskExprTypeCat::dataType(ast::IDataType *dt) {
    if (!dt) {
        return TypeCatE::Unknown;
    }

    if (dynamic_cast<ast::IDataTypeString *>(dt)) {
        return TypeCatE::String;
    } else if (dynamic_cast<ast::IDataTypeBool *>(dt)) {
        return TypeCatE::Bool;
    } else if (dynamic_cast<ast::IDataTypeFloat *>(dt)) {
        return TypeCatE::Float;
    } else if (dynamic_cast<ast::IDataTypeInt *>(dt)) {
        return TypeCatE::Int;
    } else if (dynamic_cast<ast::IDataTypeEnum *>(dt)) {
        return TypeCatE::Enum;
    } else if (dynamic_cast<ast::IDataTypeChandle *>(dt)) {
        return TypeCatE::Chandle;
    }

    // A user-defined type is resolved as far as its declaration, which is
    // enough to place the ones that matter. What is left genuinely Unknown --
    // a template parameter, an unresolved name -- stays that way, and Unknown
    // is compatible with everything.
    ast::IDataTypeUserDefined *udt = dynamic_cast<ast::IDataTypeUserDefined *>(dt);

    if (udt && udt->getType_id() && udt->getType_id()->getTarget()) {
        ast::IScopeChild *c =
            m_ctxt->resolveSymbolPathRef(udt->getType_id()->getTarget());

        // An enum resolves to an ISymbolEnumScope, which is an ISymbolScope
        // and *not* an ISymbolTypeScope, so neither the type-scope route nor
        // TaskGetElemSymbolScope produces an IEnumDecl from one.
        if (dynamic_cast<ast::ISymbolEnumScope *>(c)) {
            return TypeCatE::Enum;
        }

        ast::ISymbolTypeScope *sts = dynamic_cast<ast::ISymbolTypeScope *>(c);
        ast::IScopeChild *decl = sts?sts->getTarget():c;

        if (dynamic_cast<ast::IEnumDecl *>(decl)) {
            return TypeCatE::Enum;
        }

        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(decl);

        if (ts) {
            // A built-in collection stays Unknown: `list<int>` against an
            // `int` parameter is a mistake, but the collections are declared
            // as IStruct in BuiltinsFactory, so calling them composite would
            // be right for the wrong reason and wrong for `array<int,4>`
            // against an aggregate literal.
            if (builtinCollectionKind(ts) != CollectionKind::None) {
                return TypeCatE::Unknown;
            }

            if (dynamic_cast<ast::IStruct *>(ts)
                || dynamic_cast<ast::IComponent *>(ts)
                || dynamic_cast<ast::IAction *>(ts)) {
                return TypeCatE::Aggregate;
            }
        }
    }

    return TypeCatE::Unknown;
}

TypeCatE TaskExprTypeCat::merge(TypeCatE a, TypeCatE b) {
    if (a == b) {
        return a;
    }
    if (a == TypeCatE::Unknown || b == TypeCatE::Unknown) {
        return TypeCatE::Unknown;
    }
    if (a == TypeCatE::Float || b == TypeCatE::Float) {
        // Only if the other side is numeric; a `string + float` is already
        // ill-formed and is not this pass's problem.
        if (compatible(TypeCatE::Float, a) && compatible(TypeCatE::Float, b)) {
            return TypeCatE::Float;
        }
        return TypeCatE::Unknown;
    }
    if (compatible(TypeCatE::Int, a) && compatible(TypeCatE::Int, b)) {
        return TypeCatE::Int;
    }
    return TypeCatE::Unknown;
}

bool TaskExprTypeCat::compatible(TypeCatE decl, TypeCatE actual) {
    if (decl == TypeCatE::Unknown || actual == TypeCatE::Unknown) {
        return true;
    }
    if (decl == actual) {
        return true;
    }

    switch (decl) {
        case TypeCatE::Int:
        case TypeCatE::Bool:
        case TypeCatE::Float:
        case TypeCatE::Enum:
            // The numeric family converts freely: `bit` and `int` differ only
            // in signedness, `bool` is a one-bit value, and an enum has an
            // integer representation (PSS 3.1 4.5).
            return (actual == TypeCatE::Int || actual == TypeCatE::Bool ||
                    actual == TypeCatE::Float || actual == TypeCatE::Enum);

        case TypeCatE::Chandle:
            return (actual == TypeCatE::Null);

        case TypeCatE::String:
        case TypeCatE::Aggregate:
        case TypeCatE::Null:
            return false;

        default:
            return true;
    }
}

const char *TaskExprTypeCat::name(TypeCatE c) {
    switch (c) {
        case TypeCatE::Int: return "int";
        case TypeCatE::Bool: return "bool";
        case TypeCatE::Float: return "float";
        case TypeCatE::String: return "string";
        case TypeCatE::Enum: return "an enum value";
        case TypeCatE::Chandle: return "chandle";
        case TypeCatE::Aggregate: return "an aggregate literal";
        case TypeCatE::Null: return "null";
        default: return "an unknown type";
    }
}

const char *TaskExprTypeCat::dataTypeName(ast::IDataType *dt, TypeCatE c) {
    if (c == TypeCatE::Int) {
        ast::IDataTypeInt *i = dynamic_cast<ast::IDataTypeInt *>(dt);
        if (i && !i->getIs_signed()) {
            return "bit";
        }
    }
    return name(c);
}

}
