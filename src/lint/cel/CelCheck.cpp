/*
 * CelCheck.cpp
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
#include <functional>
#include <unordered_map>
#include <unordered_set>
#include "CelCheck.h"
#include "CelFunctions.h"
#include "CelNode.h"
#include "CelParser.h"
#include "../regex/Regex.h"

namespace pssp {
namespace lint {
namespace cel {

namespace {

bool isIdentText(const std::string &s) {
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

// CEL's own type names, less the kinds the profile excludes; the evaluator
// resolves the same set.
bool builtinTypeName(const std::string &name) {
    static const char *names[] = {
        "bool", "int", "double", "string", "list", "map", "null_type", "type", "optional_type"};
    for (const char *n : names) {
        if (name == n) {
            return true;
        }
    }
    return false;
}

// CEL type names that the profile leaves out (lint-rule-expressions.md §3).
bool excludedTypeName(const std::string &name) {
    static const char *names[] = {
        "uint", "bytes", "dyn", "google.protobuf.Timestamp", "google.protobuf.Duration"};
    for (const char *n : names) {
        if (name == n) {
            return true;
        }
    }
    return false;
}

// How a rule author writes the function: "+" for _+_, "in" for @in.
std::string surfaceName(const std::string &fn) {
    if (fn == op::In) {
        return "in";
    } else if (fn == op::Index) {
        return "[]";
    } else if (fn == op::OptIndex) {
        return "[?]";
    } else if (fn.size() == 2 && fn[1] == '_') {
        return fn.substr(0, 1);
    } else if (fn.size() > 2 && fn.front() == '_' && fn.back() == '_') {
        return fn.substr(1, fn.size() - 2);
    }
    return fn;
}

ExprUP cloneShallow(const Expr *e) {
    ExprUP c(new Expr());
    c->id = e->id;
    c->begin = e->begin;
    c->end = e->end;
    c->height = e->height;
    c->kind = e->kind;
    c->cval = e->cval;
    c->name = e->name;
    c->testOnly = e->testOnly;
    c->optIndices = e->optIndices;
    c->iterVar = e->iterVar;
    c->accuVar = e->accuVar;
    return c;
}

ExprUP cloneDeep(const Expr *e) {
    if (!e) {
        return nullptr;
    }
    ExprUP c = cloneShallow(e);
    c->operand = cloneDeep(e->operand.get());
    for (const ExprUP &a : e->args) {
        c->args.push_back(cloneDeep(a.get()));
    }
    for (const Entry &ent : e->entries) {
        Entry n;
        n.id = ent.id;
        n.begin = ent.begin;
        n.field = ent.field;
        n.key = cloneDeep(ent.key.get());
        n.value = cloneDeep(ent.value.get());
        n.optional = ent.optional;
        c->entries.push_back(std::move(n));
    }
    c->iterRange = cloneDeep(e->iterRange.get());
    c->accuInit = cloneDeep(e->accuInit.get());
    c->loopCond = cloneDeep(e->loopCond.get());
    c->loopStep = cloneDeep(e->loopStep.get());
    c->result = cloneDeep(e->result.get());
    c->overload = e->overload;
    c->field = e->field;
    c->regex = e->regex;
    return c;
}

const Define *findDefine(const CheckEnv &env, const std::string &name, bool call) {
    // The last of a name wins: the loader lists a rule's own helpers after
    // the file's, which they shadow.
    for (auto it=env.defines.rbegin(); it!=env.defines.rend(); it++) {
        if (it->name == name && it->call == call) {
            return &*it;
        }
    }
    return nullptr;
}

class Checker {
public:
    Checker(const CheckEnv &env, const CheckOptions &opts,
            const std::unordered_set<const Define *> &bad) :
        m_env(env), m_opts(opts), m_reg(FunctionRegistry::get()), m_bad(bad) {
        for (const auto &v : env.vars) {
            m_scope.push_back({v.first, v.first, v.second});
        }
        m_globals = m_scope.size();
    }

    CheckResult run(const Expr *e, uint32_t source, const Type *expected, const char *what) {
        CheckResult res;
        m_source = source;
        if (!profile(e, source)) {
            Type t;
            ExprUP c = visit(e, t);
            t = resolve(t);
            if (expected && t.kind != Type::Kind::Error) {
                Type j;
                if (!join(*expected, t, j)) {
                    std::string place = what ? std::string(what) + ": must be "
                        : std::string("the expression must be ");
                    error(e->begin, place + expected->str() + ", but this expression is '"
                        + t.str() + "'");
                }
                t = resolve(t);
            }
            res.type = t;
            if (m_errors.empty() && !m_failed) {
                res.expr = std::move(c);
            }
        }
        res.errors = std::move(m_errors);
        for (const auto &o : m_reg.all()) {
            if (m_used.count(o.get())) {
                res.overloads.push_back(o.get());
            }
        }
        return res;
    }

private:
    struct Var {
        std::string     name;       // as the expression writes it
        std::string     runtime;    // as the evaluator binds it
        Type            type;
    };

    void error(uint32_t offset, const std::string &msg,
            CheckError::Kind kind=CheckError::Kind::Type) {
        m_errors.push_back({m_source, offset, msg, kind});
    }

    // Profile violations, once per body. True if there were any.
    bool profile(const Expr *e, uint32_t source) {
        std::vector<ProfileError> errs = checkProfile(e);
        for (const ProfileError &pe : errs) {
            m_errors.push_back({source, pe.offset, pe.message, CheckError::Kind::Profile});
        }
        return !errs.empty();
    }

    //************************************************************************
    //* Type variables
    //************************************************************************

    Type fresh() {
        return Type::var("%" + std::to_string(++m_nextVar));
    }

    static bool isVar(const Type &t) {
        return t.kind == Type::Kind::Param && !t.param.empty() && t.param[0] == '%';
    }

    // The representative of a variable's alias chain.
    std::string root(std::string v) const {
        for (;;) {
            auto it = m_subst.find(v);
            if (it == m_subst.end() || !isVar(it->second)) {
                return v;
            }
            v = it->second.param;
        }
    }

    const Type *bound(const std::string &v) const {
        auto it = m_subst.find(root(v));
        return (it == m_subst.end()) ? nullptr : &it->second;
    }

    Type resolve(const Type &t) const {
        if (isVar(t)) {
            std::string r = root(t.param);
            const Type *b = bound(r);
            return b ? resolve(*b) : Type::var(r);
        }
        Type out = t;
        for (Type &a : out.args) {
            a = resolve(a);
        }
        return out;
    }

    bool occurs(const std::string &v, const Type &t) const {
        Type r = resolve(t);
        if (isVar(r)) {
            return r.param == v;
        }
        for (const Type &a : r.args) {
            if (occurs(v, a)) {
                return true;
            }
        }
        return false;
    }

    /**
     * The least type both `a` and `b` fit, binding and widening variables on
     * the way; false if there is none. Widening is what lets `[a.lhs, b]`
     * be a list of the nearest common base class.
     */
    bool join(const Type &a, const Type &b, Type &out) {
        if (isVar(a)) {
            return joinVar(a.param, b, out);
        } else if (isVar(b)) {
            return joinVar(b.param, a, out);
        }
        using K = Type::Kind;
        if (a.kind == K::Error || b.kind == K::Error) {
            out = Type(K::Error);
            return true;
        }
        if (a.kind == K::Null && (b.kind == K::Node || b.kind == K::Struct || b.kind == K::Null)) {
            out = b;
            return true;
        } else if (b.kind == K::Null && (a.kind == K::Node || a.kind == K::Struct)) {
            out = a;
            return true;
        }
        if (a.kind != b.kind) {
            return false;
        }
        switch (a.kind) {
            case K::List:
            case K::Optional: {
                Type e;
                if (!join(a.args[0], b.args[0], e)) {
                    return false;
                }
                out = a;
                out.args[0] = e;
                return true;
            }
            case K::Map: {
                Type k, v;
                if (!join(a.args[0], b.args[0], k) || !join(a.args[1], b.args[1], v)) {
                    return false;
                }
                out = Type::map(k, v);
                return true;
            }
            case K::Node:
                out = Type::node(commonBase(a.cls, b.cls));
                return true;
            case K::Struct:
                out = a;
                return a.cls == b.cls;
            case K::TypeType:
                out = (a.param == b.param) ? a : Type(K::TypeType);
                return true;
            case K::Int:
                // Values of one enum stay tagged; anything else is an int.
                out = (a.param == b.param) ? a : Type(K::Int);
                return true;
            case K::Param:
                // An uninstantiated signature parameter; never reaches here.
                out = a;
                return a.param == b.param;
            default:
                out = a;
                return true;
        }
    }

    bool joinVar(const std::string &v, const Type &t, Type &out) {
        std::string r = root(v);
        if (isVar(t)) {
            std::string s = root(t.param);
            if (s == r) {
                out = resolve(Type::var(r));
                return true;
            }
            const Type *br = bound(r), *bs = bound(s);
            if (br && bs) {
                Type x = *br, y = *bs, j;
                if (!join(x, y, j)) {
                    return false;
                }
                m_subst[root(r)] = j;
                m_subst[s] = Type::var(r);
            } else if (bs) {
                m_subst[r] = Type::var(s);
            } else {
                m_subst[s] = Type::var(r);
            }
            out = resolve(Type::var(r));
            return true;
        }
        const Type *b = bound(r);
        if (!b) {
            if (occurs(r, t)) {
                return false;
            }
            m_subst[r] = t;
            out = t;
            return true;
        }
        Type cur = *b, j;
        if (!join(cur, t, j)) {
            return false;
        }
        m_subst[r] = j;
        out = j;
        return true;
    }

    // A signature's parameters (A, B, K, V) as fresh variables, one set per
    // instantiation.
    Type instantiate(const Type &t, std::unordered_map<std::string, Type> &vars) {
        if (t.kind == Type::Kind::Param) {
            auto it = vars.find(t.param);
            if (it == vars.end()) {
                it = vars.emplace(t.param, fresh()).first;
            }
            return it->second;
        }
        Type out = t;
        for (Type &a : out.args) {
            a = instantiate(a, vars);
        }
        return out;
    }

    std::string typeStr(const Type &t) const {
        return resolve(t).str();
    }

    static bool isNumeric(const Type &t) {
        return t.kind == Type::Kind::Int || t.kind == Type::Kind::Double;
    }

    //************************************************************************
    //* Scope
    //************************************************************************

    // The innermost variable of a name, or -1.
    int lookup(const std::string &name) const {
        for (int i=static_cast<int>(m_scope.size())-1; i>=0; i--) {
            if (m_scope[i].name == name) {
                return i;
            }
        }
        return -1;
    }

    void push(const std::string &name, const std::string &runtime, const Type &t) {
        m_scope.push_back({name, runtime, t});
        m_runtime.push_back(runtime);
    }

    void pop() {
        m_scope.pop_back();
        m_runtime.pop_back();
    }

    // In an inlined helper, a name that means something outside the helper
    // (a declared variable, a type) must not be hidden, when the helper runs,
    // by a variable of the expression that uses it: the evaluator looks names
    // up in one stack.
    bool captured(const std::string &name, uint32_t offset) {
        if (m_inlining.empty()) {
            return false;
        }
        for (const std::string &r : m_runtime) {
            if (r == name) {
                error(offset, "helper '" + m_inlining.back()->name + "' uses '" + name
                    + "', which a variable of the same name hides where the helper is used;"
                    " rename that variable");
                return true;
            }
        }
        return false;
    }

    //************************************************************************
    //* Expressions
    //************************************************************************

    ExprUP visit(const Expr *e, Type &t) {
        switch (e->kind) {
            case ExprKind::Const: return visitConst(e, t);
            case ExprKind::Ident: return visitIdent(e, t);
            case ExprKind::Select: return visitSelect(e, t);
            case ExprKind::Call: return visitCall(e, t);
            case ExprKind::List: return visitList(e, t);
            case ExprKind::Map: return visitMap(e, t);
            case ExprKind::Comprehension: return visitComprehension(e, t);
            case ExprKind::Struct: break;
        }
        // Struct literals: reported by the profile check.
        t = Type(Type::Kind::Error);
        return cloneShallow(e);
    }

    ExprUP visitConst(const Expr *e, Type &t) {
        using K = Const::Kind;
        switch (e->cval.kind) {
            case K::Null: t = Type(Type::Kind::Null); break;
            case K::Bool: t = Type(Type::Kind::Bool); break;
            case K::Int: t = Type(Type::Kind::Int); break;
            case K::Double: t = Type(Type::Kind::Double); break;
            case K::String: t = Type(Type::Kind::String); break;
            default: t = Type(Type::Kind::Error); break;     // profile
        }
        return cloneShallow(e);
    }

    ExprUP visitIdent(const Expr *e, Type &t) {
        const std::string &name = e->name;
        int v = lookup(name);
        if (v >= 0) {
            if (static_cast<size_t>(v) < m_globals && captured(name, e->begin)) {
                t = Type(Type::Kind::Error);
                return cloneShallow(e);
            }
            t = narrowed(e, m_scope[v].type);
            ExprUP c = cloneShallow(e);
            c->name = m_scope[v].runtime;
            return c;
        }
        if (const Define *d = findDefine(m_env, name, false)) {
            return inlineDefine(*d, e, {}, {}, t);
        }
        if (findDefine(m_env, name, true)) {
            error(e->begin, "'" + name + "' is a helper with parameters; call it: " + name + "(...)");
            t = Type(Type::Kind::Error);
            return cloneShallow(e);
        }
        if (builtinTypeName(name) || lookupTypeName(name)) {
            captured(name, e->begin);
            t = Type::typeOf(name);
            return cloneShallow(e);
        }
        if (excludedTypeName(name)) {
            error(e->begin, "type '" + name + "' is not supported in pss-rules");
        } else {
            error(e->begin, "undeclared reference to '" + name + "'");
        }
        t = Type(Type::Kind::Error);
        return cloneShallow(e);
    }

    static bool lookupTypeName(const std::string &name) {
        Value v;
        return lookupType(name, v);
    }

    // How a message refers to `e`: its name, or a field path ending in one.
    static std::string varName(const Expr *e) {
        if (e->kind == ExprKind::Ident) {
            return e->name;
        }
        if (e->kind == ExprKind::Select && !e->testOnly) {
            std::string o = varName(e->operand.get());
            return (o == "x") ? o : o + "." + e->name;
        }
        return "x";
    }

    // "A, B and C", or the first four "and 2 more".
    static std::string listNames(const std::vector<std::string> &names) {
        size_t n = (names.size() > 5) ? 4 : names.size();
        std::string s;
        for (size_t i=0; i<n; i++) {
            s += (i ? (i + 1 == n && n == names.size() ? " and " : ", ") : "") + names[i];
        }
        if (n < names.size()) {
            s += " and " + std::to_string(names.size() - n) + " more";
        }
        return s;
    }

    // The type of field `name` of `on`, the type of `operand`; Error
    // (reported) if it has none.
    Type fieldOf(const Type &on, const Expr *operand, const std::string &name, uint32_t offset,
            int32_t &index) {
        using K = Type::Kind;
        Type r = resolve(on);
        index = -1;
        switch (r.kind) {
            case K::Error:
                return r;
            case K::Node:
            case K::Struct: {
                FieldRef f;
                // A node's field is its class's only. A field of a class
                // deriving from it is an error that says how to reach it:
                // test the class first, which narrows (`type(c) == Action
                // && c.name`), so the read cannot fail at run time.
                bool found = (r.kind == K::Node) ?
                    (r.cls && nodeFieldType(r.cls, name, f)) : structFieldType(r.cls, name, f);
                if (!found) {
                    std::string msg = "type '" + r.str() + "' has no field '" + name + "'";
                    std::vector<std::string> derived;
                    if (r.kind == K::Node) {
                        derived = derivedFieldClasses(r.cls, name);
                    }
                    if (!derived.empty()) {
                        msg += "; " + (derived.size() == 1 ? derived[0] + " has it"
                            : listNames(derived) + " have it");
                        std::string v = varName(operand);
                        msg += ": test the class first, as in type(" + v + ") == " + derived[0]
                            + " && " + v + "." + name;
                    } else if (r.kind == K::Node) {
                        msg += r.cls ? ", nor does any class derived from it"
                            : ", nor does any node class";
                    }
                    error(offset, msg);
                    return Type(K::Error);
                }
                if (!f.error.empty()) {
                    error(offset, f.error);
                    return Type(K::Error);
                }
                index = f.index;
                return f.type;
            }
            case K::Map: {
                Type k;
                if (!join(r.args[0], Type(K::String), k)) {
                    error(offset, "cannot select '" + name + "' from a map with '"
                        + typeStr(r.args[0]) + "' keys; index it instead");
                    return Type(K::Error);
                }
                return r.args[1];
            }
            case K::Null:
                error(offset, "cannot select '" + name + "' from null");
                return Type(K::Error);
            case K::Param:
                error(offset, "cannot select '" + name + "' from a value whose type is not known");
                return Type(K::Error);
            default:
                error(offset, "a value of type '" + r.str() + "' has no field '" + name + "'");
                return Type(K::Error);
        }
    }

    ExprUP visitSelect(const Expr *e, Type &t) {
        // A qualified name, as CEL resolves one: when `a` is not a variable,
        // `a.b.c` may name the declared variable "a.b.c". This is how a rule's
        // options are declared (C4.1): `options.pattern`, each with its own
        // type.
        std::string path, root;
        if (!e->testOnly && pathOf(e, path, root) && lookup(root) < 0) {
            if (lookup(path) >= 0) {
                ExprUP id = cloneShallow(e);
                id->kind = ExprKind::Ident;
                id->name = path;
                return visitIdent(id.get(), t);
            }
            std::string known;
            for (const Var &v : m_scope) {
                if (v.name.size() > root.size() && v.name.compare(0, root.size() + 1, root + ".") == 0
                        && known.find("'" + v.name + "'") == std::string::npos) {
                    known += (known.empty() ? "" : ", ") + ("'" + v.name + "'");
                }
            }
            if (!known.empty()) {
                error(e->begin, "undeclared reference to '" + path + "' (declared: " + known + ")");
                t = Type(Type::Kind::Error);
                return cloneShallow(e);
            }
        }
        Type ot;
        ExprUP operand = visit(e->operand.get(), ot);
        Type r = resolve(ot);

        // ExprBinOp.BinOp_Eq: an enum constant, an int.
        if (r.kind == Type::Kind::TypeType && !e->testOnly) {
            int64_t v;
            if (isEnum(r.param) && enumConstant(r.param, e->name, v)) {
                ExprUP c = cloneShallow(e);
                c->kind = ExprKind::Const;
                c->cval.kind = Const::Kind::Int;
                c->cval.i = v;
                c->name.clear();
                t = Type(Type::Kind::Int);
                t.param = r.param;
                return c;
            }
            error(e->begin, isEnum(r.param) ?
                "enum '" + r.param + "' has no member '" + e->name + "'" :
                "type '" + (r.param.empty() ? std::string("type") : r.param)
                    + "' has no member '" + e->name + "'");
            t = Type(Type::Kind::Error);
            return cloneShallow(e);
        }

        ExprUP c = cloneShallow(e);
        c->operand = std::move(operand);
        // Selecting from an optional applies to its value and stays optional.
        bool opt = (r.kind == Type::Kind::Optional);
        Type on = opt ? r.args[0] : r;
        Type ft = fieldOf(on, e->operand.get(), e->name, selectOffset(e), c->field);
        if (e->testOnly) {
            t = (ft.kind == Type::Kind::Error) ? ft : Type(Type::Kind::Bool);
        } else {
            t = (opt && ft.kind != Type::Kind::Error) ? Type::optional(ft) : narrowed(e, ft);
        }
        return c;
    }

    //************************************************************************
    //* Narrowing: on the right of `type(x) == K && ...`, and in the first
    //* result of `type(x) == K ? ... : ...`, x is a K. x is a variable or a
    //* chain of field selections from one (node.lhs).
    //************************************************************************

    struct Fact {
        std::string     path;       // "c", "node.lhs"
        std::string     root;       // the variable
        int             scope;      // which variable of that name
        uint16_t        cls;
    };

    static bool pathOf(const Expr *e, std::string &path, std::string &root) {
        if (e->kind == ExprKind::Ident) {
            path = root = e->name;
            return true;
        } else if (e->kind == ExprKind::Select && !e->testOnly && pathOf(e->operand.get(), path, root)) {
            path += "." + e->name;
            return true;
        }
        return false;
    }

    // The facts a true `cond` establishes: its `type(x) == K` and
    // `x.isa(K)` terms, through `&&`.
    void factsOf(const Expr *cond, std::vector<Fact> &out) const {
        if (cond->kind != ExprKind::Call) {
            return;
        }
        if (cond->operand) {
            const Expr *cls = cond->args.empty() ? nullptr : cond->args[0].get();
            uint16_t k;
            Fact f;
            if (cond->name == "isa" && cond->args.size() == 1 && cls->kind == ExprKind::Ident
                    && lookup(cls->name) < 0 && lookupClass(cls->name, k)
                    && pathOf(cond->operand.get(), f.path, f.root)) {
                f.scope = lookup(f.root);
                f.cls = k;
                if (f.scope >= 0) {
                    out.push_back(f);
                }
            }
            return;
        }
        if (cond->name == op::LogicalAnd) {
            for (const ExprUP &a : cond->args) {
                factsOf(a.get(), out);
            }
            return;
        }
        if (cond->name != op::Equals) {
            return;
        }
        for (int i=0; i<2; i++) {
            const Expr *call = cond->args[i].get(), *cls = cond->args[1-i].get();
            uint16_t k;
            Fact f;
            if (call->kind == ExprKind::Call && call->name == "type" && !call->operand
                    && call->args.size() == 1 && cls->kind == ExprKind::Ident
                    && lookup(cls->name) < 0 && lookupClass(cls->name, k)
                    && pathOf(call->args[0].get(), f.path, f.root)) {
                f.scope = lookup(f.root);
                f.cls = k;
                if (f.scope >= 0) {
                    out.push_back(f);
                }
            }
        }
    }

    // `t`, the type of `e`, narrowed by what the enclosing conditions know.
    Type narrowed(const Expr *e, const Type &t) const {
        if (m_facts.empty()) {
            return t;
        }
        Type r = resolve(t);
        std::string path, root;
        if (r.kind != Type::Kind::Node || !pathOf(e, path, root)) {
            return t;
        }
        for (auto it=m_facts.rbegin(); it!=m_facts.rend(); it++) {
            // The same variable: not one a comprehension has since bound.
            if (it->path == path && lookup(it->root) == it->scope
                    && (!r.cls || isSubclass(it->cls, r.cls))) {
                return Type::node(it->cls);
            }
        }
        return t;
    }

    // Checks `e` knowing that `cond` is true.
    ExprUP visitAssuming(const Expr *cond, const Expr *e, Type &t) {
        size_t n = m_facts.size();
        factsOf(cond, m_facts);
        ExprUP c = visit(e, t);
        m_facts.resize(n);
        return c;
    }

    // Where to report a bad field: at the field name, if the source has it
    // after the operand ("a.b"), else at the selection.
    static uint32_t selectOffset(const Expr *e) {
        if (e->operand && e->operand->end < e->end && !e->testOnly) {
            return e->operand->end + 1;
        }
        return e->begin;
    }

    ExprUP visitList(const Expr *e, Type &t) {
        ExprUP c = cloneShallow(e);
        Type elem = fresh();
        size_t next_opt = 0;
        bool bad = false;
        for (size_t i=0; i<e->args.size(); i++) {
            Type at;
            c->args.push_back(visit(e->args[i].get(), at));
            if (next_opt < e->optIndices.size() && e->optIndices[next_opt] == i) {
                next_opt++;
                Type inner = fresh(), o;
                if (!join(Type::optional(inner), at, o)) {
                    error(e->args[i]->begin, "an optional element '?e' needs an optional, not '"
                        + typeStr(at) + "'");
                    bad = true;
                    continue;
                }
                at = inner;
            }
            Type before = resolve(elem), j;
            if (!bad && !join(elem, at, j)) {
                error(e->args[i]->begin, "list elements must all have one type, but this one is '"
                    + typeStr(at) + "' and the ones before are '" + before.str()
                    + "' (pss-rules has no dyn)");
                bad = true;
            }
        }
        t = bad ? Type(Type::Kind::Error) : Type::list(elem);
        return c;
    }

    ExprUP visitMap(const Expr *e, Type &t) {
        ExprUP c = cloneShallow(e);
        Type kt = fresh(), vt = fresh();
        bool bad = false;
        for (const Entry &ent : e->entries) {
            Entry n;
            n.id = ent.id;
            n.begin = ent.begin;
            n.optional = ent.optional;
            Type k, v;
            n.key = visit(ent.key.get(), k);
            n.value = visit(ent.value.get(), v);
            c->entries.push_back(std::move(n));
            if (bad) {
                continue;
            }
            Type rk = resolve(k);
            using K = Type::Kind;
            if (!(rk.kind == K::Int || rk.kind == K::String || rk.kind == K::Bool
                    || rk.kind == K::Error || isVar(rk))) {
                error(ent.key->begin, "a map key must be an int, a string or a bool, not '"
                    + rk.str() + "'");
                bad = true;
                continue;
            }
            if (ent.optional) {
                Type inner = fresh(), o;
                if (!join(Type::optional(inner), v, o)) {
                    error(ent.value->begin, "an optional entry '?k: v' needs an optional value, not '"
                        + typeStr(v) + "'");
                    bad = true;
                    continue;
                }
                v = inner;
            }
            Type kb = resolve(kt), vb = resolve(vt), j;
            if (!join(kt, k, j)) {
                error(ent.key->begin, "map keys must all have one type, but this one is '"
                    + typeStr(k) + "' and the ones before are '" + kb.str()
                    + "' (pss-rules has no dyn)");
                bad = true;
            } else if (!join(vt, v, j)) {
                error(ent.value->begin, "map values must all have one type, but this one is '"
                    + typeStr(v) + "' and the ones before are '" + vb.str()
                    + "' (pss-rules has no dyn)");
                bad = true;
            }
        }
        t = bad ? Type(Type::Kind::Error) : Type::map(kt, vt);
        return c;
    }

    // A macro's condition, for the message when it is not a bool.
    struct Predicate {
        const Expr      *expr = nullptr;
        std::string     macro;
    };

    // An operand that must be bool: `&&`, `||`, the condition of `?:`, a
    // macro's condition.
    void requireBool(const Expr *operand, const Type &t, const std::string &context) {
        Type r = resolve(t), j;
        if (r.kind == Type::Kind::Error || join(Type(Type::Kind::Bool), t, j)) {
            return;
        }
        if (operand == m_pred.expr) {
            error(operand->begin, "the condition of " + m_pred.macro + "() must be bool, not '"
                + r.str() + "'");
        } else {
            error(operand->begin, context + " must be bool, not '" + r.str() + "'");
        }
    }

    ExprUP visitComprehension(const Expr *e, Type &t) {
        ExprUP c = cloneShallow(e);
        if (e->iterVar == "#unused") {
            // cel.bind(v, init, body): not iteration, and not nesting.
            Type it;
            c->iterRange = cloneDeep(e->iterRange.get());
            c->accuInit = visit(e->accuInit.get(), it);
            c->loopCond = cloneDeep(e->loopCond.get());
            c->loopStep = cloneDeep(e->loopStep.get());
            push(e->accuVar, e->accuVar, it);
            c->result = visit(e->result.get(), t);
            pop();
            return c;
        }

        // Nesting is of loop bodies: the range, the initial value and the
        // result are evaluated once, at the enclosing level, so a receiver
        // chain (`l.filter(...).map(...)`) is not nesting. Reported once per
        // body at the limit, at its first comprehension past the limit.
        std::string macro = e->name.empty() ? std::string("comprehension") : e->name;
        if (m_nesting == m_opts.maxNesting && !m_nesting_reported) {
            m_nesting_reported = true;
            error(e->begin, macro + "() nests comprehensions " + std::to_string(m_nesting + 1)
                + " deep, and at most " + std::to_string(m_opts.maxNesting) + " are allowed in"
                " one expression or helper; move the inner part into a define: helper",
                CheckError::Kind::Limit);
        }

        Type range;
        c->iterRange = visit(e->iterRange.get(), range);
        Type rr = resolve(range), iter;
        switch (rr.kind) {
            case Type::Kind::List: iter = rr.args[0]; break;
            case Type::Kind::Map: iter = rr.args[0]; break;
            case Type::Kind::Error: iter = rr; break;
            default:
                error(e->iterRange->begin, macro + "() needs a list or a map, not '"
                    + rr.str() + "'");
                iter = Type(Type::Kind::Error);
                break;
        }

        Type accu;
        c->accuInit = visit(e->accuInit.get(), accu);
        push(e->iterVar, e->iterVar, iter);
        push(e->accuVar, e->accuVar, accu);

        bool reported = m_nesting_reported;
        if (++m_nesting == m_opts.maxNesting) {
            m_nesting_reported = false;
        }
        Type cond;
        c->loopCond = visit(e->loopCond.get(), cond);

        Predicate saved = m_pred;
        m_pred = Predicate();
        const Expr *step = e->loopStep.get();
        if (step->kind == ExprKind::Call) {
            if (step->name == op::LogicalAnd || step->name == op::LogicalOr) {
                m_pred.expr = step->args[1].get();          // all, exists
            } else if (step->name == op::Conditional) {
                m_pred.expr = step->args[0].get();          // exists_one, filter, map(x, p, t)
            }
        }
        m_pred.macro = macro;
        Type st, j;
        c->loopStep = visit(step, st);
        m_pred = saved;
        m_nesting--;
        m_nesting_reported = reported;
        if (!join(accu, st, j)) {
            error(e->begin, macro + "(): the step's type '" + typeStr(st)
                + "' does not match the accumulator's '" + typeStr(accu) + "'");
        }
        m_scope.pop_back();     // the iteration variable, under the accumulator
        m_scope.pop_back();
        m_runtime.pop_back();
        m_runtime.pop_back();
        push(e->accuVar, e->accuVar, accu);
        c->result = visit(e->result.get(), t);
        pop();
        return c;
    }

    ExprUP visitCall(const Expr *e, Type &t) {
        const std::string &fn = e->name;

        if (fn == op::LogicalAnd || fn == op::LogicalOr) {
            ExprUP c = cloneShallow(e);
            for (size_t i=0; i<e->args.size(); i++) {
                const Expr *a = e->args[i].get();
                Type at;
                c->args.push_back((i == 1 && fn == op::LogicalAnd) ?
                    visitAssuming(e->args[0].get(), a, at) : visit(a, at));
                requireBool(a, at, "an operand of '" + surfaceName(fn) + "'");
            }
            use(fn);
            t = Type(Type::Kind::Bool);
            return c;
        } else if (fn == op::Conditional) {
            ExprUP c = cloneShallow(e);
            Type ct, a, b, j;
            c->args.push_back(visit(e->args[0].get(), ct));
            requireBool(e->args[0].get(), ct, "the condition of '?:'");
            c->args.push_back(visitAssuming(e->args[0].get(), e->args[1].get(), a));
            c->args.push_back(visit(e->args[2].get(), b));
            Type ra = resolve(a), rb = resolve(b);
            if (!join(a, b, j)) {
                error(e->args[2]->begin, "the two results of '?:' must have one type, but they are '"
                    + ra.str() + "' and '" + rb.str() + "'");
                j = Type(Type::Kind::Error);
            }
            use(fn);
            t = j;
            return c;
        } else if (fn == op::NotStrictlyFalse) {
            ExprUP c = cloneShallow(e);
            Type at;
            c->args.push_back(visit(e->args[0].get(), at));
            t = Type(Type::Kind::Bool);
            return c;
        } else if (fn == op::OptSelect) {
            // a.?f: optional(the field's type)
            ExprUP c = cloneShallow(e);
            Type ot;
            c->args.push_back(visit(e->args[0].get(), ot));
            c->args.push_back(cloneDeep(e->args[1].get()));
            Type r = resolve(ot);
            Type on = (r.kind == Type::Kind::Optional) ? r.args[0] : r;
            int32_t index;
            Type ft = fieldOf(on, e->args[0].get(), e->args[1]->cval.s, e->args[1]->begin, index);
            use(fn);
            t = (ft.kind == Type::Kind::Error) ? ft : Type::optional(ft);
            return c;
        }

        // A helper.
        if (!e->operand) {
            if (const Define *d = findDefine(m_env, fn, true)) {
                if (d->params.size() != e->args.size()) {
                    error(e->begin, "helper '" + fn + "' takes " + std::to_string(d->params.size())
                        + (d->params.size() == 1 ? " argument" : " arguments") + ", not "
                        + std::to_string(e->args.size()));
                    t = Type(Type::Kind::Error);
                    return cloneShallow(e);
                }
                std::vector<ExprUP> args;
                std::vector<Type> types;
                for (const ExprUP &a : e->args) {
                    Type at;
                    args.push_back(visit(a.get(), at));
                    types.push_back(at);
                }
                return inlineDefine(*d, e, std::move(args), types, t);
            }
        }

        // A namespaced global, `optional.of(x)`, unless `optional` is a variable.
        std::string name = fn;
        const Expr *target = e->operand.get();
        if (target && target->kind == ExprKind::Ident && lookup(target->name) < 0
                && m_reg.hasFunction(target->name + "." + fn)) {
            name = target->name + "." + fn;
            target = nullptr;
        }

        ExprUP c = cloneShallow(e);
        c->name = name;
        std::vector<Type> types;
        bool poisoned = false;
        if (target) {
            Type tt;
            c->operand = visit(target, tt);
            types.push_back(tt);
            poisoned |= (resolve(tt).kind == Type::Kind::Error);
        }
        for (const ExprUP &a : e->args) {
            Type at;
            c->args.push_back(visit(a.get(), at));
            types.push_back(at);
            poisoned |= (resolve(at).kind == Type::Kind::Error);
        }

        const std::vector<const Overload *> *cands = m_reg.find(name);
        if (!cands) {
            if (!e->operand && findDefine(m_env, fn, false)) {
                error(e->begin, "'" + fn + "' is a helper without parameters; write it without ()");
            } else {
                error(e->begin, "undeclared reference to function '" + name + "'");
            }
            t = Type(Type::Kind::Error);
            return c;
        }
        if (poisoned) {
            t = Type(Type::Kind::Error);
            return c;
        }
        t = resolveCall(e, name, target != nullptr, types, *cands, c->overload);
        if (c->overload && c->overload->classArg >= 0 && t.kind != Type::Kind::Error) {
            classOperand(e, *c->overload, types, t);
        }
        if (name == "matches" && t.kind != Type::Kind::Error) {
            literalPattern(target ? e->args[0].get() : e->args[1].get(), *c, t);
        }
        if (t.kind != Type::Kind::Error) {
            flagsOperands(e, name, types, t);
        }
        if ((name == "type_named" || name == "derives_from") && !target
                && t.kind != Type::Kind::Error) {
            literalTypePath(e->args[name == "type_named" ? 0 : 1].get(), t);
        }
        return c;
    }

    // The enum an int is a value of, or "".
    std::string enumOf(const Type &t) {
        Type r = resolve(t);
        return (r.kind == Type::Kind::Int) ? r.param : std::string();
    }

    // An argument as written, for a message: `FieldAttr.Rand`, `node.attr`.
    static std::string spelled(const Expr *e) {
        std::string path, root;
        if (pathOf(e, path, root)) {
            return path;
        }
        return "the argument";
    }

    // Flags words (C6.8; E4 of linter-post-readiness-2026-10-11.md). A
    // flags value is tested with has_flag(); used as a number (int(), string(),
    // arithmetic, ordering) it would depend on the bit values, which are the
    // AST's, not the rule format's. has_flag() takes ints, but a constant of
    // the wrong enum, or of one that is not flags, is an error.
    void flagsOperands(const Expr *e, const std::string &name, const std::vector<Type> &types,
            Type &t) {
        static const std::unordered_set<std::string> numeric = {
            "int", "double", "string", "_+_", "_-_", "_*_", "_/_", "_%_", "-_",
            "_<_", "_<=_", "_>_", "_>=_"};
        std::vector<const Expr *> args;
        if (e->operand) {
            args.push_back(e->operand.get());
        }
        for (const ExprUP &a : e->args) {
            args.push_back(a.get());
        }
        if (name == "has_flag" && types.size() == 2) {
            std::string word = enumOf(types[0]), flag = enumOf(types[1]);
            if (!word.empty() && !isFlagsEnum(word)) {
                error(args[0]->begin, "has_flag() tests a set of flags, and " + spelled(args[0])
                    + " is a '" + word + "' value, which is not one; compare it with == instead");
                t = Type(Type::Kind::Error);
            } else if (!flag.empty() && !isFlagsEnum(flag)) {
                error(args[1]->begin, spelled(args[1]) + " is a member of enum '" + flag
                    + "', which is not a set of flags");
                t = Type(Type::Kind::Error);
            } else if (!word.empty() && !flag.empty() && word != flag) {
                error(args[1]->begin, spelled(args[1]) + " is not a '" + word + "' flag, and "
                    + spelled(args[0]) + " is a set of '" + word + "' flags");
                t = Type(Type::Kind::Error);
            }
            return;
        }
        if (!numeric.count(name)) {
            return;
        }
        for (size_t i=0; i<types.size() && i<args.size(); i++) {
            std::string en = enumOf(types[i]);
            if (en.empty() || !isFlagsEnum(en)) {
                continue;
            }
            const Expr *a = args[i];
            bool constant = a->kind == ExprKind::Select && a->operand
                && a->operand->kind == ExprKind::Ident && a->operand->name == en;
            std::string word = (constant || spelled(a) == "the argument") ? "x" : spelled(a);
            error(a->begin, spelled(a) + (constant ? " is a '" + en + "' flag" :
                " is a set of '" + en + "' flags") + ", not a number: test a flag with has_flag("
                + word + ", " + en + "." + (constant ? a->name : std::string("<flag>")) + ")");
            t = Type(Type::Kind::Error);
            return;
        }
    }

    // type_named() and derives_from() with a literal path: it must be a PSS
    // type name, `p::S` or `::S`, with no template arguments.
    void literalTypePath(const Expr *path, Type &t) {
        if (path->kind != ExprKind::Const || path->cval.kind != Const::Kind::String) {
            return;
        }
        std::string why;
        if (!typePathValid(path->cval.s, why)) {
            error(path->begin, "'" + path->cval.s + "' is not a PSS type name: " + why);
            t = Type(Type::Kind::Error);
        }
    }

    // `n.isa(Action)`, `enclosing(n, Action)`: the operand must be a node
    // class, known here; enclosing()'s result is a node of that class.
    void classOperand(const Expr *e, const Overload &o, const std::vector<Type> &types,
            Type &t) {
        size_t i = static_cast<size_t>(o.classArg);
        const Expr *arg = e->operand ? (i ? e->args[i-1].get() : e->operand.get())
            : e->args[i].get();
        Type r = resolve(types[i]);
        uint16_t cls;
        if (r.kind != Type::Kind::TypeType || !lookupClass(r.param, cls)) {
            std::string what = (r.kind == Type::Kind::TypeType && !r.param.empty()) ?
                "'" + r.param + "'" : "a '" + r.str() + "' value";
            error(arg->begin, surfaceName(o.function) + "() needs a node class, such as Action, "
                "written out; " + what + " is not one");
            t = Type(Type::Kind::Error);
            return;
        }
        if (o.resultIsClass) {
            t = Type::node(cls);
        }
    }

    // matches() with a literal pattern: compiled now, once, so a pattern
    // outside the supported RE2 syntax is a check error, not a run-time one.
    void literalPattern(const Expr *pattern, Expr &call, Type &t) {
        if (pattern->kind != ExprKind::Const || pattern->cval.kind != Const::Kind::String) {
            return;
        }
        try {
            call.regex.reset(regex::Regex::compile(pattern->cval.s));
        } catch (const regex::RegexError &ex) {
            error(pattern->begin, std::string("invalid regular expression: ") + ex.what()
                + " (at byte " + std::to_string(ex.offset()) + " of the pattern)",
                CheckError::Kind::Limit);
            t = Type(Type::Kind::Error);
        }
    }

    void use(const std::string &fn) {
        if (const std::vector<const Overload *> *os = m_reg.find(fn)) {
            m_used.insert(os->front());
        }
    }

    Type resolveCall(const Expr *e, const std::string &name, bool receiver,
            const std::vector<Type> &types, const std::vector<const Overload *> &cands,
            const Overload *&chosen) {
        struct Match {
            const Overload                          *o;
            std::unordered_map<std::string, Type>   subst;
            Type                                    result;
        };
        std::vector<Match> matches;
        const Overload *excluded = nullptr;
        const auto start = m_subst;
        const int startVar = m_nextVar;

        // `1 == 1.0`, `1 in [1.0]`: equality across int and double is in the
        // profile, which a signature of (A, A) cannot say.
        bool hetero = false;
        if (types.size() == 2 && !receiver) {
            Type a = resolve(types[0]), b = resolve(types[1]);
            if (name == op::Equals || name == op::NotEquals) {
                hetero = isNumeric(a) && isNumeric(b) && a.kind != b.kind;
            } else if (name == op::In && isNumeric(a)) {
                if ((b.kind == Type::Kind::List || b.kind == Type::Kind::Map)
                        && isNumeric(resolve(b.args[0])) && resolve(b.args[0]).kind != a.kind) {
                    hetero = true;
                }
            }
        }

        for (const Overload *o : cands) {
            if (o->kind == FnKind::Macro || o->receiver != receiver
                    || o->params.size() != types.size()) {
                continue;
            }
            if (hetero) {
                bool fits = (name != op::In) || (resolve(types[1]).kind == Type::Kind::List) ==
                    (o->params[1].kind == Type::Kind::List);
                if (fits) {
                    matches.push_back({o, m_subst, Type(Type::Kind::Bool)});
                    break;
                }
                continue;
            }
            m_subst = start;
            std::unordered_map<std::string, Type> vars;
            bool ok = true;
            for (size_t i=0; i<types.size() && ok; i++) {
                Type j;
                ok = join(instantiate(o->params[i], vars), types[i], j);
            }
            if (!ok) {
                continue;
            }
            if (!o->inProfile) {
                excluded = excluded ? excluded : o;
                continue;
            }
            matches.push_back({o, m_subst, instantiate(o->result, vars)});
        }

        if (matches.empty()) {
            m_subst = start;
            m_nextVar = startVar;
            if (excluded) {
                error(e->begin, "'" + excluded->display + "' is not supported in pss-rules");
            } else {
                error(e->begin, noMatch(name, receiver, types, cands));
            }
            return Type(Type::Kind::Error);
        }
        if (matches.size() == 1) {
            m_subst = matches[0].subst;
            chosen = matches[0].o->impl ? matches[0].o : nullptr;
            m_used.insert(matches[0].o);
            return matches[0].result;
        }
        // Several fit (operands whose type is not yet known): fine if they
        // agree on the result; the evaluator picks one by the values. The
        // operands stay as unknown as they were.
        std::string r0;
        Type result;
        for (size_t i=0; i<matches.size(); i++) {
            m_subst = matches[i].subst;
            Type r = resolve(matches[i].result);
            if (i == 0) {
                r0 = r.str();
                result = r;
            } else if (r.str() != r0) {
                m_subst = start;
                error(e->begin, "cannot tell which '" + surfaceName(name)
                    + "' applies: the operand types are not known well enough");
                return Type(Type::Kind::Error);
            }
        }
        m_subst = start;
        for (const Match &m : matches) {
            m_used.insert(m.o);
        }
        chosen = nullptr;
        return result;
    }

    std::string noMatch(const std::string &name, bool receiver, const std::vector<Type> &types,
            const std::vector<const Overload *> &cands) const {
        std::string msg = "no matching overload for '" + surfaceName(name) + "' applied to (";
        for (size_t i=0; i<types.size(); i++) {
            msg += (i ? ", " : "") + typeStr(types[i]);
        }
        msg += ")";
        if (receiver) {
            msg += " (the first is the receiver)";
        }
        std::vector<std::string> forms;
        for (const Overload *o : cands) {
            if (o->kind != FnKind::Macro && o->inProfile) {
                forms.push_back(o->display);
            }
        }
        if (!forms.empty() && forms.size() <= 6) {
            msg += "; it takes ";
            for (size_t i=0; i<forms.size(); i++) {
                msg += (i ? (i + 1 == forms.size() ? " or " : ", ") : "") + forms[i];
            }
        }
        return msg;
    }

    //************************************************************************
    //* define: helpers
    //************************************************************************

    /**
     * `site` uses helper `d` with checked arguments `args` (of types
     * `types`). The body is checked with only the declared variables and the
     * parameters in scope; the result is the body, each parameter bound to
     * its argument by a cel.bind under a name no rule can write.
     */
    ExprUP inlineDefine(const Define &d, const Expr *site, std::vector<ExprUP> args,
            const std::vector<Type> &types, Type &t) {
        for (size_t i=0; i<m_inlining.size(); i++) {
            if (m_inlining[i] == &d) {
                std::string path;
                for (size_t j=i; j<m_inlining.size(); j++) {
                    path += m_inlining[j]->name + " -> ";
                }
                error(site->begin, "helpers call each other in a cycle: " + path + d.name,
                    CheckError::Kind::Limit);
                t = Type(Type::Kind::Error);
                return cloneShallow(site);
            }
        }
        // A helper with errors of its own: checkDefines() reports them, once.
        if (m_bad.count(&d)) {
            m_failed = true;
            t = Type(Type::Kind::Error);
            return cloneShallow(site);
        }

        // The body sees the declared variables and its parameters, nothing of
        // the expression that uses it.
        std::vector<Var> saved(m_scope.begin() + m_globals, m_scope.end());
        m_scope.resize(m_globals);
        std::vector<std::string> runtime;
        for (size_t i=0; i<d.params.size(); i++) {
            runtime.push_back("@" + d.name + "." + d.params[i]);
            push(d.params[i], runtime.back(), types[i]);
        }
        uint32_t source = m_source;
        int nesting = m_nesting;
        bool nesting_reported = m_nesting_reported;
        Predicate pred = m_pred;
        m_source = d.source;
        m_nesting = 0;
        m_nesting_reported = false;
        m_pred = Predicate();
        m_inlining.push_back(&d);

        ExprUP body = visit(d.body, t);

        m_inlining.pop_back();
        m_source = source;
        m_nesting = nesting;
        m_nesting_reported = nesting_reported;
        m_pred = pred;
        for (size_t i=0; i<d.params.size(); i++) {
            pop();
        }
        m_scope.insert(m_scope.end(), saved.begin(), saved.end());

        for (size_t i=d.params.size(); i-- > 0; ) {
            body = mkBind(runtime[i], std::move(args[i]), std::move(body), site);
        }
        return body;
    }

    static ExprUP mkBind(const std::string &var, ExprUP init, ExprUP body, const Expr *site) {
        auto mk = [site](ExprKind k) {
            ExprUP x(new Expr());
            x->kind = k;
            x->begin = site->begin;
            x->end = site->end;
            return x;
        };
        ExprUP c = mk(ExprKind::Comprehension);
        c->name = "cel.bind";
        c->iterVar = "#unused";
        c->iterRange = mk(ExprKind::List);
        c->accuVar = var;
        c->accuInit = std::move(init);
        c->loopCond = mk(ExprKind::Const);
        c->loopCond->cval.kind = Const::Kind::Bool;
        c->loopStep = mk(ExprKind::Ident);
        c->loopStep->name = var;
        c->result = std::move(body);
        return c;
    }

