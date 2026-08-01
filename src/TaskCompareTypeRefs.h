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

    bool intEqual(ast::IDataTypeInt *t1, ast::IDataTypeInt *t2);

    /// Width may be absent (plain ``int``), and may be an expression this
    /// evaluator cannot fold. Absent-vs-absent is equal; anything that cannot
    /// be folded to a value is reported unequal.
    bool widthEqual(ast::IExpr *w1, ast::IExpr *w2);

    /// Two user-defined type references name the same type when their
    /// reference paths resolve to the same declaration.
    bool userDefinedEqual(
        ast::IDataTypeUserDefined   *t1,
        ast::IDataTypeUserDefined   *t2);

    /// Textual fallback for a type reference that never resolved -- the
    /// normal state when one file of a multi-file model is opened alone.
    bool typeIdNameEqual(ast::ITypeIdentifier *t1, ast::ITypeIdentifier *t2);

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
