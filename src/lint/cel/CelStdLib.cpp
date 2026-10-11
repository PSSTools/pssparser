/*
 * CelStdLib.cpp
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
 * CEL's standard functions, as far as the pss-rules profile has them
 * (lint-rule-expressions.md §3; lint-core-plan.md C3.2), registered with
 * their signatures, costs and docs.
 *
 * Registration order is documentation order: docs/lint-functions.rst lists
 * the groups and overloads as they appear here. Behaviour follows the CEL
 * spec, and cel-go where the spec leaves it open (string(double) uses Go's
 * shortest-form formatting; bool(string) accepts what Go's ParseBool does).
 */
#include <cerrno>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include "CelEval.h"
#include "CelFunctions.h"
#include "CelOps.h"
#include "../regex/Regex.h"

namespace pssp {
namespace lint {
namespace cel {

int cmpNumeric(const Value &a, const Value &b) {
    auto cmpIntDouble = [](int64_t i, double d) {
        if (std::isnan(d)) {
            return 2;
        }
        double di = static_cast<double>(i);
        return (di < d) ? -1 : (di > d) ? 1 : 0;
    };
    if (a.kind == Value::Kind::Int && b.kind == Value::Kind::Int) {
        return (a.i < b.i) ? -1 : (a.i > b.i) ? 1 : 0;
    }
    if (a.kind == Value::Kind::Int) {
        return cmpIntDouble(a.i, b.d);
    }
    if (b.kind == Value::Kind::Int) {
        int c = cmpIntDouble(b.i, a.d);
        return (c == 2) ? 2 : -c;
    }
    if (std::isnan(a.d) || std::isnan(b.d)) {
        return 2;
    }
    return (a.d < b.d) ? -1 : (a.d > b.d) ? 1 : 0;
}

const Value *mapFind(const ValueMap &m, const Value &key) {
    for (const auto &kv : m) {
        if (celEquals(kv.first, key)) {
            return &kv.second;
        }
    }
    return nullptr;
}

bool isValidMapKey(const Value &v) {
    return v.kind == Value::Kind::Int || v.kind == Value::Kind::Bool
        || v.kind == Value::Kind::String;
}

namespace {

using K = Value::Kind;

size_t utf8Length(const std::string &s) {
    size_t n = 0;
    for (unsigned char c : s) {
        if ((c & 0xC0) != 0x80) {
            n++;
        }
    }
    return n;
}

bool addOverflows(int64_t a, int64_t b) {
    return (b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b);
}

bool subOverflows(int64_t a, int64_t b) {
    return (b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b);
}

bool mulOverflows(int64_t a, int64_t b) {
    if (a == 0 || b == 0) {
        return false;
    }
    if (a == -1) {
        return b == INT64_MIN;
    }
    if (b == -1) {
        return a == INT64_MIN;
    }
    int64_t r = static_cast<int64_t>(static_cast<uint64_t>(a) * static_cast<uint64_t>(b));
    return r / b != a;
}

// CEL's zero values, for optional.ofNonZeroValue().
bool isZero(const Value &v) {
    switch (v.kind) {
        case K::Null: return true;
        case K::Bool: return !v.b;
        case K::Int: return v.i == 0;
        case K::Double: return v.d == 0.0;
        case K::String: return v.s.empty();
        case K::List: return v.list->empty();
        case K::Map: return v.map->empty();
        case K::Optional: return !v.opt;
        default: return false;
    }
}

}

/**
 * Go's strconv.FormatFloat(d, 'g', -1, 64), which is what cel-go's
 * string(double) returns: the shortest digits that read back as the same
 * double, in %e form when the exponent is below -4 or at least 6 (Go's
 * threshold in the shortest mode).
 */
std::string formatDouble(double d) {
    if (std::isnan(d)) {
        return "NaN";
    }
    if (std::isinf(d)) {
        return (d > 0) ? "+Inf" : "-Inf";
    }
    if (d == 0.0) {
        return std::signbit(d) ? "-0" : "0";
    }
    // Shortest round-tripping digits.
    char buf[64];
    for (int prec=1; prec<=17; prec++) {
        std::snprintf(buf, sizeof(buf), "%.*e", prec - 1, d);
        if (std::strtod(buf, nullptr) == d) {
            break;
        }
    }
    std::string s(buf);
    bool neg = (s[0] == '-');
    if (neg) {
        s = s.substr(1);
    }
    size_t epos = s.find('e');
    int exp = std::atoi(s.c_str() + epos + 1);
    std::string digits;
    for (size_t i=0; i<epos; i++) {
        if (s[i] != '.') {
            digits += s[i];
        }
    }
    while (digits.size() > 1 && digits.back() == '0') {
        digits.pop_back();
    }
    int nd = static_cast<int>(digits.size());
    int dp = exp + 1;     // the decimal point's position in digits

    std::string out = neg ? "-" : "";
    if (exp < -4 || exp >= 6) {
        out += digits[0];
        if (nd > 1) {
            out += "." + digits.substr(1);
        }
        char eb[16];
        std::snprintf(eb, sizeof(eb), "e%c%02d", (exp < 0) ? '-' : '+', std::abs(exp));
        out += eb;
    } else if (dp <= 0) {
        out += "0." + std::string(static_cast<size_t>(-dp), '0') + digits;
    } else if (dp >= nd) {
        out += digits + std::string(static_cast<size_t>(dp - nd), '0');
    } else {
        out += digits.substr(0, static_cast<size_t>(dp)) + "." + digits.substr(static_cast<size_t>(dp));
    }
    return out;
}

namespace {

//****************************************************************************
//* Implementations. Each receives evaluated, error-free operands whose kinds
//* the overload's signature has already admitted.
//****************************************************************************

Value notImpl(CallArgs &c) { return Value::boolean(!c[0].b); }

Value equalsImpl(CallArgs &c) { return Value::boolean(celEquals(c[0], c[1])); }
Value notEqualsImpl(CallArgs &c) { return Value::boolean(!celEquals(c[0], c[1])); }

int cmp(const Value &a, const Value &b) {
    if (a.isNumeric()) {
        return cmpNumeric(a, b);
    } else if (a.kind == K::String) {
        int r = a.s.compare(b.s);
        return (r < 0) ? -1 : (r > 0) ? 1 : 0;
    }
    return (a.b == b.b) ? 0 : (!a.b ? -1 : 1);
}

// 2 (unordered, NaN) makes every ordering false.
Value lessImpl(CallArgs &c) { int r = cmp(c[0], c[1]); return Value::boolean(r != 2 && r < 0); }
Value lessEqImpl(CallArgs &c) { int r = cmp(c[0], c[1]); return Value::boolean(r != 2 && r <= 0); }
Value greaterImpl(CallArgs &c) { int r = cmp(c[0], c[1]); return Value::boolean(r != 2 && r > 0); }
Value greaterEqImpl(CallArgs &c) { int r = cmp(c[0], c[1]); return Value::boolean(r != 2 && r >= 0); }

Value addInt(CallArgs &c) {
    if (addOverflows(c[0].i, c[1].i)) return Value::error("integer overflow");
    return Value::integer(c[0].i + c[1].i);
}
Value subInt(CallArgs &c) {
    if (subOverflows(c[0].i, c[1].i)) return Value::error("integer overflow");
    return Value::integer(c[0].i - c[1].i);
}
Value mulInt(CallArgs &c) {
    if (mulOverflows(c[0].i, c[1].i)) return Value::error("integer overflow");
    return Value::integer(c[0].i * c[1].i);
}
Value divInt(CallArgs &c) {
    if (c[1].i == 0) return Value::error("division by zero");
    if (c[0].i == INT64_MIN && c[1].i == -1) return Value::error("integer overflow");
    return Value::integer(c[0].i / c[1].i);
}
Value modInt(CallArgs &c) {
    if (c[1].i == 0) return Value::error("modulus by zero");
    if (c[0].i == INT64_MIN && c[1].i == -1) return Value::error("integer overflow");
    return Value::integer(c[0].i % c[1].i);
}
Value negInt(CallArgs &c) {
    if (c[0].i == INT64_MIN) return Value::error("integer overflow");
    return Value::integer(-c[0].i);
}
Value addDouble(CallArgs &c) { return Value::dbl(c[0].d + c[1].d); }
Value subDouble(CallArgs &c) { return Value::dbl(c[0].d - c[1].d); }
Value mulDouble(CallArgs &c) { return Value::dbl(c[0].d * c[1].d); }
Value divDouble(CallArgs &c) { return Value::dbl(c[0].d / c[1].d); }
Value negDouble(CallArgs &c) { return Value::dbl(-c[0].d); }
Value addString(CallArgs &c) { return Value::string(c[0].s + c[1].s); }
Value addList(CallArgs &c) {
    ValueList r(*c[0].list);
    r.insert(r.end(), c[1].list->begin(), c[1].list->end());
    return Value::mkList(std::move(r));
}

Value inList(CallArgs &c) {
    for (const Value &v : *c[1].list) {
        if (celEquals(c[0], v)) {
            return Value::boolean(true);
        }
    }
    return Value::boolean(false);
}
Value inMap(CallArgs &c) { return Value::boolean(mapFind(*c[1].map, c[0]) != nullptr); }

// List indexes are ints; an integral double is accepted outside the profile
// (the conformance suite indexes with dyn(0.0)).
bool listIndex(const Value &b, int64_t &idx) {
    if (b.kind == K::Int) {
        idx = b.i;
        return true;
    }
    if (b.kind == K::Double && std::trunc(b.d) == b.d) {
        idx = static_cast<int64_t>(b.d);
        return true;
    }
    return false;
}

Value indexList(const Value &l, const Value &b) {
    int64_t idx;
    if (!listIndex(b, idx)) {
        const Value ops[] = {l, b};
        return noOverload("_[_]", nullptr, ops, 2);
    }
    if (idx < 0 || static_cast<uint64_t>(idx) >= l.list->size()) {
        return Value::error("index " + std::to_string(idx) + " out of range for a list of size "
            + std::to_string(l.list->size()));
    }
    return (*l.list)[static_cast<size_t>(idx)];
}

Value indexMap(const Value &m, const Value &k) {
    const Value *v = mapFind(*m.map, k);
    return v ? *v : Value::error("no such key");
}

Value optIndexList(const Value &l, const Value &b) {
    int64_t idx;
    if (listIndex(b, idx) && (idx < 0 || static_cast<uint64_t>(idx) >= l.list->size())) {
        return Value::none();
    }
    Value v = indexList(l, b);
    return v.isError() ? v : Value::some(std::move(v));
}

Value optIndexMap(const Value &m, const Value &k) {
    const Value *v = mapFind(*m.map, k);
    return v ? Value::some(*v) : Value::none();
}

// On an optional, indexing applies to its value and stays optional:
// optional.of(l)[i] is l[?i], and none stays none.
Value optionalIndex(CallArgs &c) {
    const Value &o = c[0];
    if (!o.opt) {
        return o;
    }
    if (o.opt->kind == K::List) {
        return optIndexList(*o.opt, c[1]);
    } else if (o.opt->kind == K::Map) {
        return optIndexMap(*o.opt, c[1]);
    }
    return noOverload("_[_]", nullptr, c.args, c.n);
}

Value indexListImpl(CallArgs &c) { return indexList(c[0], c[1]); }
Value indexMapImpl(CallArgs &c) { return indexMap(c[0], c[1]); }
Value optIndexListImpl(CallArgs &c) { return optIndexList(c[0], c[1]); }
Value optIndexMapImpl(CallArgs &c) { return optIndexMap(c[0], c[1]); }

const Value &operand0(CallArgs &c) { return c.target ? *c.target : c[0]; }

Value sizeString(CallArgs &c) {
    return Value::integer(static_cast<int64_t>(utf8Length(operand0(c).s)));
}
Value sizeList(CallArgs &c) { return Value::integer(static_cast<int64_t>(operand0(c).list->size())); }
Value sizeMap(CallArgs &c) { return Value::integer(static_cast<int64_t>(operand0(c).map->size())); }

Value containsImpl(CallArgs &c) {
    return Value::boolean(c.target->s.find(c[0].s) != std::string::npos);
}
Value startsWithImpl(CallArgs &c) {
    const std::string &s = c.target->s, &t = c[0].s;
    return Value::boolean(s.size() >= t.size() && s.compare(0, t.size(), t) == 0);
}
Value endsWithImpl(CallArgs &c) {
    const std::string &s = c.target->s, &t = c[0].s;
    return Value::boolean(s.size() >= t.size() && s.compare(s.size() - t.size(), t.size(), t) == 0);
}

Value matchesImpl(CallArgs &c) {
    const std::string &text = c.target ? c.target->s : c[0].s;
    const std::string &pattern = c.target ? c[0].s : c[1].s;
    // A literal pattern was compiled when the expression was checked; any
    // other is compiled per call.
    try {
        std::unique_ptr<regex::Regex> owned;
        const regex::Regex *re = c.regex;
        if (!re) {
            owned.reset(regex::Regex::compile(pattern));
            re = owned.get();
        }
        uint64_t re_steps = 0;
        bool m = re->search(text, &re_steps);
        c.steps = re_steps / 64;
        return Value::boolean(m);
    } catch (const regex::RegexError &ex) {
        return Value::error(std::string("invalid regular expression: ") + ex.what());
    }
}

Value identity(CallArgs &c) { return c[0]; }

Value doubleToInt(CallArgs &c) {
    double d = c[0].d;
    if (std::isnan(d) || d <= -9223372036854775809.0 || d >= 9223372036854775808.0) {
        return Value::error("double is out of range for int");
    }
    return Value::integer(static_cast<int64_t>(d));
}
Value stringToInt(CallArgs &c) {
    const std::string &s = c[0].s;
    char *end = nullptr;
    errno = 0;
    long long v = std::strtoll(s.c_str(), &end, 10);
    if (s.empty() || *end != '\0' || errno == ERANGE) {
        return Value::error("cannot convert string '" + s + "' to int");
    }
    return Value::integer(static_cast<int64_t>(v));
}
Value intToDouble(CallArgs &c) { return Value::dbl(static_cast<double>(c[0].i)); }
Value stringToDouble(CallArgs &c) {
    const std::string &s = c[0].s;
    char *end = nullptr;
    double v = std::strtod(s.c_str(), &end);
    if (s.empty() || *end != '\0') {
        return Value::error("cannot convert string '" + s + "' to double");
    }
    return Value::dbl(v);
}
Value intToString(CallArgs &c) { return Value::string(std::to_string(c[0].i)); }
Value doubleToString(CallArgs &c) { return Value::string(formatDouble(c[0].d)); }
Value boolToString(CallArgs &c) { return Value::string(c[0].b ? "true" : "false"); }
Value stringToBool(CallArgs &c) {
    static const char *const T[] = {"1", "t", "T", "true", "TRUE", "True"};
    static const char *const F[] = {"0", "f", "F", "false", "FALSE", "False"};
    for (const char *t : T) {
        if (c[0].s == t) return Value::boolean(true);
    }
    for (const char *f : F) {
        if (c[0].s == f) return Value::boolean(false);
    }
    return Value::error("cannot convert string '" + c[0].s + "' to bool");
}
Value typeImpl(CallArgs &c) { return Value::type(typeName(c[0])); }

Value optionalOf(CallArgs &c) { return Value::some(c[0]); }
Value optionalOfNonZero(CallArgs &c) { return isZero(c[0]) ? Value::none() : Value::some(c[0]); }
Value optionalNone(CallArgs &) { return Value::none(); }
Value optionalHasValue(CallArgs &c) { return Value::boolean(static_cast<bool>(c.target->opt)); }
Value optionalValue(CallArgs &c) {
    if (!c.target->opt) {
        return Value::error("optional.none() dereference");
    }
    return *c.target->opt;
}

}

void registerStdLib(FunctionRegistry &r) {
    using C = Cost;
    r.level(Level::L0, Scope::File);

    r.group("Logic");
    r.add("logical_and", "_&&_(bool, bool) -> bool", nullptr, C::Constant,
        "Logical and. Commutative over errors: `false` on either side decides the result, "
        "even when the other side is an error.");
    r.add("logical_or", "_||_(bool, bool) -> bool", nullptr, C::Constant,
        "Logical or. Commutative over errors: `true` on either side decides the result, "
        "even when the other side is an error.");
    r.add("logical_not", "!_(bool) -> bool", &notImpl, C::Constant, "Logical not.");
    r.add("conditional", "_?_:_(bool, A, A) -> A", nullptr, C::Constant,
        "Conditional. Only the chosen branch is evaluated, so an error in the other one "
        "does not matter.");

    r.group("Equality and ordering");
    r.add("equals", "_==_(A, A) -> bool", &equalsImpl, C::Linear,
        "Equality. Numbers compare by value across int and double (`1 == 1.0`); lists and "
        "maps compare element-wise; AST nodes compare by identity (the same node), not by "
        "content.");
    r.add("not_equals", "_!=_(A, A) -> bool", &notEqualsImpl, C::Linear, "Inequality: `!(a == b)`.");
    struct Ord { const char *op, *name; Impl impl; };
    const Ord ords[] = {
        {"_<_", "less", &lessImpl}, {"_<=_", "less_equals", &lessEqImpl},
        {"_>_", "greater", &greaterImpl}, {"_>=_", "greater_equals", &greaterEqImpl}};
    struct Operands { const char *suffix, *types; };
    const Operands kinds[] = {
        {"bool", "bool, bool"}, {"int64", "int, int"}, {"int64_double", "int, double"},
        {"double", "double, double"}, {"double_int64", "double, int"}, {"string", "string, string"}};
    for (const Ord &o : ords) {
        for (const Operands &k : kinds) {
            std::string id = std::string(o.name) + "_" + k.suffix;
            std::string sig = std::string(o.op) + "(" + k.types + ") -> bool";
            r.add(id.c_str(), sig.c_str(), o.impl, C::Constant,
                "Ordering. Strings order by code point, `false < true`, and int and double "
                "compare by value; any comparison with NaN is false.");
        }
    }

    r.group("Arithmetic");
    r.add("add_int64", "_+_(int, int) -> int", &addInt, C::Constant,
        "Addition. Overflowing int64 is an error, not a wrap-around.");
    r.add("add_double", "_+_(double, double) -> double", &addDouble, C::Constant, "Addition.");
    r.add("subtract_int64", "_-_(int, int) -> int", &subInt, C::Constant,
        "Subtraction. Overflow is an error.");
    r.add("subtract_double", "_-_(double, double) -> double", &subDouble, C::Constant, "Subtraction.");
    r.add("multiply_int64", "_*_(int, int) -> int", &mulInt, C::Constant,
        "Multiplication. Overflow is an error.");
    r.add("multiply_double", "_*_(double, double) -> double", &mulDouble, C::Constant,
        "Multiplication.");
    r.add("divide_int64", "_/_(int, int) -> int", &divInt, C::Constant,
        "Division, truncating toward zero. Division by zero is an error.");
    r.add("divide_double", "_/_(double, double) -> double", &divDouble, C::Constant,
        "Division (IEEE 754: dividing by zero gives an infinity or NaN).");
    r.add("modulo_int64", "_%_(int, int) -> int", &modInt, C::Constant,
        "Remainder, with the sign of the dividend. Modulus by zero is an error.");
    r.add("negate_int64", "-_(int) -> int", &negInt, C::Constant, "Negation. `-(-2^63)` is an error.");
    r.add("negate_double", "-_(double) -> double", &negDouble, C::Constant, "Negation.");
    r.add("add_string", "_+_(string, string) -> string", &addString, C::Linear, "Concatenation.");
    r.add("add_list", "_+_(list(A), list(A)) -> list(A)", &addList, C::Linear, "Concatenation.");

    r.group("Lists and maps");
    r.add("in_list", "@in(A, list(A)) -> bool", &inList, C::Linear,
        "Membership, by equality (as `==`).");
    r.add("in_map", "@in(K, map(K, V)) -> bool", &inMap, C::Constant, "Whether the map has the key.");
    r.add("index_list", "_[_](list(A), int) -> A", &indexListImpl, C::Constant,
        "The element at a zero-based index. Out of range is an error; use `l[?i]` when the "
        "index may be out of range.");
    r.add("index_list_double", "_[_](list(A), double) -> A", &indexListImpl, C::Constant,
        "An integral double as a list index. CEL allows it; the pss-rules profile does not.")
        .inProfile = false;
    r.add("index_map", "_[_](map(K, V), K) -> V", &indexMapImpl, C::Constant,
        "The value under a key. A missing key is an error; use `m[?k]` or `m.?k` when the key "
        "may be absent.");
    r.add("optional_list_index_int", "_[_](optional(list(A)), int) -> optional(A)",
        &optionalIndex, C::Constant,
        "Indexing an optional list applies to its value and stays optional: "
        "`optional.of(l)[i]` is `l[?i]`, and `optional.none()[i]` is `optional.none()`.");
    r.add("optional_map_index_value", "_[_](optional(map(K, V)), K) -> optional(V)",
        &optionalIndex, C::Constant,
        "Indexing an optional map applies to its value and stays optional: "
        "`optional.of(m)[k]` is `m[?k]`.");
    r.add("list_optindex_optional_int", "_[?_](list(A), int) -> optional(A)", &optIndexListImpl,
        C::Constant, "The element at an index, or `optional.none()` if the index is out of range.");
    r.add("map_optindex_optional_value", "_[?_](map(K, V), K) -> optional(V)", &optIndexMapImpl,
        C::Constant, "The value under a key, or `optional.none()` if the key is absent.");
    r.add("optional_list_optindex_optional_int", "_[?_](optional(list(A)), int) -> optional(A)",
        &optionalIndex, C::Constant,
        "`[?i]` on an optional list: the value's element, or `optional.none()`.");
    r.add("optional_map_optindex_optional_value", "_[?_](optional(map(K, V)), K) -> optional(V)",
        &optionalIndex, C::Constant,
        "`[?k]` on an optional map: the value under the key, or `optional.none()`.");
    r.add("size_list", "size(list(A)) -> int", &sizeList, C::Constant, "The number of elements.");
    r.add("list_size", "list(A).size() -> int", &sizeList, C::Constant, "The number of elements.");
    r.add("size_map", "size(map(K, V)) -> int", &sizeMap, C::Constant, "The number of entries.");
    r.add("map_size", "map(K, V).size() -> int", &sizeMap, C::Constant, "The number of entries.");

    r.group("Strings");
    r.add("size_string", "size(string) -> int", &sizeString, C::Linear,
        "The length in Unicode code points (not bytes).");
    r.add("string_size", "string.size() -> int", &sizeString, C::Linear,
        "The length in Unicode code points (not bytes).");
    r.add("contains_string", "string.contains(string) -> bool", &containsImpl, C::Linear,
        "Whether the argument occurs in the string.");
    r.add("starts_with_string", "string.startsWith(string) -> bool", &startsWithImpl, C::Linear,
        "Whether the string begins with the argument.");
    r.add("ends_with_string", "string.endsWith(string) -> bool", &endsWithImpl, C::Linear,
        "Whether the string ends with the argument.");
    r.add("matches", "matches(string, string) -> bool", &matchesImpl, C::Custom,
        "Whether the RE2 pattern (second argument) matches anywhere in the string; anchor it "
        "with `^...$` for a whole-string match. Linear time: backreferences and lookaround are "
        "not supported. An invalid pattern is an error. Costs one step per 64 steps of the "
        "regular-expression engine.");
    r.add("matches_string", "string.matches(string) -> bool", &matchesImpl, C::Custom,
        "Receiver form of `matches(string, string)`.");

    r.group("Conversions");
    r.add("int64_to_int64", "int(int) -> int", &identity, C::Constant, "Identity.");
    r.add("double_to_int64", "int(double) -> int", &doubleToInt, C::Constant,
        "Truncates toward zero. NaN, and values outside the int64 range, are errors.");
    r.add("string_to_int64", "int(string) -> int", &stringToInt, C::Linear,
        "Parses a decimal integer. Anything else, or a value out of range, is an error.");
    r.add("double_to_double", "double(double) -> double", &identity, C::Constant, "Identity.");
    r.add("int64_to_double", "double(int) -> double", &intToDouble, C::Constant,
        "The nearest double (large values lose precision).");
    r.add("string_to_double", "double(string) -> double", &stringToDouble, C::Linear,
        "Parses a floating-point number. Anything else is an error.");
    r.add("string_to_string", "string(string) -> string", &identity, C::Constant, "Identity.");
    r.add("int64_to_string", "string(int) -> string", &intToString, C::Constant, "Decimal.");
    r.add("double_to_string", "string(double) -> string", &doubleToString, C::Constant,
        "The shortest decimal that reads back as the same double, as cel-go writes it: "
        "`123.456`, `1e+06`, `-0.0045`, `NaN`, `+Inf`.");
    r.add("bool_to_string", "string(bool) -> string", &boolToString, C::Constant,
        "`'true'` or `'false'`.");
    r.add("bool_to_bool", "bool(bool) -> bool", &identity, C::Constant, "Identity.");
    r.add("string_to_bool", "bool(string) -> bool", &stringToBool, C::Constant,
        "`'true'`, `'TRUE'`, `'True'`, `'t'`, `'T'` and `'1'` are true; `'false'`, `'FALSE'`, "
        "`'False'`, `'f'`, `'F'` and `'0'` are false; anything else is an error.");
    r.add("type", "type(A) -> type", &typeImpl, C::Constant,
        "The value's type: `int`, `list`, ..., or an AST node's own class, e.g. "
        "`type(node) == ActionTraversal`.");
    r.add("to_dyn", "dyn(A) -> A", &identity, C::Constant,
        "CEL's dynamic-type cast. Not in the pss-rules profile, which has no `dyn` type.")
        .inProfile = false;

    r.group("Optionals");
    r.add("optional_of", "optional.of(A) -> optional(A)", &optionalOf, C::Constant,
        "An optional holding the value.");
    r.add("optional_ofNonZeroValue", "optional.ofNonZeroValue(A) -> optional(A)",
        &optionalOfNonZero, C::Constant,
        "`optional.none()` if the value is its type's zero value (`0`, `''`, `false`, `[]`, "
        "`{}`, `null`), otherwise an optional holding it.");
    r.add("optional_none", "optional.none() -> optional(A)", &optionalNone, C::Constant,
        "The empty optional.");
    r.add("optional_hasValue", "optional(A).hasValue() -> bool", &optionalHasValue, C::Constant,
        "Whether the optional holds a value.");
    r.add("optional_value", "optional(A).value() -> A", &optionalValue, C::Constant,
        "The value. An error on `optional.none()`.");
    r.add("optional_or_optional", "optional(A).or(optional(A)) -> optional(A)", nullptr,
        C::Constant, "This optional if it has a value, otherwise the argument. The argument is "
        "evaluated only when needed.");
    r.add("optional_orValue_value", "optional(A).orValue(A) -> A", nullptr, C::Constant,
        "The value if there is one, otherwise the argument. The argument is evaluated only "
        "when needed.");
    // Not a call in the source (`x.?f`), but the parser makes it one, with
    // the field name as a string constant.
    Overload &optsel = r.macro("select_optional_field", "_?._", "A.?field -> optional(B)",
        "Optional field selection: `optional.of(x.field)` if the map has the key or the node "
        "has the field set (as `has()`), otherwise `optional.none()`. Chains: on an optional, "
        "selection applies to its value.");
    optsel.kind = FnKind::Operator;
    optsel.params = {Type::parse("A"), Type::parse("string")};
    optsel.result = Type::parse("optional(B)");
    r.macro("optMap", "optMap", "optional(A).optMap(x, B) -> optional(B)",
        "Macro. `o.optMap(x, e)`: if `o` has a value, `optional.of(e)` with `x` bound to it, "
        "otherwise `optional.none()`.");
    r.macro("optFlatMap", "optFlatMap", "optional(A).optFlatMap(x, optional(B)) -> optional(B)",
        "Macro. `o.optFlatMap(x, e)`: if `o` has a value, `e` (itself an optional) with `x` "
        "bound to it, otherwise `optional.none()`.");

    r.group("Macros");
    r.macro("has", "has", "has(e.f) -> bool",
        "Presence, never the field's value: a map has the key; an AST node's field is set (a "
        "node field when not null, a list when not empty, a scalar when not zero).");
    r.macro("all", "all", "list(A).all(x, bool) -> bool",
        "Whether the predicate holds for every element (for a map, every key). Stops at the "
        "first `false`; an error is absorbed if another element decides the result.");
    r.macro("exists", "exists", "list(A).exists(x, bool) -> bool",
        "Whether the predicate holds for some element (for a map, some key). Stops at the "
        "first `true`.");
    r.macro("exists_one", "exists_one", "list(A).exists_one(x, bool) -> bool",
        "Whether the predicate holds for exactly one element. `existsOne` is the same macro.");
    r.macro("map", "map", "list(A).map(x, B) -> list(B)",
        "The transformed elements. `l.map(x, p, t)` transforms only the elements for which "
        "`p` holds.");
    r.macro("filter", "filter", "list(A).filter(x, bool) -> list(A)",
        "The elements for which the predicate holds.");
    r.macro("cel_bind", "cel.bind", "cel.bind(x, A, B) -> B",
        "Evaluates the second argument once, binds it to `x`, and evaluates the third. A rule's "
        "`let:` entries are this macro.");
}

}
}
}
