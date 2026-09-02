/**
 * AstBuilderIntTemplate.cpp
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
 *
 * ---------------------------------------------------------------------------
 * Triple-quoted string special elements -- PSS 3.1 §4.7.1.
 *
 * Split out of AstBuilderInt.cpp, which is large enough already, but these are
 * AstBuilderInt members rather than a separate class: building the expressions
 * inside a template needs mkExpr, mkDataType, mkId and the live scope stack,
 * all of which are AstBuilderInt's.
 *
 * The structure of a template is not a grammar -- it is delimiter matching,
 * which TemplateScanner does. Everything *inside* a delimiter is ordinary PSS,
 * so it is handed to the real generated parser, entered at whichever rule the
 * context calls for. That means the full expression grammar with zero grammar
 * changes and no possibility of two grammars drifting apart.
 * ---------------------------------------------------------------------------
 */
#include "AstBuilderInt.h"
#include "TemplateScanner.h"
#include "Marker.h"
#include "PSSLexer.h"
#include "PSSParser.h"
#include "pssp/ast/IFactory.h"
#include "dmgr/impl/DebugMacros.h"
#include <cstring>

namespace pssp {

/**
 * Collects the first syntax error from a fragment parse.
 *
 * The fragment parser must NOT use AstBuilderInt as its error listener. A raw
 * ANTLR message rebased out of a fragment -- "mismatched input '}' expecting
 * ..." -- is exactly the useless diagnostic D3.3 exists to prevent, so errors
 * are collected here and re-reported with the `{ {` hint attached.
 */
class FragmentErrorListener : public antlr4::BaseErrorListener {
public:
    virtual void syntaxError(
            antlr4::Recognizer          *recognizer,
            antlr4::Token               *offendingSymbol,
            size_t                      line,
            size_t                      charPositionInLine,
            const std::string           &msg,
            std::exception_ptr          e) override {
        if (!m_has) {
            m_has = true;
            m_msg = msg;
            m_sym = offendingSymbol ? offendingSymbol->getText() : std::string();
        }
    }

    bool hasError() const { return m_has; }

    const std::string &msg() const { return m_msg; }

    const std::string &sym() const { return m_sym; }

private:
    bool        m_has = false;
    std::string m_msg;
    std::string m_sym;
};

/**
 * D1 (mustache instance): the fragment parser hits the identical ANTLR
 * follow-set shapes as the main grammar's classifier in AstBuilderInt.cpp --
 * strip the same raw-jargon shapes into prose rather than pasting ANTLR's
 * message straight into "malformed mustache expression: <this>".
 */
static std::string humanizeFragmentError(const std::string &msg, const std::string &sym) {
    if (msg.find("mismatched input") != std::string::npos) {
        if (msg.find("expecting {ID, ESCAPED_ID}") != std::string::npos ||
                msg.find("expecting {'::', ID, ESCAPED_ID}") != std::string::npos) {
            return "expected identifier before '" + sym + "'";
        }
        std::string expecting = msg.substr(msg.find("expecting"));
        if (expecting.size() > 60) {
            return "unexpected '" + sym + "'";
        }
        return "unexpected '" + sym + "' " + expecting;
    }
    if (msg.find("extraneous input") != std::string::npos) {
        return "unexpected '" + sym + "'";
    }
    return msg;
}

/**
 * Owns one throwaway parser over a fragment of template text.
 *
 * The generated parser exposes a public method per rule, so a fragment can be
 * parsed starting at `expression`, `procedural_foreach_stmt`, and so on. The
 * ATN and DFA cache are static, so instances after the first are cheap.
 *
 * Declaration order matters here: each member is constructed from the one
 * above it, and the whole thing must outlive the parse tree it produces.
 */
class FragmentParser {
public:
    FragmentParser(const std::string &text) :
        m_input(text), m_lexer(&m_input), m_tokens(&m_lexer), m_parser(&m_tokens) {
        m_lexer.removeErrorListeners();
        m_lexer.addErrorListener(&m_listener);
        m_parser.removeErrorListeners();
        m_parser.addErrorListener(&m_listener);
    }

    PSSParser &parser() { return m_parser; }

