/*
 * CelEval.h
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
 * Tree-walking evaluator (lint-core-plan.md C3.1), over every value kind in
 * CelValue.h. Until the checker lands (C3.3) it runs the parsed AST and
 * resolves names (variables, types, enum constants, node fields) as it goes;
 * from C3.3 on, the checked AST arrives with those already resolved.
 *
 * Semantics are CEL's: errors are values; `&&`, `||` and `?:` absorb them
 * where the other operand decides; `1 == 1.0`; int64 overflow is an error;
 * comprehensions stop as soon as their condition is false. Optionals chain:
 * selecting or indexing an optional applies to its value and stays optional
 * (`optional.of(m).a` is `m.?a`). Nodes compare by identity.
 *
 * Calls dispatch through the function registry (CelFunctions.h, C3.2): the
 * first overload whose signature admits the evaluated operands. Only the
 * non-strict operators (`&&`, `||`, `?:`, `.?`) and the lazy `or`/`orValue`
 * are implemented here.
 *
 * A checked expression (CelCheck.h, C3.3) runs the same way, but a call the
 * checker resolved goes straight to its overload, and a field it resolved is
 * read by index rather than by name.
 */
#pragma once
#include <cstdint>
#include <string>
#include <utility>
#include <vector>
#include "CelAst.h"
#include "CelValue.h"

namespace pssp {
namespace lint {
namespace cel {

struct Overload;
class Host;

struct EvalOptions {
    // Every node evaluated and every comprehension iteration costs one step
    // (lint-rule-expressions.md §5). Q-E5: the real number comes from C8.
    uint64_t        maxSteps = 1000000;
    // Passed to every function call (CallArgs::host): the lint run, for the
    // PSS library's functions. Not owned.
    const Host      *host = nullptr;
};

class CelEval {
public:
    explicit CelEval(const EvalOptions &opts=EvalOptions());

    /**
     * Evaluates `e`. An error is an ordinary result (Value::Kind::Error), as
     * in CEL; a budget overrun is reported the same way, with
     * budgetExceeded() set.
     */
    Value eval(const Expr *e);

    /** Evaluates `e` with `vars` in scope (name, value). */
    Value eval(const Expr *e, const std::vector<std::pair<std::string, Value>> &vars);

    /**
     * Records every overload a call dispatches to, in call order (tests use
     * it to check that a case exercises the overload it is written for).
     */
    void setTrace(std::vector<const Overload *> *trace) { m_trace = trace; }

    uint64_t steps() const { return m_steps; }
    bool budgetExceeded() const { return m_budget_exceeded; }

private:
    Value evalExpr(const Expr *e);
    Value evalCall(const Expr *e);
    Value evalComprehension(const Expr *e);
    Value evalSelect(const Expr *e);
    Value evalIdent(const Expr *e);
    Value selectField(const Value &op, const std::string &name);
    Value optSelect(const Value &op, const std::string &name);
    Value hasSelect(const Value &op, const std::string &name);
    Value evalList(const Expr *e);
    Value evalMap(const Expr *e);

    Value evalAnd(const Expr *e);
    Value evalOr(const Expr *e);
    Value evalConditional(const Expr *e);

    Value callFunction(const std::string &fn, const Value *target,
        const std::vector<Value> &args, const Expr *call);
    Value callOverload(const Overload *o, const Value *target, const std::vector<Value> &args,
        const Expr *call);

    const Value *lookup(const std::string &name) const;
    void step();
    void charge(uint64_t steps);

private:
    EvalOptions                                 m_opts;
    uint64_t                                    m_steps;
    bool                                        m_budget_exceeded;
    std::vector<std::pair<std::string, Value>>  m_vars;
    std::vector<const Overload *>               *m_trace = nullptr;
};

/**
 * CEL equality, with heterogeneous numeric comparison: 1 == 1.0 is true, and
 * values of different non-numeric kinds are unequal rather than an error.
 */
bool celEquals(const Value &a, const Value &b);

}
}
}
