/*
 * CelLexer.h
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
 * Hand-written lexer for the CEL expression syntax (lint-core-plan.md D-C1).
 * The reference is the lexis in cel-spec doc/langdef.md and CEL.g4.
 */
#pragma once
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace pssp {
namespace lint {
namespace cel {

enum class Tok {
    End,
    Ident,          // includes reserved words; the parser decides
    QuotedIdent,    // `a.b` field selector (escaped identifier)
    Int,
    Uint,
    Double,
    String,
    Bytes,
    True,
    False,
    Null,
    In,
    LParen, RParen, LBracket, RBracket, LBrace, RBrace,
    Dot, Comma, Colon, Question,
    Plus, Minus, Star, Slash, Percent,
    Bang, Lt, Le, Gt, Ge, EqEq, Ne,
    AndAnd, OrOr,
};

const char *tokName(Tok t);

struct Token {
    Tok             kind = Tok::End;
    uint32_t        begin = 0;
    uint32_t        end = 0;
    std::string     text;       // Ident: the name; String/Bytes: decoded value
    uint64_t        uval = 0;   // Int/Uint magnitude (sign is the parser's)
    double          dval = 0.0;
    bool            overflow = false;   // Int literal magnitude > UINT64_MAX
};

/**
 * A syntax error, located by byte offset. One per expression: the parser does
 * no recovery, by design (C2.1).
 */
class SyntaxError : public std::runtime_error {
public:
    SyntaxError(uint32_t offset, const std::string &msg) :
        std::runtime_error(msg), m_offset(offset) { }

    uint32_t offset() const { return m_offset; }

private:
    uint32_t        m_offset;
};

class CelLexer {
public:
    explicit CelLexer(const std::string &text);

    /** Tokenizes the whole input. Throws SyntaxError. The last token is End. */
    std::vector<Token> tokenize();

private:
    Token next();
    void skipSpaceAndComments();
    Token lexNumber();
    Token lexString(uint32_t start, bool raw, bool bytes);
    void appendCodePoint(std::string &out, uint32_t cp, uint32_t at, bool bytes);

    char peek(uint32_t ahead=0) const {
        return (m_pos + ahead < m_text.size()) ? m_text[m_pos + ahead] : '\0';
    }

    const std::string   &m_text;
    uint32_t            m_pos;
};

}
}
}
