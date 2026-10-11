/*
 * CelFunctions.h
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
 * The function registry (lint-core-plan.md C3.2): every operator, function
 * and macro a rule can use, one entry per overload.
 *
 * Each entry carries its signature, implementation, analysis level, scope,
 * cost class and doc string. That one table is what the evaluator dispatches
 * on, what the checker (C3.3) types calls against, what level/scope
 * inference (C4.1) reads, and what docs/lint-functions.rst is generated from
 * (scripts/gen_lint_functions.py), so none of them can disagree.
 *
 * Overload ids follow cel-go's where cel-go has the overload ("size_string",
 * "add_int64", "less_double_int64"), so traces and messages can be compared
 * with the reference implementation.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "CelType.h"
#include "CelValue.h"

namespace pssp {
namespace lint {
namespace regex { class Regex; }
namespace cel {

/** Analysis level (lint-rule-expressions.md §3): what a function needs. */
enum class Level : uint8_t {
    L0,     // syntax only
    L1,     // symbols (resolution)
    L2,     // types
    L3,     // constant values
    L4      // whole model
};

/** Whether a rule calling the function must re-run on any change (model). */
enum class Scope : uint8_t { File, Model };

/**
 * What a call costs, beyond the one step every evaluated node costs.
 * Linear: one step per list or map element, and per 64 string bytes, in the
 * operands; charged by the evaluator, so an implementation cannot forget.
 * Custom: the implementation reports its own cost (CallArgs::steps).
 */
enum class Cost : uint8_t { Constant, Linear, Custom };

enum class FnKind : uint8_t { Operator, Function, Macro };

/**
 * What the evaluator's caller supplies to the functions that need more than
 * their operands: the PSS library (lib/PssLib.h) derives its run context
 * from this. The CEL layer only passes it through; a call made without one
 * (CelEval used on its own) gets null, and such a function returns an error.
 */
class Host {
public:
    virtual ~Host();
};

struct CallArgs {
    const Value     *target = nullptr;      // the receiver, for a receiver-style call
    const Value     *args = nullptr;
    size_t          n = 0;
    uint64_t        steps = 0;              // Cost::Custom: the implementation's charge
    // matches(): the pattern, when the checker compiled it (a literal)
    const regex::Regex  *regex = nullptr;
    const Host          *host = nullptr;        // EvalOptions::host

    const Value &operator[](size_t i) const { return args[i]; }
};

/** A strict implementation: every operand is already evaluated, none an error. */
using Impl = Value (*)(CallArgs &c);

struct Overload {
    std::string         id;
    std::string         function;           // "size", "_+_", "optional.of"
    FnKind              kind = FnKind::Function;
    bool                receiver = false;
    std::vector<Type>   params;             // the receiver first, if any; empty for a macro
    Type                result;
    // Null for the non-strict operators, lazy functions and macros, which the
    // parser or the evaluator implements itself.
    Impl                impl = nullptr;
    Level               level = Level::L0;
    Scope               scope = Scope::File;
    Cost                cost = Cost::Constant;
    std::string         group;
    // "cel": CEL's standard library; "pss": the PSS library (lib/PssLib.cpp).
    std::string         library;
    std::string         doc;
    std::string         display;            // "string.contains(string) -> bool"
    // False: accepted by the evaluator (the conformance suite uses it) but
    // outside the pss-rules profile, so the checker refuses it and the
    // generated reference leaves it out.
    bool                inProfile = true;
    // When >= 0, this operand (the receiver counts as 0) is a `type` that
    // must name a node class (`n.isa(Action)`), which the checker verifies.
    int8_t              classArg = -1;
    // With classArg: the result is a node of that class, not `result`'s
    // (`enclosing(n, Action)` is an Action).
    bool                resultIsClass = false;
    // A node or record operand may be null (an unset field, a `resolves_to`
    // or `file_of` that found nothing), which the function takes as "none":
    // is_owned(null) is false, decls_in(null) is []. Without it, a null
    // operand is a "no matching overload" error.
    bool                nullable = false;

    /** Whether run-time operands fit the parameter types. */
    bool admits(const Value *target, const Value *args, size_t n) const;
};

class FunctionRegistry {
public:
    /** The registry, built once on first use. */
    static const FunctionRegistry &get();

    /** Every overload, in registration (documentation) order. */
    const std::vector<std::unique_ptr<Overload>> &all() const { return m_all; }

    /** The overloads of a function name, or null if the name is unknown. */
    const std::vector<const Overload *> *find(const std::string &function) const;

    bool hasFunction(const std::string &function) const { return find(function) != nullptr; }

    /**
     * The first overload of `function` whose receiver form, arity and
     * parameter types admit the operands; null if none.
     */
    const Overload *resolve(const std::string &function, const Value *target,
        const Value *args, size_t n) const;

    //* Registration (CelStdLib.cpp, lib/PssLib.cpp). The library, group,
    //* level and scope set here apply to the entries added after them.
    void group(const std::string &name) { m_group = name; }
    void library(const std::string &name) { m_library = name; }
    void level(Level l, Scope s) { m_level = l; m_scope = s; }

    /**
     * Adds an overload. `sig` is "name(T, ...) -> R", "T.name(T, ...) -> R"
     * for a receiver-style function, or "ns.name(...) -> R" for a namespaced
     * global such as optional.of. Throws std::invalid_argument on a bad one.
     */
    Overload &add(const char *id, const char *sig, Impl impl, Cost cost, const char *doc);

    /** A macro: documented and listed, expanded by the parser. */
    Overload &macro(const char *id, const char *function, const char *display, const char *doc);

private:
    FunctionRegistry();

private:
    std::vector<std::unique_ptr<Overload>>                              m_all;
    std::unordered_map<std::string, std::vector<const Overload *>>      m_by_name;
    std::string                                                         m_group;
    std::string                                                         m_library = "cel";
    Level                                                               m_level = Level::L0;
    Scope                                                               m_scope = Scope::File;
};

/** Registers the standard library (CelStdLib.cpp). */
void registerStdLib(FunctionRegistry &r);

/** Registers the PSS function library (lib/PssLib.cpp; lint-core-plan.md C6). */
void registerPssLib(FunctionRegistry &r);

/** A double as string(double) gives it: Go's shortest 'g' form ("1e+06"). */
std::string formatDouble(double d);

const char *levelName(Level l);
const char *scopeName(Scope s);
const char *costName(Cost c);

/** "no matching overload for 'fn' applied to (int, string)" */
Value noOverload(const std::string &fn, const Value *target, const Value *args, size_t n);

}
}
}
