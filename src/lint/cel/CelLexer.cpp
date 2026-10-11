/*
 * CelLexer.cpp
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
#include <cstdio>
#include <cstdlib>
#include "CelLexer.h"

namespace pssp {
namespace lint {
namespace cel {

const char *tokName(Tok t) {
    switch (t) {
        case Tok::End: return "end of expression";
        case Tok::Ident: return "identifier";
        case Tok::QuotedIdent: return "quoted identifier";
        case Tok::Int: return "integer literal";
        case Tok::Uint: return "unsigned integer literal";
        case Tok::Double: return "double literal";
        case Tok::String: return "string literal";
        case Tok::Bytes: return "bytes literal";
        case Tok::True: return "'true'";
        case Tok::False: return "'false'";
        case Tok::Null: return "'null'";
        case Tok::In: return "'in'";
        case Tok::LParen: return "'('";
        case Tok::RParen: return "')'";
        case Tok::LBracket: return "'['";
        case Tok::RBracket: return "']'";
        case Tok::LBrace: return "'{'";
        case Tok::RBrace: return "'}'";
        case Tok::Dot: return "'.'";
        case Tok::Comma: return "','";
        case Tok::Colon: return "':'";
        case Tok::Question: return "'?'";
        case Tok::Plus: return "'+'";
        case Tok::Minus: return "'-'";
        case Tok::Star: return "'*'";
        case Tok::Slash: return "'/'";
        case Tok::Percent: return "'%'";
        case Tok::Bang: return "'!'";
        case Tok::Lt: return "'<'";
        case Tok::Le: return "'<='";
        case Tok::Gt: return "'>'";
        case Tok::Ge: return "'>='";
        case Tok::EqEq: return "'=='";
        case Tok::Ne: return "'!='";
        case Tok::AndAnd: return "'&&'";
        case Tok::OrOr: return "'||'";
    }
    return "?";
}

static bool isIdentStart(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
}

static bool isIdentPart(char c) {
    return isIdentStart(c) || (c >= '0' && c <= '9');
}

static bool isDigit(char c) {
    return c >= '0' && c <= '9';
}

static int hexVal(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

CelLexer::CelLexer(const std::string &text) : m_text(text), m_pos(0) {

}

std::vector<Token> CelLexer::tokenize() {
    std::vector<Token> ret;
    while (true) {
        ret.push_back(next());
        if (ret.back().kind == Tok::End) {
            break;
        }
    }
    return ret;
}

void CelLexer::skipSpaceAndComments() {
    while (m_pos < m_text.size()) {
        char c = m_text[m_pos];
        if (c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f') {
            m_pos++;
        } else if (c == '/' && peek(1) == '/') {
            while (m_pos < m_text.size() && m_text[m_pos] != '\n') {
                m_pos++;
            }
        } else {
            break;
        }
    }
}

Token CelLexer::next() {
    skipSpaceAndComments();

    Token t;
    t.begin = m_pos;

    if (m_pos >= m_text.size()) {
        t.kind = Tok::End;
        t.end = m_pos;
        return t;
    }

    char c = m_text[m_pos];

    // String and bytes literals, with their optional r/b prefixes (in either
    // order and either case). Checked before identifiers: `r'x'` is a string.
    {
        uint32_t p = m_pos;
        bool raw = false, bytes = false;
        for (int i=0; i<2 && p < m_text.size(); i++) {
            char pc = m_text[p];
            if ((pc == 'r' || pc == 'R') && !raw) {
                raw = true; p++;
            } else if ((pc == 'b' || pc == 'B') && !bytes) {
                bytes = true; p++;
            } else {
                break;
            }
        }
        if (p < m_text.size() && (m_text[p] == '"' || m_text[p] == '\'')) {
            uint32_t start = m_pos;
            m_pos = p;
            return lexString(start, raw, bytes);
        }
    }

    if (isIdentStart(c)) {
        uint32_t s = m_pos;
        while (m_pos < m_text.size() && isIdentPart(m_text[m_pos])) {
            m_pos++;
        }
        t.text = m_text.substr(s, m_pos - s);
        t.end = m_pos;
        if (t.text == "true") {
            t.kind = Tok::True;
        } else if (t.text == "false") {
            t.kind = Tok::False;
        } else if (t.text == "null") {
            t.kind = Tok::Null;
        } else if (t.text == "in") {
            t.kind = Tok::In;
        } else {
            t.kind = Tok::Ident;
        }
        return t;
    }

    if (isDigit(c) || (c == '.' && isDigit(peek(1)))) {
        return lexNumber();
    }

    if (c == '`') {
        // Escaped field selector: `a.b-c`. Any character but a backtick or a
        // newline; the parser only accepts it after '.'.
        m_pos++;
        uint32_t s = m_pos;
        while (m_pos < m_text.size() && m_text[m_pos] != '`' && m_text[m_pos] != '\n') {
            m_pos++;
        }
        if (m_pos >= m_text.size() || m_text[m_pos] != '`') {
            throw SyntaxError(t.begin, "unterminated quoted identifier");
        }
        t.text = m_text.substr(s, m_pos - s);
        m_pos++;
        t.kind = Tok::QuotedIdent;
        t.end = m_pos;
        if (t.text.empty()) {
            throw SyntaxError(t.begin, "empty quoted identifier");
        }
        return t;
    }

    m_pos++;
    switch (c) {
        case '(': t.kind = Tok::LParen; break;
        case ')': t.kind = Tok::RParen; break;
        case '[': t.kind = Tok::LBracket; break;
        case ']': t.kind = Tok::RBracket; break;
        case '{': t.kind = Tok::LBrace; break;
        case '}': t.kind = Tok::RBrace; break;
        case '.': t.kind = Tok::Dot; break;
        case ',': t.kind = Tok::Comma; break;
        case ':': t.kind = Tok::Colon; break;
        case '?': t.kind = Tok::Question; break;
        case '+': t.kind = Tok::Plus; break;
        case '-': t.kind = Tok::Minus; break;
        case '*': t.kind = Tok::Star; break;
        case '/': t.kind = Tok::Slash; break;
        case '%': t.kind = Tok::Percent; break;
        case '!':
            if (peek() == '=') { m_pos++; t.kind = Tok::Ne; } else { t.kind = Tok::Bang; }
            break;
        case '<':
            if (peek() == '=') { m_pos++; t.kind = Tok::Le; } else { t.kind = Tok::Lt; }
            break;
        case '>':
            if (peek() == '=') { m_pos++; t.kind = Tok::Ge; } else { t.kind = Tok::Gt; }
            break;
        case '=':
            if (peek() == '=') { m_pos++; t.kind = Tok::EqEq; break; }
            throw SyntaxError(t.begin, "unexpected '='; use '==' to compare");
        case '&':
            if (peek() == '&') { m_pos++; t.kind = Tok::AndAnd; break; }
            throw SyntaxError(t.begin, "unexpected '&'; logical and is '&&'");
        case '|':
            if (peek() == '|') { m_pos++; t.kind = Tok::OrOr; break; }
            throw SyntaxError(t.begin, "unexpected '|'; logical or is '||'");
        default: {
            std::string what;
            if (static_cast<unsigned char>(c) >= 0x20 && static_cast<unsigned char>(c) < 0x7f) {
                what = std::string("'") + c + "'";
            } else {
                char buf[16];
                snprintf(buf, sizeof(buf), "0x%02x", static_cast<unsigned char>(c));
                what = std::string("byte ") + buf;
            }
            throw SyntaxError(t.begin, "unexpected character " + what);
        }
    }
    t.end = m_pos;
    return t;
}

Token CelLexer::lexNumber() {
    Token t;
    t.begin = m_pos;

    // Hexadecimal integer
    if (peek() == '0' && (peek(1) == 'x' || peek(1) == 'X')) {
        m_pos += 2;
        uint32_t s = m_pos;
        uint64_t v = 0;
        while (hexVal(peek()) >= 0) {
            if (v > (UINT64_MAX >> 4)) {
                t.overflow = true;
            }
            v = (v << 4) | static_cast<uint64_t>(hexVal(peek()));
            m_pos++;
        }
        if (m_pos == s) {
            throw SyntaxError(t.begin, "hexadecimal literal has no digits");
        }
        t.uval = v;
        t.kind = Tok::Int;
        if (peek() == 'u' || peek() == 'U') {
            m_pos++;
            t.kind = Tok::Uint;
        }
        if (isIdentPart(peek())) {
            throw SyntaxError(m_pos, "invalid character in numeric literal");
        }
        t.end = m_pos;
        return t;
    }

    uint32_t s = m_pos;
    bool is_double = false;
    while (isDigit(peek())) {
        m_pos++;
    }
    if (peek() == '.' && isDigit(peek(1))) {
        is_double = true;
        m_pos++;
        while (isDigit(peek())) {
            m_pos++;
        }
    }
    if (peek() == 'e' || peek() == 'E') {
        uint32_t save = m_pos;
        m_pos++;
        if (peek() == '+' || peek() == '-') {
            m_pos++;
        }
        if (isDigit(peek())) {
            is_double = true;
            while (isDigit(peek())) {
                m_pos++;
            }
        } else {
            m_pos = save;
            throw SyntaxError(save, "exponent has no digits");
        }
    }

    std::string lexeme = m_text.substr(s, m_pos - s);
    if (is_double) {
        t.kind = Tok::Double;
        t.dval = std::strtod(lexeme.c_str(), nullptr);
        if (peek() == 'u' || peek() == 'U') {
            throw SyntaxError(m_pos, "a double literal cannot have a 'u' suffix");
        }
    } else {
        uint64_t v = 0;
        for (char d : lexeme) {
            uint64_t dv = static_cast<uint64_t>(d - '0');
            if (v > (UINT64_MAX - dv) / 10) {
                t.overflow = true;
            }
            v = v * 10 + dv;
        }
        t.uval = v;
        t.kind = Tok::Int;
        if (peek() == 'u' || peek() == 'U') {
            m_pos++;
            t.kind = Tok::Uint;
        }
    }
    if (isIdentPart(peek())) {
        throw SyntaxError(m_pos, "invalid character in numeric literal");
    }
    t.end = m_pos;
    return t;
}

void CelLexer::appendCodePoint(std::string &out, uint32_t cp, uint32_t at, bool bytes) {
    if (bytes) {
        // \x and octal escapes in a bytes literal denote one byte.
        out.push_back(static_cast<char>(cp));
        return;
    }
    if (cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) {
        throw SyntaxError(at, "escape sequence is not a valid Unicode code point");
    }
    if (cp < 0x80) {
        out.push_back(static_cast<char>(cp));
    } else if (cp < 0x800) {
        out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else if (cp < 0x10000) {
        out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else {
        out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    }
}

Token CelLexer::lexString(uint32_t start, bool raw, bool bytes) {
    Token t;
    t.begin = start;
    t.kind = bytes ? Tok::Bytes : Tok::String;

    char q = peek();
    bool triple = (peek(1) == q && peek(2) == q);
    m_pos += triple ? 3 : 1;

    std::string &out = t.text;
    while (true) {
        if (m_pos >= m_text.size()) {
            throw SyntaxError(start, "unterminated string literal");
        }
        char c = m_text[m_pos];
        if (triple) {
            if (c == q && peek(1) == q && peek(2) == q) {
                m_pos += 3;
                break;
            }
        } else {
            if (c == q) {
                m_pos++;
                break;
            }
            if (c == '\n' || c == '\r') {
                throw SyntaxError(start,
                    "unterminated string literal (a quoted string cannot span lines; "
                    "use a triple-quoted string)");
            }
        }

        if (c != '\\' || raw) {
            out.push_back(c);
            m_pos++;
            continue;
        }

        // Escape sequence
        uint32_t esc = m_pos;
        m_pos++;
        if (m_pos >= m_text.size()) {
            throw SyntaxError(start, "unterminated string literal");
        }
        char e = m_text[m_pos++];
        switch (e) {
            case 'a': out.push_back('\a'); break;
            case 'b': out.push_back('\b'); break;
            case 'f': out.push_back('\f'); break;
            case 'n': out.push_back('\n'); break;
            case 'r': out.push_back('\r'); break;
            case 't': out.push_back('\t'); break;
            case 'v': out.push_back('\v'); break;
            case '\\': out.push_back('\\'); break;
            case '?': out.push_back('?'); break;
            case '"': out.push_back('"'); break;
            case '\'': out.push_back('\''); break;
            case '`': out.push_back('`'); break;
            case 'x': case 'X': {
                int h1 = hexVal(peek()), h2 = hexVal(peek(1));
                if (h1 < 0 || h2 < 0) {
                    throw SyntaxError(esc, "\\x escape needs two hexadecimal digits");
                }
                m_pos += 2;
                appendCodePoint(out, static_cast<uint32_t>(h1 * 16 + h2), esc, bytes);
            } break;
            case 'u': case 'U': {
                int n = (e == 'u') ? 4 : 8;
                if (bytes) {
                    throw SyntaxError(esc, "\\u and \\U escapes are not allowed in a bytes literal");
                }
                uint32_t cp = 0;
                for (int i=0; i<n; i++) {
                    int h = hexVal(peek());
                    if (h < 0) {
                        throw SyntaxError(esc, std::string("\\") + e + " escape needs "
                            + std::to_string(n) + " hexadecimal digits");
                    }
                    cp = (cp << 4) | static_cast<uint32_t>(h);
                    m_pos++;
                }
                appendCodePoint(out, cp, esc, false);
            } break;
            case '0': case '1': case '2': case '3': {
                char o2 = peek(), o3 = peek(1);
                if (o2 < '0' || o2 > '7' || o3 < '0' || o3 > '7') {
                    throw SyntaxError(esc, "octal escape needs three octal digits");
                }
                m_pos += 2;
                uint32_t cp = static_cast<uint32_t>((e - '0') * 64 + (o2 - '0') * 8 + (o3 - '0'));
                appendCodePoint(out, cp, esc, bytes);
            } break;
            default:
                throw SyntaxError(esc, std::string("invalid escape sequence '\\") + e + "'");
        }
    }

    t.end = m_pos;
    return t;
}

}
}
}
