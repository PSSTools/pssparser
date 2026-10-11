/*
 * Regex.cpp
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
#include <algorithm>
#include <cstring>
#include <utility>
#include "Regex.h"

namespace pssp {
namespace lint {
namespace regex {

using Range = std::pair<uint32_t, uint32_t>;
using Ranges = std::vector<Range>;

static constexpr uint32_t MaxCodePoint = 0x10FFFF;
static constexpr int MaxRepeat = 1000;          // RE2's limit
static constexpr size_t MaxProgram = 20000;     // instructions
// Group nesting. One level costs about 600 bytes of stack in the WASM build
// (C0 measurement), whose default stack is 64 KiB.
static constexpr int MaxNesting = 32;

enum class AssertKind : uint8_t {
    BeginText, EndText, BeginLine, EndLine, WordBoundary, NotWordBoundary
};

struct Inst {
    enum class Op : uint8_t { Class, Any, AnyNotNL, Split, Jmp, Match, Assert };

    Op              op = Op::Match;
    AssertKind      assertion = AssertKind::BeginText;
    uint32_t        x = 0;      // Split: first target; Jmp: target
    uint32_t        y = 0;      // Split: second target
    Ranges          ranges;     // Class (sorted, disjoint)
};

namespace {

//****************************************************************************
//* Character classes
//****************************************************************************

void normalize(Ranges &r) {
    std::sort(r.begin(), r.end());
    Ranges out;
    for (const Range &x : r) {
        if (!out.empty() && x.first <= out.back().second + 1) {
            out.back().second = std::max(out.back().second, x.second);
        } else {
            out.push_back(x);
        }
    }
    r.swap(out);
}

Ranges negate(const Ranges &in) {
    Ranges r(in);
    normalize(r);
    Ranges out;
    uint32_t next = 0;
    for (const Range &x : r) {
        if (x.first > next) {
            out.push_back({next, x.first - 1});
        }
        next = x.second + 1;
    }
    if (next <= MaxCodePoint) {
        out.push_back({next, MaxCodePoint});
    }
    return out;
}

void addFolded(Ranges &r, uint32_t lo, uint32_t hi, bool fold) {
    r.push_back({lo, hi});
    if (!fold) {
        return;
    }
    // ASCII case folding only (documented in Regex.h).
    uint32_t a = std::max<uint32_t>(lo, 'a'), b = std::min<uint32_t>(hi, 'z');
    if (a <= b) {
        r.push_back({a - 32, b - 32});
    }
    a = std::max<uint32_t>(lo, 'A');
    b = std::min<uint32_t>(hi, 'Z');
    if (a <= b) {
        r.push_back({a + 32, b + 32});
    }
}

const Ranges &digitRanges() {
    static const Ranges r = {{'0', '9'}};
    return r;
}

const Ranges &wordRanges() {
    static const Ranges r = {{'0', '9'}, {'A', 'Z'}, {'_', '_'}, {'a', 'z'}};
    return r;
}

const Ranges &spaceRanges() {
    // RE2's \s is [\t\n\f\r ]
    static const Ranges r = {{'\t', '\n'}, {'\f', '\r'}, {' ', ' '}};
    return r;
}

bool posixClass(const std::string &name, Ranges &out) {
    struct P { const char *n; Ranges r; };
    static const P table[] = {
        {"alnum", {{'0', '9'}, {'A', 'Z'}, {'a', 'z'}}},
        {"alpha", {{'A', 'Z'}, {'a', 'z'}}},
        {"ascii", {{0, 0x7F}}},
        {"blank", {{'\t', '\t'}, {' ', ' '}}},
        {"cntrl", {{0, 0x1F}, {0x7F, 0x7F}}},
        {"digit", {{'0', '9'}}},
        {"graph", {{'!', '~'}}},
        {"lower", {{'a', 'z'}}},
        {"print", {{' ', '~'}}},
        {"punct", {{'!', '/'}, {':', '@'}, {'[', '`'}, {'{', '~'}}},
        {"space", {{'\t', '\r'}, {' ', ' '}}},
        {"upper", {{'A', 'Z'}}},
        {"word", {{'0', '9'}, {'A', 'Z'}, {'_', '_'}, {'a', 'z'}}},
        {"xdigit", {{'0', '9'}, {'A', 'F'}, {'a', 'f'}}},
    };
    for (const P &p : table) {
        if (name == p.n) {
            out.insert(out.end(), p.r.begin(), p.r.end());
            return true;
        }
    }
    return false;
}

bool isWordChar(int32_t c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
}

// Decodes one UTF-8 code point at s[i]; invalid input decodes as U+FFFD
// consuming one byte, so every input has a meaning and the scan always moves.
uint32_t decodeUtf8(const std::string &s, size_t i, size_t &len) {
    unsigned char c0 = static_cast<unsigned char>(s[i]);
    if (c0 < 0x80) {
        len = 1;
        return c0;
    }
    int n = (c0 >= 0xF0 && c0 < 0xF8) ? 4 : (c0 >= 0xE0) ? 3 : (c0 >= 0xC0) ? 2 : 0;
    if (n == 0 || i + n > s.size()) {
        len = 1;
        return 0xFFFD;
    }
    uint32_t cp = c0 & (0x7F >> n);
    for (int k=1; k<n; k++) {
        unsigned char ck = static_cast<unsigned char>(s[i+k]);
        if ((ck & 0xC0) != 0x80) {
            len = 1;
            return 0xFFFD;
        }
        cp = (cp << 6) | (ck & 0x3F);
    }
    len = static_cast<size_t>(n);
    return cp;
}

//****************************************************************************
//* Parse tree
//****************************************************************************

struct Node;
using NodeUP = std::unique_ptr<Node>;

struct Node {
    enum class K { Empty, Class, Any, AnyNotNL, Concat, Alt, Repeat, Assert };

    K                   k = K::Empty;
    Ranges              ranges;
    std::vector<NodeUP> kids;
    int                 min = 0;
    int                 max = -1;       // -1: unbounded
    AssertKind          assertion = AssertKind::BeginText;
};

NodeUP mkNode(Node::K k) {
    NodeUP n(new Node());
    n->k = k;
    return n;
}

struct Flags {
    bool    fold = false;       // i
    bool    dotNL = false;      // s
    bool    multiLine = false;  // m
};

class Parser {
public:
    explicit Parser(const std::string &p) : m_p(p), m_pos(0), m_depth(0) { }

    NodeUP parse() {
        Flags f;
        NodeUP n = parseAlt(f);
        if (m_pos < m_p.size()) {
            // Only an unmatched ')' stops parseAlt early.
            throw RegexError(m_pos, "unexpected ')'");
        }
        return n;
    }

private:
    bool eof() const { return m_pos >= m_p.size(); }
    char peek(size_t k=0) const { return (m_pos + k < m_p.size()) ? m_p[m_pos + k] : '\0'; }

    NodeUP parseAlt(Flags &f) {
        std::vector<NodeUP> alts;
        alts.push_back(parseConcat(f));
        while (peek() == '|') {
            m_pos++;
            alts.push_back(parseConcat(f));
        }
        if (alts.size() == 1) {
            return std::move(alts[0]);
        }
        NodeUP n = mkNode(Node::K::Alt);
        n->kids = std::move(alts);
        return n;
    }

    NodeUP parseConcat(Flags &f) {
        NodeUP n = mkNode(Node::K::Concat);
        while (!eof() && peek() != '|' && peek() != ')') {
            NodeUP atom = parseAtom(f);
            if (!atom) {
                continue;   // a flag group such as (?i): no node of its own
            }
            n->kids.push_back(parseQuantifiers(std::move(atom)));
        }
        return n;
    }

    bool tryParseBraces(int &min, int &max) {
        // {n} {n,} {n,m}; anything else means '{' is a literal, as in RE2.
        size_t p = m_pos + 1;
        auto num = [&](int &v) {
            size_t s = p;
            long acc = 0;
            while (p < m_p.size() && m_p[p] >= '0' && m_p[p] <= '9') {
                acc = acc * 10 + (m_p[p] - '0');
                if (acc > 100000) acc = 100000;
                p++;
            }
            v = static_cast<int>(acc);
            return p > s;
        };
        if (!num(min)) {
            return false;
        }
        if (p < m_p.size() && m_p[p] == '}') {
            max = min;
        } else if (p < m_p.size() && m_p[p] == ',') {
            p++;
            if (p < m_p.size() && m_p[p] == '}') {
                max = -1;
            } else if (!num(max) || p >= m_p.size() || m_p[p] != '}') {
                return false;
            }
        } else {
            return false;
        }
        m_pos = p + 1;
        return true;
    }

    NodeUP parseQuantifiers(NodeUP atom) {
        bool quantified = false;
        while (!eof()) {
            size_t qpos = m_pos;
            int min, max;
            char c = peek();
            if (c == '*') { min = 0; max = -1; m_pos++; }
            else if (c == '+') { min = 1; max = -1; m_pos++; }
            else if (c == '?') { min = 0; max = 1; m_pos++; }
            else if (c == '{') {
                if (!tryParseBraces(min, max)) {
                    break;
                }
                if (max != -1 && min > max) {
                    throw RegexError(qpos, "bad repetition: minimum is larger than maximum");
                }
                if (min > MaxRepeat || max > MaxRepeat) {
                    throw RegexError(qpos, "bad repetition: counts above 1000 are not allowed");
                }
            } else {
                break;
            }
            if (quantified) {
                if (c == '+') {
                    throw RegexError(qpos, "possessive quantifiers are not supported (RE2 syntax)");
                }
                throw RegexError(qpos, "bad repetition operator: a quantifier cannot follow a quantifier");
            }
            quantified = true;
            if (peek() == '?') {
                m_pos++;    // lazy: same language, so the same NFA for a yes/no match
            }
            NodeUP r = mkNode(Node::K::Repeat);
            r->min = min;
            r->max = max;
            r->kids.push_back(std::move(atom));
            atom = std::move(r);
        }
        return atom;
    }

    NodeUP classNode(Ranges r) {
        normalize(r);
        NodeUP n = mkNode(Node::K::Class);
        n->ranges = std::move(r);
        return n;
    }

    NodeUP literal(uint32_t cp, const Flags &f) {
        Ranges r;
        addFolded(r, cp, cp, f.fold);
        return classNode(std::move(r));
    }

    NodeUP assertNode(AssertKind k) {
        NodeUP n = mkNode(Node::K::Assert);
        n->assertion = k;
        return n;
    }

    uint32_t nextCodePoint() {
        size_t len;
        uint32_t cp = decodeUtf8(m_p, m_pos, len);
        m_pos += len;
        return cp;
    }

    NodeUP parseAtom(Flags &f) {
        size_t start = m_pos;
        char c = peek();
        switch (c) {
            case '(':
                return parseGroup(f);
            case '[':
                return parseClass(f);
            case '.':
                m_pos++;
                return mkNode(f.dotNL ? Node::K::Any : Node::K::AnyNotNL);
            case '^':
                m_pos++;
                return assertNode(f.multiLine ? AssertKind::BeginLine : AssertKind::BeginText);
            case '$':
                m_pos++;
                return assertNode(f.multiLine ? AssertKind::EndLine : AssertKind::EndText);
            case '*': case '+': case '?':
                throw RegexError(start, std::string("missing argument to repetition operator '") + c + "'");
            case '{': {
                int mn, mx;
                size_t save = m_pos;
                if (tryParseBraces(mn, mx)) {
                    throw RegexError(save, "missing argument to repetition operator '{'");
                }
                m_pos++;
                return literal('{', f);
            }
            case '\\':
                return parseEscape(f, false, nullptr);
            default:
                return literal(nextCodePoint(), f);
        }
    }

    NodeUP parseGroup(Flags &f) {
        size_t start = m_pos;
        m_pos++;    // '('
        Flags inner = f;
        if (peek() == '?') {
            m_pos++;
            char c = peek();
            if (c == '=' || c == '!') {
                throw RegexError(start, "lookahead is not supported (RE2 syntax)");
            }
            if (c == '<' && (peek(1) == '=' || peek(1) == '!')) {
                throw RegexError(start, "lookbehind is not supported (RE2 syntax)");
            }
            if (c == '>') {
                throw RegexError(start, "atomic groups are not supported (RE2 syntax)");
            }
            if (c == 'P' || c == '<') {
                // Named group: (?P<name>re) or (?<name>re)
                if (c == 'P') {
                    m_pos++;
                    if (peek() != '<') {
                        throw RegexError(start, "invalid named group");
                    }
                }
                m_pos++;
                size_t ns = m_pos;
                while (!eof() && (isWordChar(peek()))) {
                    m_pos++;
                }
                if (m_pos == ns || peek() != '>') {
                    throw RegexError(start, "invalid named group");
                }
                m_pos++;
            } else {
                // Flags: (?flags) or (?flags:re)
                bool neg = false, any = false;
                while (true) {
                    char fc = peek();
                    if (fc == 'i') { inner.fold = !neg; }
                    else if (fc == 's') { inner.dotNL = !neg; }
                    else if (fc == 'm') { inner.multiLine = !neg; }
                    else if (fc == 'U') { /* ungreedy: no effect on a yes/no match */ }
                    else if (fc == '-' && !neg) { neg = true; m_pos++; continue; }
                    else break;
                    any = true;
                    m_pos++;
                }
                if (peek() == ')') {
                    if (!any) {
                        throw RegexError(start, "missing flags in '(?)'");
                    }
                    m_pos++;
                    f = inner;      // applies to the rest of the enclosing group
                    return nullptr;
                }
                if (peek() != ':') {
                    throw RegexError(start, "invalid or unsupported group syntax '(?'");
                }
                m_pos++;
            }
        }

        if (++m_depth > MaxNesting) {
            throw RegexError(start, "groups nest too deeply");
        }
        NodeUP n = parseAlt(inner);
        m_depth--;
        if (peek() != ')') {
            throw RegexError(start, "missing closing ')'");
        }
        m_pos++;
        return n;
    }

    // Parses an escape at m_pos (on the backslash). In a class, `into` is set
    // and the escape's characters are added to it; otherwise a node is
    // returned.
    NodeUP parseEscape(Flags &f, bool in_class, Ranges *into) {
        size_t start = m_pos;
        m_pos++;    // '\'
        if (eof()) {
            throw RegexError(start, "trailing backslash at the end of the pattern");
        }
        char c = m_p[m_pos++];

        const Ranges *perl = nullptr;
        bool neg = false;
        switch (c) {
            case 'd': perl = &digitRanges(); break;
            case 'D': perl = &digitRanges(); neg = true; break;
            case 'w': perl = &wordRanges(); break;
            case 'W': perl = &wordRanges(); neg = true; break;
            case 's': perl = &spaceRanges(); break;
            case 'S': perl = &spaceRanges(); neg = true; break;
            default: break;
        }
        if (perl) {
            Ranges r = neg ? negate(*perl) : *perl;
            if (in_class) {
                into->insert(into->end(), r.begin(), r.end());
                return nullptr;
            }
            return classNode(std::move(r));
        }

        if (!in_class) {
            switch (c) {
                case 'b': return assertNode(AssertKind::WordBoundary);
                case 'B': return assertNode(AssertKind::NotWordBoundary);
                case 'A': return assertNode(AssertKind::BeginText);
                case 'z': return assertNode(AssertKind::EndText);
                case 'Q': {
                    // \Q...\E: literal text
                    NodeUP n = mkNode(Node::K::Concat);
                    while (!eof()) {
                        if (peek() == '\\' && peek(1) == 'E') {
                            m_pos += 2;
                            break;
                        }
                        n->kids.push_back(literal(nextCodePoint(), f));
                    }
                    return n;
                }
                default: break;
            }
        }

        uint32_t cp;
        switch (c) {
            case 'a': cp = 0x07; break;
            case 'f': cp = 0x0C; break;
            case 't': cp = 0x09; break;
            case 'n': cp = 0x0A; break;
            case 'r': cp = 0x0D; break;
            case 'v': cp = 0x0B; break;
            case 'x': {
                auto hv = [](char h) -> int {
                    if (h >= '0' && h <= '9') return h - '0';
                    if (h >= 'a' && h <= 'f') return h - 'a' + 10;
                    if (h >= 'A' && h <= 'F') return h - 'A' + 10;
                    return -1;
                };
                if (peek() == '{') {
                    m_pos++;
                    uint32_t v = 0;
                    size_t ds = m_pos;
                    while (!eof() && hv(peek()) >= 0) {
                        v = v * 16 + static_cast<uint32_t>(hv(peek()));
                        if (v > MaxCodePoint) {
                            throw RegexError(start, "escape sequence is out of the Unicode range");
                        }
                        m_pos++;
                    }
                    if (m_pos == ds || peek() != '}') {
                        throw RegexError(start, "invalid \\x{...} escape");
                    }
                    m_pos++;
                    cp = v;
                } else {
                    int h1 = hv(peek()), h2 = hv(peek(1));
                    if (h1 < 0 || h2 < 0) {
                        throw RegexError(start, "\\x escape needs two hexadecimal digits");
                    }
                    m_pos += 2;
                    cp = static_cast<uint32_t>(h1 * 16 + h2);
                }
            } break;
            case '0': case '1': case '2': case '3': case '4': case '5': case '6': case '7': {
                // RE2: \0, or an octal escape of up to three digits. A single
                // non-zero digit is a backreference, which RE2 does not have.
                if (c != '0' && !(peek() >= '0' && peek() <= '7')) {
                    throw RegexError(start, "backreferences are not supported (RE2 syntax)");
                }
                uint32_t v = static_cast<uint32_t>(c - '0');
                for (int k=0; k<2 && peek() >= '0' && peek() <= '7'; k++) {
                    v = v * 8 + static_cast<uint32_t>(m_p[m_pos++] - '0');
                }
                cp = v;
            } break;
            case '8': case '9':
                throw RegexError(start, "backreferences are not supported (RE2 syntax)");
            case 'p': case 'P':
                throw RegexError(start, "Unicode character classes (\\p, \\P) are not supported");
            case 'C':
                throw RegexError(start, "\\C (any byte) is not supported");
            default:
                // Any escaped ASCII punctuation stands for itself.
                if ((c >= '!' && c <= '/') || (c >= ':' && c <= '@')
                        || (c >= '[' && c <= '`') || (c >= '{' && c <= '~')) {
                    cp = static_cast<uint32_t>(c);
                    break;
                }
                throw RegexError(start, std::string("invalid escape sequence '\\") + c + "'");
        }

        if (in_class) {
            addFolded(*into, cp, cp, f.fold);
            return nullptr;
        }
        return literal(cp, f);
    }

    // Reads one class member character (for a range end), returning it.
    uint32_t classChar(Flags &f, bool &was_set, Ranges &r) {
        was_set = false;
        if (peek() == '\\') {
            Ranges tmp;
            Flags nf = f;
            nf.fold = false;
            size_t before = m_pos;
            parseEscape(nf, true, &tmp);
            if (tmp.size() != 1 || tmp[0].first != tmp[0].second) {
                // \d etc. cannot be a range end
                r.insert(r.end(), tmp.begin(), tmp.end());
                was_set = true;
                (void)before;
                return 0;
            }
            return tmp[0].first;
        }
        return nextCodePoint();
    }

    NodeUP parseClass(Flags &f) {
        size_t start = m_pos;
        m_pos++;    // '['
        bool neg = false;
        if (peek() == '^') {
            neg = true;
            m_pos++;
        }
        Ranges r;
        bool first = true;
        while (true) {
            if (eof()) {
                throw RegexError(start, "missing closing ']'");
            }
            if (peek() == ']' && !first) {
                m_pos++;
                break;
            }
            first = false;

            if (peek() == '[' && peek(1) == ':') {
                size_t e = m_p.find(":]", m_pos + 2);
                if (e != std::string::npos) {
                    std::string name = m_p.substr(m_pos + 2, e - (m_pos + 2));
                    bool pneg = false;
                    if (!name.empty() && name[0] == '^') {
                        pneg = true;
                        name = name.substr(1);
                    }
                    Ranges pr;
                    if (!posixClass(name, pr)) {
                        throw RegexError(m_pos, "invalid character class name '[:" + name + ":]'");
                    }
                    if (pneg) {
                        pr = negate(pr);
                    }
                    r.insert(r.end(), pr.begin(), pr.end());
                    m_pos = e + 2;
                    continue;
                }
            }

            size_t item = m_pos;
            bool was_set;
            uint32_t lo = classChar(f, was_set, r);
            if (was_set) {
                continue;
            }
            if (peek() == '-' && peek(1) != ']' && m_pos + 1 < m_p.size()) {
                m_pos++;
                bool hi_set;
                uint32_t hi = classChar(f, hi_set, r);
                if (hi_set) {
                    throw RegexError(item, "bad character class range");
                }
                if (hi < lo) {
                    throw RegexError(item, "bad character class range: the end is before the start");
                }
                addFolded(r, lo, hi, f.fold);
            } else {
                addFolded(r, lo, lo, f.fold);
            }
        }
        if (neg) {
            r = negate(r);
        }
        return classNode(std::move(r));
    }

    const std::string   &m_p;
    size_t              m_pos;
    int                 m_depth;
};

