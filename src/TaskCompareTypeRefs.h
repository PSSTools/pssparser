/**
 * TaskCompareTypeRefs.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IFactory.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "TaskCompareVal.h"

namespace pssp {




/**
 * Decides whether two *generic type* template arguments name the same type.
 *
 * This is the equality used by ``TaskGetSpecializedTemplateType::find`` to
 * decide whether a requested specialization already exists, so both failure
 * directions have teeth:
 *
 * - saying *unequal* for two arguments that are the same type mints a fresh
 *   specialization per use site, each of which runs a full ``TaskResolveRefs``;
 * - saying *equal* for two that are not silently gives one type's bindings to
 *   uses of the other.
 *
 * Dispatch is by node kind, so **every** ``IDataType`` kind must be handled.
 * An unhandled kind lands in ``visitDataType``, which records ``Kind::Unknown``
 * -- and two Unknowns compare unequal rather than equal, because under-merging
 * costs time while over-merging is wrong.
 */
class TaskCompareTypeRefs : public virtual ast::VisitorBase {
public:
    TaskCompareTypeRefs(
        IFactory                *factory,
        ast::ISymbolScope       *root);

    virtual ~TaskCompareTypeRefs();

    /**
     * The three answers this comparison can give.
     *
     * ``Unsure`` was folded into ``NotEqual`` until it had a second caller.
     * For specialization dedup that is the right collapse -- see the class
     * comment -- but it is exactly wrong for a *diagnostic*, where saying
     * "these two declarations disagree" about types this class merely could
     * not compare rejects valid code.  The two callers want opposite
     * defaults, so the uncertainty is now reported rather than resolved here.
     *
     * Sources of ``Unsure``: a data-type kind with no visitor, an integer
     * width that will not fold to a constant, an unresolved user-defined
     * reference whose spellings differ, and any reference that resolves to a
     * ``typedef`` (an alias is the same type as what it aliases, which
     * nothing in this parser currently expands).
     */
    enum class Rel {
        Equal,
        NotEqual,
        Unsure
    };

    /**
     * Decide whether ``tref1`` and ``tref2`` name the same type.
     *
     * Callers that must not act on doubt should test against a specific
     * ``Rel``; ``equal()`` below is the "treat doubt as different" reading.
     */
    Rel compare(
        ast::IDataType          *tref1,
        ast::IDataType          *tref2);

    /**
     * ``compare() == Rel::Equal``: doubt reads as different.
     *
     * This is what specialization dedup wants -- an unnecessary
     * specialization costs time, where merging two distinct types is wrong.
     */
    bool equal(
        ast::IDataType          *tref1,
        ast::IDataType          *tref2);

    virtual void visitDataType(ast::IDataType *i) override;

    virtual void visitDataTypeBool(ast::IDataTypeBool *i) override;

    virtual void visitDataTypeChandle(ast::IDataTypeChandle *i) override;

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) override;

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) override;

    virtual void visitDataTypePyObj(ast::IDataTypePyObj *i) override;

    virtual void visitDataTypeRef(ast::IDataTypeRef *i) override;

    virtual void visitDataTypeString(ast::IDataTypeString *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;


private:

    /// The closed set of ``IDataType`` node kinds, as classified by the
    /// visitors above. ``Unknown`` means a kind was added to the AST without
    /// a visitor here.
    enum class Kind {
        Unknown,
        Bool,
        Chandle,
        Enum,
        Int,
        PyObj,
        Ref,
        String,
        UserDefined
    };

    /// Classify `t`, returning its kind and leaving the node in `m_type`.
    Kind classify(ast::IDataType *t);

    Rel intEqual(ast::IDataTypeInt *t1, ast::IDataTypeInt *t2);

    /// Width may be absent (plain ``int``), and may be an expression this
    /// evaluator cannot fold. Absent-vs-absent is equal; a width that will
    /// not fold -- a template parameter, say -- is ``Unsure``.
    Rel widthEqual(ast::IExpr *w1, ast::IExpr *w2);

    /// Two user-defined type references name the same type when their
    /// reference paths resolve to the same declaration.
    Rel userDefinedEqual(
        ast::IDataTypeUserDefined   *t1,
        ast::IDataTypeUserDefined   *t2);

    /// Textual fallback for a type reference that never resolved -- the
    /// normal state when one file of a multi-file model is opened alone.
    /// Matching spellings are taken as the same type; differing ones are
    /// ``Unsure``, since an unresolved name says nothing about what it names.
    Rel typeIdNameEqual(ast::ITypeIdentifier *t1, ast::ITypeIdentifier *t2);

    /// True if `t` is a reference that resolves to a ``typedef``.  An alias
    /// and its underlying type are one type, and nothing here expands one, so
    /// any comparison involving an alias is ``Unsure`` rather than unequal.
    bool isTypedefRef(ast::IDataType *t);

    /// True if `t` is a user-defined reference that names nothing this run
    /// could find.  Consulted only where the alternative would be to call it
    /// *different* from something; see compare().
    bool isUnresolvedRef(ast::IDataType *t);

private:
    static dmgr::IDebug             *m_dbg;
    IFactory                        *m_factory;
    ast::ISymbolScope               *m_root;
    TaskEvalExpr                    m_expr_eval;
    TaskCompareVal                  m_comp_val;
    Kind                            m_kind;
    ast::IDataType                  *m_type;

};

}
