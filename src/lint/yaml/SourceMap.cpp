/*
 * SourceMap.cpp
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
#include "SourceMap.h"

namespace pssp {
namespace lint {
namespace yaml {

LineIndex::LineIndex(const std::string &text) {
    m_starts.push_back(0);
    for (size_t i=0; i<text.size(); i++) {
        if (text[i] == '\n') {
            m_starts.push_back(static_cast<uint32_t>(i + 1));
        }
    }
}

Mark LineIndex::at(uint32_t offset) const {
    auto it = std::upper_bound(m_starts.begin(), m_starts.end(), offset);
    size_t line = static_cast<size_t>(it - m_starts.begin());     // 1-based
    Mark m;
    m.line = static_cast<uint32_t>(line);
    m.col = offset - m_starts[line - 1] + 1;
    m.offset = offset;
    return m;
}

namespace {

// One value byte as the source produces it, before the style's folding: the
// byte, and the source offset it is charged to.
struct Cand {
    char        ch;
    uint32_t    off;
};

// Produces a scalar's candidate bytes from the source, on demand: a scalar's
// extent is not known up front (a plain scalar ends where the value does), so
// the walk pulls only as many bytes as the value needs.
class Source {
public:
    Source(const std::string &text, uint32_t begin, Node::Style style) :
            m_t(text), m_pos(begin), m_style(style), m_indent(-1), m_line_start(true) { }

    void setIndent(int indent) { m_indent = indent; }

    // The source offset of the next unread byte.
    uint32_t pos() const { return static_cast<uint32_t>(m_pos); }

    bool next(Cand &c) {
        if (m_qi < m_q.size()) {
            c = m_q[m_qi++];
            return true;
        }
        m_q.clear();
        m_qi = 0;
        switch (m_style) {
            case Node::Style::SingleQuoted: return nextSquo(c);
            case Node::Style::DoubleQuoted: return nextDquo(c);
            case Node::Style::Literal:
            case Node::Style::Folded: return nextBlock(c);
            default: return nextRaw(c);
        }
    }

private:
    bool eof() const { return m_pos >= m_t.size(); }

    bool nextRaw(Cand &c) {
        if (eof()) {
            return false;
        }
        c = Cand{m_t[m_pos], static_cast<uint32_t>(m_pos)};
        m_pos++;
        return true;
    }

    // '' is one quote; a lone ' ends the scalar.
    bool nextSquo(Cand &c) {
        if (eof()) {
            return false;
        }
        if (m_t[m_pos] == '\'') {
            if (m_pos + 1 < m_t.size() && m_t[m_pos+1] == '\'') {
                c = Cand{'\'', static_cast<uint32_t>(m_pos)};
                m_pos += 2;
                return true;
            }
            return false;
        }
        return nextRaw(c);
    }

    static int hexval(char h) {
        if (h >= '0' && h <= '9') return h - '0';
        if (h >= 'a' && h <= 'f') return h - 'a' + 10;
        if (h >= 'A' && h <= 'F') return h - 'A' + 10;
        return -1;
    }

    void pushUtf8(uint32_t cp, uint32_t off) {
        char buf[4];
        size_t n;
        if (cp < 0x80) {
            buf[0] = static_cast<char>(cp); n = 1;
        } else if (cp < 0x800) {
            buf[0] = static_cast<char>(0xC0 | (cp >> 6));
            buf[1] = static_cast<char>(0x80 | (cp & 0x3F)); n = 2;
        } else if (cp < 0x10000) {
            buf[0] = static_cast<char>(0xE0 | (cp >> 12));
            buf[1] = static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            buf[2] = static_cast<char>(0x80 | (cp & 0x3F)); n = 3;
        } else {
            buf[0] = static_cast<char>(0xF0 | (cp >> 18));
            buf[1] = static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
            buf[2] = static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            buf[3] = static_cast<char>(0x80 | (cp & 0x3F)); n = 4;
        }
        for (size_t i=0; i<n; i++) {
            m_q.push_back(Cand{buf[i], off});
        }
    }

    // Escapes are decoded, every byte charged to the backslash; an escaped
    // line break and the next line's indentation produce nothing; an
    // unescaped '"' ends the scalar.
    bool nextDquo(Cand &c) {
        while (true) {
            if (eof() || m_t[m_pos] == '"') {
                return false;
            }
            if (m_t[m_pos] != '\\') {
                return nextRaw(c);
            }
            uint32_t at = static_cast<uint32_t>(m_pos);
            if (m_pos + 1 >= m_t.size()) {
                return false;
            }
            char e = m_t[m_pos+1];
            m_pos += 2;
            uint32_t cp;
            int ndig = 0;
            switch (e) {
                case '0': cp = 0x00; break;
                case 'a': cp = 0x07; break;
                case 'b': cp = 0x08; break;
                case 't': case '\t': cp = 0x09; break;
                case 'n': cp = 0x0A; break;
                case 'v': cp = 0x0B; break;
                case 'f': cp = 0x0C; break;
                case 'r': cp = 0x0D; break;
                case 'e': cp = 0x1B; break;
                case ' ': cp = 0x20; break;
                case '"': cp = 0x22; break;
                case '/': cp = 0x2F; break;
                case '\\': cp = 0x5C; break;
                case 'N': cp = 0x85; break;
                case '_': cp = 0xA0; break;
                case 'L': cp = 0x2028; break;
                case 'P': cp = 0x2029; break;
                case 'x': ndig = 2; cp = 0; break;
                case 'u': ndig = 4; cp = 0; break;
                case 'U': ndig = 8; cp = 0; break;
                case '\r':
                case '\n':
                    // Escaped line break: the break and the next line's
                    // leading whitespace vanish.
                    if (e == '\r' && !eof() && m_t[m_pos] == '\n') {
                        m_pos++;
                    }
                    while (!eof() && (m_t[m_pos] == ' ' || m_t[m_pos] == '\t')) {
                        m_pos++;
                    }
                    continue;
                default:
                    return false;
            }
            for (int i=0; i<ndig; i++) {
                if (eof() || hexval(m_t[m_pos]) < 0) {
                    return false;
                }
                cp = cp * 16 + static_cast<uint32_t>(hexval(m_t[m_pos++]));
            }
            // An escaped JSON surrogate pair is one code point (the loader
            // joins rapidyaml's two halves, YamlDoc.cpp).
            if (e == 'u' && cp >= 0xD800 && cp < 0xDC00 && m_pos + 6 <= m_t.size()
                    && m_t[m_pos] == '\\' && m_t[m_pos+1] == 'u') {
                uint32_t lo = 0;
                bool ok = true;
                for (int i=0; i<4; i++) {
                    int h = hexval(m_t[m_pos+2+i]);
                    ok &= (h >= 0);
                    lo = lo * 16 + static_cast<uint32_t>(h < 0 ? 0 : h);
                }
                if (ok && lo >= 0xDC00 && lo < 0xE000) {
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                    m_pos += 6;
                }
            }
            pushUtf8(cp, at);
            c = m_q[m_qi++];
            return true;
        }
    }

    // A block scalar's body, line by line: each content line less the
    // block's indentation, then its line break; a blank line is its break
    // alone. A non-blank line indented less than the block ends it.
    bool nextBlock(Cand &c) {
        while (true) {
            if (eof()) {
                return false;
            }
            if (m_line_start) {
                size_t eol = m_t.find('\n', m_pos);
                if (eol == std::string::npos) {
                    eol = m_t.size();
                }
                size_t sp = m_pos;
                while (sp < eol && m_t[sp] == ' ') {
                    sp++;
                }
                bool blank = (sp == eol) || (m_t[sp] == '\r' && sp + 1 == eol);
                if (blank) {
                    // Spaces past the indentation on a blank line are
                    // content in a literal block; offer them, the walk drops
                    // what the value does not have.
                    m_pos = std::min(m_pos + static_cast<size_t>(std::max(m_indent, 0)), sp);
                } else {
                    if (static_cast<int>(sp - m_pos) < m_indent) {
                        return false;
                    }
                    m_pos += static_cast<size_t>(m_indent);
                }
                m_line_start = false;
            }
            if (eof()) {
                return false;
            }
            char ch = m_t[m_pos];
            c = Cand{ch, static_cast<uint32_t>(m_pos)};
            m_pos++;
            if (ch == '\n') {
                m_line_start = true;
            }
            return true;
        }
    }

    const std::string   &m_t;
    size_t              m_pos;
    Node::Style         m_style;
    int                 m_indent;
    bool                m_line_start;
    std::vector<Cand>   m_q;
    size_t              m_qi = 0;
};

bool isBlank(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
}

// The block's indentation: the first non-blank source line's leading spaces,
// less the first non-blank value line's (a literal keeps extra indentation,
// and an explicit indentation indicator leaves some in the value).
int blockIndent(const std::string &text, uint32_t begin, const std::string &value) {
    size_t p = begin;
    while (p < text.size()) {
        size_t eol = text.find('\n', p);
        if (eol == std::string::npos) {
            eol = text.size();
        }
        size_t sp = p;
        while (sp < eol && text[sp] == ' ') {
            sp++;
        }
        if (sp < eol && text[sp] != '\r') {
            size_t src_lead = sp - p;
            size_t v = 0;
            while (v < value.size() && value[v] == '\n') {
                v++;
            }
            size_t val_lead = 0;
            while (v + val_lead < value.size() && value[v + val_lead] == ' ') {
                val_lead++;
            }
            return (src_lead >= val_lead) ? static_cast<int>(src_lead - val_lead) : -1;
        }
        p = eol + 1;
    }
    return 0;
}

}

uint32_t sourceOffset(const Node &n, uint32_t off) {
    if (n.srcMap.empty()) {
        return n.mark.offset;
    }
    size_t size = n.s.size();
    if (off > size) {
        off = static_cast<uint32_t>(size);
    }
    size_t last = size;
    while (last > 0 && isBlank(n.s[last-1])) {
        last--;
    }
    if (off >= last && last > 0) {
        return n.srcMap[last-1] + 1;
    }
    return n.srcMap[off];
}

bool mapScalar(
        const std::string           &text,
        uint32_t                    begin,
        Node::Style                 style,
        const std::string           &value,
        std::vector<uint32_t>       &out) {
    out.assign(value.size() + 1, begin);
    if (begin > text.size()) {
        return false;
    }

    Source src(text, begin, style);
    bool block = (style == Node::Style::Literal || style == Node::Style::Folded);
    if (block) {
        int indent = blockIndent(text, begin, value);
        if (indent < 0) {
            return false;
        }
        src.setIndent(indent);
    }

    std::vector<uint32_t> map(value.size() + 1, begin);
    uint32_t end = begin;
    Cand c;
    for (size_t v=0; v<value.size(); v++) {
        char want = value[v];
        while (true) {
            if (!src.next(c)) {
                return false;
            }
            if (c.ch == want) {
                break;
            }
            // A folded line break becomes a space.
            if (want == ' ' && c.ch == '\n') {
                break;
            }
            // Whitespace the style drops: indentation of a continuation
            // line, trailing spaces before a fold, the break of a line
            // folded into the next.
            if (isBlank(c.ch)) {
                continue;
            }
            return false;
        }
        map[v] = c.off;
        end = src.pos();
    }
    map[value.size()] = value.empty() ? begin : end;
    out.swap(map);
    return true;
}

}
}
}
