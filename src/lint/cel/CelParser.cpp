/*
 * CelParser.cpp
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
#include <cstring>
#include "CelParser.h"

namespace pssp {
namespace lint {
namespace cel {

namespace {

// Reserved by the spec for embedding hosts: never an identifier or a global
// function name (receiver-call names and field selectors may use them).
const char *Reserved[] = {
    "as", "break", "const", "continue", "else", "for", "function", "if",
    "import", "let", "loop", "package", "namespace", "return", "var", "void",
    "while", nullptr
};

bool isReserved(const std::string &s) {
    for (const char **r=Reserved; *r; r++) {
        if (s == *r) {
            return true;
        }
    }
    return false;
}

struct DepthGuard {
    DepthGuard(int &d) : m_d(d) { m_d++; }
    ~DepthGuard() { m_d--; }
    int &m_d;
};

}

CelParser::CelParser(const std::string &text, const ParseOptions &opts) :
    m_text(text), m_opts(opts), m_idx(0), m_next_id(1), m_depth(0) {

}

ExprUP CelParser::parse() {
    CelLexer lexer(m_text);
    m_toks = lexer.tokenize();
    m_idx = 0;

    if (at(Tok::End)) {
        fail("expected an expression");
    }
    ExprUP e = parseExpr();
    if (!at(Tok::End)) {
        fail(std::string("unexpected ") + tokName(tok().kind) + " after the end of the expression");
    }
    return e;
}

const Token &CelParser::expect(Tok k, const char *context) {
    if (!at(k)) {
        fail(std::string("expected ") + tokName(k) + " " + context
            + ", found " + tokName(tok().kind));
    }
    return advance();
}

void CelParser::fail(const std::string &msg) {
    throw SyntaxError(tok().begin, msg);
}

void CelParser::fail(uint32_t offset, const std::string &msg) {
    throw SyntaxError(offset, msg);
}

ExprUP CelParser::mk(ExprKind kind, uint32_t begin, uint32_t end) {
    ExprUP e(new Expr());
    e->id = m_next_id++;
    e->kind = kind;
    e->begin = begin;
    e->end = end;
    return e;
}

// Computes a composite node's height from its children, which are complete,
// and enforces maxHeight. Every node with children passes through here when
// it is built, so the limit trips before a tall tree exists. `op_pos` is the
// operator that joins the children, where the error is reported: in a long
// `a + a + ...` chain, the `+` that went one level too far.
ExprUP CelParser::seal(ExprUP e, uint32_t op_pos) {
    uint32_t h = 0;
    auto take = [&h](const ExprUP &c) {
        if (c && c->height > h) {
            h = c->height;
        }
    };
    take(e->operand);
    for (const ExprUP &a : e->args) {
        take(a);
    }
    for (const Entry &ent : e->entries) {
        take(ent.key);
        take(ent.value);
    }
    take(e->iterRange);
    take(e->accuInit);
    take(e->loopCond);
    take(e->loopStep);
    take(e->result);
    e->height = h + 1;
    if (e->height > m_opts.maxHeight) {
        fail((op_pos != NoPos) ? op_pos : e->begin, "expression is too deeply nested (more than "
            + std::to_string(m_opts.maxHeight) + " levels); split it with let: or define:");
    }
    return e;
}

ExprUP CelParser::mkCall(const char *fn, uint32_t begin, uint32_t end) {
    ExprUP e = mk(ExprKind::Call, begin, end);
    e->name = fn;
    return e;
}

ExprUP CelParser::mkCall1(const char *fn, ExprUP a) {
    ExprUP e = mkCall(fn, a->begin, a->end);
    e->args.push_back(std::move(a));
    return seal(std::move(e));
}

ExprUP CelParser::mkCall2(const char *fn, ExprUP a, ExprUP b, uint32_t op_pos) {
    ExprUP e = mkCall(fn, a->begin, b->end);
    e->args.push_back(std::move(a));
    e->args.push_back(std::move(b));
    return seal(std::move(e), op_pos);
}

ExprUP CelParser::mkIdent(const std::string &name, uint32_t begin, uint32_t end) {
    ExprUP e = mk(ExprKind::Ident, begin, end);
    e->name = name;
    return e;
}

ExprUP CelParser::mkBool(bool v, uint32_t begin, uint32_t end) {
    ExprUP e = mk(ExprKind::Const, begin, end);
    e->cval.kind = Const::Kind::Bool;
    e->cval.b = v;
    return e;
}

// Expr = ConditionalOr ["?" ConditionalOr ":" Expr]
ExprUP CelParser::parseExpr() {
    DepthGuard g(m_depth);
    if (m_depth > m_opts.maxDepth) {
        fail("expression nests too deeply (limit " + std::to_string(m_opts.maxDepth) + ")");
    }

    ExprUP cond = parseOr();
    if (!at(Tok::Question)) {
        return cond;
    }
    uint32_t q = advance().begin;
    ExprUP t = parseOr();
    expect(Tok::Colon, "in a conditional ('?:')");
    ExprUP f = parseExpr();

    ExprUP e = mkCall(op::Conditional, cond->begin, f->end);
    e->args.push_back(std::move(cond));
    e->args.push_back(std::move(t));
    e->args.push_back(std::move(f));
    return seal(std::move(e), q);
}

// Logical chains are built balanced, as cel-go does, so a long `a || b || ...`
// costs log(n) evaluator depth rather than n.
// ops[i] is the operator between terms[i] and terms[i+1].
ExprUP CelParser::balance(const char *fn, std::vector<ExprUP> &terms,
        const std::vector<uint32_t> &ops, size_t lo, size_t hi) {
    if (lo == hi) {
        return std::move(terms[lo]);
    }
    size_t mid = (lo + hi + 1) / 2;
    ExprUP l = balance(fn, terms, ops, lo, mid-1);
    ExprUP r = balance(fn, terms, ops, mid, hi);
    return mkCall2(fn, std::move(l), std::move(r), ops[mid-1]);
}

ExprUP CelParser::parseOr() {
    std::vector<ExprUP> terms;
    std::vector<uint32_t> ops;
    terms.push_back(parseAnd());
    while (at(Tok::OrOr)) {
        ops.push_back(advance().begin);
        terms.push_back(parseAnd());
    }
    return balance(op::LogicalOr, terms, ops, 0, terms.size()-1);
}

ExprUP CelParser::parseAnd() {
    std::vector<ExprUP> terms;
    std::vector<uint32_t> ops;
    terms.push_back(parseRelation());
    while (at(Tok::AndAnd)) {
        ops.push_back(advance().begin);
        terms.push_back(parseRelation());
    }
    return balance(op::LogicalAnd, terms, ops, 0, terms.size()-1);
}

ExprUP CelParser::parseRelation() {
    ExprUP lhs = parseAddition();
    while (true) {
        const char *fn = nullptr;
        switch (tok().kind) {
            case Tok::Lt: fn = op::Less; break;
            case Tok::Le: fn = op::LessEquals; break;
            case Tok::Gt: fn = op::Greater; break;
            case Tok::Ge: fn = op::GreaterEquals; break;
            case Tok::EqEq: fn = op::Equals; break;
            case Tok::Ne: fn = op::NotEquals; break;
            case Tok::In: fn = op::In; break;
            default: break;
        }
        if (!fn) {
            return lhs;
        }
        uint32_t at_op = advance().begin;
        ExprUP rhs = parseAddition();
        lhs = mkCall2(fn, std::move(lhs), std::move(rhs), at_op);
    }
}

ExprUP CelParser::parseAddition() {
    ExprUP lhs = parseMultiplication();
    while (at(Tok::Plus) || at(Tok::Minus)) {
        const char *fn = at(Tok::Plus) ? op::Add : op::Subtract;
        uint32_t at_op = advance().begin;
        ExprUP rhs = parseMultiplication();
        lhs = mkCall2(fn, std::move(lhs), std::move(rhs), at_op);
    }
    return lhs;
}

ExprUP CelParser::parseMultiplication() {
    ExprUP lhs = parseUnary();
    while (at(Tok::Star) || at(Tok::Slash) || at(Tok::Percent)) {
        const char *fn = at(Tok::Star) ? op::Multiply :
            at(Tok::Slash) ? op::Divide : op::Modulo;
        uint32_t at_op = advance().begin;
        ExprUP rhs = parseUnary();
        lhs = mkCall2(fn, std::move(lhs), std::move(rhs), at_op);
    }
    return lhs;
}

// Unary = Member | "!" {"!"} Member | "-" {"-"} Member
//
// As in CEL.g4, a '-' directly before a numeric literal is the literal's sign
// (so -9223372036854775808 is representable, and -1.5 is a constant), and
// only the remaining minus signs become negation calls.
ExprUP CelParser::parseUnary() {
    if (at(Tok::Bang)) {
        std::vector<uint32_t> ops;
        while (at(Tok::Bang)) {
            ops.push_back(advance().begin);
        }
        ExprUP e = parseMember(parsePrimary(false, 0));
        for (auto it=ops.rbegin(); it!=ops.rend(); it++) {
            ExprUP n = mkCall(op::LogicalNot, *it, e->end);
            n->args.push_back(std::move(e));
            e = seal(std::move(n));
        }
        return e;
    }
    if (at(Tok::Minus)) {
        std::vector<uint32_t> ops;
        while (at(Tok::Minus)) {
            ops.push_back(advance().begin);
        }
        ExprUP e;
        if (at(Tok::Int) || at(Tok::Double)) {
            uint32_t sign = ops.back();
            ops.pop_back();
            e = parseMember(parsePrimary(true, sign));
        } else {
            e = parseMember(parsePrimary(false, 0));
        }
        for (auto it=ops.rbegin(); it!=ops.rend(); it++) {
            ExprUP n = mkCall(op::Negate, *it, e->end);
            n->args.push_back(std::move(e));
            e = seal(std::move(n));
        }
        return e;
    }
    return parseMember(parsePrimary(false, 0));
}

// Member = Primary | Member "." SELECTOR ["(" [ExprList] ")"] | Member "[" Expr "]"
// plus the optional forms `.?f` and `[?e]`.
ExprUP CelParser::parseMember(ExprUP e) {
    while (true) {
        if (at(Tok::Dot)) {
            uint32_t at_op = advance().begin;
            bool opt = false;
            if (at(Tok::Question)) {
                advance();
                opt = true;
            }
            if (!at(Tok::Ident) && !at(Tok::QuotedIdent)) {
                if (at(Tok::True) || at(Tok::False) || at(Tok::Null) || at(Tok::In)) {
                    fail(std::string("'") + tok().text + "' is a keyword and cannot be a field name");
                }
                fail(std::string("expected a field or method name after '.', found ")
                    + tokName(tok().kind));
            }
            const Token &id = advance();
            bool quoted = (id.kind == Tok::QuotedIdent);

            if (!opt && !quoted && at(Tok::LParen)) {
                // Receiver-style call: target.fn(args)
                std::vector<ExprUP> args = parseArgs();
                ExprUP c = mkCall(id.text.c_str(), e->begin, m_toks[m_idx-1].end);
                c->operand = std::move(e);
                c->args = std::move(args);
                e = expandMacro(seal(std::move(c), at_op));
                continue;
            }
            if (opt) {
                ExprUP field = mk(ExprKind::Const, id.begin, id.end);
                field->cval.kind = Const::Kind::String;
                field->cval.s = id.text;
                ExprUP c = mkCall(op::OptSelect, e->begin, id.end);
                c->args.push_back(std::move(e));
                c->args.push_back(std::move(field));
                e = seal(std::move(c), at_op);
            } else {
                ExprUP s = mk(ExprKind::Select, e->begin, id.end);
                s->name = id.text;
                s->operand = std::move(e);
                e = seal(std::move(s), at_op);
            }
        } else if (at(Tok::LBracket)) {
            uint32_t at_op = advance().begin;
            bool opt = false;
            if (at(Tok::Question)) {
                advance();
                opt = true;
            }
            ExprUP idx = parseExpr();
            const Token &close = expect(Tok::RBracket, "to close the index");
            ExprUP c = mkCall(opt ? op::OptIndex : op::Index, e->begin, close.end);
            c->args.push_back(std::move(e));
            c->args.push_back(std::move(idx));
            e = seal(std::move(c), at_op);
        } else {
            return e;
        }
    }
}

std::vector<ExprUP> CelParser::parseArgs() {
    expect(Tok::LParen, "to open the argument list");
    std::vector<ExprUP> args;
    if (!at(Tok::RParen)) {
        while (true) {
            args.push_back(parseExpr());
            if (at(Tok::Comma)) {
                advance();
                if (at(Tok::RParen)) {
                    fail("trailing ',' in an argument list");
                }
                continue;
            }
            break;
        }
    }
    expect(Tok::RParen, "to close the argument list");
    return args;
}

ExprUP CelParser::parsePrimary(bool negate, uint32_t neg_begin) {
    if (negate) {
        return parseLiteral(true, neg_begin);
    }

    switch (tok().kind) {
        case Tok::Int: case Tok::Uint: case Tok::Double:
        case Tok::String: case Tok::Bytes:
        case Tok::True: case Tok::False: case Tok::Null:
            return parseLiteral(false, 0);

        case Tok::LParen: {
            advance();
            ExprUP e = parseExpr();
            expect(Tok::RParen, "to close '('");
            return e;
        }

        case Tok::LBracket:
            return parseList();

        case Tok::LBrace:
            return parseMap();

        case Tok::Dot:
        case Tok::Ident: {
            uint32_t begin = tok().begin;
            bool leading_dot = false;
            if (at(Tok::Dot)) {
                advance();
                leading_dot = true;
                if (!at(Tok::Ident)) {
                    fail(std::string("expected an identifier after a leading '.', found ")
                        + tokName(tok().kind));
                }
            }

            // Message construction: a qualified name followed by '{'.
            {
                size_t k = 0;
                while (tok(k).kind == Tok::Ident && tok(k+1).kind == Tok::Dot
                        && tok(k+2).kind == Tok::Ident) {
                    k += 2;
                }
                if (tok(k).kind == Tok::Ident && tok(k+1).kind == Tok::LBrace) {
                    std::string name = leading_dot ? "." : "";
                    for (size_t i=0; i<=k; i++) {
                        const Token &t = advance();
                        name += (t.kind == Tok::Dot) ? std::string(".") : t.text;
                    }
                    return parseStruct(name, begin);
                }
            }

            const Token &id = advance();
            if (isReserved(id.text)) {
                fail(id.begin, "'" + id.text + "' is a reserved word and cannot be used as a name");
            }
            std::string name = (leading_dot ? "." : "") + id.text;
            if (at(Tok::LParen)) {
                std::vector<ExprUP> args = parseArgs();
                ExprUP c = mkCall(name.c_str(), begin, m_toks[m_idx-1].end);
                c->args = std::move(args);
                return expandMacro(seal(std::move(c)));
            }
            return mkIdent(name, begin, id.end);
        }

        case Tok::QuotedIdent:
            fail("a quoted identifier is only allowed as a field name after '.'");

        case Tok::End:
            fail("expected an expression, found the end of the input");

        default:
            fail(std::string("expected an expression, found ") + tokName(tok().kind));
    }
}

ExprUP CelParser::parseLiteral(bool negate, uint32_t neg_begin) {
    const Token &t = advance();
    uint32_t begin = negate ? neg_begin : t.begin;
    ExprUP e = mk(ExprKind::Const, begin, t.end);
    Const &c = e->cval;

    switch (t.kind) {
        case Tok::Int:
            c.kind = Const::Kind::Int;
            if (t.overflow
                    || (!negate && t.uval > static_cast<uint64_t>(INT64_MAX))
                    || (negate && t.uval > static_cast<uint64_t>(INT64_MAX) + 1)) {
                fail(begin, "integer literal is out of range for a 64-bit signed integer");
            }
            if (negate) {
                c.i = (t.uval == static_cast<uint64_t>(INT64_MAX) + 1) ?
                    INT64_MIN : -static_cast<int64_t>(t.uval);
            } else {
                c.i = static_cast<int64_t>(t.uval);
            }
            break;
        case Tok::Uint:
            c.kind = Const::Kind::Uint;
            if (t.overflow) {
                fail(begin, "unsigned integer literal is out of range for 64 bits");
            }
            c.u = t.uval;
            break;
        case Tok::Double:
            c.kind = Const::Kind::Double;
            c.d = negate ? -t.dval : t.dval;
            break;
        case Tok::String:
            c.kind = Const::Kind::String;
            c.s = t.text;
            break;
        case Tok::Bytes:
            c.kind = Const::Kind::Bytes;
            c.s = t.text;
            break;
        case Tok::True:
            c.kind = Const::Kind::Bool;
            c.b = true;
            break;
        case Tok::False:
            c.kind = Const::Kind::Bool;
            c.b = false;
            break;
        case Tok::Null:
            c.kind = Const::Kind::Null;
            break;
        default:
            fail(t.begin, std::string("expected a literal, found ") + tokName(t.kind));
    }
    return e;
}

ExprUP CelParser::parseList() {
    uint32_t begin = advance().begin;   // '['
    ExprUP e = mk(ExprKind::List, begin, begin);
    while (!at(Tok::RBracket)) {
        if (at(Tok::Question)) {
            advance();
            e->optIndices.push_back(static_cast<uint32_t>(e->args.size()));
        }
        e->args.push_back(parseExpr());
        if (at(Tok::Comma)) {
            advance();
            continue;
        }
        if (!at(Tok::RBracket)) {
            fail(std::string("expected ',' or ']' in a list, found ") + tokName(tok().kind));
        }
    }
    e->end = advance().end;
    return seal(std::move(e));
}

ExprUP CelParser::parseMap() {
    uint32_t begin = advance().begin;   // '{'
    ExprUP e = mk(ExprKind::Map, begin, begin);
    while (!at(Tok::RBrace)) {
        Entry ent;
        ent.id = m_next_id++;
        ent.begin = tok().begin;
        if (at(Tok::Question)) {
            advance();
            ent.optional = true;
        }
        ent.key = parseExpr();
        expect(Tok::Colon, "between a map key and its value");
        ent.value = parseExpr();
        e->entries.push_back(std::move(ent));
        if (at(Tok::Comma)) {
            advance();
            continue;
        }
        if (!at(Tok::RBrace)) {
            fail(std::string("expected ',' or '}' in a map, found ") + tokName(tok().kind));
        }
    }
    e->end = advance().end;
    return seal(std::move(e));
}

ExprUP CelParser::parseStruct(std::string name, uint32_t begin) {
    advance();  // '{'
    ExprUP e = mk(ExprKind::Struct, begin, begin);
    e->name = name;
    while (!at(Tok::RBrace)) {
        Entry ent;
        ent.id = m_next_id++;
        ent.begin = tok().begin;
        if (at(Tok::Question)) {
            advance();
            ent.optional = true;
        }
        if (!at(Tok::Ident) && !at(Tok::QuotedIdent)) {
            fail(std::string("expected a field name, found ") + tokName(tok().kind));
        }
        ent.field = advance().text;
        expect(Tok::Colon, "after a field name");
        ent.value = parseExpr();
        e->entries.push_back(std::move(ent));
        if (at(Tok::Comma)) {
            advance();
            continue;
        }
        if (!at(Tok::RBrace)) {
            fail(std::string("expected ',' or '}' in a message literal, found ") + tokName(tok().kind));
        }
    }
    e->end = advance().end;
    return seal(std::move(e));
}

//****************************************************************************
//* Macros
//*
//* Expanded exactly as the CEL spec (and cel-go) expand them, so that the
//* evaluator implements one construct, the comprehension, and the
//* conformance suite's expectations apply unchanged. A call that has a macro's
//* name but not its argument count is an ordinary call, again as in cel-go.
//****************************************************************************

ExprUP CelParser::expandMacro(ExprUP call) {
    const std::string &fn = call->name;
    size_t n = call->args.size();

    if (!call->operand) {
        if (fn == "has" && n == 1) {
            Expr *a = call->args[0].get();
            if (a->kind != ExprKind::Select || a->testOnly) {
                fail(a->begin, "has() needs a field selection, e.g. has(node.rhs)");
            }
            ExprUP sel = std::move(call->args[0]);
            sel->testOnly = true;
            sel->begin = call->begin;
            sel->end = call->end;
            return sel;
        }
        return call;
    }

    if (fn == "bind" && n == 3 && call->operand->kind == ExprKind::Ident
            && call->operand->name == "cel") {
        Expr *v = call->args[0].get();
        if (v->kind != ExprKind::Ident || v->name[0] == '.') {
            fail(v->begin, "cel.bind() needs a simple name as its first argument");
        }
        return mkBind(v->name, std::move(call->args[1]), std::move(call->args[2]),
            call->begin, call->end);
    }

    // cel-go's optional library: o.optMap(x, e) and o.optFlatMap(x, e). cel-go
    // copies `o` into the expansion and so evaluates it twice; here it is
    // bound once, to a name no rule can write (@opt):
    //   cel.bind(@opt, o, @opt.hasValue()
    //       ? optional.of(cel.bind(x, @opt.value(), e))   // optMap
    //       : optional.none())
    // optFlatMap leaves out the optional.of().
    if ((fn == "optMap" || fn == "optFlatMap") && n == 2) {
        Expr *v = call->args[0].get();
        if (v->kind != ExprKind::Ident || v->name[0] == '.') {
            fail(v->begin, fn + "() needs a simple name as its first argument");
        }
        uint32_t b = call->begin, e = call->end;
        const char *opt = "@opt";
        auto member = [&](const char *f) {
            ExprUP c = mkCall(f, b, e);
            c->operand = mkIdent(opt, b, e);
            return seal(std::move(c));
        };
        auto global = [&](const char *f) {
            ExprUP c = mkCall(f, b, e);
            c->operand = mkIdent("optional", b, e);
            return c;
        };
        ExprUP then = mkBind(v->name, member("value"), std::move(call->args[1]), b, e);
        if (fn == "optMap") {
            ExprUP of = global("of");
            of->args.push_back(std::move(then));
            then = seal(std::move(of));
        }
        ExprUP cond = mkCall(op::Conditional, b, e);
        cond->args.push_back(member("hasValue"));
        cond->args.push_back(std::move(then));
        cond->args.push_back(seal(global("none")));
        return mkBind(opt, std::move(call->operand), seal(std::move(cond)), b, e);
    }

    if (((fn == "all" || fn == "exists" || fn == "exists_one" || fn == "existsOne"
            || fn == "filter") && n == 2)
            || (fn == "map" && (n == 2 || n == 3))) {
        return mkComprehension(std::move(call), fn.c_str());
    }
    return call;
}

// cel.bind(v, init, body): a comprehension over an empty list whose
// accumulator is the bound name, as cel-go expands it.
ExprUP CelParser::mkBind(const std::string &var, ExprUP init, ExprUP body,
        uint32_t begin, uint32_t end) {
    ExprUP c = mk(ExprKind::Comprehension, begin, end);
    c->name = "cel.bind";
    c->iterVar = "#unused";
    c->iterRange = mk(ExprKind::List, begin, begin);
    c->accuVar = var;
    c->accuInit = std::move(init);
    c->loopCond = mkBool(false, begin, begin);
    c->loopStep = mkIdent(var, begin, end);
    c->result = std::move(body);
    return seal(std::move(c));
}

ExprUP CelParser::mkComprehension(ExprUP call, const char *macro) {
    std::string m = macro;
    Expr *v = call->args[0].get();
    if (v->kind != ExprKind::Ident || v->name[0] == '.') {
        fail(v->begin, m + "() needs a simple name as its first argument");
    }
    uint32_t b = call->begin, e = call->end;
    std::string iv = v->name;

    ExprUP c = mk(ExprKind::Comprehension, b, e);
    c->name = (m == "existsOne") ? "exists_one" : m;
    c->iterVar = iv;
    c->accuVar = AccuVar;
    c->iterRange = std::move(call->operand);

    auto accu = [&]() { return mkIdent(AccuVar, b, e); };

    if (m == "all" || m == "exists") {
        bool is_all = (m == "all");
        ExprUP pred = std::move(call->args[1]);
        c->accuInit = mkBool(is_all, b, e);
        ExprUP cond_arg = is_all ? accu() : mkCall1(op::LogicalNot, accu());
        c->loopCond = mkCall1(op::NotStrictlyFalse, std::move(cond_arg));
        c->loopStep = mkCall2(is_all ? op::LogicalAnd : op::LogicalOr,
            accu(), std::move(pred));
        c->result = accu();
    } else if (m == "exists_one" || m == "existsOne") {
        ExprUP pred = std::move(call->args[1]);
        ExprUP zero = mk(ExprKind::Const, b, e);
        zero->cval.kind = Const::Kind::Int;
        zero->cval.i = 0;
        ExprUP one = mk(ExprKind::Const, b, e);
        one->cval.kind = Const::Kind::Int;
        one->cval.i = 1;
        ExprUP one2 = mk(ExprKind::Const, b, e);
        one2->cval.kind = Const::Kind::Int;
        one2->cval.i = 1;

        c->accuInit = std::move(zero);
        c->loopCond = mkBool(true, b, e);
        ExprUP step = mkCall(op::Conditional, b, e);
        step->args.push_back(std::move(pred));
        step->args.push_back(mkCall2(op::Add, accu(), std::move(one)));
        step->args.push_back(accu());
        c->loopStep = seal(std::move(step));
        c->result = mkCall2(op::Equals, accu(), std::move(one2));
    } else {
        // map(x, t), map(x, p, t), filter(x, p)
        bool is_filter = (m == "filter");
        ExprUP pred, xform;
        if (is_filter) {
            pred = std::move(call->args[1]);
            xform = mkIdent(iv, v->begin, v->end);
        } else if (call->args.size() == 3) {
            pred = std::move(call->args[1]);
            xform = std::move(call->args[2]);
        } else {
            xform = std::move(call->args[1]);
        }
        c->accuInit = mk(ExprKind::List, b, e);
        c->loopCond = mkBool(true, b, e);

        ExprUP one = mk(ExprKind::List, xform->begin, xform->end);
        one->args.push_back(std::move(xform));
        ExprUP append = mkCall2(op::Add, accu(), seal(std::move(one)));
        if (pred) {
            ExprUP step = mkCall(op::Conditional, b, e);
            step->args.push_back(std::move(pred));
            step->args.push_back(std::move(append));
            step->args.push_back(accu());
            c->loopStep = seal(std::move(step));
        } else {
            c->loopStep = std::move(append);
        }
        c->result = accu();
    }
    return seal(std::move(c));
}

//****************************************************************************
//* Profile check (lint-rule-expressions.md §3, "Out, initially")
//****************************************************************************

namespace {

void profileWalk(const Expr *e, std::vector<ProfileError> &errs) {
    if (!e) {
        return;
    }
    switch (e->kind) {
        case ExprKind::Const:
            if (e->cval.kind == Const::Kind::Bytes) {
                errs.push_back({e->begin, "bytes literals are not supported in pss-rules"});
            } else if (e->cval.kind == Const::Kind::Uint) {
                errs.push_back({e->begin,
                    "unsigned integer literals are not supported in pss-rules; use an int"});
            }
            break;
        case ExprKind::Struct:
            errs.push_back({e->begin,
                "message construction ('" + e->name + "{...}') is not supported in pss-rules"});
            for (const Entry &ent : e->entries) {
                profileWalk(ent.value.get(), errs);
            }
            break;
        case ExprKind::Ident:
            if (e->name[0] == '.') {
                errs.push_back({e->begin,
                    "absolute names ('" + e->name + "') are not supported in pss-rules"});
            }
            break;
        case ExprKind::Select:
            profileWalk(e->operand.get(), errs);
            break;
        case ExprKind::Call: {
            static const char *TwoVar[] = {
                "all", "exists", "existsOne", "exists_one", "transformList",
                "transformMap", "transformMapEntry", nullptr
            };
            if (e->operand && e->args.size() == 3) {
                for (const char **t=TwoVar; *t; t++) {
                    if (e->name == *t) {
                        errs.push_back({e->begin,
                            "two-variable comprehensions ('" + e->name
                            + "(k, v, ...)') are not supported in pss-rules"});
                        break;
                    }
                }
            }
            profileWalk(e->operand.get(), errs);
            for (const ExprUP &a : e->args) {
                profileWalk(a.get(), errs);
            }
        } break;
        case ExprKind::List:
            for (const ExprUP &a : e->args) {
                profileWalk(a.get(), errs);
            }
            break;
        case ExprKind::Map:
            for (const Entry &ent : e->entries) {
                profileWalk(ent.key.get(), errs);
                profileWalk(ent.value.get(), errs);
            }
            break;
        case ExprKind::Comprehension:
            profileWalk(e->iterRange.get(), errs);
            profileWalk(e->accuInit.get(), errs);
            profileWalk(e->loopCond.get(), errs);
            profileWalk(e->loopStep.get(), errs);
            profileWalk(e->result.get(), errs);
            break;
    }
}

}

std::vector<ProfileError> checkProfile(const Expr *e) {
    std::vector<ProfileError> errs;
    profileWalk(e, errs);
    return errs;
}

}
}
}