    /** True when the fragment parsed cleanly *and* consumed all of its input. */
    bool ok() {
        return !m_listener.hasError() && m_tokens.LA(1) == antlr4::Token::EOF;
    }

    std::string error() {
        if (m_listener.hasError()) {
            return humanizeFragmentError(m_listener.msg(), m_listener.sym());
        } else if (m_tokens.LA(1) != antlr4::Token::EOF) {
            return "unexpected '" + m_tokens.LT(1)->getText() + "'";
        } else {
            return "";
        }
    }

private:
    FragmentErrorListener       m_listener;
    antlr4::ANTLRInputStream    m_input;
    PSSLexer                    m_lexer;
    antlr4::CommonTokenStream   m_tokens;
    PSSParser                   m_parser;
};

/**
 * Saves and restores the builder state that a re-entrant fragment build would
 * otherwise corrupt.
 *
 * - `m_expr`, because a template can appear *inside* an expression
 *   (`f("""{{a}}""")`), so mkExpr is already in flight when we recurse.
 * - `m_collectDocStrings`, because docstring collection is the only thing that
 *   reads `m_tokens`, and `m_tokens` belongs to the *outer* parse. A docstring
 *   lookup with a fragment token would index the wrong stream. Turning
 *   collection off for the duration is simpler and safer than swapping the
 *   stream, which is a unique_ptr over a stack-owned object.
 */
class FragmentGuard {
public:
    FragmentGuard(ast::IExpr *&expr, bool &collect_docstrings) :
            m_expr(expr), m_saved_expr(expr),
            m_collect(collect_docstrings), m_saved_collect(collect_docstrings) {
        m_collect = false;
    }

    ~FragmentGuard() {
        m_expr = m_saved_expr;
        m_collect = m_saved_collect;
    }

private:
    ast::IExpr      *&m_expr;
    ast::IExpr      *m_saved_expr;
    bool            &m_collect;
    bool            m_saved_collect;
};

/**
 * One level of the block stack maintained while walking scanned tokens.
 *
 * `dst` is where elements are appended; `scope` is where template-local
 * declarations are registered. For an if/else-if/else chain the frames are the
 * *clauses*, and `owner_if` is the TemplateIf they all belong to -- which is
 * what lets `else` attach a new clause to the existing node rather than
 * opening a nested one.
 */
struct TemplateFrame {
    std::vector<ast::ITemplateElemUP>   *dst;
    ast::ISymbolScope                   *scope;
    ast::ITemplateIf                    *owner_if;   //< non-null for a clause frame
    int32_t                             line;        //< of the opening directive
    int32_t                             col;
};

struct TemplateBuildState {
    std::vector<TemplateFrame>  stack;

