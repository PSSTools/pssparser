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
    DEBUG_ENTER("equal");

    // A parameter with nothing bound has no type. Two such are equal; one
    // bound and one not are not.
    if (!tref1 || !tref2) {
        DEBUG_LEAVE("equal (null) %d", (tref1 == tref2));
        return (tref1 == tref2);
    }

    Kind kind1 = classify(tref1);
    ast::IDataType *type1 = m_type;
    Kind kind2 = classify(tref2);
    ast::IDataType *type2 = m_type;

    if (kind1 != kind2) {
        DEBUG_LEAVE("equal (kind %d vs %d) 0", (int)kind1, (int)kind2);
        return false;
    }

    bool ret = false;
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
            ret = true;
            break;

        case Kind::Unknown:
        default:
            // A data-type kind with no visitor here. Report unequal -- that
            // costs a redundant specialization, where guessing equal would
            // hand one type's bindings to uses of another.
            DEBUG_ERROR("TaskCompareTypeRefs: no comparison for %s",
                typeid(*type1).name());
            ret = false;
            break;
    }

    DEBUG_LEAVE("equal %d", ret);
    return ret;
}

TaskCompareTypeRefs::Kind TaskCompareTypeRefs::classify(ast::IDataType *t) {
    m_kind = Kind::Unknown;
    m_type = t;
    t->accept(m_this);
    return m_kind;
}

bool TaskCompareTypeRefs::intEqual(
        ast::IDataTypeInt       *t1,
        ast::IDataTypeInt       *t2) {
    // Signedness is part of the type: `bit[32]` and `int` are both 32 bits
    // wide and are not the same type.
    if (t1->getIs_signed() != t2->getIs_signed()) {
        DEBUG("Int signedness differs");
        return false;
    }
    return widthEqual(t1->getWidth(), t2->getWidth());
}

bool TaskCompareTypeRefs::widthEqual(ast::IExpr *w1, ast::IExpr *w2) {
    if (!w1 || !w2) {
        DEBUG("Int width (null) %d", (w1 == w2));
        return (w1 == w2);
    }

    IValUP v1(m_expr_eval.eval(w1));
    IValUP v2(m_expr_eval.eval(w2));
    bool ret = m_comp_val.equal(v1.get(), v2.get());
    DEBUG("Int width %d", ret);
    return ret;
}

bool TaskCompareTypeRefs::userDefinedEqual(
        ast::IDataTypeUserDefined   *t1,
        ast::IDataTypeUserDefined   *t2) {
    if (!t1 || !t2) {
        return (t1 == t2);
    }
    if (t1->getIs_global() != t2->getIs_global()) {
        return false;
    }

    ast::ITypeIdentifier *id1 = t1->getType_id();
    ast::ITypeIdentifier *id2 = t2->getType_id();
    if (!id1 || !id2) {
        return (id1 == id2);
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
            return (c1 == c2);
        }
    }

    // Unresolved -- the normal state when a single file of a multi-file model
    // is checked on its own. Fall back to the written name so that dedup still
    // behaves, rather than minting a specialization per use site.
    return typeIdNameEqual(id1, id2);
}

bool TaskCompareTypeRefs::typeIdNameEqual(
        ast::ITypeIdentifier    *id1,
        ast::ITypeIdentifier    *id2) {
    if (id1->getElems().size() != id2->getElems().size()) {
        return false;
    }
    for (uint32_t i=0; i<id1->getElems().size(); i++) {
        ast::IExprId *e1 = id1->getElems().at(i)->getId();
        ast::IExprId *e2 = id2->getElems().at(i)->getId();
        if (!e1 || !e2) {
            if (e1 != e2) {
                return false;
            }
        } else if (e1->getId() != e2->getId()) {
            return false;
        }

        // Two same-named references with different template arguments are
        // different types. Without resolution there is nothing to compare
        // them by, so report unequal rather than merging them.
        if (id1->getElems().at(i)->getParams() ||
            id2->getElems().at(i)->getParams()) {
            DEBUG("typeIdName: parameterized and unresolved -- unequal");
            return false;
        }
    }
    return true;
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
