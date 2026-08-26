/*
 * TestDocCommentExtractor.cpp
 *
 * Unit tests for the doc-comment association and normalization rules
 * (docs/doc_comments.rst).  The extractor is exercised over a real token
 * stream but without the AST builder, so a failure here points at the rules
 * rather than at a visitor.
 */

#include <memory>
#include <string>
#include <vector>

#include "gtest/gtest.h"

#include "antlr4-runtime.h"
#include "PSSLexer.h"

#include "DocCommentExtractor.h"

using namespace antlr4;
using namespace pssp;

namespace {

/**
 * Lexes a source fragment and keeps the stream alive for the duration of a
 * test.  The extractor holds a borrowed pointer, and the tokens themselves are
 * owned by the stream.
 */
class Lexed {
public:
    Lexed(const std::string &src) : m_src(src) {
        m_input = std::unique_ptr<ANTLRInputStream>(new ANTLRInputStream(m_src));
        m_lexer = std::unique_ptr<PSSLexer>(new PSSLexer(m_input.get()));
        m_tokens = std::unique_ptr<CommonTokenStream>(
            new CommonTokenStream(m_lexer.get()));
        m_tokens->fill();
    }

    CommonTokenStream *tokens() { return m_tokens.get(); }

    /** First on-channel token whose text is *text*. */
    Token *find(const std::string &text, int32_t nth=0) {
        int32_t seen = 0;
        for (size_t i=0; i<m_tokens->size(); i++) {
            Token *t = m_tokens->get(i);
            if (t->getChannel() == Token::DEFAULT_CHANNEL &&
                    t->getText() == text) {
                if (seen == nth) {
                    return t;
                }
                seen++;
            }
        }
        return nullptr;
    }

private:
    std::string                         m_src;
    std::unique_ptr<ANTLRInputStream>   m_input;
    std::unique_ptr<PSSLexer>           m_lexer;
    std::unique_ptr<CommonTokenStream>  m_tokens;
};

/** Leading doc text for the *nth* on-channel occurrence of *anchor_text*. */
std::string leading(
        const std::string       &src,
        const std::string       &anchor_text,
        int32_t                 nth=0,
        DocCommentOptions       opts=DocCommentOptions()) {
    Lexed lx(src);
    DocCommentExtractor ex(lx.tokens(), 1, opts);
    Token *anchor = lx.find(anchor_text, nth);
    EXPECT_TRUE(anchor != nullptr) << "no token " << anchor_text;
    if (!anchor) {
        return "<no-anchor>";
    }
    DocComment dc;
    if (!ex.extractLeading(anchor, dc)) {
        return "";
    }
    return dc.text;
}

} /* anonymous namespace */

// ---------------------------------------------------------------------------
// Classification
// ---------------------------------------------------------------------------

TEST(DocCommentForms, classify) {
    EXPECT_EQ(DocCommentExtractor::classify("// x"),    DocCommentForm::Line);
    EXPECT_EQ(DocCommentExtractor::classify("/// x"),   DocCommentForm::DocLine);
    EXPECT_EQ(DocCommentExtractor::classify("//! x"),   DocCommentForm::DocLine);
    EXPECT_EQ(DocCommentExtractor::classify("/* x */"), DocCommentForm::Block);
    EXPECT_EQ(DocCommentExtractor::classify("/** x */"),DocCommentForm::DocBlock);
    EXPECT_EQ(DocCommentExtractor::classify("/*! x */"),DocCommentForm::DocBlock);
    // No room for a body: an empty block comment, not a doc block.
    EXPECT_EQ(DocCommentExtractor::classify("/**/"),    DocCommentForm::Block);
    EXPECT_EQ(DocCommentExtractor::classify("int"),     DocCommentForm::None);
}

// ---------------------------------------------------------------------------
// Association (§3.2)
// ---------------------------------------------------------------------------

TEST(DocCommentAssoc, adjacent_line_comment) {
    EXPECT_EQ(leading("component C {\n// doc\nint f1;\n}\n", "int"), "doc");
}

TEST(DocCommentAssoc, adjacent_block_comment) {
    EXPECT_EQ(leading("component C {\n/** doc */\nint f1;\n}\n", "int"), "doc");
}

// D6: zero whitespace between the comment and the declaration is a valid
// association; the old code returned an empty string here.
TEST(DocCommentAssoc, no_whitespace_before_declaration) {
    EXPECT_EQ(leading("component C {\n/** doc */int f1;\n}\n", "int"), "doc");
}

