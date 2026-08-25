/**
 * TaskExprTypeCat.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IDataType.h"
#include "pssp/ast/IExpr.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The broad *category* an expression or a declared type belongs to.
 *
 * This is deliberately not a type: PSS has no unified type-inference pass
 * (see known issue P3-X6c), and building one is a much larger job than the
 * checks that need it. A category is enough to catch the mistakes that
 * actually occur -- a string where a number belongs, an aggregate literal
 * where a scalar belongs -- without pretending to know widths, signedness,
 * or which struct a value came from.
 *
 * `Unknown` is the honest answer and the safe one: nothing is ever reported
 * when either side of a comparison is Unknown.
 */
enum class TypeCatE {
    Unknown,
    Int,
    Bool,
    Float,
    String,
    Enum,
    Chandle,
    Aggregate,     ///< a list/map/struct literal -- `{1,2,3}`, `{.a=1}`
    Null           ///< the `null` literal
};

class TaskExprTypeCat {
public:
    TaskExprTypeCat(ResolveContext *ctxt);

    virtual ~TaskExprTypeCat();

    /** Classify an expression. Returns Unknown whenever unsure. */
    TypeCatE expr(ast::IExpr *e);

    /** Classify a declared data type. User-defined types are Unknown. */
    TypeCatE dataType(ast::IDataType *dt);

    /**
     * True unless the two categories are definitively incompatible. Unknown
     * is compatible with everything.
     */
    static bool compatible(TypeCatE decl, TypeCatE actual);

    /** A name suitable for a diagnostic -- "int", "string", "null", ... */
    static const char *name(TypeCatE c);

    /** As `name`, but distinguishes `bit` from `int` when the type says so. */
    static const char *dataTypeName(ast::IDataType *dt, TypeCatE c);

private:
    /** The category of a ref-path that has already been resolved. */
    TypeCatE refPath(ast::IExpr *e);

    /** The category of the declaration a ref-path resolved to. */
    static TypeCatE declared(ast::IScopeChild *c, TaskExprTypeCat *self);

    /** The common category of the two arms of an arithmetic/conditional op. */
    static TypeCatE merge(TypeCatE a, TypeCatE b);

private:
    static dmgr::IDebug             *m_dbg;
    ResolveContext                  *m_ctxt;
    int32_t                         m_depth;

};

}
