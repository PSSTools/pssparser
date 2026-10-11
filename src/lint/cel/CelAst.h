/*
 * CelAst.h
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
 * The parsed form of a CEL expression (lint-core-plan.md C2.1).
 *
 * The shape is the canonical CEL AST that cel-go and cel-cpp use, not one of
 * our own: operators are calls to functions with the reserved names below
 * (`_+_`, `_&&_`, `@in`, ...) and macros are expanded into Comprehension
 * nodes at parse time. Keeping the canonical shape means the conformance
 * suite's parse expectations, and any other implementation used as an oracle,
 * describe the same tree.
 *
 * Every node records the byte range of the source text it was parsed from.
 * Offsets are into the expression string as the parser saw it; mapping them
 * back to a line and column in a rule file is the YAML layer's job (C2.2).
 */
#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace pssp {
namespace lint {
namespace regex { class Regex; }
namespace cel {

struct Const {
    enum class Kind { Null, Bool, Int, Uint, Double, String, Bytes };

    Kind            kind = Kind::Null;
    bool            b = false;
    int64_t         i = 0;
    uint64_t        u = 0;
    double          d = 0.0;
    std::string     s;          // String (UTF-8) and Bytes (raw)
};

enum class ExprKind {
    Const,
    Ident,
    Select,
    Call,
    List,
    Map,
    Struct,
    Comprehension
};

struct Expr;
using ExprUP = std::unique_ptr<Expr>;
struct Overload;

/**
 * One entry of a map literal or a message (struct) literal. For a map, `key`
 * is set; for a struct, `field` names the field and `key` is null.
 */
struct Entry {
    int32_t         id = 0;
    uint32_t        begin = 0;
    std::string     field;
    ExprUP          key;
    ExprUP          value;
    bool            optional = false;   // `?k: v`
};

struct Expr {
    int32_t         id = 0;
    uint32_t        begin = 0;
    uint32_t        end = 0;
    uint32_t        height = 1;         // longest path to a leaf, this node included
    ExprKind        kind = ExprKind::Const;

    Const           cval;               // Const

    // Ident: the name. Select: the field. Call: the function.
    // Struct: the (possibly qualified, possibly leading-dot) message name.
    // Comprehension: the macro it was expanded from ("all", "cel.bind").
    std::string     name;

    ExprUP          operand;            // Select operand; Call target (or null)
    bool            testOnly = false;   // Select produced by has()

    std::vector<ExprUP>     args;       // Call arguments; List elements
    std::vector<uint32_t>   optIndices; // List: indices of `?e` elements

    std::vector<Entry>      entries;    // Map, Struct

    // Comprehension
    std::string     iterVar;
    std::string     accuVar;
    ExprUP          iterRange;
    ExprUP          accuInit;
    ExprUP          loopCond;
    ExprUP          loopStep;
    ExprUP          result;

    // Set by the checker (C3.3), in the checked AST only.
    // Call: the one overload the operand types select; null when several
    // can apply, and the evaluator chooses by the run-time values.
    const Overload  *overload = nullptr;
    // Select (and has()) of a node or struct: the field, for readFieldAt().
    int32_t         field = -1;
    // matches() with a literal pattern: the pattern, compiled once, when the
    // expression was checked.
    std::shared_ptr<const regex::Regex>     regex;
};

/**
 * Reserved function names for operators, as in the CEL specification. Using
 * the spec's spelling lets error messages and the function registry speak
 * the same language as every other CEL implementation.
 */
namespace op {
constexpr const char *Conditional   = "_?_:_";
constexpr const char *LogicalAnd    = "_&&_";
constexpr const char *LogicalOr     = "_||_";
constexpr const char *LogicalNot    = "!_";
constexpr const char *Negate        = "-_";
constexpr const char *Equals        = "_==_";
constexpr const char *NotEquals     = "_!=_";
constexpr const char *Less          = "_<_";
constexpr const char *LessEquals    = "_<=_";
constexpr const char *Greater       = "_>_";
constexpr const char *GreaterEquals = "_>=_";
constexpr const char *Add           = "_+_";
constexpr const char *Subtract      = "_-_";
constexpr const char *Multiply      = "_*_";
constexpr const char *Divide        = "_/_";
constexpr const char *Modulo        = "_%_";
constexpr const char *In            = "@in";
constexpr const char *Index         = "_[_]";
constexpr const char *OptIndex      = "_[?_]";
constexpr const char *OptSelect     = "_?._";
// Internal to macro expansion: false only for `false`; errors read as true.
constexpr const char *NotStrictlyFalse = "@not_strictly_false";
}

/** Accumulator name used by the comprehension macros (cel-go's spelling). */
constexpr const char *AccuVar = "@result";

}
}
}
