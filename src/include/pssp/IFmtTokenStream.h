/**
 * IFmtTokenStream.h
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
#pragma once
#include <cstdint>
#include <memory>
#include <string>

namespace pssp {

/**
 * The channels a token can arrive on.
 *
 * These are the values in PSSLexer.g4, restated here so a consumer never has
 * to hardcode a bare integer.  A source-formatting tool cares about all of
 * them: whitespace and comments are not noise to it, they are the payload.
 */
enum FmtTokenChannelE {
    /** Everything the parser sees. */
    FmtTokenChannel_Default    = 0,
    /** ``WS``: runs of space, tab, CR and LF. */
    FmtTokenChannel_WS         = 10,
    /** ``SL_COMMENT``: ``//`` through end of line, newline included. */
    FmtTokenChannel_SlComment  = 11,
    /** ``ML_COMMENT``: ``/`` ``*`` through ``*`` ``/``, non-nesting. */
    FmtTokenChannel_MlComment  = 12,
    /**
     * Synthetic.  Carries text the lexer could not tokenize -- see
     * :cpp:member:`IFmtTokenStream::TYPE_ERROR_CHAR`.  No lexer rule produces
     * this channel; the token stream manufactures it.
     */
    FmtTokenChannel_Error      = 13,
    /**
     * Synthetic.  Carries a leading byte-order mark -- see
     * :cpp:member:`IFmtTokenStream::TYPE_BOM`.
     */
    FmtTokenChannel_Bom        = 14
};

/**
 * One token, as a value.
 *
 * This is a struct rather than an interface on purpose.  Tokens are bulk data
 * -- a large source file produces tens of thousands of them -- and a virtual
 * accessor per field would cost more than the data.
 *
 * Offsets and columns count **code points**, not bytes, because that is what
 * ANTLR's input stream counts and it is also what a Python ``str`` counts.  A
 * consumer that reads the file into a Python string can index it directly with
 * :cpp:member:`start` and :cpp:member:`stop`.
 */
struct FmtToken {
    /** Position in the stream, 0-based.  Contiguous, including trivia. */
    int32_t     index;

    /** Lexer token type.  See :cpp:func:`IFmtTokenStream::getTypeName`. */
    int32_t     type;

    /** One of :cpp:enum:`FmtTokenChannelE`. */
    int32_t     channel;

    /** First code point of the token, 0-based, **inclusive**. */
    int32_t     start;

    /** Last code point of the token, 0-based, **inclusive**. */
    int32_t     stop;

    /** Line of :cpp:member:`start`, 1-based. */
    int32_t     line;

    /** Column of :cpp:member:`start`, 0-based. */
    int32_t     col;

    /** The token's source text, UTF-8, exactly as written. */
    std::string text;
};

class IFmtTokenStream;
using IFmtTokenStreamUP=std::unique_ptr<IFmtTokenStream>;

/**
 * A complete, lossless token stream: every character of the input appears in
 * exactly one token, in order.
 *
 * The contract this exists to provide is:
 *
 * .. code-block:: text
 *
 *     concat(at(i).text for i in 0..size()) == the input, byte for byte
 *
 * and it holds for **any** input, including input that does not lex.  That
 * unconditional form is the point.  A formatter's safety argument rests on
 * being able to reproduce its input exactly, and a guarantee with an "unless
 * the file has a syntax error" clause is not one a formatter can rest on --
 * malformed files are precisely when a user most wants the tool to leave their
 * source alone rather than mangle it.
 *
 * Characters no lexer rule matches are therefore not dropped.  They are
 * gathered into synthetic tokens of type :cpp:member:`TYPE_ERROR_CHAR` on
 * :cpp:enumerator:`FmtTokenChannel_Error`, so a consumer can both round-trip
 * them and notice them.
 *
 * The stream lexes without parsing.  No AST is built, no ``compile if`` is
 * evaluated, and nothing is discarded for being on the losing branch of one.
 */
class IFmtTokenStream {
public:

    /**
     * Type of a synthetic token covering text no lexer rule matched.
     *
     * Negative so it can never collide with a generated token type.  ANTLR
     * already uses -1 for EOF, which this stream does not emit at all: an EOF
     * token has no source text, so it would be the one token that breaks the
     * "concatenate to get the input back" rule.
     */
    static constexpr int32_t TYPE_ERROR_CHAR = -2;

    /**
     * Type of a synthetic token holding a leading UTF-8 byte-order mark.
     *
     * The BOM gets its own token because ANTLR's input stream removes it
     * before the lexer ever sees it.  Left at that, a BOM'd file would come
     * back three bytes shorter -- a silent modification, and exactly the class
     * of thing this interface exists to make impossible.  It is not whitespace
     * and not an error, so it is neither: a consumer emits it back, first,
     * unchanged, and otherwise ignores it.
     *
     * At most one appears, always at index 0.
     */
    static constexpr int32_t TYPE_BOM = -3;

    virtual ~IFmtTokenStream() { }

    /** Number of tokens, trivia and error tokens included. */
    virtual uint32_t size() const = 0;

    /**
     * The token at *idx*.  The reference is valid for the lifetime of the
     * stream.  Behavior is undefined if *idx* is out of range; check
     * :cpp:func:`size` first.
     */
    virtual const FmtToken &at(uint32_t idx) const = 0;

    /**
     * Symbolic name of a token type -- ``"TOK_SEMICOLON"``, ``"ID"``,
     * ``"SL_COMMENT"``.  Returns ``"ERROR_CHAR"`` for
     * :cpp:member:`TYPE_ERROR_CHAR` and an empty string for a type this
     * grammar does not define.
     *
     * Present because a test that asserts on ``42`` is a test nobody can read,
     * and because the numbers move every time a rule is added to the grammar.
     */
    virtual const std::string &getTypeName(int32_t type) const = 0;

    /**
     * Number of :cpp:member:`TYPE_ERROR_CHAR` tokens in the stream.
     *
     * Zero means every character was matched by a lexer rule.  It says nothing
     * about whether the result *parses*.
     */
    virtual uint32_t getNumErrors() const = 0;

    /**
     * False when the input was not valid UTF-8.
     *
     * PSS source is UTF-8; a file that is not is a file this stream cannot
     * describe, because offsets and columns are defined in code points and the
     * input has none.  Rather than substitute replacement characters -- which
     * would corrupt the text while appearing to succeed -- the stream degrades
     * to a single :cpp:member:`TYPE_ERROR_CHAR` token holding the whole input
     * verbatim.  Concatenation still returns the bytes exactly; nothing else
     * is claimed.
     *
     * ``start``/``stop`` count **bytes** in that degenerate case, since code
     * points are not defined for the input.
     *
     * The right response for a formatter is to leave the file alone and say
     * why.  That is a better outcome than a mangled file and a clean exit.
     */
    virtual bool isValidUtf8() const = 0;

};

}
