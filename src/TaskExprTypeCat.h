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
#include <memory>
#include <string>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/ISymbolScope.h"
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

/**
 * The kind of a value's type, finer than TypeCatE: what the front-end checks
 * that need an operand's type (casts, operators, `in`, arguments) ask.
 */
enum class TypeKindE {
    Unknown,       ///< not known -- never report on this
    Void,          ///< the result of a void function
    Int,           ///< `int`, `bit[N]`, or a bit/part select of one
    Bool,
    Float,
    String,
    Enum,
    Chandle,
    Struct,        ///< a struct, or a flow or resource object (StructKind)
    Component,
    Action,
    Array,         ///< `array<T,N>`, or a fixed-size array declaration
    List,
    Map,
    Set,
    Null,          ///< the `null` literal
    Aggregate,     ///< an aggregate literal -- `{1,2,3}`, `{.a=1}`
    Other          ///< a type known to be none of the above (pyobj, monitor, ...)
};

/**
 * The type of an expression, as far as it is known (§2 step 0 of the
 * front-end checks: an arbitrary operand -- `a.b`, `a[i]`, `s[i..j]`, a
 * call's result -- not only a bare name).
 *
 * Built only from what the linker has bound: each path element's `decl`,
 * a declaration's written type, the specialized parameter list of a
 * collection. Where any step is not known the answer is Unknown, and a
 * check never reports on Unknown.
 */
struct ExprType {
    TypeKindE           kind = TypeKindE::Unknown;
    /** The type as declared, when the value has a declaration. */
    ast::IDataType      *dt = 0;
    /**
     * The named type: the struct, component, action or enum, or the
     * collection's specialization. Null for the built-in scalars.
     */
    ast::ISymbolScope   *scope = 0;
    /** Int: declared `int` (signed) rather than `bit`. */
    bool                is_signed = false;
    /** Array: the element count, when it is a constant; -1 otherwise. */
    int64_t             size = -1;
    /** Declared `ref` (a reference field or parameter). */
    bool                is_ref = false;

    ExprType() { }
    explicit ExprType(TypeKindE k) : kind(k) { }

    bool known() const { return kind != TypeKindE::Unknown; }

    /** A collection: array, list, map or set. */
    bool isCollection() const {
        return kind == TypeKindE::Array || kind == TypeKindE::List
            || kind == TypeKindE::Map || kind == TypeKindE::Set;
    }

    /** An aggregate data type (7.1): a struct or a collection. */
    bool isAggregate() const {
        return kind == TypeKindE::Struct || isCollection();
    }

    /** The broad category, as TaskExprTypeCat::expr() names it. */
    TypeCatE cat() const;

    /** For a diagnostic, and for the typer's tests: `int`, `struct p_s`, ... */
    std::string describe() const;
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

    /**
     * The type of `e`, which must already be resolved. Follows member
     * paths, subscripts, slices, bit selects and calls (the return type);
     * Unknown wherever a step is not bound.
     */
    ExprType typeOf(ast::IExpr *e);

    /** The type a declared data type names, through typedefs. */
    ExprType typeOfDataType(ast::IDataType *dt);

    /**
     * The type of a value of declaration `decl` -- a field, variable,
     * parameter, enum item, or a function (its return type).
     */
    ExprType typeOfDecl(ast::IScopeChild *decl);

    /** The type of `t[sub]`: an index, or a slice when `sub` is one. */
    ExprType subscript(const ExprType &t, ast::IExpr *sub);

    /** The element type a collection holds: its (map: value) parameter. */
    ExprType elemType(const ExprType &t);

    /** A name suitable for a diagnostic -- "int", "string", "null", ... */
    static const char *name(TypeCatE c);

    /** As `name`, but distinguishes `bit` from `int` when the type says so. */
    static const char *dataTypeName(ast::IDataType *dt, TypeCatE c);

private:
    /** typeOf() of a member path's elements, from `t` (the receiver's type). */
    ExprType typeOfElems(
        ExprType                                            t,
        const std::vector<ast::IExprMemberPathElemUP>       &elems,
        uint32_t                                            first,
        bool                                                has_recv);

    /**
     * One member path element, `recv` being the type it is applied to when
     * `has_recv` (a member, or a method of a literal), else a name.
     */
    ExprType typeOfElem(const ExprType &recv, ast::IExprMemberPathElem *elem, bool has_recv);

    /** The result type of a built-in method of `recv` with no declaration. */
    ExprType builtinMethod(const ExprType &recv, const std::string &name);

    /** A collection specialization's template parameter `idx`, as a type. */
    ExprType collectionParam(const ExprType &t, int32_t idx);

    /**
     * The type a template type parameter is bound to, when `path` -- the
     * reference that found it -- reaches it through a specialization.
     */
    ExprType boundTypeParam(ast::IScopeChild *param, ast::ISymbolRefPath *path);

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