private:
    const CheckEnv                              &m_env;
    const CheckOptions                          &m_opts;
    const FunctionRegistry                      &m_reg;
    std::vector<CheckError>                     m_errors;
    std::unordered_map<std::string, Type>       m_subst;
    int                                         m_nextVar = 0;
    uint32_t                                    m_source = 0;
    std::vector<Var>                            m_scope;
    size_t                                      m_globals = 0;
    // Every variable the evaluator will have bound at this point, inlined
    // helpers' callers included.
    std::vector<std::string>                    m_runtime;
    int                                         m_nesting = 0;     // loop bodies around this point
    bool                                        m_nesting_reported = false;
    Predicate                                   m_pred;
    std::vector<const Define *>                 m_inlining;
    std::vector<Fact>                           m_facts;
    const std::unordered_set<const Define *>    &m_bad;
    bool                                        m_failed = false;
    std::unordered_set<const Overload *>        m_used;
};

// The helpers a body uses, with the offset of each use; names its own
// comprehension variables hide are not uses.
void helperUses(const CheckEnv &env, const Expr *e, std::vector<std::string> &bound,
        std::vector<std::pair<const Define *, uint32_t>> &out) {
    if (!e) {
        return;
    }
    auto isBound = [&bound](const std::string &n) {
        for (const std::string &b : bound) {
            if (b == n) {
                return true;
            }
        }
        return false;
    };
    switch (e->kind) {
        case ExprKind::Ident:
            if (!isBound(e->name)) {
                if (const Define *d = findDefine(env, e->name, false)) {
                    out.push_back({d, e->begin});
                }
            }
            break;
        case ExprKind::Call:
            if (!e->operand) {
                if (const Define *d = findDefine(env, e->name, true)) {
                    out.push_back({d, e->begin});
                }
            }
            helperUses(env, e->operand.get(), bound, out);
            for (const ExprUP &a : e->args) {
                helperUses(env, a.get(), bound, out);
            }
            break;
        case ExprKind::Select:
            helperUses(env, e->operand.get(), bound, out);
            break;
        case ExprKind::List:
            for (const ExprUP &a : e->args) {
                helperUses(env, a.get(), bound, out);
            }
            break;
        case ExprKind::Map:
        case ExprKind::Struct:
            for (const Entry &ent : e->entries) {
                helperUses(env, ent.key.get(), bound, out);
                helperUses(env, ent.value.get(), bound, out);
            }
            break;
        case ExprKind::Comprehension:
            helperUses(env, e->iterRange.get(), bound, out);
            helperUses(env, e->accuInit.get(), bound, out);
            bound.push_back(e->iterVar);
            bound.push_back(e->accuVar);
            helperUses(env, e->loopCond.get(), bound, out);
            helperUses(env, e->loopStep.get(), bound, out);
            helperUses(env, e->result.get(), bound, out);
            bound.pop_back();
            bound.pop_back();
            break;
        case ExprKind::Const:
            break;
    }
}