// D3: a blank line breaks the association, for line comments as well as block
// comments.  The old code enforced this for blocks only.
TEST(DocCommentAssoc, blank_line_rejects_line_comment) {
    EXPECT_EQ(leading("component C {\n// far away\n\nint f1;\n}\n", "int"), "");
}

TEST(DocCommentAssoc, blank_line_rejects_block_comment) {
    EXPECT_EQ(leading("component C {\n/** far away */\n\nint f1;\n}\n", "int"), "");
}

TEST(DocCommentAssoc, consecutive_line_comments_accumulate) {
    EXPECT_EQ(
        leading("component C {\n// one\n// two\nint f1;\n}\n", "int"),
        "one\ntwo");
}

// D4: two line-comment blocks separated by a blank line are not concatenated;
// only the adjacent one documents.
TEST(DocCommentAssoc, separated_line_comment_blocks_do_not_merge) {
    EXPECT_EQ(
        leading("component C {\n// block one\n\n// block two\nint f1;\n}\n", "int"),
        "block two");
}

TEST(DocCommentAssoc, adjacent_block_comments_do_not_merge) {
    EXPECT_EQ(
        leading("component C {\n/** one */\n/** two */\nint f1;\n}\n", "int"),
        "two");
}

TEST(DocCommentAssoc, no_comment_yields_nothing) {
    EXPECT_EQ(leading("component C {\nint f1;\n}\n", "int"), "");
}

TEST(DocCommentAssoc, comment_at_buffer_start) {
    EXPECT_EQ(leading("// doc\ncomponent C {}\n", "component"), "doc");
}

// §3.5.4: a comment on the same line as the preceding construct trails that
// construct and must not lead the next declaration.
TEST(DocCommentAssoc, trailing_comment_does_not_lead_the_next_declaration) {
    EXPECT_EQ(
        leading("component C {\nint a; // bytes\nint b;\n}\n", "int", 1),
        "");
}

TEST(DocCommentAssoc, trailing_comment_is_skipped_but_leading_still_found) {
    EXPECT_EQ(
        leading("component C {\nint a; // bytes\n// doc for b\nint b;\n}\n", "int", 1),
        "doc for b");
}

// ---------------------------------------------------------------------------
// Forms and marker residue (D8)
// ---------------------------------------------------------------------------

TEST(DocCommentForms, no_marker_residue) {
    EXPECT_EQ(leading("component C {\n// doc\nint f1;\n}\n",    "int"), "doc");
    EXPECT_EQ(leading("component C {\n/// doc\nint f1;\n}\n",   "int"), "doc");
    EXPECT_EQ(leading("component C {\n//! doc\nint f1;\n}\n",   "int"), "doc");
    EXPECT_EQ(leading("component C {\n/* doc */\nint f1;\n}\n", "int"), "doc");
    EXPECT_EQ(leading("component C {\n/** doc */\nint f1;\n}\n","int"), "doc");
    EXPECT_EQ(leading("component C {\n/*! doc */\nint f1;\n}\n","int"), "doc");
}

TEST(DocCommentForms, doxygen_trailing_marker_is_stripped) {
    EXPECT_EQ(leading("component C {\n///< doc\nint f1;\n}\n",    "int"), "doc");
    EXPECT_EQ(leading("component C {\n/**< doc */\nint f1;\n}\n", "int"), "doc");
}

// A plain `//` has no `<` form in Doxygen, so the character is content.
TEST(DocCommentForms, plain_line_comment_keeps_a_leading_angle) {
    EXPECT_EQ(leading("component C {\n//<insert>\nint f1;\n}\n", "int"), "<insert>");
}

TEST(DocCommentForms, empty_block_comment_is_empty) {
    EXPECT_EQ(leading("component C {\n/**/\nint f1;\n}\n", "int"), "");
}

// ---------------------------------------------------------------------------
// Normalization (§3.3)
// ---------------------------------------------------------------------------

// D5: the `*` continuation must be stripped at any indentation depth, and the
// body must be dedented.  The old code handled exactly one leading whitespace
// character and never dedented at all, so the result was unusable as RST.
TEST(DocCommentNorm, star_continuation_at_eight_spaces) {
    std::string src =
        "component C {\n"
        "        /**\n"
        "         * Line one.\n"
        "         *\n"
        "         *     indented code\n"
        "         */\n"
        "        int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Line one.\n\n    indented code");
}

