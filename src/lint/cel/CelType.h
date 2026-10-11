/*
 * CelType.h
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
 * CEL types (lint-core-plan.md C3.2, C3.3): as function signatures in the
 * registry write them, and as the checker infers them.
 *
 * Written form, as in the CEL spec: bool, int, double, string, null_type,
 * type, list(T), map(K, V), optional(T), node (any AST node), a schema class
 * (ExprBin: that class or one deriving from it), a schema struct (Location),
 * and single upper-case letters for type parameters (A, B, K, V). The checker
 * also makes type variables of its own, which no written form can name.
 */
#pragma once
#include <string>
#include <vector>
#include "CelValue.h"

namespace pssp {
namespace lint {
namespace cel {

struct Type {
    enum class Kind {
        Null, Bool, Int, Double, String, List, Map, Optional, TypeType, Node, Struct, Param,
        // The checker's: an expression already reported as wrong. It fits
        // anywhere, so one mistake is reported once.
        Error
    };

    Kind                kind = Kind::Null;
    // Param: its name. TypeType: the name of the type it denotes, when known
    // (the type of the expression `ExprBinOp` is the type named ExprBinOp).
    // Int: the schema enum an enum or flags field, or an enum constant, is a
    // value of ("FieldAttr"), else empty. Still an int everywhere; the
    // checker reads it to keep flags words out of arithmetic (C6.8).
    std::string         param;
    uint16_t            cls = 0;    // Node: the schema class, 0 for any; Struct: the struct
    std::vector<Type>   args;       // List: [elem]; Map: [key, value]; Optional: [value]

    Type() = default;
    explicit Type(Kind k) : kind(k) { }
    static Type list(Type elem) { Type t(Kind::List); t.args.push_back(std::move(elem)); return t; }
    static Type map(Type k, Type v) {
        Type t(Kind::Map); t.args.push_back(std::move(k)); t.args.push_back(std::move(v)); return t;
    }
    static Type optional(Type v) {
        Type t(Kind::Optional); t.args.push_back(std::move(v)); return t;
    }
    static Type node(uint16_t cls) { Type t(Kind::Node); t.cls = cls; return t; }
    static Type structType(uint16_t st) { Type t(Kind::Struct); t.cls = st; return t; }
    static Type typeOf(std::string name) { Type t(Kind::TypeType); t.param = std::move(name); return t; }
    static Type var(std::string name) { Type t(Kind::Param); t.param = std::move(name); return t; }

    /** Parses the written form; throws std::invalid_argument on a bad one. */
    static Type parse(const std::string &text);

    /** The written form; a type variable of the checker's own is `?`. */
    std::string str() const;

    /**
     * Whether a run-time value can have this type. Shallow: a list matches
     * list(T) whatever its elements are, since the checker has already
     * established element types; a parameter matches anything.
     */
    bool admits(const Value &v) const;
};

}
}
}
