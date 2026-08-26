/*
 * TestFmtCst.cpp
 *
 * The parse-only concrete syntax tree.
 *
 * Two properties matter more than the rest and are tested first: the tree's
 * token indices index the accompanying stream, and `compile if` keeps both
 * branches.  The first is what makes structure and text usable together; the
 * second is the whole reason this exists instead of the AST.
 */

#include <sstream>
#include <string>
#include <vector>

#include "gtest/gtest.h"

#include "pssp/IFmtCst.h"
#include "FmtCst.h"

using namespace pssp;

namespace {

static IFmtCstUP parse(const std::string &src) {
    std::istringstream in(src);
    return IFmtCstUP(new FmtCst(&in));
}

/** Depth-first walk collecting every node. */
static void collect(IFmtCstNode *n, std::vector<IFmtCstNode *> &out) {
    out.push_back(n);
    for (uint32_t i=0; i<n->getNumChildren(); i++) {
        collect(n->getChild(i), out);
    }
}

static std::vector<IFmtCstNode *> allNodes(IFmtCst *cst) {
    std::vector<IFmtCstNode *> out;
    if (cst->getRoot()) {
        collect(cst->getRoot(), out);
    }
    return out;
}

/** Concatenation of the terminals' text, in tree order. */
static std::string terminalText(IFmtCst *cst) {
    std::string ret;
    std::vector<IFmtCstNode *> nodes = allNodes(cst);
    for (size_t i=0; i<nodes.size(); i++) {
        if (!nodes[i]->isRule() && nodes[i]->getTokenIndex() >= 0) {
            ret += cst->getTokens()->at(nodes[i]->getTokenIndex()).text;
        }
    }
    return ret;
}

const std::string SIMPLE =
    "component pss_top {\n"
    "    action A { rand int x; }\n"
    "}\n";

// -------------------------------------------------------------------------
// Structure and text agree
// -------------------------------------------------------------------------

TEST(FmtCst, RootIsTheCompilationUnit) {
    IFmtCstUP cst = parse(SIMPLE);
    ASSERT_NE(nullptr, cst->getRoot());
    ASSERT_TRUE(cst->getRoot()->isRule());
    ASSERT_EQ("compilation_unit", cst->getRoot()->getRuleName());
    ASSERT_EQ(0u, cst->getNumSyntaxErrors());
}

TEST(FmtCst, TokenIndicesIndexTheAccompanyingStream) {
    IFmtCstUP cst = parse(SIMPLE);
    IFmtTokenStream *toks = cst->getTokens();

    std::vector<IFmtCstNode *> nodes = allNodes(cst.get());
    for (size_t i=0; i<nodes.size(); i++) {
        if (nodes[i]->isRule()) {
            ASSERT_EQ(-1, nodes[i]->getTokenIndex());
        } else if (nodes[i]->getTokenIndex() >= 0) {
            ASSERT_LT(static_cast<uint32_t>(nodes[i]->getTokenIndex()),
                toks->size());
        }
    }
}

TEST(FmtCst, TerminalsAreTheDefaultChannelTokensInOrder) {
    // The join that everything above this depends on: walking the tree and
    // walking the stream must produce the same code, in the same order.
    IFmtCstUP cst = parse(SIMPLE);
    IFmtTokenStream *toks = cst->getTokens();

    std::string from_stream;
    for (uint32_t i=0; i<toks->size(); i++) {
        if (toks->at(i).channel == FmtTokenChannel_Default) {
            from_stream += toks->at(i).text;
        }
    }

    ASSERT_EQ(from_stream, terminalText(cst.get()));
}

TEST(FmtCst, TokenStreamStillRoundTrips) {
    // Parsing must not cost the losslessness the token stream provides.
    IFmtCstUP cst = parse(SIMPLE);
    std::string ret;
    for (uint32_t i=0; i<cst->getTokens()->size(); i++) {
        ret += cst->getTokens()->at(i).text;
    }
    ASSERT_EQ(SIMPLE, ret);
}

TEST(FmtCst, RuleSpansCoverTheirTerminals) {
    IFmtCstUP cst = parse(SIMPLE);
    std::vector<IFmtCstNode *> nodes = allNodes(cst.get());

    for (size_t i=0; i<nodes.size(); i++) {
        IFmtCstNode *n = nodes[i];
        if (!n->isRule() || n->getStartToken() < 0) {
            continue;
        }
        ASSERT_LE(n->getStartToken(), n->getStopToken()) << n->getRuleName();

        std::vector<IFmtCstNode *> sub;
        collect(n, sub);
        for (size_t j=0; j<sub.size(); j++) {
            int32_t idx = sub[j]->getTokenIndex();
            if (!sub[j]->isRule() && idx >= 0) {
                ASSERT_GE(idx, n->getStartToken()) << n->getRuleName();
                ASSERT_LE(idx, n->getStopToken()) << n->getRuleName();
            }
        }
    }
}

// -------------------------------------------------------------------------
// Nothing was folded away
// -------------------------------------------------------------------------

TEST(FmtCst, BothCompileIfBranchesArePresent) {
    // The reason this API exists.  Building the AST evaluates the condition
    // and keeps one branch; a tool that reproduces source needs both.
    IFmtCstUP cst = parse(
        "package p {\n"
        "  compile if (false) {\n"
        "    component taken { }\n"
        "  } else {\n"
        "    component not_taken { }\n"
        "  }\n"
        "}\n");

    ASSERT_EQ(0u, cst->getNumSyntaxErrors());
    std::string text = terminalText(cst.get());
    ASSERT_NE(std::string::npos, text.find("taken"));
    ASSERT_NE(std::string::npos, text.find("not_taken"));
}

TEST(FmtCst, RedundantParenthesesSurvive) {
    // An AST folds `((x))` to `x`.  Reformatting source that way is a change
    // the author did not ask for, so the parentheses must still be here.
    IFmtCstUP cst = parse("component c { int x; constraint { ((x)) > 0; } }");

    int32_t lparens = 0;
    std::vector<IFmtCstNode *> nodes = allNodes(cst.get());
    for (size_t i=0; i<nodes.size(); i++) {
        if (!nodes[i]->isRule() && nodes[i]->getTokenIndex() >= 0 &&
                cst->getTokens()->at(nodes[i]->getTokenIndex()).text == "(") {
            lparens++;
        }
    }
    ASSERT_EQ(2, lparens);
}

// -------------------------------------------------------------------------
// Degraded input
// -------------------------------------------------------------------------

TEST(FmtCst, SyntaxErrorsAreCountedNotThrown) {
    IFmtCstUP cst = parse("component c { this is not pss }");
    ASSERT_GT(cst->getNumSyntaxErrors(), 0u);
    // A tree is still produced -- ANTLR recovers -- and the token stream is
    // still complete, which is what lets a caller emit the input unchanged.
    ASSERT_NE(nullptr, cst->getRoot());
}

TEST(FmtCst, InvalidUtf8YieldsNoTreeAndSaysWhy) {
    IFmtCstUP cst = parse("// caf\xE9\ncomponent c { }\n");
    ASSERT_EQ(nullptr, cst->getRoot());
    ASSERT_FALSE(cst->getTokens()->isValidUtf8());
}

TEST(FmtCst, ByteOrderMarkDoesNotShiftTheTree) {
    // The BOM is a token in the stream but not in the grammar.  If the index
    // mapping were off by it, every terminal in a BOM'd file would name the
    // wrong token -- silently, and only for files with a BOM.
    IFmtCstUP with = parse("\xEF\xBB\xBF" "component c { }\n");
    IFmtCstUP without = parse("component c { }\n");

    ASSERT_EQ(0u, with->getNumSyntaxErrors());
    ASSERT_EQ(terminalText(without.get()), terminalText(with.get()));
}

TEST(FmtCst, UnlexableTextDoesNotShiftTheTree) {
    IFmtCstUP cst = parse("component c { } $ component d { }\n");
    ASSERT_EQ(1u, cst->getTokens()->getNumErrors());

    // The `$` is in the stream but never in the tree, and the terminals after
    // it still name their own tokens.
    std::vector<IFmtCstNode *> nodes = allNodes(cst.get());
    for (size_t i=0; i<nodes.size(); i++) {
        int32_t idx = nodes[i]->getTokenIndex();
        if (!nodes[i]->isRule() && idx >= 0) {
            ASSERT_NE(IFmtTokenStream::TYPE_ERROR_CHAR,
                cst->getTokens()->at(idx).type);
        }
    }
    ASSERT_NE(std::string::npos, terminalText(cst.get()).find("d"));
}

TEST(FmtCst, EmptyInput) {
    IFmtCstUP cst = parse("");
    ASSERT_NE(nullptr, cst->getRoot());
    ASSERT_EQ(0u, cst->getTokens()->size());
}

}
