/**
 * TemplateScanner.cpp
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
 * Created on:
 *     Author:
 */
#include "TemplateScanner.h"

namespace pssp {

TemplateScanner::TemplateScanner() : m_line(1), m_col(1) { }

TemplateScanner::~TemplateScanner() { }

static bool isWs(char c) {
    return c == ' ' || c == '\t' || c == '\r';
}

void TemplateScanner::advance(const std::string &raw, int32_t from, int32_t to) {
    for (int32_t i=from; i<to; i++) {
        if (raw[i] == '\n') {
            m_line++;
            m_col = 1;
        } else {
            m_col++;
        }
    }
}

int32_t TemplateScanner::findClose(
        const std::string   &raw,
        int32_t             i,
        const char          *close) {
    int32_t n = (int32_t)raw.size();

    while (i < n) {
        if (raw.compare(i, 2, close) == 0) {
            return i;
        }

        if (raw[i] == '"') {
            // A string literal inside the delimiters. Skip it, or `{{ m["}}"] }}`
            // -- which is legal PSS -- would terminate at the wrong place.
            if (raw.compare(i, 3, "\"\"\"") == 0) {
                std::string::size_type e = raw.find("\"\"\"", i+3);
                if (e == std::string::npos) {
                    // Unterminated; let the delimiter search fail rather than
                    // running off the end here.
                    return -1;
                }
                i = (int32_t)e + 3;
                continue;
            } else {
                i++;
                while (i < n && raw[i] != '"') {
                    // §4.7 gives triple-quoted strings no escape mechanism, but
                    // an ordinary "..." nested *inside* a mustache is ordinary
                    // PSS, where \" is an escape.
                    i += (raw[i] == '\\') ? 2 : 1;
                }
                if (i >= n) {
                    return -1;
                }
                i++;    // the closing quote
                continue;
            }
        }
        i++;
    }
    return -1;
}

void TemplateScanner::scan(
        const std::string   &raw,
        int32_t             base_line,
        int32_t             base_col) {
    m_tokens.clear();
    m_errors.clear();
    m_line = base_line;
    m_col = base_col;

    int32_t n = (int32_t)raw.size();
    int32_t i = 0;
    int32_t text_start = 0;
    int32_t text_line = m_line;
    int32_t text_col = m_col;

    // Close the run of literal text that ends at `end`, if it is non-empty.
    auto flushText = [&](int32_t end) {
        if (end > text_start) {
            TemplateToken t;
            t.kind = TemplateTokenKind::Text;
            t.offset = text_start;
            t.extent = end - text_start;
            t.inner_off = text_start;
            t.inner_ext = end - text_start;
            t.line = text_line;
            t.col = text_col;
            t.inner_line = text_line;
            t.inner_col = text_col;
            t.is_own_line = false;
            m_tokens.push_back(t);
        }
    };

    while (i < n) {
        if (raw[i] != '{') {
            i++;
            continue;
        }

        // Order matters: `{#}` must be tested before `{#`, or every line
        // comment reads as an unterminated block comment.
        bool is_line_comment  = (raw.compare(i, 3, "{#}") == 0);
        bool is_block_comment = !is_line_comment && (raw.compare(i, 2, "{#") == 0);
        bool is_mustache      = (raw.compare(i, 2, "{{") == 0);
        bool is_directive     = (raw.compare(i, 2, "{%") == 0);

        if (!is_line_comment && !is_block_comment && !is_mustache && !is_directive) {
            // A lone `{` is ordinary text. This is also what makes `{ {` a
            // conformant spelling for a literal `{{` (D3.2): it needs no
            // scanner support at all.
            i++;
            continue;
        }

        flushText(i);
        advance(raw, text_start, i);

        int32_t tok_line = m_line;
        int32_t tok_col = m_col;

        TemplateToken t;
        t.line = tok_line;
        t.col = tok_col;
        t.offset = i;
        t.is_own_line = false;

        if (is_line_comment) {
            // `{#}` runs to and including the next newline.
            std::string::size_type nl = raw.find('\n', i+3);
            int32_t content_end = (nl == std::string::npos) ? n : (int32_t)nl;
            int32_t end = (nl == std::string::npos) ? n : (int32_t)nl + 1;
            t.kind = TemplateTokenKind::LineComment;
            t.extent = end - i;
            t.inner_off = i + 3;
            t.inner_ext = content_end - (i + 3);
            advance(raw, i, i+3);
            t.inner_line = m_line;
            t.inner_col = m_col;
            advance(raw, i+3, end);
            m_tokens.push_back(t);
            i = end;
        } else if (is_block_comment) {
            // Nothing inside is scanned -- §4.7.1.3 is explicit that mustaches
            // and directives inside a comment are not interpreted. So this is a
            // plain find, not findClose().
            std::string::size_type ce = raw.find("#}", i+2);
            if (ce == std::string::npos) {
                m_errors.push_back({110, "unterminated template comment",
                    i, n-i, tok_line, tok_col});
                markOwnLineDirectives(raw);
                return;
            }
            int32_t e = (int32_t)ce;
            t.kind = TemplateTokenKind::BlockComment;
            t.extent = (e + 2) - i;
            t.inner_off = i + 2;
            t.inner_ext = e - (i + 2);
            advance(raw, i, i+2);
            t.inner_line = m_line;
            t.inner_col = m_col;
            advance(raw, i+2, e+2);
            m_tokens.push_back(t);
            i = e + 2;
        } else {
            const char *close = is_mustache ? "}}" : "%}";
            int32_t e = findClose(raw, i+2, close);
            if (e == -1) {
                if (is_mustache) {
                    // PSS108. The caller attaches the `{ {` hint (D3.3) -- a
                    // C programmer who wrote a legal array initializer must be
                    // told the workaround, not just that something is wrong.
                    m_errors.push_back({108, "", i, n-i, tok_line, tok_col});
                } else {
                    m_errors.push_back({110, "unterminated template directive",
                        i, n-i, tok_line, tok_col});
                }
                markOwnLineDirectives(raw);
                return;
            }
            t.kind = is_mustache ? TemplateTokenKind::Mustache
                                 : TemplateTokenKind::Directive;
            t.extent = (e + 2) - i;
            t.inner_off = i + 2;
            t.inner_ext = e - (i + 2);
            advance(raw, i, i+2);
            t.inner_line = m_line;
            t.inner_col = m_col;
            advance(raw, i+2, e+2);
            m_tokens.push_back(t);
            i = e + 2;
        }

        text_start = i;
        text_line = m_line;
        text_col = m_col;
    }

    flushText(n);

    markOwnLineDirectives(raw);
}

void TemplateScanner::markOwnLineDirectives(const std::string &raw) {
    int32_t n = (int32_t)raw.size();

    for (size_t ti=0; ti<m_tokens.size(); ti++) {
        TemplateToken &t = m_tokens.at(ti);
        if (t.kind != TemplateTokenKind::Directive &&
            t.kind != TemplateTokenKind::BlockComment &&
            t.kind != TemplateTokenKind::LineComment) {
            continue;
        }

        // Walk out to the enclosing line in `raw`, then require every byte of
        // it that is not covered by a directive or comment to be whitespace.
        int32_t ls = t.offset;
        while (ls > 0 && raw[ls-1] != '\n') {
            ls--;
        }
        int32_t le = t.offset + t.extent;
        while (le < n && raw[le-1] != '\n') {
            le++;
        }

        // Deliberately a scan rather than an index: this is O(line-length x
        // tokens) per directive, which for a template -- tens of lines, tens of
        // tokens -- is a few thousand comparisons. An interval index would be
        // faster and harder to get right, and templates never get big enough
        // for it to matter.
        bool own_line = true;
        int32_t p = ls;
        while (p < le && own_line) {
            // Is p inside some token that contributes no output?
            bool covered = false;
            for (size_t tj=0; tj<m_tokens.size(); tj++) {
                const TemplateToken &o = m_tokens.at(tj);
                if (o.kind == TemplateTokenKind::Text) {
                    continue;
                }
                if (p >= o.offset && p < o.offset + o.extent) {
                    if (o.kind == TemplateTokenKind::Mustache) {
                        // A mustache produces output, so the line is not
                        // directive-only.
                        own_line = false;
                    }
                    p = o.offset + o.extent;
                    covered = true;
                    break;
                }
            }
            if (!covered) {
                if (raw[p] != '\n' && !isWs(raw[p])) {
                    own_line = false;
                }
                p++;
            }
        }

        t.is_own_line = own_line;
    }
}

bool TemplateScanner::hasSpecials() const {
    for (std::vector<TemplateToken>::const_iterator
        it=m_tokens.begin(); it!=m_tokens.end(); it++) {
        if (it->kind != TemplateTokenKind::Text) {
            return true;
        }
    }
    return false;
}

}