// Errors in the helpers themselves, whatever uses them: names, parameters,
// the profile, and cycles. `bad` collects the helpers they make unusable.
void defineErrors(const CheckEnv &env, std::vector<CheckError> &errs,
        std::unordered_set<const Define *> &bad) {
    const FunctionRegistry &reg = FunctionRegistry::get();
    for (const Define &d : env.defines) {
        if (!d.body) {
            bad.insert(&d);     // unparsable: the caller reported it
            continue;
        }
        if (d.call && reg.hasFunction(d.name)) {
            errs.push_back({d.source, 0, "helper '" + d.name + "' has the name of a library "
                "function, which it would hide"});
            bad.insert(&d);
        }
        for (size_t i=0; i<d.params.size(); i++) {
            for (size_t j=0; j<i; j++) {
                if (d.params[i] == d.params[j]) {
                    errs.push_back({d.source, 0, "helper '" + d.name
                        + "' has two parameters named '" + d.params[i] + "'"});
                    bad.insert(&d);
                }
            }
        }
        for (const ProfileError &pe : checkProfile(d.body)) {
            errs.push_back({d.source, pe.offset, pe.message, CheckError::Kind::Profile});
            bad.insert(&d);
        }
    }

    // Cycles: a depth-first walk over the helper call graph, reporting each
    // cycle once, at the use that closes it.
    std::unordered_map<const Define *, std::vector<std::pair<const Define *, uint32_t>>> edges;
    for (const Define &d : env.defines) {
        std::vector<std::string> bound(d.params);
        helperUses(env, d.body, bound, edges[&d]);
    }
    enum class Mark { None, Active, Done };
    std::unordered_map<const Define *, Mark> mark;
    std::vector<const Define *> path;
    std::function<void(const Define *)> dfs = [&](const Define *d) {
        mark[d] = Mark::Active;
        path.push_back(d);
        for (const auto &use : edges[d]) {
            if (mark[use.first] == Mark::Active) {
                std::string p;
                bool on = false;
                for (const Define *x : path) {
                    on |= (x == use.first);
                    if (on) {
                        p += x->name + " -> ";
                        bad.insert(x);
                    }
                }
                errs.push_back({d->source, use.second,
                    "helpers call each other in a cycle: " + p + use.first->name,
                    CheckError::Kind::Limit});
            } else if (mark[use.first] == Mark::None) {
                dfs(use.first);
            }
        }
        path.pop_back();
        mark[d] = Mark::Done;
    };
    for (const Define &d : env.defines) {
        if (mark[&d] == Mark::None) {
            dfs(&d);
        }
    }
}

}