TEST(DocCommentNorm, star_continuation_at_zero_indent) {
    std::string src =
        "component C {\n"
        "/**\n"
        "* Line one.\n"
        "* Line two.\n"
        "*/\n"
        "int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Line one.\nLine two.");
}

TEST(DocCommentNorm, block_without_star_continuation_dedents) {
    std::string src =
        "component C {\n"
        "    /**\n"
        "        Line one.\n"
        "\n"
        "            indented code\n"
        "     */\n"
        "    int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Line one.\n\n    indented code");
}

TEST(DocCommentNorm, first_line_content_after_opening_marker) {
    std::string src =
        "component C {\n"
        "    /** Summary.\n"
        "     *  More detail.\n"
        "     */\n"
        "    int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Summary.\nMore detail.");
}

// A run of line comments has no opening-marker line, so every line's
// indentation counts and the relative indent must survive.
TEST(DocCommentNorm, line_comment_run_preserves_relative_indent) {
    std::string src =
        "component C {\n"
        "    /// Line one.\n"
        "    ///\n"
        "    ///     indented code\n"
        "    int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Line one.\n\n    indented code");
}

// The conventional single space after `//` is removed by the marker strip,
// not left to the dedent.  Leaving it to the dedent made the whole run
// sensitive to one line written without it: the common prefix dropped to
// zero and every other line kept a one-space indent, which reStructuredText
// reads as a block quote.
TEST(DocCommentNorm, line_comment_run_survives_a_missing_space) {
    std::string src =
        "component C {\n"
        "    //@doc(text = \"x\")\n"
        "    // Real prose.\n"
        "    int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "@doc(text = \"x\")\nReal prose.");
}

// The same run written conventionally must come out identically -- the fix
// must not depend on which spelling appears.
TEST(DocCommentNorm, line_comment_run_with_every_space_present) {
    std::string src =
        "component C {\n"
        "    // First.\n"
        "    // Second.\n"
        "    int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "First.\nSecond.");
}

// Stripping one space must not eat deliberate indentation: `//     code` is
// still four columns in from `// text`.
TEST(DocCommentNorm, line_comment_relative_indent_survives_the_space_strip) {
    std::string src =
        "component C {\n"
        "    // Intro.\n"
        "    //     indented code\n"
        "    // Outro.\n"
        "    int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Intro.\n    indented code\nOutro.");
}

// All three line forms strip the space identically, and `///<` still loses
// its `<` before the space is considered.
TEST(DocCommentNorm, every_line_form_strips_the_space) {
    EXPECT_EQ(leading("component C {\n// doc\nint f1;\n}\n", "int"), "doc");
    EXPECT_EQ(leading("component C {\n/// doc\nint f1;\n}\n", "int"), "doc");
    EXPECT_EQ(leading("component C {\n//! doc\nint f1;\n}\n", "int"), "doc");
    EXPECT_EQ(leading("component C {\n///< doc\nint f1;\n}\n", "int"), "doc");
    // A plain `//<` is not a Doxygen trailing marker, so the `<` is content
    // and only the space that follows the marker is removed.
    EXPECT_EQ(leading("component C {\n//< doc\nint f1;\n}\n", "int"), "< doc");
}

TEST(DocCommentNorm, tabs_expand_before_dedent) {
    // One tab of indent on the body, two on the nested line: at tab width 4
    // the nested line ends up indented four spaces relative to the body.
    std::string src =
        "component C {\n"
        "/**\n"
        "\t Line one.\n"
        "\t\t nested\n"
        "*/\n"
        "int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "Line one.\n    nested");
}

TEST(DocCommentNorm, single_line_block_has_no_trailing_space) {
    EXPECT_EQ(leading("component C {\n/**  doc  */\nint f1;\n}\n", "int"), "doc");
}

TEST(DocCommentNorm, blank_lines_are_trimmed_at_both_ends) {
    std::string src =
        "component C {\n"
        "/**\n"
        " *\n"
        " * doc\n"
        " *\n"
        " */\n"
        "int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int"), "doc");
}

// ---------------------------------------------------------------------------
// Raw fidelity (§3.3) and location
// ---------------------------------------------------------------------------

TEST(DocCommentRaw, raw_is_verbatim_for_a_block) {
    Lexed lx("component C {\n    /** doc\n     * more */\n    int f1;\n}\n");
    DocCommentExtractor ex(lx.tokens(), 7);
    DocComment dc;
    ASSERT_TRUE(ex.extractLeading(lx.find("int"), dc));
    EXPECT_EQ(dc.raw, "/** doc\n     * more */");
    EXPECT_EQ(dc.form, DocCommentForm::DocBlock);
    EXPECT_EQ(dc.location.fileid, 7);
    EXPECT_EQ(dc.location.lineno, 2);
    EXPECT_EQ(dc.location.linepos, 5);
    EXPECT_FALSE(dc.trailing);
}

