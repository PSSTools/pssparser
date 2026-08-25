/**
 * TemplateScanner.h
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
#pragma once
#include <string>
#include <vector>
#include <stdint.h>

namespace pssp {

/**
 * The five things a triple-quoted string can be made of -- PSS 3.1 §4.7.1.
 */
enum class TemplateTokenKind {
    Text,           //< literal text between special elements
    Mustache,       //< {{ expression }}          §4.7.1.1
    Directive,      //< {% ... %}                 §4.7.1.2
    BlockComment,   //< {# ... #}                 §4.7.1.3
    LineComment     //< {#} ... end of line       §4.7.1.3
};

/**
 * One lexical element of a template string.
 *
 * `offset`/`extent` cover the element *including* its delimiters; `inner_off`/
 * `inner_ext` cover the content between them. Both are byte offsets into the
 * `raw` text that was scanned, which is what a renderer needs in order to
 * splice. `line`/`col` are absolute file positions, already rebased onto the
 * position the template started at.
 */
struct TemplateToken {
    TemplateTokenKind   kind;
    int32_t             offset;
    int32_t             extent;
    int32_t             inner_off;
    int32_t             inner_ext;
    int32_t             line;
    int32_t             col;
    int32_t             inner_line;     //< position of inner_off, for fragment rebasing
    int32_t             inner_col;
    bool                is_own_line;
};

/**
 * A lexical error found while scanning. `code` is the numeric part of the
 * marker ID (108, 110), so the caller can pick the right message without the
 * scanner depending on the marker machinery.
 */
struct TemplateScanError {
    int32_t             code;
    std::string         detail;
    int32_t             offset;
    int32_t             extent;
    int32_t             line;
    int32_t             col;
};

/**
 * Splits a triple-quoted string's content into text runs and special elements.
 *
 * This is deliberately *only* delimiter matching. The template structure is
 * not a grammar: `{{`...`}}`, `{%`...`%}`, `{#`...`#}` and `{#}`...newline do
 * not recurse -- directives nest at the *block* level, which is a stack the
 * caller maintains, not a nesting of delimiters. Everything inside a delimiter
 * is ordinary PSS that the real parser handles, so nothing here knows about
 * expressions, identifiers or keywords.
 *
 * Keeping it free of ANTLR and of the AST factory is what makes it testable on
 * its own, which matters because the edge cases here are where this goes
 * wrong.
 *
 * Block structure -- an unclosed `{% if %}`, a `{%%}` too many, an `{% else %}`
 * with no `if` -- is *not* checked here. That needs the directive keyword,
 * which means classifying directive content, which is the caller's job
 * (TaskBuildTemplate). The split keeps this class purely lexical.
 */
class TemplateScanner {
public:
    TemplateScanner();

    virtual ~TemplateScanner();

    /**
     * Scan `raw`, the content of a triple-quoted string with its quotes
     * already stripped.
     *
     * `base_line`/`base_col` are the file position of raw[0] -- for a
     * TRIPLE_DOUBLE_QUOTED_STRING token that is the token's own line and its
     * `charPositionInLine + 3`, the three being the opening `"""`.
     */
    void scan(
        const std::string   &raw,
        int32_t             base_line,
        int32_t             base_col);

    const std::vector<TemplateToken> &tokens() const { return m_tokens; }

    const std::vector<TemplateScanError> &errors() const { return m_errors; }

    /** True when at least one element is a mustache, directive or comment. */
    bool hasSpecials() const;

private:

    /**
     * Find the closing delimiter `close` starting at `i`, skipping over string
     * literals.
     *
     * `{{ m["}}"] }}` is legal PSS, so a naive search for `}}` would stop
     * inside the subscript. Both `"..."` (honouring `\"`) and `"""..."""` are
     * skipped. Comments are *not* skipped -- a comment inside a mustache is
     * not a thing.
     *
     * Returns the offset of the delimiter, or -1 if the end of the text is
     * reached first.
     */
    int32_t findClose(
        const std::string   &raw,
        int32_t             i,
        const char          *close);

    /** Advance m_line/m_col over raw[from..to). */
    void advance(const std::string &raw, int32_t from, int32_t to);

    /**
     * Second pass: mark directives and comments that stand alone on their
     * line.
     *
     * §4.7.1.2: when a line holds directives and nothing else but whitespace,
     * that whitespace *and the terminating newline* are excluded from the
     * result. That is an evaluation rule, but deciding it needs the raw text,
     * so it is settled once here rather than by every renderer.
     *
     * A mustache on the line disqualifies it -- a mustache produces output.
     * Comments do not produce output, so they are permitted alongside.
     */
    void markOwnLineDirectives(const std::string &raw);

private:
    std::vector<TemplateToken>          m_tokens;
    std::vector<TemplateScanError>      m_errors;
    int32_t                             m_line;
    int32_t                             m_col;
};

}
