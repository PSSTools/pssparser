/*
 * FmtTokenStream.cpp
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
#include "FmtTokenStream.h"

#include "antlr4-runtime.h"
#include "support/Utf8.h"
#include "PSSLexer.h"

namespace pssp {

using namespace antlr4;

FmtTokenStream::FmtTokenStream(std::istream *in) :
    m_num_errors(0), m_valid_utf8(true), m_line(1), m_col(0), m_col_bias(0) {
    loadTypeNames();

    // Read the input ourselves rather than handing the stream to ANTLR.  Two
    // things ANTLRInputStream does are unacceptable for a lossless stream, and
    // both are invisible from the far side of it:
    //
    //   - it strips a leading UTF-8 BOM, so a BOM'd file comes back three
    //     bytes shorter;
    //   - it throws IllegalArgumentException on input that is not valid UTF-8,
    //     so a mis-encoded file becomes an exception in the caller rather than
    //     a diagnosable result.
    //
    // Owning the bytes here is what lets both be handled as data.
    std::string src(
        (std::istreambuf_iterator<char>(*in)),
        std::istreambuf_iterator<char>());

    size_t bom_len = 0;
    if (src.size() >= 3 &&
            static_cast<unsigned char>(src[0]) == 0xEF &&
            static_cast<unsigned char>(src[1]) == 0xBB &&
            static_cast<unsigned char>(src[2]) == 0xBF) {
        bom_len = 3;
    }

    std::string body = src.substr(bom_len);

    if (!antlrcpp::Utf8::strictDecode(body).has_value()) {
        // Not UTF-8.  Offsets and columns are defined in code points and this
        // input has none, so the honest answer is one token holding the file:
        // the bytes come back exactly and nothing further is claimed.
        m_valid_utf8 = false;
        FmtToken err;
        err.type = IFmtTokenStream::TYPE_ERROR_CHAR;
        err.channel = FmtTokenChannel_Error;
        err.start = 0;
        err.stop = static_cast<int32_t>(src.size())-1;
        err.line = 1;
        err.col = 0;
        err.text = src;
        if (!src.empty()) {
            push(err);
            m_num_errors++;
        }
        return;
    }

    int32_t base = 0;
    if (bom_len) {
        FmtToken bom;
        bom.type = IFmtTokenStream::TYPE_BOM;
        bom.channel = FmtTokenChannel_Bom;
        bom.start = 0;
        bom.stop = 0;
        bom.line = 1;
        bom.col = 0;
        bom.text = src.substr(0, bom_len);
        push(bom);
        // One code point consumed, so everything the lexer reports is shifted
        // by one -- offsets everywhere, and columns on the first line only.
        base = 1;
        m_col_bias = 1;
    }

    lex(body, base);
}

void FmtTokenStream::loadTypeNames() {
    // The vocabulary is static per grammar, but reaching it needs an instance.
    // An empty input costs nothing and keeps this independent of whether the
    // real lex happens at all -- the invalid-UTF-8 path returns before it.
    ANTLRInputStream empty("");
    PSSLexer lexer(&empty);

    const dfa::Vocabulary &vocab = lexer.getVocabulary();
    for (size_t t=0; t<=vocab.getMaxTokenType(); t++) {
        std::string_view name = vocab.getSymbolicName(t);
        if (!name.empty()) {
            m_type_names[static_cast<int32_t>(t)] = std::string(name);
        }
    }
    m_type_names[IFmtTokenStream::TYPE_ERROR_CHAR] = "ERROR_CHAR";
    m_type_names[IFmtTokenStream::TYPE_BOM] = "BOM";
}

void FmtTokenStream::lex(const std::string &body, int32_t base) {
    ANTLRInputStream input(body);
    PSSLexer lexer(&input);

    // The console listener would print to stderr, and this stream's whole
    // point is that unlexable input is data rather than a failure: it becomes
    // an ERROR_CHAR token below.  A library that writes to stderr on behalf of
    // its caller is a library that cannot be embedded.
    lexer.removeErrorListeners();

    CommonTokenStream tokens(&lexer);
    tokens.fill();

    // `expect` is the first code point not yet accounted for.  Every token the
    // lexer produces must start exactly there; when one does not, the lexer
    // recovered from an unmatched character by consuming it silently, and the
    // characters between are recovered here instead of being lost.
    size_t expect = 0;
    size_t total = input.size();

    for (size_t i=0; i<tokens.size(); i++) {
        Token *t = tokens.get(i);

        if (t->getType() == Token::EOF) {
            // Deliberately not emitted: it has no source text, so including it
            // would be the one token that breaks concatenation.
            continue;
        }

        size_t start = t->getStartIndex();
        size_t stop = t->getStopIndex();

        if (start > expect) {
            FmtToken err;
            err.type = IFmtTokenStream::TYPE_ERROR_CHAR;
            err.channel = FmtTokenChannel_Error;
            err.start = base+static_cast<int32_t>(expect);
            err.stop = base+static_cast<int32_t>(start-1);
            err.line = m_line;
            err.col = m_col;
            err.text = input.getText(misc::Interval(expect, start-1));
            push(err);
            m_num_errors++;
        }

        FmtToken tok;
        tok.type = static_cast<int32_t>(t->getType());
        tok.channel = static_cast<int32_t>(t->getChannel());
        tok.start = base+static_cast<int32_t>(start);
        tok.stop = base+static_cast<int32_t>(stop);
        // Take the position from ANTLR rather than the running cursor: it is
        // the authority, and using it resynchronizes after an error token.
        tok.line = static_cast<int32_t>(t->getLine());
        tok.col = static_cast<int32_t>(t->getCharPositionInLine());
        if (tok.line == 1) {
            tok.col += m_col_bias;
        }
        tok.text = t->getText();
        m_line = tok.line;
        m_col = tok.col;
        push(tok);

        expect = stop+1;
    }

    if (expect < total) {
        FmtToken err;
        err.type = IFmtTokenStream::TYPE_ERROR_CHAR;
        err.channel = FmtTokenChannel_Error;
        err.start = base+static_cast<int32_t>(expect);
        err.stop = base+static_cast<int32_t>(total-1);
        err.line = m_line;
        err.col = m_col;
        err.text = input.getText(misc::Interval(expect, total-1));
        push(err);
        m_num_errors++;
    }
}

FmtTokenStream::~FmtTokenStream() { }

const std::string &FmtTokenStream::getTypeName(int32_t type) const {
    std::map<int32_t,std::string>::const_iterator it = m_type_names.find(type);
    return (it != m_type_names.end())?it->second:m_no_such_type;
}

void FmtTokenStream::push(FmtToken &tok) {
    tok.index = static_cast<int32_t>(m_tokens.size());
    m_tokens.push_back(tok);
    advance(tok.text);
}

void FmtTokenStream::advance(const std::string &text) {
    for (std::string::const_iterator it=text.begin(); it!=text.end(); it++) {
        unsigned char c = static_cast<unsigned char>(*it);
        if (c == '\n') {
            m_line++;
            m_col = 0;
        } else if ((c & 0xC0) != 0x80) {
            // Not a UTF-8 continuation byte, so this is one code point.  The
            // column must count what ANTLR counts, and ANTLR counts code
            // points -- see the note on FmtToken.
            m_col++;
        }
    }
}

}