    TemplateFrame &top() { return stack.back(); }
};

// ---------------------------------------------------------------------------
// Small text helpers over directive content
// ---------------------------------------------------------------------------

static bool isIdentChar(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c == '_';
}

/** Offset of the first non-whitespace byte at or after `i`. */
static int32_t skipWs(const std::string &s, int32_t i) {
    while (i < (int32_t)s.size() &&
            (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) {
        i++;
    }
    return i;
}

/** True when `s` has `kw` as a whole word starting at `i`. */
static bool wordAt(const std::string &s, int32_t i, const char *kw) {
    int32_t n = (int32_t)strlen(kw);
    if (s.compare(i, n, kw) != 0) {
        return false;
    }
    return (i+n >= (int32_t)s.size()) || !isIdentChar(s[i+n]);
}

/**
 * True when the directive body looks like `identifier = ...` -- the §4.7.1.2
 * assignment form.
 *
 * `==` is excluded, so a stray comparison is reported as a malformed
 * declaration rather than silently treated as an assignment. `lhs_off` is where
 * the identifier starts and `eq_off` where the `=` is, both needed to keep the
 * sub-parsed halves column-aligned.
 */
static bool looksLikeAssign(
        const std::string   &s,
        int32_t             i,
        int32_t             &lhs_off,
        int32_t             &lhs_len,
        int32_t             &eq_off) {
    lhs_off = i;
    while (i < (int32_t)s.size() && isIdentChar(s[i])) {
        i++;
    }
    lhs_len = i - lhs_off;
    if (!lhs_len) {
        return false;
    }
    i = skipWs(s, i);
    if (i >= (int32_t)s.size() || s[i] != '=') {
        return false;
    }
    if (i+1 < (int32_t)s.size() && s[i+1] == '=') {
        return false;
    }
    eq_off = i;
    return true;
}

/**
 * Replace `[from, to)` with spaces.
 *
 * Used to blank a keyword out of a directive body before sub-parsing it, so
 * that the remaining text keeps its original columns and locations rebase
 * correctly without any per-case arithmetic.
 */
static void blank(std::string &s, int32_t from, int32_t to) {
    for (int32_t i=from; i<to && i<(int32_t)s.size(); i++) {
        s[i] = ' ';
    }
}

// ---------------------------------------------------------------------------
// Location rebasing and diagnostics
// ---------------------------------------------------------------------------

void AstBuilderInt::rebaseLoc(int32_t &line, int32_t &col) const {
    if (!m_frag.active) {
        return;
    }
    // The column offset applies only on the fragment's first line: from line 2
    // on, the fragment's own column already *is* the file column, because the
    // fragment text broke at a real newline.
    if (line == 1) {
        col = m_frag.col + col - 1;
    }
    line = m_frag.line + line - 1;
}

void AstBuilderInt::templateMarker(
        int32_t             code,
        const std::string   &detail,
        int32_t             line,
        int32_t             col,
        int32_t             extent) {
    if (!m_marker_l) {
        return;
    }

    // D3.3: every diagnostic reachable from a `{{` collision names the
    // workaround inline. A C programmer who wrote a legal array initializer
    // and is told only "syntax error in mustache expression" has learned
    // nothing useful.
    static const char *HINT =
        "; if '{{' was intended as literal text, separate the braces ('{ {')";

    std::string msg;
    switch (code) {
        case 108:
            msg = "unterminated mustache expression";
            msg += HINT;
            msg += " -- triple-quoted strings have no escape mechanism";
            break;
        case 109:
            msg = "malformed mustache expression: " + detail;
            msg += HINT;
            break;
        default:
            // PSS110/PSS111 stay terse. A malformed `{% %}` or `{# #}` cannot
            // be produced by ordinary target code the way `{{` can, so the
            // hint would be noise.
            msg = detail;
            break;
    }

    ast::Location loc;
    loc.fileid = m_file_id;
    loc.lineno = line;
    loc.linepos = col;
    loc.extent = extent;

    Marker m(msg, MarkerSeverityE::Error, loc);
    m_marker_l->marker(&m);
}

// ---------------------------------------------------------------------------
// Fragment sub-parse
// ---------------------------------------------------------------------------

ast::IExpr *AstBuilderInt::fragmentExpr(
        const std::string   &text,
        int32_t             line,
        int32_t             col,
        std::string         &err) {
    FragmentParser fp(text);
    PSSParser::ExpressionContext *ctx = fp.parser().expression();

    if (!fp.ok()) {
        err = fp.error();
        if (err.empty()) {
            err = "not an expression";
        }
        return 0;
    }

    FragmentGuard guard(m_expr, m_collectDocStrings);
    FragmentBase saved = m_frag;
    m_frag = {line, col, true};
    ast::IExpr *ret = mkExpr(ctx);
    m_frag = saved;
    return ret;
}

// ---------------------------------------------------------------------------
// Building
// ---------------------------------------------------------------------------

void AstBuilderInt::appendTemplateElem(
        TemplateBuildState  &st,
        ast::ITemplateElem  *elem,
        const TemplateToken &tok) {
    elem->setIs_own_line(tok.is_own_line);
    elem->setLocation({m_file_id, tok.line, tok.col, tok.extent});
    elem->setIndex((int32_t)st.top().dst->size());
    st.top().dst->push_back(ast::ITemplateElemUP(elem));
}

void AstBuilderInt::registerTemplateLocal(
        ast::ISymbolScope                   *scope,
        ast::IProceduralStmtDataDeclaration *decl,
        const TemplateToken                 &tok) {
    const std::string &name = decl->getName()->getId();

    std::unordered_map<std::string,int32_t>::const_iterator it =
        scope->getSymtab().find(name);
    if (it != scope->getSymtab().end()) {
        templateMarker(111,
            "duplicate variable declaration " + name +
                ", previously declared in this template",
            tok.line, tok.col, tok.extent);
        return;
    }

    int32_t idx = (int32_t)scope->getChildren().size();
    decl->setIndex(idx);
    scope->getSymtab().insert({name, idx});
    scope->getChildren().push_back(ast::IScopeChildUP(decl));
}

ast::ITemplateString *AstBuilderInt::mkTemplateString(
        PSSParser::String_literalContext *ctx) {
    if (!ctx || !ctx->TRIPLE_DOUBLE_QUOTED_STRING()) {
        // §4.7.1 admits special elements inside `"""..."""` only, never inside
        // a plain `"..."`.
        return 0;
    }

    antlr4::Token *tok = ctx->TRIPLE_DOUBLE_QUOTED_STRING()->getSymbol();
    std::string text = tok->getText();

    return mkTemplateString(
        text.substr(3, text.size()-6),
        (int32_t)tok->getLine(),
        // charPositionInLine is 0-based and names the first `"`; the content
        // starts three bytes later, and Location columns are 1-based.
        (int32_t)tok->getCharPositionInLine() + 4);
}

ast::ITemplateString *AstBuilderInt::mkTemplateString(
        const std::string   &raw,
        int32_t             base_line,
        int32_t             base_col) {
    DEBUG_ENTER("mkTemplateString");

    TemplateScanner scanner;
    scanner.scan(raw, base_line, base_col);

    for (std::vector<TemplateScanError>::const_iterator
        it=scanner.errors().begin(); it!=scanner.errors().end(); it++) {
        templateMarker(it->code, it->detail, it->line, it->col, it->extent);
    }

    if (!scanner.hasSpecials()) {
        // The common case: an ordinary triple-quoted string. It stays a plain
        // ExprString, which keeps "has specials" a type test rather than a
        // list-length test.
        DEBUG_LEAVE("mkTemplateString (no specials)");
        return 0;
    }

    ast::ITemplateString *tmpl = m_factory->mkTemplateString("<template>", raw);
    tmpl->setLocation({m_file_id, base_line, base_col, (int32_t)raw.size()});

    TemplateBuildState st;
    st.stack.push_back({&tmpl->getElems(), tmpl, 0, base_line, base_col});

    for (std::vector<TemplateToken>::const_iterator
        it=scanner.tokens().begin(); it!=scanner.tokens().end(); it++) {
        const TemplateToken &tok = *it;

        switch (tok.kind) {
            case TemplateTokenKind::Text: {
                appendTemplateElem(st, m_factory->mkTemplateText(
                    "<template-text>", tok.offset, tok.extent,
                    raw.substr(tok.inner_off, tok.inner_ext)), tok);
            } break;

            case TemplateTokenKind::Mustache: {
                std::string err;
                ast::IExpr *e = fragmentExpr(
                    raw.substr(tok.inner_off, tok.inner_ext),
                    tok.inner_line, tok.inner_col, err);
                if (!e) {
                    templateMarker(109, err, tok.line, tok.col, tok.extent);
                    break;
                }
                appendTemplateElem(st, m_factory->mkTemplateExpr(
                    "<template-expr>", tok.offset, tok.extent, e), tok);
            } break;

            case TemplateTokenKind::BlockComment:
            case TemplateTokenKind::LineComment: {
                // Retained, not discarded. Evaluation drops comments
                // (§4.7.1.3); parsing must not, or a formatter loses them.
                ast::ITemplateComment *c = m_factory->mkTemplateComment(
                    "<template-comment>", tok.offset, tok.extent,
                    raw.substr(tok.inner_off, tok.inner_ext));
                c->setIs_line(tok.kind == TemplateTokenKind::LineComment);
                appendTemplateElem(st, c, tok);
            } break;

            case TemplateTokenKind::Directive: {
                buildTemplateDirective(raw, tok, st);
            } break;
        }
    }

    // Anything still open at the end of the string never got its `{%%}`.
    while (st.stack.size() > 1) {
        TemplateFrame f = st.top();
        templateMarker(110, "unclosed template block at end of string",
            f.line, f.col, 0);
        st.stack.pop_back();
    }

    DEBUG_LEAVE("mkTemplateString (%d elems)", tmpl->getElems().size());
    return tmpl;
}

void AstBuilderInt::buildTemplateDirective(
        const std::string   &raw,
        const TemplateToken &tok,
        TemplateBuildState  &st) {
    std::string inner = raw.substr(tok.inner_off, tok.inner_ext);
    int32_t i = skipWs(inner, 0);

    // Every sub-parse below preserves column alignment with `inner`: keywords
    // that must be stripped are blanked rather than removed, and a synthesized
    // body is appended at the end where it shifts nothing.
    FragmentBase frag = {tok.inner_line, tok.inner_col, true};

    // ---- `{%%}` -- close the innermost block --------------------------------
    if (i >= (int32_t)inner.size()) {
        if (st.stack.size() <= 1) {
            templateMarker(111, "template block close with no open block",
                tok.line, tok.col, tok.extent);
        } else {
            st.stack.pop_back();
        }
        return;
    }

    // ---- `{% else %}` / `{% else if (c) %}` ---------------------------------
    // A new clause on the *same* TemplateIf, not a nested one: the source is a
    // flat directive sequence and making it a tree would be an invention that
    // a formatter then has to undo.
    if (wordAt(inner, i, "else")) {
        if (st.stack.size() <= 1 || !st.top().owner_if) {
            templateMarker(111, "'else' with no preceding 'if'",
                tok.line, tok.col, tok.extent);
            return;
        }
        ast::ITemplateIf *owner = st.top().owner_if;

        ast::IExpr *cond = 0;
        int32_t j = skipWs(inner, i+4);
        if (j < (int32_t)inner.size()) {
            if (!wordAt(inner, j, "if")) {
                templateMarker(110,
                    "malformed template directive: expected 'if' or nothing after 'else'",
                    tok.line, tok.col, tok.extent);
                return;
            }
            std::string frag_text = inner;
            blank(frag_text, i, i+4);           // hide `else`, keep the columns
            frag_text += " {}";                 // procedural_stmt needs a body

            FragmentParser fp(frag_text);
            PSSParser::Procedural_if_else_stmtContext *ctx =
                fp.parser().procedural_if_else_stmt();
            if (!fp.ok()) {
                templateMarker(110,
                    "malformed template directive: " + fp.error(),
                    tok.line, tok.col, tok.extent);
                return;
            }
            FragmentGuard guard(m_expr, m_collectDocStrings);
            FragmentBase saved = m_frag;
            m_frag = frag;
            cond = mkExpr(ctx->expression());
            m_frag = saved;
        }

        st.stack.pop_back();

        ast::ITemplateIfClause *clause = m_factory->mkTemplateIfClause(
            "<template-if-clause>", tok.offset, tok.extent);
        clause->setCond(cond);
        clause->setIs_own_line(tok.is_own_line);
        clause->setLocation({m_file_id, tok.line, tok.col, tok.extent});
        clause->setIndex((int32_t)owner->getClauses().size());
        owner->getClauses().push_back(ast::ITemplateIfClauseUP(clause));
        st.stack.push_back({&clause->getBody(), clause, owner, tok.line, tok.col});
        return;
    }

    // ---- `{% if ( c ) %}` ---------------------------------------------------
    if (wordAt(inner, i, "if")) {
        std::string frag_text = inner + " {}";

        FragmentParser fp(frag_text);
        PSSParser::Procedural_if_else_stmtContext *ctx =
            fp.parser().procedural_if_else_stmt();
        if (!fp.ok()) {
            templateMarker(110, "malformed template directive: " + fp.error(),
                tok.line, tok.col, tok.extent);
            return;
        }

        ast::IExpr *cond = 0;
        {
            FragmentGuard guard(m_expr, m_collectDocStrings);
            FragmentBase saved = m_frag;
            m_frag = frag;
            cond = mkExpr(ctx->expression());
            m_frag = saved;
        }

        ast::ITemplateIf *node = m_factory->mkTemplateIf(
            "<template-if>", tok.offset, tok.extent);
        // Append to the enclosing frame *before* pushing the clause frame.
        appendTemplateElem(st, node, tok);

        ast::ITemplateIfClause *clause = m_factory->mkTemplateIfClause(
            "<template-if-clause>", tok.offset, tok.extent);
        clause->setCond(cond);
        clause->setIs_own_line(tok.is_own_line);
        clause->setLocation({m_file_id, tok.line, tok.col, tok.extent});
        clause->setIndex(0);
        node->getClauses().push_back(ast::ITemplateIfClauseUP(clause));
        st.stack.push_back({&clause->getBody(), clause, node, tok.line, tok.col});
        return;
    }

    // ---- `{% foreach ( [it :] expr [ [idx] ] ) %}` ---------------------------
    if (wordAt(inner, i, "foreach")) {
        std::string frag_text = inner + " {}";

        FragmentParser fp(frag_text);
        PSSParser::Procedural_foreach_stmtContext *ctx =
            fp.parser().procedural_foreach_stmt();
        if (!fp.ok()) {
            templateMarker(110, "malformed template directive: " + fp.error(),
                tok.line, tok.col, tok.extent);
            return;
        }

        ast::ITemplateForeach *node = 0;
        {
            FragmentGuard guard(m_expr, m_collectDocStrings);
            FragmentBase saved = m_frag;
            m_frag = frag;

            node = m_factory->mkTemplateForeach(
                "<template-foreach>", tok.offset, tok.extent,
                mkExpr(ctx->expression()));
            if (ctx->iterator_identifier()) {
                node->setIt(mkId(ctx->iterator_identifier()->identifier()));
            }
            if (ctx->index_identifier()) {
                node->setIdx(mkId(ctx->index_identifier()->identifier()));
            }
            m_frag = saved;
        }

        appendTemplateElem(st, node, tok);

        // §4.7.1.2: the iterator and index are "added to the scope until the
        // block closing directive". Synthesizing a ProceduralStmtDataDeclaration
        // per variable is what visitProcedural_foreach_stmt does, and it means
        // `{% int x; %}` and a procedural `int x;` resolve through one path.
        if (node->getIt()) {
            ast::IExprId *id = m_factory->mkExprId(
                node->getIt()->getId(), node->getIt()->getIs_escaped());
            id->setLocation(node->getIt()->getLocation());
            registerTemplateLocal(node,
                m_factory->mkProceduralStmtDataDeclaration(id, 0, 0), tok);
        }
        if (node->getIdx()) {
            ast::IExprId *id = m_factory->mkExprId(
                node->getIdx()->getId(), node->getIdx()->getIs_escaped());
            id->setLocation(node->getIdx()->getLocation());
            registerTemplateLocal(node,
                m_factory->mkProceduralStmtDataDeclaration(id, 0, 0), tok);
        }

        st.stack.push_back({&node->getBody(), node, 0, tok.line, tok.col});
        return;
    }

    // ---- `{% repeat ( [idx :] expr ) %}` ------------------------------------
    if (wordAt(inner, i, "repeat")) {
        std::string frag_text = inner + " {}";

        FragmentParser fp(frag_text);
        PSSParser::Procedural_repeat_stmtContext *ctx =
            fp.parser().procedural_repeat_stmt();
        if (!fp.ok()) {
            templateMarker(110, "malformed template directive: " + fp.error(),
                tok.line, tok.col, tok.extent);
            return;
        }

        ast::ITemplateRepeat *node = 0;
        {
            FragmentGuard guard(m_expr, m_collectDocStrings);
            FragmentBase saved = m_frag;
            m_frag = frag;

            node = m_factory->mkTemplateRepeat(
                "<template-repeat>", tok.offset, tok.extent,
                mkExpr(ctx->expression()));
            if (ctx->identifier()) {
                node->setIdx(mkId(ctx->identifier()));
            }
            m_frag = saved;
        }

        appendTemplateElem(st, node, tok);

        if (node->getIdx()) {
            ast::IExprId *id = m_factory->mkExprId(
                node->getIdx()->getId(), node->getIdx()->getIs_escaped());
            id->setLocation(node->getIdx()->getLocation());
            registerTemplateLocal(node,
                m_factory->mkProceduralStmtDataDeclaration(id, 0, 0), tok);
        }

        st.stack.push_back({&node->getBody(), node, 0, tok.line, tok.col});
        return;
    }

    // ---- `{% identifier = expression ; %}` ----------------------------------
    int32_t lhs_off = 0, lhs_len = 0, eq_off = 0;
    if (looksLikeAssign(inner, i, lhs_off, lhs_len, eq_off)) {
        std::string rhs = inner.substr(eq_off+1);
        // Drop the trailing `;` -- keep it as whitespace so columns hold.
        int32_t semi = (int32_t)rhs.find_last_not_of(" \t\r\n");
        if (semi < 0 || rhs[semi] != ';') {
            templateMarker(110,
                "malformed template directive: expected ';' after assignment",
                tok.line, tok.col, tok.extent);
            return;
        }
        rhs[semi] = ' ';

        // The RHS sub-parse starts eq_off+1 bytes into `inner`, all on the
        // directive's first line unless the directive itself wrapped.
        std::string err;
        ast::IExpr *rhs_e = fragmentExpr(rhs,
            tok.inner_line, tok.inner_col + eq_off + 1, err);
        if (!rhs_e) {
            templateMarker(110, "malformed template directive: " + err,
                tok.line, tok.col, tok.extent);
            return;
        }

        ast::IExprId *lhs = m_factory->mkExprId(
            inner.substr(lhs_off, lhs_len), false);
        lhs->setLocation({m_file_id, tok.inner_line, tok.inner_col + lhs_off, lhs_len});

        appendTemplateElem(st, m_factory->mkTemplateAssign(
            "<template-assign>", tok.offset, tok.extent, lhs, rhs_e), tok);
        return;
    }

    // ---- `{% data_type name [= expr] {, ...} ; %}` --------------------------
    {
        std::string frag_text = inner;
        int32_t semi = (int32_t)frag_text.find_last_not_of(" \t\r\n");
        if (semi < 0 || frag_text[semi] != ';') {
            templateMarker(110,
                "malformed template directive: expected ';' after declaration",
                tok.line, tok.col, tok.extent);
            return;
        }
        frag_text[semi] = ' ';      // the rule does not include the `;`

        FragmentParser fp(frag_text);
        PSSParser::Procedural_data_declarationContext *ctx =
            fp.parser().procedural_data_declaration();
        if (!fp.ok()) {
            templateMarker(110, "malformed template directive: " + fp.error(),
                tok.line, tok.col, tok.extent);
            return;
        }

        ast::ITemplateVarDecl *node = m_factory->mkTemplateVarDecl(
            "<template-var-decl>", tok.offset, tok.extent);

        {
            FragmentGuard guard(m_expr, m_collectDocStrings);
            FragmentBase saved = m_frag;
            m_frag = frag;

            std::vector<PSSParser::Procedural_data_instantiationContext *> items =
                ctx->procedural_data_instantiation();
            for (std::vector<PSSParser::Procedural_data_instantiationContext *>::const_iterator
                it=items.begin(); it!=items.end(); it++) {
                ast::IDataType *type = mkDataType(ctx->data_type());
                ast::IExprId *name = mkId((*it)->identifier());
                ast::IExpr *init = ((*it)->expression())
                    ? mkExpr((*it)->expression()) : 0;
                type = applyArrayDims(type, (*it)->array_dim());

                ast::IProceduralStmtDataDeclaration *decl =
                    m_factory->mkProceduralStmtDataDeclaration(name, type, init);
                decl->setLocation(name->getLocation());
                node->getDecls().push_back(
                    ast::IProceduralStmtDataDeclarationUP(decl, false));

                // Declared into the *enclosing* scope, which is what makes the
                // variable visible to later elements of the same block and
                // invisible after its `{%%}`.
                registerTemplateLocal(st.top().scope, decl, tok);
            }
            m_frag = saved;
        }

        appendTemplateElem(st, node, tok);
    }
}

}
