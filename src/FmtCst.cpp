/*
 * FmtCst.cpp
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
#include "FmtCst.h"

#include <iterator>
#include <sstream>

#include "antlr4-runtime.h"
#include "PSSLexer.h"
#include "PSSParser.h"

namespace pssp {

using namespace antlr4;

namespace {

/**
 * Counts syntax errors and says nothing.
 *
 * The default listener writes to stderr, which a library must not do on its
 * caller's behalf.  What a formatter needs from the parser is one bit -- did
 * this match the grammar -- and it gets that from the count.
 */
class CountingErrorListener : public BaseErrorListener {
public:
    CountingErrorListener() : m_count(0) { }

    virtual void syntaxError(
        Recognizer *, Token *, size_t, size_t,
        const std::string &, std::exception_ptr) override {
        m_count++;
    }

    uint32_t count() const { return m_count; }

private:
    uint32_t m_count;
};

/**
 * Translates ANTLR token indices into IFmtTokenStream indices.
 *
 * The two streams hold the same lexer tokens in the same order, but the
 * formatting stream also carries synthetic tokens -- a leading BOM, and runs
 * of text no lexer rule matched.  Dropping those recovers ANTLR's numbering
 * exactly, so the mapping is a single walk rather than anything clever.
 */
class TokenIndexMap {
public:
    TokenIndexMap(const FmtTokenStream *tokens) : m_last_code(-1) {
        for (uint32_t i=0; i<tokens->size(); i++) {
            int32_t type = tokens->at(i).type;
            if (type != IFmtTokenStream::TYPE_ERROR_CHAR &&
                    type != IFmtTokenStream::TYPE_BOM) {
                m_map.push_back(static_cast<int32_t>(i));
            }
            if (tokens->at(i).channel == FmtTokenChannel_Default) {
                m_last_code = static_cast<int32_t>(i);
            }
        }
    }

    /** -1 for anything out of range, which includes ANTLR's EOF token. */
    int32_t operator()(size_t antlr_idx) const {
        return (antlr_idx < m_map.size())?m_map[antlr_idx]:-1;
    }

    /**
     * The last token the parser could see, or -1 if there was none.
     *
     * `compilation_unit` -- and any rule the parser closes at end of input --
     * stops on EOF, which has no text and no place in the token stream.
     * Reporting -1 for its stop would leave the root spanning nothing while
     * its children span the file, so the span ends at the last real token
     * instead.
     */
    int32_t lastCode() const { return m_last_code; }

private:
    std::vector<int32_t>    m_map;
    int32_t                 m_last_code;
};

/** Copies *tree* into our own nodes.  Recursion depth is the grammar's. */
static FmtCstNode *materialize(
        tree::ParseTree                     *tree,
        const std::vector<std::string>      &rule_names,
        const TokenIndexMap                 &map) {
    static const std::string empty;

    tree::TerminalNode *term = dynamic_cast<tree::TerminalNode *>(tree);
    if (term) {
        Token *sym = term->getSymbol();
        int32_t idx = (sym->getType() == Token::EOF)
            ? -1 : map(sym->getTokenIndex());
        FmtCstNode *node = new FmtCstNode(
            false,
            dynamic_cast<tree::ErrorNode *>(tree) != nullptr,
            -1,
            empty,
            idx);
        node->setSpan(idx, idx);
        return node;
    }

    ParserRuleContext *ctx = dynamic_cast<ParserRuleContext *>(tree);
    if (!ctx) {
        return nullptr;
    }

    size_t rule = ctx->getRuleIndex();
    FmtCstNode *node = new FmtCstNode(
        true,
        false,
        static_cast<int32_t>(rule),
        (rule < rule_names.size())?rule_names[rule]:empty,
        -1);

    // A rule that matched nothing -- an absent optional clause -- still gets a
    // node, and has no span.  getStop() is null in that case, and is also null
    // when the parser bailed mid-rule.
    Token *start = ctx->getStart();
    Token *stop = ctx->getStop();
    node->setSpan(
        (start && start->getType() != Token::EOF)
            ? map(start->getTokenIndex()) : -1,
        (stop == nullptr) ? -1
            : (stop->getType() == Token::EOF) ? map.lastCode()
            : map(stop->getTokenIndex()));

    for (std::vector<tree::ParseTree *>::const_iterator
        it=ctx->children.begin();
        it!=ctx->children.end(); it++) {
        FmtCstNode *child = materialize(*it, rule_names, map);
        if (child) {
            node->addChild(child);
        }
    }

    return node;
}

}

FmtCstNode::FmtCstNode(
    bool                is_rule,
    bool                is_error,
    int32_t             rule_index,
    const std::string   &rule_name,
    int32_t             token_index) :
    m_is_rule(is_rule), m_is_error(is_error), m_rule_index(rule_index),
    m_rule_name(rule_name), m_token_index(token_index),
    m_start_token(-1), m_stop_token(-1) { }

FmtCstNode::~FmtCstNode() { }

FmtCst::FmtCst(std::istream *in) : m_num_syntax_errors(0) {
    std::string src(
        (std::istreambuf_iterator<char>(*in)),
        std::istreambuf_iterator<char>());

    // Lex once for the token stream, which owns the BOM handling, the UTF-8
    // check and the error-token gap filling.  ANTLR is then given the same
    // source and lexes it again for the parser.
    //
    // The second lex is deliberate rather than plumbed around.  Sharing one
    // CommonTokenStream between the two would tangle their lifetimes for a
    // saving that does not show up next to the cost of parsing, and the
    // duplicate is provably harmless: lexing is deterministic, so the two
    // agree token for token, which is what TokenIndexMap relies on.
    std::istringstream tok_in(src);
    m_tokens = std::unique_ptr<FmtTokenStream>(new FmtTokenStream(&tok_in));

    if (!m_tokens->isValidUtf8()) {
        // Nothing to parse: the token stream already says why, and inventing
        // a tree over text we could not decode would be a lie.
        return;
    }

    std::string body = src;
    if (m_tokens->size() && m_tokens->at(0).type == IFmtTokenStream::TYPE_BOM) {
        body = src.substr(m_tokens->at(0).text.size());
    }

    ANTLRInputStream input(body);
    PSSLexer lexer(&input);
    lexer.removeErrorListeners();

    CommonTokenStream tokens(&lexer);
    tokens.fill();

    PSSParser parser(&tokens);
    CountingErrorListener errors;
    parser.removeErrorListeners();
    parser.addErrorListener(&errors);

    PSSParser::Compilation_unitContext *ctx = parser.compilation_unit();

    m_num_syntax_errors = errors.count();

    TokenIndexMap map(m_tokens.get());
    m_root = std::unique_ptr<FmtCstNode>(
        materialize(ctx, parser.getRuleNames(), map));
}

FmtCst::~FmtCst() { }

}