//****************************************************************************
//* Compiler
//****************************************************************************

class Compiler {
public:
    explicit Compiler(std::vector<Inst> &prog) : m_prog(prog) { }

    void compile(const Node *n) {
        switch (n->k) {
            case Node::K::Empty:
                break;
            case Node::K::Class: {
                Inst &i = emit(Inst::Op::Class);
                i.ranges = n->ranges;
            } break;
            case Node::K::Any:
                emit(Inst::Op::Any);
                break;
            case Node::K::AnyNotNL:
                emit(Inst::Op::AnyNotNL);
                break;
            case Node::K::Assert:
                emit(Inst::Op::Assert).assertion = n->assertion;
                break;
            case Node::K::Concat:
                for (const NodeUP &k : n->kids) {
                    compile(k.get());
                }
                break;
            case Node::K::Alt: {
                // split L1, next ; L1: a ; jmp end ; next: split ... ; last
                std::vector<uint32_t> jmps;
                for (size_t k=0; k<n->kids.size(); k++) {
                    if (k + 1 < n->kids.size()) {
                        uint32_t split = pc();
                        emit(Inst::Op::Split);
                        m_prog[split].x = pc();
                        compile(n->kids[k].get());
                        jmps.push_back(pc());
                        emit(Inst::Op::Jmp);
                        m_prog[split].y = pc();
                    } else {
                        compile(n->kids[k].get());
                    }
                }
                for (uint32_t j : jmps) {
                    m_prog[j].x = pc();
                }
            } break;
            case Node::K::Repeat: {
                const Node *body = n->kids[0].get();
                for (int k=0; k<n->min; k++) {
                    compile(body);
                }
                if (n->max == -1) {
                    // L: split body, end ; body ; jmp L
                    uint32_t l = pc();
                    emit(Inst::Op::Split);
                    m_prog[l].x = pc();
                    compile(body);
                    emit(Inst::Op::Jmp).x = l;
                    m_prog[l].y = pc();
                } else {
                    // (body (body (...)?)?)?
                    std::vector<uint32_t> splits;
                    for (int k=n->min; k<n->max; k++) {
                        uint32_t s = pc();
                        emit(Inst::Op::Split);
                        m_prog[s].x = pc();
                        splits.push_back(s);
                        compile(body);
                    }
                    for (uint32_t s : splits) {
                        m_prog[s].y = pc();
                    }
                }
            } break;
        }
    }

