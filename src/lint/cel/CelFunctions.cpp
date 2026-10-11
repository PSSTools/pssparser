/*
 * CelFunctions.cpp
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
#include <cctype>
#include <stdexcept>
#include "CelFunctions.h"

namespace pssp {
namespace lint {
namespace cel {

namespace {

std::string trim(const std::string &s) {
    size_t b = s.find_first_not_of(' ');
    if (b == std::string::npos) {
        return "";
    }
    size_t e = s.find_last_not_of(' ');
    return s.substr(b, e - b + 1);
}

// Top-level comma split: "map(K, V), int" is two parameters.
std::vector<std::string> splitParams(const std::string &s) {
    std::vector<std::string> out;
    int depth = 0;
    size_t b = 0;
    for (size_t i=0; i<s.size(); i++) {
        if (s[i] == '(') {
            depth++;
        } else if (s[i] == ')') {
            depth--;
        } else if (s[i] == ',' && depth == 0) {
            out.push_back(trim(s.substr(b, i - b)));
            b = i + 1;
        }
    }
    std::string last = trim(s.substr(b));
    if (!last.empty() || !out.empty()) {
        out.push_back(last);
    }
    return out;
}

bool isIdent(const std::string &s) {
    if (s.empty() || !(std::isalpha(static_cast<unsigned char>(s[0])) || s[0] == '_')) {
        return false;
    }
    for (char c : s) {
        if (!(std::isalnum(static_cast<unsigned char>(c)) || c == '_')) {
            return false;
        }
    }
    return true;
}

// How the reference shows an operator: "int + int -> int", "list(A)[int] -> A".
std::string operatorDisplay(const Overload &o) {
    const std::string &f = o.function;
    std::vector<std::string> p;
    for (const Type &t : o.params) {
        p.push_back(t.str());
    }
    std::string r = " -> " + o.result.str();
    if (f == "_[_]") {
        return p[0] + "[" + p[1] + "]" + r;
    } else if (f == "_[?_]") {
        return p[0] + "[?" + p[1] + "]" + r;
    } else if (f == "@in") {
        return p[0] + " in " + p[1] + r;
    } else if (f == "_?_:_") {
        return p[0] + " ? " + p[1] + " : " + p[2] + r;
    } else if (p.size() == 1 && f.size() == 2 && f[1] == '_') {
        return f.substr(0, 1) + p[0] + r;
    } else if (p.size() == 2 && f.size() > 2 && f.front() == '_' && f.back() == '_') {
        return p[0] + " " + f.substr(1, f.size() - 2) + " " + p[1] + r;
    }
    return f + r;
}

}

const char *levelName(Level l) {
    switch (l) {
        case Level::L0: return "L0";
        case Level::L1: return "L1";
        case Level::L2: return "L2";
        case Level::L3: return "L3";
        case Level::L4: return "L4";
    }
    return "?";
}

const char *scopeName(Scope s) {
    return (s == Scope::Model) ? "model" : "file";
}

const char *costName(Cost c) {
    switch (c) {
        case Cost::Constant: return "constant";
        case Cost::Linear: return "linear";
        case Cost::Custom: return "custom";
    }
    return "?";
}

Value noOverload(const std::string &fn, const Value *target, const Value *args, size_t n) {
    std::string msg = "no matching overload for '" + fn + "' applied to (";
    bool first = true;
    if (target) {
        msg += typeName(*target);
        first = false;
    }
    for (size_t i=0; i<n; i++) {
        if (!first) {
            msg += ", ";
        }
        msg += typeName(args[i]);
        first = false;
    }
    msg += ")";
    return Value::error(msg);
}

bool Overload::admits(const Value *target, const Value *args, size_t n) const {
    if (receiver != (target != nullptr)) {
        return false;
    }
    size_t off = receiver ? 1 : 0;
    if (params.size() != n + off) {
        return false;
    }
    auto fits = [this](const Type &t, const Value &v) {
        return t.admits(v) || (nullable && v.kind == Value::Kind::Null
            && (t.kind == Type::Kind::Node || t.kind == Type::Kind::Struct));
    };
    if (receiver && !fits(params[0], *target)) {
        return false;
    }
    for (size_t i=0; i<n; i++) {
        if (!fits(params[i + off], args[i])) {
            return false;
        }
    }
    return true;
}

const FunctionRegistry &FunctionRegistry::get() {
    static const FunctionRegistry inst;
    return inst;
}

Host::~Host() { }

FunctionRegistry::FunctionRegistry() {
    registerStdLib(*this);
    registerPssLib(*this);
}

const std::vector<const Overload *> *FunctionRegistry::find(const std::string &function) const {
    auto it = m_by_name.find(function);
    return (it == m_by_name.end()) ? nullptr : &it->second;
}

const Overload *FunctionRegistry::resolve(const std::string &function, const Value *target,
        const Value *args, size_t n) const {
    const std::vector<const Overload *> *ovs = find(function);
    if (!ovs) {
        return nullptr;
    }
    for (const Overload *o : *ovs) {
        if (o->kind != FnKind::Macro && o->admits(target, args, n)) {
            return o;
        }
    }
    return nullptr;
}

Overload &FunctionRegistry::add(const char *id, const char *sig, Impl impl, Cost cost,
        const char *doc) {
    std::string s(sig);
    auto bad = [&](const std::string &why) {
        return std::invalid_argument(std::string("function signature '") + sig + "': " + why);
    };

    size_t arrow = s.rfind("->");
    if (arrow == std::string::npos) {
        throw bad("no '->'");
    }
    std::string lhs = trim(s.substr(0, arrow));
    if (lhs.empty() || lhs.back() != ')') {
        throw bad("no parameter list");
    }
    // The parameter list's '(' is the one matching the final ')'.
    int depth = 0;
    size_t open = std::string::npos;
    for (size_t i=lhs.size(); i-- > 0; ) {
        if (lhs[i] == ')') {
            depth++;
        } else if (lhs[i] == '(' && --depth == 0) {
            open = i;
            break;
        }
    }
    if (open == std::string::npos) {
        throw bad("unbalanced parentheses");
    }

    std::unique_ptr<Overload> o(new Overload());
    o->id = id;
    o->impl = impl;
    o->cost = cost;
    o->doc = doc;
    o->group = m_group;
    o->library = m_library;
    o->level = m_level;
    o->scope = m_scope;

    std::string name = lhs.substr(0, open);
    size_t dot = name.rfind('.');
    o->function = name;
    if (dot != std::string::npos) {
        // "string.contains" has a receiver type; "optional.of" is a namespaced
        // global ("optional" alone is not a type: optional(T) is).
        std::string prefix = name.substr(0, dot);
        try {
            o->params.push_back(Type::parse(prefix));
            o->receiver = true;
            o->function = name.substr(dot + 1);
        } catch (const std::invalid_argument &) {
            if (!isIdent(prefix)) {
                throw bad("bad receiver or namespace '" + prefix + "'");
            }
        }
    }
    for (const std::string &p : splitParams(lhs.substr(open + 1, lhs.size() - open - 2))) {
        o->params.push_back(Type::parse(p));
    }
    o->result = Type::parse(trim(s.substr(arrow + 2)));

    char c0 = o->function[0];
    o->kind = (std::isalpha(static_cast<unsigned char>(c0)) || o->function.find('.') != std::string::npos)
        ? FnKind::Function : FnKind::Operator;
    if (o->kind == FnKind::Operator) {
        o->display = operatorDisplay(*o);
    } else {
        o->display = trim(lhs) + " -> " + o->result.str();
    }

    for (const auto &e : m_all) {
        if (e->id == o->id) {
            throw bad("duplicate overload id '" + o->id + "'");
        }
    }
    m_by_name[o->function].push_back(o.get());
    m_all.push_back(std::move(o));
    return *m_all.back();
}

Overload &FunctionRegistry::macro(const char *id, const char *function, const char *display,
        const char *doc) {
    std::unique_ptr<Overload> o(new Overload());
    o->id = id;
    o->function = function;
    o->kind = FnKind::Macro;
    o->display = display;
    o->doc = doc;
    o->group = m_group;
    o->library = m_library;
    o->level = m_level;
    o->scope = m_scope;
    m_by_name[o->function].push_back(o.get());
    m_all.push_back(std::move(o));
    return *m_all.back();
}

}
}
}
