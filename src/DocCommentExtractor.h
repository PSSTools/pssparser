/*
 * DocCommentExtractor.h
 *
 * Associates comments in the hidden token channels with the declarations they
 * document, and normalizes them into text a documentation generator can use
 * directly.
 *
 * The association rules and the normalization steps are specified in
 * docs/doc_comments.rst; that page is the contract, this is the implementation.
 */

#pragma once
#include <string>
#include <vector>

#include "BufferedTokenStream.h"
#include "Token.h"
#include "pssp/ast/Location.h"

namespace pssp {

/**
 * Lexical form of a doc comment.  Retained on the extracted comment so a
 * consumer can apply a dialect (Doxygen, Javadoc, ...) that keys off the
 * marker without re-lexing the source.
 */
enum class DocCommentForm {
    None = 0,   //!< no comment was associated
    Line,       //!< `//`
    DocLine,    //!< `///` or `//!`
    Block,      //!< `/* ... */`
    DocBlock    //!< `/** ... */` or `/*! ... */`
};

const char *toString(DocCommentForm form);

/**
 * A comment associated with a declaration.
 */
struct DocComment {
    /** Verbatim source text of the comment block, markers included. */
    std::string     raw;
    /** Normalized body -- what getDocstring() returns. */
    std::string     text;
    /** Form of the first comment in the block. */
    DocCommentForm  form = DocCommentForm::None;
    /** First character of the comment block. */
    ast::Location   location;
    /** True when this is a same-line trailing comment. */
    bool            trailing = false;

    bool valid() const { return form != DocCommentForm::None; }

    void clear() {
        raw.clear();
        text.clear();
        form = DocCommentForm::None;
        location = ast::Location();
        trailing = false;
    }
};

struct DocCommentOptions {
    /**
     * Columns a tab advances when leading indentation is normalized.  Only
     * indentation is affected; tabs inside the body are left alone.
     */
    int32_t tab_width = 4;

    //! When true, only the marked forms (`///`, `//!`, `/**`, `/*!`) count as
    //! documentation and an ordinary line or block comment is ignored.
    //!
    //! Default false: in PSS sources an ordinary comment above a declaration is
    //! overwhelmingly meant to describe it, and requiring a marker would make
    //! the common case undocumented.  Projects that want the stricter Doxygen
    //! reading can opt in.
    bool    strict_markers = false;
};

/**
 * Extracts doc comments from a token stream.
 *
 * Holds no state beyond its inputs, so one instance can serve a whole parse.
 * The token stream must outlive the extractor.
 */
class DocCommentExtractor {
public:
    DocCommentExtractor(
            antlr4::BufferedTokenStream *toks,
            int32_t                     file_id,
            const DocCommentOptions     &opts = DocCommentOptions());

    virtual ~DocCommentExtractor();

    void setFileId(int32_t file_id) { m_file_id = file_id; }

    void setOptions(const DocCommentOptions &opts) { m_opts = opts; }

    const DocCommentOptions &options() const { return m_opts; }

    /**
     * Find the doc comment block that leads the declaration starting at
     * *anchor*.  Returns false and leaves *out* cleared when there is none.
     */
    bool extractLeading(antlr4::Token *anchor, DocComment &out) const;

    /**
     * Find a trailing comment beginning on the same line as *stop*, the last
     * token of a declaration.  Returns false when there is none.
     */
    bool extractTrailing(antlr4::Token *stop, DocComment &out) const;

    // -- Pieces exposed for unit testing ------------------------------------

    /** Classify a comment by its opening marker. */
    static DocCommentForm classify(const std::string &raw);

    /** Normalize one comment block (already concatenated) to body text. */
    static std::string normalize(
            const std::vector<std::string>  &raws,
            DocCommentForm                  form,
            const DocCommentOptions         &opts);

    /**
     * Source line on which *t* last has content.  A single-line comment token
     * includes its terminating newline, so its text spans two lines while its
     * content occupies only the first; block comments and whitespace do not.
     * Getting this wrong is what made the old code treat an adjacent line
     * comment and a blank-line-separated one identically.
     */
    static int32_t lastContentLine(antlr4::Token *t);

private:
    static bool isComment(antlr4::Token *t);

    static bool isBlockForm(DocCommentForm f) {
        return f == DocCommentForm::Block || f == DocCommentForm::DocBlock;
    }

    bool isDoc(DocCommentForm f) const {
        return f != DocCommentForm::None &&
            (!m_opts.strict_markers ||
                f == DocCommentForm::DocLine ||
                f == DocCommentForm::DocBlock);
    }

    /** Build the result from *run*, which is in reverse source order. */
    bool finish(const std::vector<antlr4::Token *> &run, DocComment &out) const;

private:
    antlr4::BufferedTokenStream     *m_tokens;
    int32_t                         m_file_id;
    DocCommentOptions               m_opts;
};

} /* namespace pssp */