CelChecker::CelChecker(const CheckEnv &env, const CheckOptions &opts) :
    m_env(env), m_opts(opts) {
    defineErrors(env, m_define_errors, m_bad);
}

CheckResult CelChecker::check(const Expr *e, uint32_t source,
        const Type *expected, const char *what) const {
    Checker c(m_env, m_opts, m_bad);
    return c.run(e, source, expected, what);
}

std::vector<CheckError> CelChecker::checkDefines() const {
    return m_define_errors;
}

bool parseDefineHead(const std::string &key, Define &out, std::string &err) {
    size_t lp = key.find('(');
    std::string name = key.substr(0, lp);
    while (!name.empty() && name.back() == ' ') {
        name.pop_back();
    }
    if (!isIdentText(name)) {
        err = "a helper is 'name' or 'name(param, ...)', not '" + key + "'";
        return false;
    }
    out.name = name;
    out.params.clear();
    out.call = (lp != std::string::npos);
    if (!out.call) {
        return true;
    }
    if (key.back() != ')') {
        err = "a helper is 'name' or 'name(param, ...)', not '" + key + "'";
        return false;
    }
    std::string inner = key.substr(lp + 1, key.size() - lp - 2);
    size_t b = 0;
    while (b <= inner.size()) {
        size_t c = inner.find(',', b);
        std::string p = inner.substr(b, (c == std::string::npos) ? std::string::npos : c - b);
        size_t s = p.find_first_not_of(' '), e = p.find_last_not_of(' ');
        p = (s == std::string::npos) ? "" : p.substr(s, e - s + 1);
        if (p.empty() && c == std::string::npos && out.params.empty()) {
            break;      // name()
        }
        if (!isIdentText(p)) {
            err = "helper '" + name + "': '" + p + "' is not a parameter name";
            return false;
        }
        out.params.push_back(p);
        if (c == std::string::npos) {
            break;
        }
        b = c + 1;
    }
    return true;
}

Type typeOfValue(const Value &v) {
    static int next = 0;
    auto unknown = []() { return Type::var("%v" + std::to_string(++next)); };
    using K = Value::Kind;
    switch (v.kind) {
        case K::Null: return Type(Type::Kind::Null);
        case K::Bool: return Type(Type::Kind::Bool);
        case K::Int: return Type(Type::Kind::Int);
        case K::Double: return Type(Type::Kind::Double);
        case K::String: return Type(Type::Kind::String);
        case K::Type: return Type::typeOf(v.s);
        case K::Node: return Type::node(v.node.kind);
        case K::Struct: return Type::structType(static_cast<uint16_t>(v.i));
        case K::List:
            return Type::list(v.list->empty() ? unknown() : typeOfValue(v.list->front()));
        case K::Map:
            if (v.map->empty()) {
                Type k = unknown();
                return Type::map(k, unknown());
            }
            return Type::map(typeOfValue(v.map->front().first), typeOfValue(v.map->front().second));
        case K::Optional:
            return Type::optional(v.opt ? typeOfValue(*v.opt) : unknown());
        case K::Error: return Type(Type::Kind::Error);
    }
    return Type(Type::Kind::Error);
}

}
}
}
