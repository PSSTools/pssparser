/*
 * CelEval.cpp
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
 */
#include <cmath>
#include "CelEval.h"
#include "CelFunctions.h"
#include "CelNode.h"
#include "CelOps.h"

namespace pssp {
namespace lint {
namespace cel {

const char *kindName(Value::Kind k) {
    switch (k) {
        case Value::Kind::Null: return "null_type";
        case Value::Kind::Bool: return "bool";
        case Value::Kind::Int: return "int";
        case Value::Kind::Double: return "double";
        case Value::Kind::String: return "string";
        case Value::Kind::List: return "list";
        case Value::Kind::Map: return "map";
        case Value::Kind::Optional: return "optional_type";
        case Value::Kind::Node: return "node";
        case Value::Kind::Struct: return "struct";
        case Value::Kind::Type: return "type";
        case Value::Kind::Error: return "error";
    }
    return "?";
}

std::string typeName(const Value &v) {
    switch (v.kind) {
        case Value::Kind::Node: return nodeClassName(v.node.kind);
        case Value::Kind::Struct: return structName(static_cast<uint16_t>(v.i));
        default: return kindName(v.kind);
    }
}

namespace {

struct BudgetExceeded { };

// The names that are types when no variable has them: CEL's own (less the
// kinds the profile excludes), then the schema's classes, structs and enums.
bool builtinType(const std::string &name) {
    static const char *names[] = {
        "bool", "int", "double", "string", "list", "map", "null_type", "type", "optional_type"};
    for (const char *n : names) {
        if (name == n) {
            return true;
        }
    }
    return false;
}

}

bool celEquals(const Value &a, const Value &b) {
    if (a.isNumeric() && b.isNumeric()) {
        return cmpNumeric(a, b) == 0;
    }
    if (a.kind != b.kind) {
        return false;
    }
    switch (a.kind) {
        case Value::Kind::Null: return true;
        case Value::Kind::Bool: return a.b == b.b;
        case Value::Kind::String: return a.s == b.s;
        case Value::Kind::List: {
            if (a.list->size() != b.list->size()) {
                return false;
            }
            for (size_t i=0; i<a.list->size(); i++) {
                if (!celEquals((*a.list)[i], (*b.list)[i])) {
                    return false;
                }
            }
            return true;
        }
        case Value::Kind::Optional:
            if (!a.opt || !b.opt) {
                return !a.opt && !b.opt;
            }
            return celEquals(*a.opt, *b.opt);
        case Value::Kind::Node:
            // Identity: the same node, not an equal-looking one.
            return a.node.ptr == b.node.ptr;
        case Value::Kind::Struct:
            return structEquals(a, b);
        case Value::Kind::Type:
            return a.s == b.s;
        case Value::Kind::Map: {
            if (a.map->size() != b.map->size()) {
                return false;
            }
            for (const auto &kv : *a.map) {
                const Value *bv = mapFind(*b.map, kv.first);
                if (!bv || !celEquals(kv.second, *bv)) {
                    return false;
                }
            }
            return true;
        }
        default:
            return false;
    }
}

CelEval::CelEval(const EvalOptions &opts) :
    m_opts(opts), m_steps(0), m_budget_exceeded(false) {

}

Value CelEval::eval(const Expr *e) {
    return eval(e, {});
}

Value CelEval::eval(const Expr *e, const std::vector<std::pair<std::string, Value>> &vars) {
    m_steps = 0;
    m_budget_exceeded = false;
    m_vars = vars;
    try {
        return evalExpr(e);
    } catch (const BudgetExceeded &) {
        m_budget_exceeded = true;
        return Value::error("evaluation budget of " + std::to_string(m_opts.maxSteps)
            + " steps exceeded");
    }
}

void CelEval::step() {
    if (++m_steps > m_opts.maxSteps) {
        throw BudgetExceeded();
    }
}

void CelEval::charge(uint64_t steps) {
    m_steps += steps;
    if (m_steps > m_opts.maxSteps) {
        throw BudgetExceeded();
    }
}

const Value *CelEval::lookup(const std::string &name) const {
    for (auto it=m_vars.rbegin(); it!=m_vars.rend(); it++) {
        if (it->first == name) {
            return &it->second;
        }
    }
    return nullptr;
}

Value CelEval::evalExpr(const Expr *e) {
    step();
    switch (e->kind) {
        case ExprKind::Const: {
            const Const &c = e->cval;
            switch (c.kind) {
                case Const::Kind::Null: return Value::null();
                case Const::Kind::Bool: return Value::boolean(c.b);
                case Const::Kind::Int: return Value::integer(c.i);
                case Const::Kind::Double: return Value::dbl(c.d);
                case Const::Kind::String: return Value::string(c.s);
                case Const::Kind::Uint:
                case Const::Kind::Bytes:
                    return Value::error("excluded by the pss-rules profile");
            }
            return Value::error("unknown constant");
        }
        case ExprKind::Ident:
            return evalIdent(e);
        case ExprKind::Select:
            return evalSelect(e);
        case ExprKind::Call:
            return evalCall(e);
        case ExprKind::List:
            return evalList(e);
        case ExprKind::Map:
            return evalMap(e);
        case ExprKind::Struct:
            return Value::error("message construction is not supported in pss-rules");
        case ExprKind::Comprehension:
            return evalComprehension(e);
    }
    return Value::error("unknown expression kind");
}

Value CelEval::evalIdent(const Expr *e) {
    if (const Value *v = lookup(e->name)) {
        return *v;
    }
    Value t;
    if (builtinType(e->name)) {
        return Value::type(e->name);
    } else if (lookupType(e->name, t)) {
        return t;
    }
    return Value::error("undeclared reference to '" + e->name + "'");
}

Value CelEval::evalSelect(const Expr *e) {
    Value op = evalExpr(e->operand.get());
    if (op.isError()) {
        return op;
    }
    // Resolved by the checker: by index.
    if (e->field >= 0) {
        if (e->testOnly) {
            bool isSet;
            if (hasFieldAt(op, e->field, isSet)) {
                return Value::boolean(isSet);
            }
        } else {
            Value out;
            uint64_t elems = 0;
            if (readFieldAt(op, e->field, out, elems)) {
                charge(elems);
                return out;
            }
        }
    }
    if (e->testOnly) {
        return hasSelect(op, e->name);
    }
    return selectField(op, e->name);
}

// `op.name`. On an optional, the selection applies to its value and stays
// optional: `optional.of(m).a` is `m.?a`, and none stays none.
Value CelEval::selectField(const Value &op, const std::string &name) {
    using K = Value::Kind;
    switch (op.kind) {
        case K::Optional:
            return op.opt ? optSelect(*op.opt, name) : op;
        case K::Map: {
            const Value *v = mapFind(*op.map, Value::string(name));
            if (!v) {
                return Value::error("no such key: '" + name + "'");
            }
            return *v;
        }
        case K::Node:
        case K::Struct: {
            Value out;
            uint64_t elems = 0;
            if (!readField(op, name, out, elems)) {
                return Value::error("type '" + typeName(op) + "' has no field '" + name + "'");
            }
            charge(elems);
            return out;
        }
        case K::Type: {
            int64_t v;
            if (enumConstant(op.s, name, v)) {
                return Value::integer(v);
            }
            return Value::error("type '" + op.s + "' has no member '" + name + "'");
        }
        case K::Null:
            // D-C6: navigating through an unset node field is an error, not a
            // default instance, so a wrong rule cannot silently never fire.
            if (!op.s.empty()) {
                return Value::error("field '" + name + "' of unset '" + op.s + "'");
            }
            return Value::error("no such key: '" + name + "' (the value is null)");
        default:
            return Value::error("a value of type '" + typeName(op) + "' has no field '"
                + name + "'");
    }
}

// `op.?name`: optional.of(op.name) if the field or key is present, else none.
Value CelEval::optSelect(const Value &op, const std::string &name) {
    using K = Value::Kind;
    switch (op.kind) {
        case K::Optional:
            return op.opt ? optSelect(*op.opt, name) : op;
        case K::Map: {
            const Value *v = mapFind(*op.map, Value::string(name));
            return v ? Value::some(*v) : Value::none();
        }
        case K::Node:
        case K::Struct: {
            bool isSet = false;
            if (!hasField(op, name, isSet)) {
                return Value::error("type '" + typeName(op) + "' has no field '" + name + "'");
            }
            if (!isSet) {
                return Value::none();
            }
            Value out;
            uint64_t elems = 0;
            readField(op, name, out, elems);
            charge(elems);
            return out.isError() ? out : Value::some(std::move(out));
        }
        default:
            return selectField(op, name);
    }
}

// has(op.name): presence, never the field's value.
Value CelEval::hasSelect(const Value &op, const std::string &name) {
    using K = Value::Kind;
    switch (op.kind) {
        case K::Optional:
            return op.opt ? hasSelect(*op.opt, name) : Value::boolean(false);
        case K::Map:
            return Value::boolean(mapFind(*op.map, Value::string(name)) != nullptr);
        case K::Node:
        case K::Struct: {
            bool isSet = false;
            if (!hasField(op, name, isSet)) {
                return Value::error("type '" + typeName(op) + "' has no field '" + name + "'");
            }
            return Value::boolean(isSet);
        }
        default: {
            Value v = selectField(op, name);
            return v.isError() ? v : Value::boolean(true);
        }
    }
}

Value CelEval::evalList(const Expr *e) {
    ValueList elems;
    elems.reserve(e->args.size());
    size_t next_opt = 0;
    for (size_t i=0; i<e->args.size(); i++) {
        Value v = evalExpr(e->args[i].get());
        if (v.isError()) {
            return v;
        }
        // `[?e]`: e is an optional; none drops the element.
        if (next_opt < e->optIndices.size() && e->optIndices[next_opt] == i) {
            next_opt++;
            if (v.kind != Value::Kind::Optional) {
                return Value::error("an optional list element needs an optional value, not '"
                    + typeName(v) + "'");
            }
            if (!v.opt) {
                continue;
            }
            elems.push_back(*v.opt);
            continue;
        }
        elems.push_back(std::move(v));
    }
    return Value::mkList(std::move(elems));
}

Value CelEval::evalMap(const Expr *e) {
    ValueMap entries;
    for (const Entry &ent : e->entries) {
        Value k = evalExpr(ent.key.get());
        if (k.isError()) {
            return k;
        }
        Value v = evalExpr(ent.value.get());
        if (v.isError()) {
            return v;
        }
        // `{?k: v}`: v is an optional; none drops the entry.
        if (ent.optional) {
            if (v.kind != Value::Kind::Optional) {
                return Value::error("an optional map entry needs an optional value, not '"
                    + typeName(v) + "'");
            }
            if (!v.opt) {
                continue;
            }
            Value inner = *v.opt;
            v = std::move(inner);
        }
        if (!isValidMapKey(k)) {
            return Value::error("unsupported map key type '" + typeName(k) + "'");
        }
        if (mapFind(entries, k)) {
            return Value::error("repeated key in a map literal");
        }
        entries.emplace_back(std::move(k), std::move(v));
    }
    return Value::mkMap(std::move(entries));
}

// CEL's commutative logic: false && x is false whatever x is, including an
// error, on either side. Only when neither side decides the result does an
// error (the left one first) propagate.
Value CelEval::evalAnd(const Expr *e) {
    Value l = evalExpr(e->args[0].get());
    if (l.isBool() && !l.b) {
        return l;
    }
    Value r = evalExpr(e->args[1].get());
    if (r.isBool() && !r.b) {
        return r;
    }
    if (l.isBool() && r.isBool()) {
        return Value::boolean(true);
    }
    if (l.isError()) return l;
    if (r.isError()) return r;
    const Value ops[] = {l, r};
    return noOverload(op::LogicalAnd, nullptr, ops, 2);
}

Value CelEval::evalOr(const Expr *e) {
    Value l = evalExpr(e->args[0].get());
    if (l.isBool() && l.b) {
        return l;
    }
    Value r = evalExpr(e->args[1].get());
    if (r.isBool() && r.b) {
        return r;
    }
    if (l.isBool() && r.isBool()) {
        return Value::boolean(false);
    }
    if (l.isError()) return l;
    if (r.isError()) return r;
    const Value ops[] = {l, r};
    return noOverload(op::LogicalOr, nullptr, ops, 2);
}

Value CelEval::evalConditional(const Expr *e) {
    Value c = evalExpr(e->args[0].get());
    if (c.isError()) {
        return c;
    }
    if (!c.isBool()) {
        return noOverload(op::Conditional, nullptr, &c, 1);
    }
    return evalExpr(e->args[c.b ? 1 : 2].get());
}

Value CelEval::evalComprehension(const Expr *e) {
    Value range = evalExpr(e->iterRange.get());
    if (range.isError()) {
        return range;
    }
    if (range.kind != Value::Kind::List && range.kind != Value::Kind::Map) {
        return Value::error("cannot iterate over a value of type '" + typeName(range) + "'");
    }

    Value accu = evalExpr(e->accuInit.get());
    m_vars.emplace_back(e->accuVar, accu);
    size_t accu_slot = m_vars.size() - 1;

    size_t n = (range.kind == Value::Kind::List) ? range.list->size() : range.map->size();
    for (size_t i=0; i<n; i++) {
        step();
        const Value &elem = (range.kind == Value::Kind::List) ?
            (*range.list)[i] : (*range.map)[i].first;
        m_vars.emplace_back(e->iterVar, elem);
        Value cond = evalExpr(e->loopCond.get());
        if (cond.isBool() && !cond.b) {
            m_vars.pop_back();
            break;
        }
        Value next = evalExpr(e->loopStep.get());
        m_vars.pop_back();
        m_vars[accu_slot].second = std::move(next);
    }

    Value ret = evalExpr(e->result.get());
    m_vars.pop_back();
    return ret;
}

Value CelEval::evalCall(const Expr *e) {
    const std::string &fn = e->name;
    const FunctionRegistry &reg = FunctionRegistry::get();

    // Non-strict operators: their operands may be errors without the result
    // being one.
    if (fn == op::LogicalAnd) {
        return evalAnd(e);
    } else if (fn == op::LogicalOr) {
        return evalOr(e);
    } else if (fn == op::Conditional) {
        return evalConditional(e);
    } else if (fn == op::NotStrictlyFalse) {
        Value v = evalExpr(e->args[0].get());
        return Value::boolean(!(v.isBool() && !v.b));
    } else if (fn == op::OptSelect) {
        Value op = evalExpr(e->args[0].get());
        if (op.isError()) {
            return op;
        }
        return optSelect(op, e->args[1]->cval.s);
    }

    // A namespaced global, `optional.of(x)`, unless `optional` is a variable.
    std::string qualified;
    const Expr *target_expr = e->operand.get();
    if (target_expr && target_expr->kind == ExprKind::Ident && !lookup(target_expr->name)
            && reg.hasFunction(target_expr->name + "." + fn)) {
        qualified = target_expr->name + "." + fn;
        target_expr = nullptr;
    }
    const std::string &name = qualified.empty() ? fn : qualified;

    // Strict: evaluate everything, and the first error wins.
    Value target;
    if (target_expr) {
        target = evalExpr(target_expr);
        if (target.isError()) {
            return target;
        }
        // or() and orValue() evaluate their argument only when needed.
        if (target.kind == Value::Kind::Optional && e->args.size() == 1
                && (fn == "or" || fn == "orValue")) {
            if (target.opt) {
                return (fn == "or") ? target : *target.opt;
            }
            Value alt = evalExpr(e->args[0].get());
            if (fn == "or" && !alt.isError() && alt.kind != Value::Kind::Optional) {
                return noOverload(fn, &target, &alt, 1);
            }
            return alt;
        }
    }
    std::vector<Value> args;
    args.reserve(e->args.size());
    for (const ExprUP &a : e->args) {
        args.push_back(evalExpr(a.get()));
        if (args.back().isError()) {
            return args.back();
        }
    }
    const Value *tp = target_expr ? &target : nullptr;
    // Resolved by the checker. The values can still differ from the static
    // types in one way, a null read from an unset node field, which admits()
    // catches.
    if (e->overload && e->overload->admits(tp, args.data(), args.size())) {
        return callOverload(e->overload, tp, args, e);
    }
    return callFunction(name, tp, args, e);
}

Value CelEval::callFunction(const std::string &fn, const Value *target,
        const std::vector<Value> &args, const Expr *call) {
    const FunctionRegistry &reg = FunctionRegistry::get();
    if (!reg.hasFunction(fn)) {
        return Value::error("undeclared reference to function '" + fn + "'");
    }
    const Overload *o = reg.resolve(fn, target, args.data(), args.size());
    if (!o || !o->impl) {
        return noOverload(fn, target, args.data(), args.size());
    }
    return callOverload(o, target, args, call);
}

Value CelEval::callOverload(const Overload *o, const Value *target,
        const std::vector<Value> &args, const Expr *call) {
    if (m_trace) {
        m_trace->push_back(o);
    }

    CallArgs c;
    c.target = target;
    c.args = args.data();
    c.n = args.size();
    c.regex = call->regex.get();
    Value ret = o->impl(c);
    if (o->cost == Cost::Linear) {
        uint64_t n = 0;
        auto size = [&n](const Value &v) {
            if (v.kind == Value::Kind::List) {
                n += v.list->size();
            } else if (v.kind == Value::Kind::Map) {
                n += v.map->size();
            } else if (v.kind == Value::Kind::String) {
                n += v.s.size() / 64;
            }
        };
        if (target) {
            size(*target);
        }
        for (const Value &a : args) {
            size(a);
        }
        charge(n);
    } else if (o->cost == Cost::Custom) {
        charge(c.steps);
    }
    return ret;
}

}
}
}
