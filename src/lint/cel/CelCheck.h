/*
 * CelCheck.h
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
 * The type checker (lint-core-plan.md C3.3; lint-rule-expressions.md §5).
 *
 * Every expression gets a static type or is an error: there is no `dyn`.
 * Types are inferred bottom-up against the environment: the declared
 * variables, the schema (node fields, structs, enum constants, class names
 * as type values) and the function registry. Type variables are unified as
 * cel-go unifies them, with two additions the profile needs:
 * - Node classes are ordered by derivation: where two node types meet (the
 *   arms of `?:`, list elements, the operands of `==`) the result is their
 *   nearest common base class, and `node` is the base of every class. A null
 *   fits any node or struct type (an unset field reads as null).
 * - `==`, `!=` and `in` accept an int against a double, since equality
 *   across them is in the profile (`1 == 1.0`).
 * - A node's fields are its class's. `type(x) == K` narrows `x` (a variable
 *   or a field path from one) to K on the right of `&&` and in the first
 *   result of `?:`, so after `children.filter(c, type(c) == Component)`,
 *   `c.children` is Component's. A field only derived classes have is an
 *   error naming them and the test to write.
 *
 * `define:` helpers are inlined at each use, as a `cel.bind` of each
 * parameter to a name no rule can write, so an argument is evaluated once
 * and the helper's body sees only its parameters and the declared variables.
 * The helpers must not call each other in a cycle. Comprehensions may nest
 * at most CheckOptions::maxNesting deep, counted in each body separately
 * (Q-E3): a helper's body starts again from 0.
 *
 * The output is a checked copy of the expression, with helpers inlined,
 * namespaced calls (`optional.of`) and enum constants resolved, each call's
 * overload chosen where the types decide it, and each node or struct field
 * resolved to its reflection entry. The evaluator runs it as it runs a parsed
 * expression, without the name lookups.
 */
#pragma once
#include <cstdint>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>
#include "CelAst.h"
#include "CelType.h"

namespace pssp {
namespace lint {
namespace cel {

struct CheckOptions {
    // Comprehensions (all, exists, exists_one, map, filter; not cel.bind)
    // nested in one body. lint-rule-expressions.md §5: `all(... exists(...))`
    // is fine, a third level is not.
    int             maxNesting = 2;
};

/** A `define:` helper: `name` (used as a name) or `name(p, ...)` (called). */
struct Define {
    std::string                 name;
    bool                        call = false;
    std::vector<std::string>    params;
    // Null when the body did not parse: the caller has reported that, and a
    // use of the helper fails without a further error.
    const Expr                  *body = nullptr;
    // Where the body's offsets point: an id of the caller's choosing, given
    // back in CheckError::source (C4.1: the YAML scalar).
    uint32_t                    source = 0;
};

struct CheckEnv {
    // Declared variables, outermost first: node, options, finding, then the
    // let: names in order. A later one shadows an earlier one.
    std::vector<std::pair<std::string, Type>>   vars;
    std::vector<Define>                         defines;
};

struct CheckError {
    // What a rule loader reports it as (C4.1): Profile, a part of CEL that
    // pss-rules leaves out (PSSP214); Limit, the nesting limit, a helper
    // cycle or a pattern the regex engine refuses (PSSP216); Type,
    // everything else (PSSP215).
    enum class Kind { Type, Limit, Profile };

    uint32_t        source = 0;
    uint32_t        offset = 0;
    std::string     message;
    Kind            kind = Kind::Type;
};

struct CheckResult {
    ExprUP                          expr;       // the checked expression; null on error
    Type                            type;
    std::vector<CheckError>         errors;
    // Every overload a call in the expression can dispatch to, inlined
    // helpers included, in registration order: what C4.1 computes a rule's
    // level and scope from.
    std::vector<const Overload *>   overloads;
};

class CelChecker {
public:
    CelChecker(const CheckEnv &env, const CheckOptions &opts=CheckOptions());

    /**
     * Checks `e`, whose offsets point into `source`. `expected` is the type
     * the place it is written requires (`where:` is bool, `report:` is
     * list(node)); `what` names the place in the message ("where").
     */
    CheckResult check(const Expr *e, uint32_t source,
        const Type *expected=nullptr, const char *what=nullptr) const;

    /**
     * Checks the helpers themselves, whether or not anything uses them: their
     * names and parameters, and that none reaches itself through calls
     * (reported with the path, "lo -> hi -> lo", at the call that closes it),
     * and the profile in their bodies. These are reported here only: check()
     * of an expression that uses such a helper fails (no expression, an
     * error type) without repeating them, so a caller must report these.
     * Type errors in a body depend on the arguments, and check() reports
     * them at each use.
     */
    std::vector<CheckError> checkDefines() const;

private:
    const CheckEnv                          &m_env;
    CheckOptions                            m_opts;
    std::vector<CheckError>                 m_define_errors;
    std::unordered_set<const Define *>      m_bad;
};

/**
 * Splits a `define:` key, `name` or `name(p, ...)`. Returns false, with
 * `err` set, when it is neither.
 */
bool parseDefineHead(const std::string &key, Define &out, std::string &err);

/** The type of a run-time value, for binding test variables: list(int). */
Type typeOfValue(const Value &v);

}
}
}
