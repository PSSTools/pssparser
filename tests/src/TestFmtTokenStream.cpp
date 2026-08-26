/*
 * TestFmtTokenStream.cpp
 *
 * The lossless-tokenization guarantee, tested at the lowest layer that can
 * state it.
 *
 * Everything above this -- a formatter, a highlighter, a comment extractor --
 * rests on being able to put the input back together from the tokens.  Proving
 * it here means a later failure is a failure of the thing above, not of the
 * foundation, and that is worth more than the tests themselves.
 */

#include <sstream>
#include <string>
#include <vector>

#include "gtest/gtest.h"

#include "pssp/IFmtTokenStream.h"
#include "FmtTokenStream.h"

using namespace pssp;

namespace {

/** Lexes *src* and returns the stream.  Never throws, whatever *src* is. */
static IFmtTokenStreamUP lex(const std::string &src) {
    std::istringstream in(src);
    return IFmtTokenStreamUP(new FmtTokenStream(&in));
}

/** The input as reassembled from the tokens. */
static std::string concat(IFmtTokenStream *s) {
    std::string ret;
    for (uint32_t i=0; i<s->size(); i++) {
        ret += s->at(i).text;
    }
    return ret;
}

/**
 * The single assertion this file exists for.  Every other test in it is a
 * different way of provoking a violation.
 */
static void assertRoundTrips(const std::string &src) {
    IFmtTokenStreamUP s = lex(src);
    ASSERT_EQ(src, concat(s.get()));

    // Indices must agree with the text, or a consumer that slices the source
    // by offset gets something other than what `text` says is there.
    for (uint32_t i=0; i<s->size(); i++) {
        const FmtToken &t = s->at(i);
        ASSERT_EQ(static_cast<int32_t>(i), t.index) << "at " << i;
        ASSERT_LE(t.start, t.stop+1) << "at " << i;
    }

    // ... and they must tile the input with no gap and no overlap.
    int32_t expect = 0;
    for (uint32_t i=0; i<s->size(); i++) {
        const FmtToken &t = s->at(i);
        ASSERT_EQ(expect, t.start) << "gap or overlap before token " << i;
        expect = t.stop+1;
    }
}

// -------------------------------------------------------------------------
// The guarantee, over inputs that lex
// -------------------------------------------------------------------------

TEST(FmtTokenStream, EmptyInput) {
    IFmtTokenStreamUP s = lex("");
    ASSERT_EQ(0u, s->size());
    ASSERT_EQ(0u, s->getNumErrors());
}

TEST(FmtTokenStream, RoundTripsASimpleComponent) {
    assertRoundTrips(
        "component pss_top {\n"
        "    action A { rand int x; }\n"
        "}\n");
}

TEST(FmtTokenStream, RoundTripsWithoutFinalNewline) {
    assertRoundTrips("component c { }");
}

TEST(FmtTokenStream, RoundTripsCRLF) {
    assertRoundTrips("component c {\r\n    int x;\r\n}\r\n");
}

TEST(FmtTokenStream, RoundTripsLoneCR) {
    // Old-Mac line endings.  Nobody writes them on purpose; a file that has
    // been through the wrong tool has them, and the formatter must survive it.
    assertRoundTrips("component c {\r    int x;\r}\r");
}

TEST(FmtTokenStream, RoundTripsTabsAndTrailingSpace) {
    assertRoundTrips("component c {   \n\tint x;\t\n}\n");
}

TEST(FmtTokenStream, RoundTripsComments) {
    assertRoundTrips(
        "// leading\n"
        "component c { /* inline */ int x; // trailing\n"
        "}\n");
}

TEST(FmtTokenStream, RoundTripsUnicodeInComments) {
    assertRoundTrips("// \xE2\x86\x92 \xE6\xBC\xA2\xE5\xAD\x97\ncomponent c { }\n");
}

TEST(FmtTokenStream, RoundTripsStrings) {
    assertRoundTrips("component c { string s = \"a\\\"b\"; }\n");
}

TEST(FmtTokenStream, RoundTripsTripleQuotedString) {
    assertRoundTrips(
        "component c {\n"
        "  exec body C = \"\"\"\n"
        "     do_something();\n"
        "  \"\"\";\n"
        "}\n");
}

// -------------------------------------------------------------------------
// The guarantee, over inputs that do not lex
// -------------------------------------------------------------------------
//
// This is the half that matters.  A guarantee that holds only for valid input
// is not one a formatter can rely on: malformed files are exactly when a user
// most wants the tool to leave their source alone rather than mangle it.

TEST(FmtTokenStream, RoundTripsUnterminatedBlockComment) {
    assertRoundTrips("component c { /* never closed\nint x;\n");
}

TEST(FmtTokenStream, RoundTripsUnterminatedString) {
    assertRoundTrips("component c { string s = \"unterminated\n}\n");
}

TEST(FmtTokenStream, RoundTripsStrayCharacters) {
    assertRoundTrips("component c { $ ` \xC2\xA7 int x; }\n");
}

TEST(FmtTokenStream, RoundTripsByteOrderMark) {
    // Split so the `c` is not swallowed by the \xBF hex escape -- C++ hex
    // escapes are greedy and "\xBFc" is one (out-of-range) character.
    assertRoundTrips("\xEF\xBB\xBF" "component c { }\n");
}

TEST(FmtTokenStream, RoundTripsInvalidUtf8) {
    // A lone continuation byte is not valid UTF-8.  Files like this exist --
    // a latin-1 comment saved by an editor that did not ask.  The stream must
    // hand the bytes back rather than throw.
    assertRoundTrips("// caf\xE9\ncomponent c { }\n");
}

TEST(FmtTokenStream, RoundTripsTruncatedUtf8Sequence) {
    assertRoundTrips("component c { } \xE6\xBC");
}

TEST(FmtTokenStream, ByteOrderMarkIsItsOwnToken) {
    IFmtTokenStreamUP s = lex("\xEF\xBB\xBF" "component c { }\n");

    ASSERT_EQ(IFmtTokenStream::TYPE_BOM, s->at(0).type);
    ASSERT_EQ(FmtTokenChannel_Bom, s->at(0).channel);
    ASSERT_EQ("BOM", s->getTypeName(s->at(0).type));
    ASSERT_EQ("\xEF\xBB\xBF", s->at(0).text);

    // A BOM is not an error and must not be counted as one, or every BOM'd
    // file would look damaged.
    ASSERT_EQ(0u, s->getNumErrors());
    ASSERT_TRUE(s->isValidUtf8());

    // One code point, so everything after it shifts by exactly one -- offsets
    // everywhere, and columns on the first line.
    ASSERT_EQ("component", s->at(1).text);
    ASSERT_EQ(1, s->at(1).start);
    ASSERT_EQ(1, s->at(1).line);
    ASSERT_EQ(1, s->at(1).col);
}

TEST(FmtTokenStream, InvalidUtf8IsReportedRatherThanThrown) {
    IFmtTokenStreamUP s = lex("// caf\xE9\ncomponent c { }\n");

    ASSERT_FALSE(s->isValidUtf8());
    ASSERT_EQ(1u, s->size());
    ASSERT_EQ(IFmtTokenStream::TYPE_ERROR_CHAR, s->at(0).type);
    ASSERT_EQ(1u, s->getNumErrors());
}

TEST(FmtTokenStream, ValidInputIsReportedAsValidUtf8) {
    IFmtTokenStreamUP s = lex("component c { } // \xE6\xBC\xA2\n");
    ASSERT_TRUE(s->isValidUtf8());
}

TEST(FmtTokenStream, RoundTripsGarbage) {
    assertRoundTrips("\x01\x02\x03 }}}} ][ '''' \"\"\"\" ####\n");
}

TEST(FmtTokenStream, UnlexableTextBecomesAnErrorToken) {
    IFmtTokenStreamUP s = lex("int $ x;");
    ASSERT_EQ(1u, s->getNumErrors());

    bool found = false;
    for (uint32_t i=0; i<s->size(); i++) {
        if (s->at(i).type == IFmtTokenStream::TYPE_ERROR_CHAR) {
            ASSERT_EQ("$", s->at(i).text);
            ASSERT_EQ(FmtTokenChannel_Error, s->at(i).channel);
            ASSERT_EQ("ERROR_CHAR", s->getTypeName(s->at(i).type));
            found = true;
        }
    }
    ASSERT_TRUE(found);
}

TEST(FmtTokenStream, AdjacentUnlexableCharactersCoalesce) {
    // One run of unmatched text is one token, not one per character: a
    // consumer counting "how broken is this file" wants runs, and a consumer
    // reassembling the text does not care either way.
    IFmtTokenStreamUP s = lex("int $$$$ x;");
    ASSERT_EQ(1u, s->getNumErrors());
    ASSERT_EQ(std::string("int $$$$ x;"), concat(s.get()));
}

TEST(FmtTokenStream, ValidInputReportsNoErrors) {
    IFmtTokenStreamUP s = lex("component c { int x; } // done\n");
    ASSERT_EQ(0u, s->getNumErrors());
}

// -------------------------------------------------------------------------
// Channels, types and positions
// -------------------------------------------------------------------------

TEST(FmtTokenStream, TriviaArrivesOnItsOwnChannels) {
    IFmtTokenStreamUP s = lex("int /* m */ x; // s\n");

    bool ws = false, sl = false, ml = false, def = false;
    for (uint32_t i=0; i<s->size(); i++) {
        switch (s->at(i).channel) {
            case FmtTokenChannel_Default: def = true; break;
            case FmtTokenChannel_WS: ws = true; break;
            case FmtTokenChannel_SlComment: sl = true; break;
            case FmtTokenChannel_MlComment: ml = true; break;
            default: FAIL() << "unexpected channel " << s->at(i).channel;
        }
    }
    ASSERT_TRUE(def);
    ASSERT_TRUE(ws);
    ASSERT_TRUE(sl);
    ASSERT_TRUE(ml);
}

TEST(FmtTokenStream, SingleLineCommentIncludesItsNewline) {
    // Consequential for a formatter: the newline belongs to the comment token,
    // not to a following whitespace token, so blank-line counting after a
    // trailing comment is off by one unless you know this.
    IFmtTokenStreamUP s = lex("// c\nint x;");
    ASSERT_EQ("SL_COMMENT", s->getTypeName(s->at(0).type));
    ASSERT_EQ("// c\n", s->at(0).text);
}

TEST(FmtTokenStream, TypeNamesAreSymbolic) {
    IFmtTokenStreamUP s = lex("component");
    ASSERT_EQ("TOK_COMPONENT", s->getTypeName(s->at(0).type));
    ASSERT_EQ("", s->getTypeName(999999));
}

TEST(FmtTokenStream, LinesAndColumnsFollowTheSource) {
    IFmtTokenStreamUP s = lex("int x;\n  int y;\n");

    // The second `int`: line 2, column 2.
    bool checked = false;
    for (uint32_t i=0; i<s->size(); i++) {
        const FmtToken &t = s->at(i);
        if (t.text == "int" && t.line == 2) {
            ASSERT_EQ(2, t.col);
            checked = true;
        }
    }
    ASSERT_TRUE(checked);
}

TEST(FmtTokenStream, PositionsSurviveAnErrorToken) {
    // The cursor used for synthetic tokens is re-seeded from ANTLR at every
    // real token, so one error cannot drift every position after it.
    IFmtTokenStreamUP s = lex("$\nint x;\n");

    bool checked = false;
    for (uint32_t i=0; i<s->size(); i++) {
        const FmtToken &t = s->at(i);
        if (t.text == "int") {
            ASSERT_EQ(2, t.line);
            ASSERT_EQ(0, t.col);
            checked = true;
        }
    }
    ASSERT_TRUE(checked);
}

TEST(FmtTokenStream, ColumnsCountCodePointsNotBytes) {
    // "// \xE6\xBC\xA2\n" is 4 code points and 6 bytes; `int` starts at
    // column 0 of the next line either way, so the discriminating case is a
    // multi-byte character *before* a token on the same line.
    IFmtTokenStreamUP s = lex("/* \xE6\xBC\xA2 */ int x;");

    bool checked = false;
    for (uint32_t i=0; i<s->size(); i++) {
        if (s->at(i).text == "int") {
            // "/* X */" is 7 code points, then one space.
            ASSERT_EQ(8, s->at(i).col);
            checked = true;
        }
    }
    ASSERT_TRUE(checked);
}

// -------------------------------------------------------------------------
// No parsing happened
// -------------------------------------------------------------------------

TEST(FmtTokenStream, BothCompileIfBranchesAreTokenized) {
    // The reason a formatter tokenizes rather than reading the AST: AST
    // construction evaluates `compile if` and drops the losing branch.  Here
    // both branches must be present, because nothing was evaluated.
    IFmtTokenStreamUP s = lex(
        "compile if (false) {\n"
        "  component taken { }\n"
        "} else {\n"
        "  component not_taken { }\n"
        "}\n");

    bool taken = false, not_taken = false;
    for (uint32_t i=0; i<s->size(); i++) {
        if (s->at(i).text == "taken") { taken = true; }
        if (s->at(i).text == "not_taken") { not_taken = true; }
    }
    ASSERT_TRUE(taken);
    ASSERT_TRUE(not_taken);
}

}