    uint32_t pc() const { return static_cast<uint32_t>(m_prog.size()); }

    Inst &emit(Inst::Op op) {
        if (m_prog.size() >= MaxProgram) {
            throw RegexError(0, "regular expression is too large");
        }
        m_prog.emplace_back();
        m_prog.back().op = op;
        return m_prog.back();
    }

private:
    std::vector<Inst>   &m_prog;
};

//****************************************************************************
//* Simulation
//****************************************************************************

class ThreadList {
public:
    explicit ThreadList(size_t n) : m_sparse(n, 0), m_dense(n, 0), m_size(0) { }

    bool contains(uint32_t pc) const {
        uint32_t i = m_sparse[pc];
        return i < m_size && m_dense[i] == pc;
    }
    void insert(uint32_t pc) {
        m_sparse[pc] = m_size;
        m_dense[m_size++] = pc;
    }
    void clear() { m_size = 0; }
    uint32_t size() const { return m_size; }
    uint32_t at(uint32_t i) const { return m_dense[i]; }

private:
    std::vector<uint32_t>   m_sparse;
    std::vector<uint32_t>   m_dense;
    uint32_t                m_size;
};

}

Regex::Regex() : m_start(0) { }

Regex::~Regex() { }

size_t Regex::size() const {
    return m_prog.size();
}

