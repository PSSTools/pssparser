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
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IExprNull.h"
#include "pssp/ast/IExprNumber.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprString.h"
#include "pssp/ast/IExprUnary.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IGenericConstraintParam.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ITypedefDeclaration.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "pssp/ast/IActionHandleField.h"
#include "pssp/ast/IDataTypePyObj.h"
#include "pssp/ast/IDataTypeRef.h"
#include "pssp/ast/IExprMemberCall.h"
#include "pssp/ast/IExprRefPathStatic.h"
#include "pssp/ast/IExprRefPathStaticRooted.h"
#include "pssp/ast/IExprSignedNumber.h"
#include "pssp/ast/IExprUnsignedNumber.h"
#include "pssp/ast/IExprSliceRange.h"
#include "pssp/ast/IFieldClaim.h"
#include "pssp/ast/IFieldCompRef.h"
#include "pssp/ast/IFieldPool.h"
#include "pssp/ast/IFieldRef.h"
#include "pssp/ast/IFunctionDefinition.h"
#include "pssp/ast/IFunctionImportProto.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IMethodParameterList.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ITargetTemplateFunction.h"
#include "pssp/ast/ITemplateCategoryTypeParamDecl.h"
#include "pssp/ast/ITemplateGenericTypeParamDecl.h"
#include "pssp/ast/ITemplateParamDeclList.h"
#include "pssp/ast/ITemplateValueParamDecl.h"
#include "pssp/IValInt.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "ExprTypeOf.h"
#include "TaskExprTypeCat.h"
#include "pssp/impl/NodeKind.h"


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
    if (NodeKind::cast<ast::IExprString>(e)) {
        return TypeCatE::String;
    } else if (NodeKind::cast<ast::IExprBool>(e)) {
        return TypeCatE::Bool;
    } else if (NodeKind::cast<ast::IExprFloatLiteral>(e)) {
        return TypeCatE::Float;
    } else if (NodeKind::cast<ast::IExprNumber>(e)) {
        return TypeCatE::Int;
    } else if (NodeKind::cast<ast::IExprNull>(e)) {
        return TypeCatE::Null;
    } else if (NodeKind::cast<ast::IExprAggrLiteral>(e)) {
        return TypeCatE::Aggregate;
    }

    // A cast states the category outright.
    if (ast::IExprCast *c = NodeKind::cast<ast::IExprCast>(e)) {
        return dataType(c->getCasting_type());
    }

    if (ast::IExprUnary *u = NodeKind::cast<ast::IExprUnary>(e)) {
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

    if (ast::IExprBin *b = NodeKind::cast<ast::IExprBin>(e)) {
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

    if (ast::IExprCond *c = NodeKind::cast<ast::IExprCond>(e)) {
        m_depth++;
        TypeCatE ret = merge(expr(c->getTrue_e()), expr(c->getFalse_e()));
        m_depth--;
        return ret;
    }

    if (NodeKind::cast<ast::IExprIn>(e)) {
        return TypeCatE::Bool;
    }

    return refPath(e);
}

TypeCatE TaskExprTypeCat::refPath(ast::IExpr *e) {
    ast::IExprRefPathContext *rp = NodeKind::cast<ast::IExprRefPathContext>(e);

    if (!rp || !rp->getTarget() || !rp->getHier_id()) {
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

    if (NodeKind::cast<ast::IEnumItem>(c)) {
        return TypeCatE::Enum;
    } else if (ast::IField *f = NodeKind::cast<ast::IField>(c)) {
        return self->dataType(f->getType());
    } else if (ast::IProceduralStmtDataDeclaration *d =
        NodeKind::cast<ast::IProceduralStmtDataDeclaration>(c)) {
        return self->dataType(d->getDatatype());
    } else if (ast::IFunctionParamDecl *p =
        NodeKind::cast<ast::IFunctionParamDecl>(c)) {
        return self->dataType(p->getType());
    } else if (ast::IGenericConstraintParam *p =
        NodeKind::cast<ast::IGenericConstraintParam>(c)) {
        // A `numeric` parameter has no type: it is integer or float (13.1.2).
        return self->dataType(p->getType());
    }

    return TypeCatE::Unknown;
}

TypeCatE TaskExprTypeCat::dataType(ast::IDataType *dt) {
    if (!dt) {
        return TypeCatE::Unknown;
    }

    if (NodeKind::cast<ast::IDataTypeString>(dt)) {
        return TypeCatE::String;
    } else if (NodeKind::cast<ast::IDataTypeBool>(dt)) {
        return TypeCatE::Bool;
    } else if (NodeKind::cast<ast::IDataTypeFloat>(dt)) {
        return TypeCatE::Float;
    } else if (NodeKind::cast<ast::IDataTypeInt>(dt)) {
        return TypeCatE::Int;
    } else if (NodeKind::cast<ast::IDataTypeEnum>(dt)) {
        return TypeCatE::Enum;
    } else if (NodeKind::cast<ast::IDataTypeChandle>(dt)) {
        return TypeCatE::Chandle;
    }

    // A user-defined type is resolved as far as its declaration, which is
    // enough to place the ones that matter. What is left genuinely Unknown --
    // a template parameter, an unresolved name -- stays that way, and Unknown
    // is compatible with everything.
    ast::IDataTypeUserDefined *udt = NodeKind::cast<ast::IDataTypeUserDefined>(dt);

    if (udt && udt->getType_id() && udt->getType_id()->getTarget()) {
        ast::IScopeChild *c =
            m_ctxt->resolveSymbolPathRef(udt->getType_id()->getTarget());

        // An enum resolves to an ISymbolEnumScope, which is an ISymbolScope
        // and *not* an ISymbolTypeScope, so neither the type-scope route nor
        // TaskGetElemSymbolScope produces an IEnumDecl from one.
        if (NodeKind::cast<ast::ISymbolEnumScope>(c)) {
            return TypeCatE::Enum;
        }

        ast::ISymbolTypeScope *sts = NodeKind::cast<ast::ISymbolTypeScope>(c);
        ast::IScopeChild *decl = sts?sts->getTarget():c;

        if (NodeKind::cast<ast::IEnumDecl>(decl)) {
            return TypeCatE::Enum;
        }

        ast::ITypeScope *ts = NodeKind::cast<ast::ITypeScope>(decl);

        if (ts) {
            // A built-in collection stays Unknown: `list<int>` against an
            // `int` parameter is a mistake, but the collections are declared
            // as IStruct in BuiltinsFactory, so calling them composite would
            // be right for the wrong reason and wrong for `array<int,4>`
            // against an aggregate literal.
            if (builtinCollectionKind(ts) != CollectionKind::None) {
                return TypeCatE::Unknown;
            }

            if (NodeKind::cast<ast::IStruct>(ts)
                || NodeKind::cast<ast::IComponent>(ts)
                || NodeKind::cast<ast::IAction>(ts)) {
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
        ast::IDataTypeInt *i = NodeKind::cast<ast::IDataTypeInt>(dt);
        if (i && !i->getIs_signed()) {
            return "bit";
        }
    }
    return name(c);
}


// ---------------------------------------------------------------------------
// ExprType: the type of an arbitrary operand (front-end checks, step 0)
// ---------------------------------------------------------------------------

TypeCatE ExprType::cat() const {
    switch (kind) {
        case TypeKindE::Int: return TypeCatE::Int;
        case TypeKindE::Bool: return TypeCatE::Bool;
        case TypeKindE::Float: return TypeCatE::Float;
        case TypeKindE::String: return TypeCatE::String;
        case TypeKindE::Enum: return TypeCatE::Enum;
        case TypeKindE::Chandle: return TypeCatE::Chandle;
        case TypeKindE::Null: return TypeCatE::Null;
        case TypeKindE::Aggregate:
        case TypeKindE::Struct:
        case TypeKindE::Component:
        case TypeKindE::Action: return TypeCatE::Aggregate;
        default: return TypeCatE::Unknown;
    }
}

static std::string scopeName(ast::ISymbolScope *s) {
    return (s) ? s->getName() : std::string("?");
}

std::string ExprType::describe() const {
    switch (kind) {
        case TypeKindE::Void: return "void";
        case TypeKindE::Int: return (is_signed) ? "int" : "bit";
        case TypeKindE::Bool: return "bool";
        case TypeKindE::Float: return "float";
        case TypeKindE::String: return "string";
        case TypeKindE::Chandle: return "chandle";
        case TypeKindE::Null: return "null";
        case TypeKindE::Aggregate: return "an aggregate literal";
        case TypeKindE::Other: return "other";
        case TypeKindE::Enum: return "enum " + scopeName(scope);
        case TypeKindE::Struct: return "struct " + scopeName(scope);
        case TypeKindE::Component: return "component " + scopeName(scope);
        case TypeKindE::Action: return "action " + scopeName(scope);
        case TypeKindE::Array:
            return (size >= 0) ? "array[" + std::to_string(size) + "]" : "array";
        case TypeKindE::List: return "list";
        case TypeKindE::Map: return "map";
        case TypeKindE::Set: return "set";
        default: return "unknown";
    }
}

/** `a` and `b` combined by an arithmetic or bitwise operator, or by `?:`. */
static ExprType mergeTypes(const ExprType &a, const ExprType &b) {
    if (!a.known() || !b.known()) {
        return ExprType();
    }
    if (a.kind == b.kind && (a.kind == TypeKindE::Int || a.kind == TypeKindE::Bool
            || a.kind == TypeKindE::Float || a.kind == TypeKindE::String)) {
        ExprType ret(a.kind);
        ret.is_signed = a.is_signed && b.is_signed;
        return ret;
    }
    if (a.kind == b.kind && a.scope && a.scope == b.scope) {
        return a;
    }
    bool a_num = (a.kind == TypeKindE::Int || a.kind == TypeKindE::Enum
        || a.kind == TypeKindE::Bool);
    bool b_num = (b.kind == TypeKindE::Int || b.kind == TypeKindE::Enum
        || b.kind == TypeKindE::Bool);
    if ((a.kind == TypeKindE::Float && (b_num || b.kind == TypeKindE::Float))
            || (b.kind == TypeKindE::Float && a_num)) {
        return ExprType(TypeKindE::Float);
    }
    if (a.kind == TypeKindE::Int && b.kind == TypeKindE::Int) {
        return ExprType(TypeKindE::Int);
    }
    return ExprType();
}

ExprType TaskExprTypeCat::typeOf(ast::IExpr *e) {
    if (!e || m_depth > 32) {
        return ExprType();
    }
    ExprType ret;
    m_depth++;

    NodeKind nk(e);
    if (nk.is<ast::IExprString>()) {
        ret = ExprType(TypeKindE::String);
    } else if (nk.is<ast::IExprBool>()) {
        ret = ExprType(TypeKindE::Bool);
    } else if (nk.is<ast::IExprFloatLiteral>()) {
        ret = ExprType(TypeKindE::Float);
    } else if (nk.is<ast::IExprNumber>()) {
        // The type of a literal is read from its text (4.6.1); only the
        // signedness is needed here: a based literal is unsigned.
        // An unbased decimal literal is an `int`; a based one (`8'hFF`,
        // `0x10`) is unsigned.
        ret = ExprType(TypeKindE::Int);
        const std::string *image = 0;
        if (ast::IExprSignedNumber *n = nk.as<ast::IExprSignedNumber>()) {
            image = &n->getImage();
        } else if (ast::IExprUnsignedNumber *n = nk.as<ast::IExprUnsignedNumber>()) {
            image = &n->getImage();
        }
        ret.is_signed = (image && image->find('\'') == std::string::npos
            && image->find_first_of("xXbBoO") == std::string::npos);
    } else if (nk.is<ast::IExprNull>()) {
        ret = ExprType(TypeKindE::Null);
    } else if (nk.is<ast::IExprAggrLiteral>()) {
        ret = ExprType(TypeKindE::Aggregate);
    } else if (ast::IExprCast *c = nk.as<ast::IExprCast>()) {
        ret = typeOfDataType(c->getCasting_type());
        ret.dt = 0;
    } else if (nk.is<ast::IExprIn>()) {
        ret = ExprType(TypeKindE::Bool);
    } else if (ast::IExprUnary *u = nk.as<ast::IExprUnary>()) {
        switch (u->getOp()) {
            case ast::ExprUnaryOp::UnaryOp_LogNot:
                ret = ExprType(TypeKindE::Bool);
                break;
            case ast::ExprUnaryOp::UnaryOp_BitAnd:
            case ast::ExprUnaryOp::UnaryOp_BitOr:
            case ast::ExprUnaryOp::UnaryOp_BitXor:
                // A reduction is one bit (8.5.6).
                ret = ExprType(TypeKindE::Int);
                break;
            default: {
                ExprType r = typeOf(u->getRhs());
                if (r.kind == TypeKindE::Int || r.kind == TypeKindE::Float
                        || r.kind == TypeKindE::Bool) {
                    ret = ExprType(r.kind);
                    ret.is_signed = r.is_signed;
                } else if (r.kind == TypeKindE::Enum) {
                    ret = ExprType(TypeKindE::Int);
                }
            } break;
        }
    } else if (ast::IExprBin *b = nk.as<ast::IExprBin>()) {
        switch (b->getOp()) {
            case ast::ExprBinOp::BinOp_LogOr:
            case ast::ExprBinOp::BinOp_LogAnd:
            case ast::ExprBinOp::BinOp_Lt:
            case ast::ExprBinOp::BinOp_Le:
            case ast::ExprBinOp::BinOp_Gt:
            case ast::ExprBinOp::BinOp_Ge:
            case ast::ExprBinOp::BinOp_Eq:
            case ast::ExprBinOp::BinOp_Ne:
                ret = ExprType(TypeKindE::Bool);
                break;
            case ast::ExprBinOp::BinOp_Shl:
            case ast::ExprBinOp::BinOp_Shr: {
                // The shift amount says nothing about the result.
                ExprType l = typeOf(b->getLhs());
                if (l.kind == TypeKindE::Int) {
                    ret = ExprType(TypeKindE::Int);
                    ret.is_signed = l.is_signed;
                }
            } break;
            default: {
                ExprType l = typeOf(b->getLhs());
                ExprType r = typeOf(b->getRhs());
                ret = mergeTypes(l, r);
                ret.dt = 0;
                if (ret.kind == TypeKindE::Enum) {
                    ret = ExprType(TypeKindE::Int);
                }
            } break;
        }
    } else if (ast::IExprCond *c = nk.as<ast::IExprCond>()) {
        ret = mergeTypes(typeOf(c->getTrue_e()), typeOf(c->getFalse_e()));
    } else if (ast::IExprRefPathStaticRooted *r = nk.as<ast::IExprRefPathStaticRooted>()) {
        if (r->getLeaf()) {
            ret = typeOfElems(ExprType(), r->getLeaf()->getElems(), 0, false);
        }
        if (r->getSlice()) {
            ret = (ret.kind == TypeKindE::Int) ? ExprType(TypeKindE::Int) : ExprType();
        }
    } else if (ast::IExprRefPathContext *r = nk.as<ast::IExprRefPathContext>()) {
        if (r->getTarget() && r->getHier_id() && r->getHier_id()->getElems().size()) {
            const std::vector<ast::IExprMemberPathElemUP> &elems =
                r->getHier_id()->getElems();
            ast::IExprMemberPathElem *first = elems.at(0).get();
            ExprType t;
            if (first->getId()->getDecl()) {
                t = typeOfElem(ExprType(), first, false);
            } else {
                // The first element is bound by the path's target.
                ast::IScopeChild *decl = m_ctxt->resolveSymbolPathRef(r->getTarget());
                if (NodeKind::cast<ast::IEnumItem>(decl)) {
                    ast::ISymbolEnumScope *es = ExprTypeOf(m_ctxt).enumOfItemPath(
                        r->getTarget());
                    if (es) {
                        t = ExprType(TypeKindE::Enum);
                        t.scope = es;
                    }
                } else {
                    t = typeOfDecl(decl);
                }
                if (first->getParams() || first->getSubscript().size()) {
                    // A call or a subscript on a name with no decl recorded.
                    if (first->getParams()) {
                        t = ExprType();
                    }
                    for (std::vector<ast::IExprUP>::const_iterator
                            it=first->getSubscript().begin();
                            t.known() && it!=first->getSubscript().end(); it++) {
                        t = subscript(t, it->get());
                    }
                }
            }
            ret = typeOfElems(t, elems, 1, false);
        }
        if (r->getSlice()) {
            ret = (ret.kind == TypeKindE::Int) ? ExprType(TypeKindE::Int) : ExprType();
        }
    } else if (ast::IExprRefPathStatic *r = nk.as<ast::IExprRefPathStatic>()) {
        if (r->getTarget()) {
            ast::IScopeChild *decl = m_ctxt->resolveSymbolPathRef(r->getTarget());
            if (NodeKind::cast<ast::IEnumItem>(decl)) {
                ast::ISymbolEnumScope *es = ExprTypeOf(m_ctxt).enumOfItemPath(
                    r->getTarget());
                if (es) {
                    ret = ExprType(TypeKindE::Enum);
                    ret.scope = es;
                }
            } else {
                ret = typeOfDecl(decl);
            }
        }
        if (r->getSlice()) {
            ret = (ret.kind == TypeKindE::Int) ? ExprType(TypeKindE::Int) : ExprType();
        }
    } else if (ast::IExprMemberCall *mc = nk.as<ast::IExprMemberCall>()) {
        ret = typeOfElems(typeOf(mc->getReceiver()), mc->getMembers(), 0, true);
    }

    m_depth--;
    return ret;
}

ExprType TaskExprTypeCat::typeOfElems(
        ExprType                                            t,
        const std::vector<ast::IExprMemberPathElemUP>       &elems,
        uint32_t                                            first,
        bool                                                has_recv) {
    for (uint32_t ii=first; ii<elems.size(); ii++) {
        bool recv = (ii > 0 || has_recv);
        if (recv && !t.known()) {
            return ExprType();
        }
        t = typeOfElem(t, elems.at(ii).get(), recv);
    }
    return t;
}

ExprType TaskExprTypeCat::typeOfElem(
        const ExprType              &recv,
        ast::IExprMemberPathElem    *elem,
        bool                        has_recv) {
    ast::IScopeChild *decl = elem->getId()->getDecl();
    ExprType t;
    if (decl) {
        t = typeOfDecl(decl);
        if (elem->getParams() && !NodeKind::cast<ast::ISymbolFunctionScope>(decl)
                && !NodeKind::cast<ast::IFunctionPrototype>(decl)
                && !NodeKind::cast<ast::IFunctionDefinition>(decl)) {
            // A call of something that is not a function.
            t = ExprType();
        }
        if (!t.known() && elem->getParams() && has_recv) {
            // A built-in method declared generically: its return type is a
            // parameter of the collection, which the receiver binds.
            t = builtinMethod(recv, elem->getId()->getId());
        }
    } else if (has_recv && elem->getParams()) {
        t = builtinMethod(recv, elem->getId()->getId());
    } else {
        return ExprType();
    }
    for (std::vector<ast::IExprUP>::const_iterator
            it=elem->getSubscript().begin();
            t.known() && it!=elem->getSubscript().end(); it++) {
        t = subscript(t, it->get());
    }
    return t;
}

ExprType TaskExprTypeCat::builtinMethod(const ExprType &recv, const std::string &name) {
    switch (recv.kind) {
        case TypeKindE::String:
            // 7.6.3
            if (name == "size" || name == "find" || name == "find_last") {
                ExprType r(TypeKindE::Int);
                r.is_signed = true;
                return r;
            } else if (name == "lower" || name == "upper") {
                return ExprType(TypeKindE::String);
            } else if (name == "split" || name == "chars" || name == "find_all") {
                return ExprType(TypeKindE::List);
            }
            break;
        case TypeKindE::Array:
        case TypeKindE::List:
        case TypeKindE::Map:
        case TypeKindE::Set:
            if (name == "size") {
                ExprType r(TypeKindE::Int);
                r.is_signed = true;
                return r;
            } else if (recv.kind == TypeKindE::List
                    && (name == "pop_front" || name == "pop_back")) {
                return elemType(recv);
            }
            break;
        default:
            break;
    }
    return ExprType();
}

ExprType TaskExprTypeCat::typeOfDecl(ast::IScopeChild *decl) {
    if (!decl || m_depth > 32) {
        return ExprType();
    }
    ExprType ret;
    m_depth++;
    NodeKind nk(decl);
    if (ast::IEnumItem *ei = nk.as<ast::IEnumItem>()) {
        if (ei->getUpper()) {
            ret = ExprType(TypeKindE::Enum);
            ret.scope = ei->getUpper();
        }
    } else if (ast::IField *f = nk.as<ast::IField>()) {
        ret = typeOfDataType(f->getType());
    } else if (ast::IProceduralStmtDataDeclaration *d =
            nk.as<ast::IProceduralStmtDataDeclaration>()) {
        ret = typeOfDataType(d->getDatatype());
    } else if (ast::IFunctionParamDecl *p = nk.as<ast::IFunctionParamDecl>()) {
        if (p->getKind() == ast::FunctionParamDeclKind::ParamKind_DataType) {
            ret = typeOfDataType(p->getType());
        }
    } else if (ast::IGenericConstraintParam *p = nk.as<ast::IGenericConstraintParam>()) {
        ret = typeOfDataType(p->getType());
    } else if (ast::ITemplateValueParamDecl *p = nk.as<ast::ITemplateValueParamDecl>()) {
        ret = typeOfDataType(p->getType());
    } else if (ast::IFieldRef *f = nk.as<ast::IFieldRef>()) {
        ret = typeOfDataType(f->getType());
        ret.is_ref = true;
    } else if (ast::IFieldCompRef *f = nk.as<ast::IFieldCompRef>()) {
        ret = typeOfDataType(f->getType());
        ret.is_ref = true;
    } else if (ast::IFieldClaim *f = nk.as<ast::IFieldClaim>()) {
        ret = typeOfDataType(f->getType());
        ret.is_ref = true;
    } else if (ast::IActionHandleField *f = nk.as<ast::IActionHandleField>()) {
        ret = typeOfDataType(f->getType());
    } else {
        // A function: the type of a call is its return type.
        ast::IFunctionPrototype *proto = nk.as<ast::IFunctionPrototype>();
        if (ast::ISymbolFunctionScope *fs = nk.as<ast::ISymbolFunctionScope>()) {
            proto = (fs->getPrototypes().size()) ? fs->getPrototypes().front() : 0;
        } else if (ast::IFunctionDefinition *fd = nk.as<ast::IFunctionDefinition>()) {
            proto = fd->getProto();
        }
        if (proto) {
            ret = (proto->getRtype())
                ? typeOfDataType(proto->getRtype()) : ExprType(TypeKindE::Void);
        }
    }
    m_depth--;
    return ret;
}

ExprType TaskExprTypeCat::typeOfDataType(ast::IDataType *dt) {
    if (!dt || m_depth > 32) {
        return ExprType();
    }
    ExprType ret;
    NodeKind nk(dt);
    if (ast::IDataTypeInt *i = nk.as<ast::IDataTypeInt>()) {
        ret = ExprType(TypeKindE::Int);
        ret.is_signed = i->getIs_signed();
    } else if (nk.is<ast::IDataTypeBool>()) {
        ret = ExprType(TypeKindE::Bool);
    } else if (nk.is<ast::IDataTypeFloat>()) {
        ret = ExprType(TypeKindE::Float);
    } else if (nk.is<ast::IDataTypeString>()) {
        ret = ExprType(TypeKindE::String);
    } else if (nk.is<ast::IDataTypeChandle>()) {
        ret = ExprType(TypeKindE::Chandle);
    } else if (nk.is<ast::IDataTypePyObj>()) {
        ret = ExprType(TypeKindE::Other);
    } else if (ast::IDataTypeEnum *e = nk.as<ast::IDataTypeEnum>()) {
        ret = typeOfDataType(e->getTid());
        if (ret.kind != TypeKindE::Enum) {
            ret = ExprType();
        }
    } else if (ast::IDataTypeRef *r = nk.as<ast::IDataTypeRef>()) {
        m_depth++;
        ret = typeOfDataType(r->getType());
        m_depth--;
        ret.is_ref = true;
        return ret;
    } else if (ast::IDataTypeUserDefined *udt = nk.as<ast::IDataTypeUserDefined>()) {
        if (!udt->getType_id() || !udt->getType_id()->getTarget()) {
            return ExprType();
        }
        ast::IScopeChild *c = m_ctxt->resolveSymbolPathRef(udt->getType_id()->getTarget());
        NodeKind ck(c);
        if (ast::ISymbolEnumScope *es = ck.as<ast::ISymbolEnumScope>()) {
            ret = ExprType(TypeKindE::Enum);
            ret.scope = es;
        } else if (ast::ISymbolTypeScope *sts = ck.as<ast::ISymbolTypeScope>()) {
            ast::ITypeScope *ts = NodeKind::cast<ast::ITypeScope>(sts->getTarget());
            switch (builtinCollectionKind(ts)) {
                case CollectionKind::Array: ret = ExprType(TypeKindE::Array); break;
                case CollectionKind::List: ret = ExprType(TypeKindE::List); break;
                case CollectionKind::Map: ret = ExprType(TypeKindE::Map); break;
                case CollectionKind::Set: ret = ExprType(TypeKindE::Set); break;
                default:
                    if (NodeKind::cast<ast::IStruct>(ts)) {
                        ret = ExprType(TypeKindE::Struct);
                    } else if (NodeKind::cast<ast::IComponent>(ts)) {
                        ret = ExprType(TypeKindE::Component);
                    } else if (NodeKind::cast<ast::IAction>(ts)) {
                        ret = ExprType(TypeKindE::Action);
                    } else if (ts) {
                        ret = ExprType(TypeKindE::Other);
                    }
                    break;
            }
            if (ret.known()) {
                ret.scope = sts;
            }
            if (ret.kind == TypeKindE::Array) {
                // The size is the specialization's second parameter.
                if (ts && ts->getParams() && ts->getParams()->getSpecialized()
                        && ts->getParams()->getParams().size() > 1) {
                    ast::ITemplateValueParamDecl *v = NodeKind::cast<ast::ITemplateValueParamDecl>(
                        ts->getParams()->getParams().at(1).get());
                    if (v && v->getDflt()) {
                        std::unique_ptr<IVal> val(TaskEvalExpr(
                            m_ctxt->getFactory(), m_ctxt->root()).eval(v->getDflt()));
                        if (IValInt *iv = dynamic_cast<IValInt *>(val.get())) {
                            ret.size = iv->getValS();
                        }
                    }
                }
            }
        } else if (ast::ITypedefDeclaration *td = ck.as<ast::ITypedefDeclaration>()) {
            m_depth++;
            ret = typeOfDataType(td->getType());
            m_depth--;
            return ret;
        } else if (ck.is<ast::ITemplateGenericTypeParamDecl>()
                || ck.is<ast::ITemplateCategoryTypeParamDecl>()) {
            m_depth++;
            ret = boundTypeParam(c, udt->getType_id()->getTarget());
            m_depth--;
            return ret;
        }
    }
    if (ret.known()) {
        ret.dt = dt;
    }
    return ret;
}

ExprType TaskExprTypeCat::boundTypeParam(ast::IScopeChild *param, ast::ISymbolRefPath *path) {
    // Only a specialization's parameter holds the bound argument in `dflt`;
    // in the generic declaration it holds the declared default, which says
    // nothing about the value. A parameter of a specialization is reached
    // through it: its path ends in a TypeSpec step and then the ParamIdx.
    const std::vector<ast::SymbolRefPathElem> &elems = path->getPath();
    if (elems.size() < 2
            || elems.at(elems.size()-1).kind != ast::SymbolRefPathElemKind::ElemKind_ParamIdx
            || elems.at(elems.size()-2).kind != ast::SymbolRefPathElemKind::ElemKind_TypeSpec) {
        return ExprType();
    }
    if (ast::ITemplateGenericTypeParamDecl *g =
            NodeKind::cast<ast::ITemplateGenericTypeParamDecl>(param)) {
        return typeOfDataType(g->getDflt());
    } else if (ast::ITemplateCategoryTypeParamDecl *c =
            NodeKind::cast<ast::ITemplateCategoryTypeParamDecl>(param)) {
        return typeOfDataType(c->getDflt());
    }
    return ExprType();
}

ExprType TaskExprTypeCat::collectionParam(const ExprType &t, int32_t idx) {
    ast::ISymbolTypeScope *sts = NodeKind::cast<ast::ISymbolTypeScope>(t.scope);
    ast::ITypeScope *ts = (sts) ? NodeKind::cast<ast::ITypeScope>(sts->getTarget()) : 0;
    if (!ts || idx < 0 || !ts->getParams() || !ts->getParams()->getSpecialized()
            || idx >= (int32_t)ts->getParams()->getParams().size()) {
        return ExprType();
    }
    ast::ITemplateParamDecl *p = ts->getParams()->getParams().at(idx).get();
    ExprType ret;
    m_depth++;
    if (ast::ITemplateGenericTypeParamDecl *g =
            NodeKind::cast<ast::ITemplateGenericTypeParamDecl>(p)) {
        ret = typeOfDataType(g->getDflt());
    } else if (ast::ITemplateCategoryTypeParamDecl *c =
            NodeKind::cast<ast::ITemplateCategoryTypeParamDecl>(p)) {
        ret = typeOfDataType(c->getDflt());
    }
    m_depth--;
    return ret;
}

ExprType TaskExprTypeCat::elemType(const ExprType &t) {
    switch (t.kind) {
        case TypeKindE::Array:
        case TypeKindE::List:
        case TypeKindE::Set:
            return collectionParam(t, 0);
        case TypeKindE::Map:
            return collectionParam(t, 1);
        default:
            return ExprType();
    }
}

ExprType TaskExprTypeCat::subscript(const ExprType &t, ast::IExpr *sub) {
    bool slice = (NodeKind::cast<ast::IExprSliceRange>(sub) != 0);
    switch (t.kind) {
        case TypeKindE::String:
            // An index or a slice of a string is a sub-string (8.6.3).
            return ExprType(TypeKindE::String);
        case TypeKindE::Int: {
            // A bit select (8.6.1).
            return (slice) ? ExprType() : ExprType(TypeKindE::Int);
        }
        case TypeKindE::Array:
        case TypeKindE::List: {
            if (slice) {
                ExprType ret(t);
                ret.size = -1;
                ret.dt = 0;
                return ret;
            }
            return elemType(t);
        }
        case TypeKindE::Map:
            return (slice) ? ExprType() : elemType(t);
        default:
            return ExprType();
    }
}

}
