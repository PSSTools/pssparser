/*
 * TaskCompareTypeRefs.cpp
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
#include <typeinfo>
#include "dmgr/impl/DebugMacros.h"
#include "pssp/IVal.h"
#include "pssp/IValInt.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskCompareTypeRefs.h"
#include "TaskCompareVal.h"


namespace pssp {



TaskCompareTypeRefs::TaskCompareTypeRefs(
    IFactory                *factory,
    ast::ISymbolScope       *root) :
    m_factory(factory), m_root(root), m_expr_eval(factory, root),
    m_comp_val(factory->getDebugMgr()), m_kind(Kind::Unknown), m_type(0) {
    DEBUG_INIT("pssp::TaskCompareTypeRefs", factory->getDebugMgr());
}

TaskCompareTypeRefs::~TaskCompareTypeRefs() {

}

bool TaskCompareTypeRefs::equal(
        ast::IDataType          *tref1,
        ast::IDataType          *tref2) {
    return (compare(tref1, tref2) == Rel::Equal);
}

TaskCompareTypeRefs::Rel TaskCompareTypeRefs::compare(
        ast::IDataType          *tref1,
        ast::IDataType          *tref2) {
    DEBUG_ENTER("compare");

    // A parameter with nothing bound has no type. Two such are equal; one
    // bound and one not are not.
    if (!tref1 || !tref2) {
        DEBUG_LEAVE("compare (null) %d", (tref1 == tref2));
        return (tref1 == tref2)?Rel::Equal:Rel::NotEqual;
    }

    // Checked before the kinds, because an alias defeats the kind comparison
    // as thoroughly as it defeats the identity one: `typedef int myint` makes
    // a UserDefined reference and an Int reference name one type.
    if (isTypedefRef(tref1) || isTypedefRef(tref2)) {
        DEBUG_LEAVE("compare (typedef) unsure");
        return Rel::Unsure;
    }

    Kind kind1 = classify(tref1);
    ast::IDataType *type1 = m_type;
    Kind kind2 = classify(tref2);
    ast::IDataType *type2 = m_type;

    if (kind1 != kind2) {
        // One unclassifiable side makes the *pair* unclassifiable: a kind
        // with no visitor here could be anything, including whatever the
        // other side is.
        if (kind1 == Kind::Unknown || kind2 == Kind::Unknown) {
            DEBUG_LEAVE("compare (kind unknown) unsure");
            return Rel::Unsure;
        }
        // A name that did not resolve is not a name that denotes something
        // else -- it denotes nothing yet. `function Missing f(); function int
        // f();` is one mistake, the unknown type, and calling it two says the
        // declarations disagree when what is true is that one of them cannot
        // be read at all.
        //
        // Narrowed to the kind-mismatch branch on purpose. Two *unresolved*
        // references of the same kind still fall through to the name
        // comparison below, which is what keeps specialization dedup working
        // for a single file of a multi-file model -- and which answers Unsure
        // for two names that differ, so the same-kind spelling of this case
        // (`Missing1` vs `Missing2`) is covered there rather than here.
        if (isUnresolvedRef(tref1) || isUnresolvedRef(tref2)) {
            DEBUG_LEAVE("compare (unresolved) unsure");
            return Rel::Unsure;
        }
        DEBUG_LEAVE("compare (kind %d vs %d) NotEqual", (int)kind1, (int)kind2);
        return Rel::NotEqual;
    }

    Rel ret = Rel::NotEqual;
    switch (kind1) {
        case Kind::Int:
            ret = intEqual(
                dynamic_cast<ast::IDataTypeInt *>(type1),
                dynamic_cast<ast::IDataTypeInt *>(type2));
            break;

        case Kind::UserDefined:
            ret = userDefinedEqual(
                dynamic_cast<ast::IDataTypeUserDefined *>(type1),
                dynamic_cast<ast::IDataTypeUserDefined *>(type2));
            break;

        case Kind::Ref:
            // A reference type is identified by what it refers to.
            ret = userDefinedEqual(
                dynamic_cast<ast::IDataTypeRef *>(type1)->getType(),
                dynamic_cast<ast::IDataTypeRef *>(type2)->getType());
            break;

        case Kind::Enum:
            // An inline enum type is identified by the enum it names. The
            // in-rangelist narrows the legal values but does not make a
            // different type.
            ret = userDefinedEqual(
                dynamic_cast<ast::IDataTypeEnum *>(type1)->getTid(),
                dynamic_cast<ast::IDataTypeEnum *>(type2)->getTid());
            break;

        case Kind::Bool:
        case Kind::Chandle:
        case Kind::PyObj:
        case Kind::String:
            // Nullary types: the kind is the whole identity.
            ret = Rel::Equal;
            break;

        case Kind::Unknown:
        default:
            // A data-type kind with no visitor here -- so nothing is known
            // about it, including whether these two instances match.
            DEBUG_ERROR("TaskCompareTypeRefs: no comparison for %s",
                typeid(*type1).name());
            ret = Rel::Unsure;
            break;
    }

    DEBUG_LEAVE("compare %d", (int)ret);
    return ret;
}

bool TaskCompareTypeRefs::isTypedefRef(ast::IDataType *t) {
    ast::IDataTypeUserDefined *ud = dynamic_cast<ast::IDataTypeUserDefined *>(t);
    if (!ud || !ud->getType_id() || !ud->getType_id()->getTarget()) {
        return false;
    }
    TaskResolveSymbolPathRef resolver(m_factory->getDebugMgr(), m_root);
    return (dynamic_cast<ast::ITypedefDeclaration *>(
        resolver.resolve(ud->getType_id()->getTarget())) != 0);
}

bool TaskCompareTypeRefs::isUnresolvedRef(ast::IDataType *t) {
    ast::IDataTypeUserDefined *ud = dynamic_cast<ast::IDataTypeUserDefined *>(t);
    if (!ud) {
        return false;
    }
    if (!ud->getType_id() || !ud->getType_id()->getTarget()) {
        return true;
    }
    TaskResolveSymbolPathRef resolver(m_factory->getDebugMgr(), m_root);
    return (resolver.resolve(ud->getType_id()->getTarget()) == 0);
}

TaskCompareTypeRefs::Kind TaskCompareTypeRefs::classify(ast::IDataType *t) {
    m_kind = Kind::Unknown;
    m_type = t;
    t->accept(m_this);
    return m_kind;
}

TaskCompareTypeRefs::Rel TaskCompareTypeRefs::intEqual(
        ast::IDataTypeInt       *t1,
        ast::IDataTypeInt       *t2) {
    // Signedness is part of the type: `bit[32]` and `int` are both 32 bits
    // wide and are not the same type.
    if (t1->getIs_signed() != t2->getIs_signed()) {
        DEBUG("Int signedness differs");
        return Rel::NotEqual;
    }
    return widthEqual(t1->getWidth(), t2->getWidth());
}

TaskCompareTypeRefs::Rel TaskCompareTypeRefs::widthEqual(
        ast::IExpr *w1, ast::IExpr *w2) {
    if (!w1 || !w2) {
        // A written width against a default one. `int` and `int[32]` are the
        // same type in PSS, but this class does not know the default width of
        // every integral kind, so it declines rather than guessing.
        //
        // Not reached in practice: the builder materializes the default, so
        // both sides carry an expression and `int` vs `int[32]` is decided
        // below, on the merits. §40's neutralization run established that, by
        // making this branch answer NotEqual and finding that no test noticed.
        // Kept as the guard it is, not as a description of anything that
        // happens.
        DEBUG("Int width (null) %d", (w1 == w2));
        return (w1 == w2)?Rel::Equal:Rel::Unsure;
    }

    IValUP v1(m_expr_eval.eval(w1));
    IValUP v2(m_expr_eval.eval(w2));

    // A width that will not fold -- a template parameter, or an expression
    // over one -- is not a width that differs.
    if (!v1 || !v2) {
        DEBUG("Int width did not fold -- unsure");
        return Rel::Unsure;
    }

    bool ret = m_comp_val.equal(v1.get(), v2.get());
    DEBUG("Int width %d", ret);
    return ret?Rel::Equal:Rel::NotEqual;
}

TaskCompareTypeRefs::Rel TaskCompareTypeRefs::userDefinedEqual(
        ast::IDataTypeUserDefined   *t1,
        ast::IDataTypeUserDefined   *t2) {
    if (!t1 || !t2) {
        return (t1 == t2)?Rel::Equal:Rel::NotEqual;
    }
    if (t1->getIs_global() != t2->getIs_global()) {
        // `::p::S` and `p::S` may well be the same type -- the second is the
        // first seen from a scope where `p` is reachable. Only resolution
        // settles it, and the resolved comparison below is reached whenever
        // resolution happened; this is the unresolved case.
        return Rel::Unsure;
    }

    ast::ITypeIdentifier *id1 = t1->getType_id();
    ast::ITypeIdentifier *id2 = t2->getType_id();
    if (!id1 || !id2) {
        return (id1 == id2)?Rel::Equal:Rel::NotEqual;
    }

    // Resolve both reference paths and compare the declarations they land on.
    // This is what makes `q::thing_s` seen through two different imports one
    // type, and what keeps two distinct specializations of one generic apart.
    if (id1->getTarget() && id2->getTarget()) {
        TaskResolveSymbolPathRef resolver(m_factory->getDebugMgr(), m_root);
        ast::IScopeChild *c1 = resolver.resolve(id1->getTarget());
        ast::IScopeChild *c2 = resolver.resolve(id2->getTarget());
        if (c1 && c2) {
            DEBUG("userDefined resolved %p vs %p", c1, c2);
            return (c1 == c2)?Rel::Equal:Rel::NotEqual;
        }
    }

    // Unresolved -- the normal state when a single file of a multi-file model
    // is checked on its own. Fall back to the written name so that dedup still
    // behaves, rather than minting a specialization per use site.
    return typeIdNameEqual(id1, id2);
}

TaskCompareTypeRefs::Rel TaskCompareTypeRefs::typeIdNameEqual(
        ast::ITypeIdentifier    *id1,
        ast::ITypeIdentifier    *id2) {
    // Every negative answer below is `Unsure`, not `NotEqual`: these two
    // references did not resolve, and an unresolved name is evidence about
    // what the user wrote rather than about what it denotes. `S` and `p::S`
    // are routinely one type. Specialization dedup reads `Unsure` as
    // "different", which is the behaviour this function has always had.
    if (id1->getElems().size() != id2->getElems().size()) {
        return Rel::Unsure;
    }
    for (uint32_t i=0; i<id1->getElems().size(); i++) {
        ast::IExprId *e1 = id1->getElems().at(i)->getId();
        ast::IExprId *e2 = id2->getElems().at(i)->getId();
        if (!e1 || !e2) {
            if (e1 != e2) {
                return Rel::Unsure;
            }
        } else if (e1->getId() != e2->getId()) {
            return Rel::Unsure;
        }

        // Two same-named references with different template arguments are
        // different types. Without resolution there is nothing to compare
        // them by, so decline rather than merging them.
        if (id1->getElems().at(i)->getParams() ||
            id2->getElems().at(i)->getParams()) {
            DEBUG("typeIdName: parameterized and unresolved -- unsure");
            return Rel::Unsure;
        }
    }
    return Rel::Equal;
}

void TaskCompareTypeRefs::visitDataType(ast::IDataType *i) {
    // The catch-all: reached only by a kind with no visitor below.
    DEBUG_ENTER("visitDataType (unhandled)");
    m_kind = Kind::Unknown;
    m_type = i;
    DEBUG_LEAVE("visitDataType");
}

void TaskCompareTypeRefs::visitDataTypeBool(ast::IDataTypeBool *i) {
    m_kind = Kind::Bool;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypeChandle(ast::IDataTypeChandle *i) {
    m_kind = Kind::Chandle;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypeEnum(ast::IDataTypeEnum *i) {
    m_kind = Kind::Enum;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypeInt(ast::IDataTypeInt *i) {
    m_kind = Kind::Int;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypePyObj(ast::IDataTypePyObj *i) {
    m_kind = Kind::PyObj;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypeRef(ast::IDataTypeRef *i) {
    m_kind = Kind::Ref;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypeString(ast::IDataTypeString *i) {
    m_kind = Kind::String;
    m_type = i;
}

void TaskCompareTypeRefs::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    m_kind = Kind::UserDefined;
    m_type = i;
}

dmgr::IDebug *TaskCompareTypeRefs::m_dbg = 0;

}