Regex *Regex::compile(const std::string &pattern) {
    Parser p(pattern);
    NodeUP tree = p.parse();

    std::unique_ptr<Regex> re(new Regex());
    Compiler c(re->m_prog);
    c.compile(tree.get());
    c.emit(Inst::Op::Match);
    re->m_start = 0;
    return re.release();
}

bool Regex::search(const std::string &text, uint64_t *steps_p) const {
    size_t n = m_prog.size();
    ThreadList clist(n), nlist(n);
    std::vector<uint32_t> stack;
    uint64_t steps = 0;

    int32_t prev = -1;
    size_t pos = 0;
    bool matched = false;

    // Follows empty transitions from `pc` at the current position, adding
    // every reached consuming instruction to `list`. Iterative: the program
    // can be long, and WASM stacks are small.
    auto addThread = [&](ThreadList &list, uint32_t pc0, int32_t cur) {
        stack.push_back(pc0);
        while (!stack.empty()) {
            uint32_t pc = stack.back();
            stack.pop_back();
            if (list.contains(pc)) {
                continue;
            }
            list.insert(pc);
            steps++;
            const Inst &i = m_prog[pc];
            switch (i.op) {
                case Inst::Op::Jmp:
                    stack.push_back(i.x);
                    break;
                case Inst::Op::Split:
                    stack.push_back(i.y);
                    stack.push_back(i.x);
                    break;
                case Inst::Op::Assert: {
                    bool ok = false;
                    switch (i.assertion) {
                        case AssertKind::BeginText: ok = (prev == -1); break;
                        case AssertKind::EndText: ok = (cur == -1); break;
                        case AssertKind::BeginLine: ok = (prev == -1 || prev == '\n'); break;
                        case AssertKind::EndLine: ok = (cur == -1 || cur == '\n'); break;
                        case AssertKind::WordBoundary:
                            ok = isWordChar(prev) != isWordChar(cur);
                            break;
                        case AssertKind::NotWordBoundary:
                            ok = isWordChar(prev) == isWordChar(cur);
                            break;
                    }
                    if (ok) {
                        stack.push_back(pc + 1);
                    }
                } break;
                case Inst::Op::Match:
                    matched = true;
                    break;
                default:
                    break;
            }
        }
    };

    while (true) {
        size_t len = 0;
        int32_t cur = -1;
        if (pos < text.size()) {
            cur = static_cast<int32_t>(decodeUtf8(text, pos, len));
        }

        // Unanchored: a new thread starts at every position.
        addThread(clist, m_start, cur);
        if (matched) {
            break;
        }
        if (cur == -1) {
            break;
        }

        nlist.clear();
        for (uint32_t k=0; k<clist.size(); k++) {
            uint32_t pc = clist.at(k);
            const Inst &i = m_prog[pc];
            steps++;
            bool take = false;
            switch (i.op) {
                case Inst::Op::Any:
                    take = true;
                    break;
                case Inst::Op::AnyNotNL:
                    take = (cur != '\n');
                    break;
                case Inst::Op::Class: {
                    uint32_t c = static_cast<uint32_t>(cur);
                    auto it = std::upper_bound(i.ranges.begin(), i.ranges.end(),
                        Range(c, UINT32_MAX));
                    take = (it != i.ranges.begin() && (it - 1)->second >= c);
                } break;
                default:
                    break;
            }
            if (take) {
                // The empty transitions out of the next state are followed at
                // the next position, where the character after is known.
                nlist.insert(pc + 1);
            }
        }

        prev = cur;
        pos += len;
        std::swap(clist, nlist);

        // Re-run the closure of the surviving threads at the new position.
        std::vector<uint32_t> seeds;
        seeds.reserve(clist.size());
        for (uint32_t k=0; k<clist.size(); k++) {
            seeds.push_back(clist.at(k));
        }
        clist.clear();
        int32_t next_cur = -1;
        if (pos < text.size()) {
            size_t l2;
            next_cur = static_cast<int32_t>(decodeUtf8(text, pos, l2));
        }
        for (uint32_t s : seeds) {
            addThread(clist, s, next_cur);
            if (matched) {
                break;
            }
        }
        if (matched) {
            break;
        }
    }

    if (steps_p) {
        *steps_p = steps;
    }
    return matched;
}

}
}
}
