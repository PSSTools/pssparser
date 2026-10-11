/*
 * CelParser.h
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
 * Hand-written recursive-descent parser for CEL (lint-core-plan.md D-C1).
 *
 * Parses the *whole* CEL expression language, including the parts the
 * pss-rules profile excludes (bytes, uint, message construction, ...). The
 * profile is enforced afterwards by checkProfile(), so an excluded feature is
 * reported as "not supported in pss-rules" rather than as a syntax error.
 */
#pragma once
#include <string>
#include <vector>
#include "CelAst.h"
#include "CelLexer.h"

namespace pssp {
namespace lint {
namespace cel {

struct ParseOptions {
    // Nesting limit (parentheses, call arguments, list/map elements, the
    // else-arm of ?:). The spec requires 12; the conformance suite's `parens`
    // test nests 32. The limit bounds stack use, which matters in WASM: one
    // level costs about 290 bytes of the 64 KiB default Emscripten stack
    // (measured C0, 2026-10-10), so 64 levels is about 18 KiB.
    int             maxDepth = 64;

    // Height limit on the resulting tree. Separate from maxDepth because a
    // chain such as `a + a + ... + a` or `x.f.f.f...` builds a tall tree
    // without any parser recursion; every later walk (checker, evaluator,
    // destructor) recurses over the height. The evaluator costs about 48
    // bytes of WASM stack per level (C0).
    uint32_t        maxHeight = 256;
};

class CelParser {
public:
    CelParser(const std::string &text, const ParseOptions &opts=ParseOptions());

    /** Parses the whole input as one expression. Throws SyntaxError. */
    ExprUP parse();

private:
    ExprUP parseExpr();
    ExprUP parseOr();
    ExprUP parseAnd();
    ExprUP parseRelation();
    ExprUP parseAddition();
    ExprUP parseMultiplication();
    ExprUP parseUnary();
    ExprUP parseMember(ExprUP primary);
    ExprUP parsePrimary(bool negate, uint32_t neg_begin);
    ExprUP parseLiteral(bool negate, uint32_t neg_begin);
    ExprUP parseList();
    ExprUP parseMap();
    ExprUP parseStruct(std::string name, uint32_t begin);
    std::vector<ExprUP> parseArgs();

    ExprUP expandMacro(ExprUP call);
    ExprUP mkComprehension(ExprUP call, const char *macro);
    ExprUP mkBind(const std::string &var, ExprUP init, ExprUP body, uint32_t begin, uint32_t end);

    ExprUP mk(ExprKind kind, uint32_t begin, uint32_t end);
    /** No operator position: a height error is reported at the node's start. */
    static constexpr uint32_t NoPos = 0xFFFFFFFFu;

    ExprUP seal(ExprUP e, uint32_t op_pos=NoPos);
    ExprUP mkCall(const char *fn, uint32_t begin, uint32_t end);
    ExprUP mkCall1(const char *fn, ExprUP a);
    ExprUP mkCall2(const char *fn, ExprUP a, ExprUP b, uint32_t op_pos=NoPos);
    ExprUP mkIdent(const std::string &name, uint32_t begin, uint32_t end);
    ExprUP mkBool(bool v, uint32_t begin, uint32_t end);
    ExprUP balance(const char *fn, std::vector<ExprUP> &terms,
            const std::vector<uint32_t> &ops, size_t lo, size_t hi);

    const Token &tok() const { return m_toks[m_idx]; }
    const Token &tok(size_t ahead) const {
        size_t i = m_idx + ahead;
        return (i < m_toks.size()) ? m_toks[i] : m_toks.back();
    }
    bool at(Tok k) const { return tok().kind == k; }
    const Token &advance() { return m_toks[m_idx++]; }
    const Token &expect(Tok k, const char *context);
    [[noreturn]] void fail(const std::string &msg);
    [[noreturn]] void fail(uint32_t offset, const std::string &msg);

private:
    const std::string       &m_text;
    ParseOptions            m_opts;
    std::vector<Token>      m_toks;
    size_t                  m_idx;
    int32_t                 m_next_id;
    int                     m_depth;
};

/**
 * A use of CEL that the pss-rules profile excludes
 * (lint-rule-expressions.md §3). Reported with the offset of the construct.
 */
struct ProfileError {
    uint32_t        offset;
    std::string     message;
};

/** Collects every profile violation in `e`, in source order. */
std::vector<ProfileError> checkProfile(const Expr *e);

}
}
}