// A multi-token run spans the whitespace between the tokens, so `raw` is
// byte-identical to the source region rather than a concatenation of texts.
TEST(DocCommentRaw, raw_spans_a_line_comment_run) {
    Lexed lx("component C {\n    // one\n    // two\n    int f1;\n}\n");
    DocCommentExtractor ex(lx.tokens(), 1);
    DocComment dc;
    ASSERT_TRUE(ex.extractLeading(lx.find("int"), dc));
    EXPECT_EQ(dc.raw, "// one\n    // two\n");
    EXPECT_EQ(dc.form, DocCommentForm::Line);
    EXPECT_EQ(dc.location.lineno, 2);
}

// ---------------------------------------------------------------------------
// lastContentLine -- the arithmetic the association rule rests on
// ---------------------------------------------------------------------------

TEST(DocCommentLines, line_comment_ends_on_its_own_line) {
    Lexed lx("// doc\nint f1;\n");
    // The single-line comment token includes its terminating newline, so its
    // text spans lines 1 and 2 while its content occupies only line 1.
    Token *c = nullptr;
    for (size_t i=0; i<lx.tokens()->size(); i++) {
        Token *t = lx.tokens()->get(i);
        if (t->getText().substr(0, 2) == "//") {
            c = t;
            break;
        }
    }
    ASSERT_TRUE(c != nullptr);
    EXPECT_EQ(DocCommentExtractor::lastContentLine(c), 1);
}

// ---------------------------------------------------------------------------
// Options (E2.5)
// ---------------------------------------------------------------------------

TEST(DocCommentOpts, permissive_is_the_default) {
    DocCommentOptions opts;
    EXPECT_FALSE(opts.strict_markers);
    EXPECT_EQ(opts.tab_width, 4);
    EXPECT_EQ(leading("component C {\n// doc\nint f1;\n}\n", "int", 0, opts), "doc");
}

TEST(DocCommentOpts, strict_mode_ignores_unmarked_forms) {
    DocCommentOptions opts;
    opts.strict_markers = true;
    EXPECT_EQ(leading("component C {\n// doc\nint f1;\n}\n",    "int", 0, opts), "");
    EXPECT_EQ(leading("component C {\n/* doc */\nint f1;\n}\n", "int", 0, opts), "");
    EXPECT_EQ(leading("component C {\n/// doc\nint f1;\n}\n",   "int", 0, opts), "doc");
    EXPECT_EQ(leading("component C {\n/** doc */\nint f1;\n}\n","int", 0, opts), "doc");
}

TEST(DocCommentOpts, tab_width_is_honored) {
    DocCommentOptions opts;
    opts.tab_width = 8;
    std::string src =
        "component C {\n"
        "/**\n"
        "\t Line one.\n"
        "\t\t nested\n"
        "*/\n"
        "int f1;\n"
        "}\n";
    EXPECT_EQ(leading(src, "int", 0, opts), "Line one.\n        nested");
}

// ---------------------------------------------------------------------------
// Trailing comments (§3.5, wired up by E5)
// ---------------------------------------------------------------------------

TEST(DocCommentTrailing, same_line_comment_is_found) {
    Lexed lx("component C {\n    int len; // bytes\n    int b;\n}\n");
    DocCommentExtractor ex(lx.tokens(), 1);
    DocComment dc;
    ASSERT_TRUE(ex.extractTrailing(lx.find(";"), dc));
    EXPECT_EQ(dc.text, "bytes");
    EXPECT_TRUE(dc.trailing);
}

TEST(DocCommentTrailing, doxygen_marker_accepted) {
    Lexed lx("component C {\n    int len; ///< bytes\n}\n");
    DocCommentExtractor ex(lx.tokens(), 1);
    DocComment dc;
    ASSERT_TRUE(ex.extractTrailing(lx.find(";"), dc));
    EXPECT_EQ(dc.text, "bytes");
}

TEST(DocCommentTrailing, comment_on_the_next_line_is_not_trailing) {
    Lexed lx("component C {\n    int len;\n    // not trailing\n    int b;\n}\n");
    DocCommentExtractor ex(lx.tokens(), 1);
    DocComment dc;
    EXPECT_FALSE(ex.extractTrailing(lx.find(";"), dc));
}
