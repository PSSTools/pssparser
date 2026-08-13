/*
 * DocCommentExtractor.cpp
 *
 * See DocCommentExtractor.h and docs/doc_comments.rst.
 */

#include "DocCommentExtractor.h"

#include <algorithm>

#include "CharStream.h"
#include "misc/Interval.h"

using namespace antlr4;

namespace pssp {

const char *toString(DocCommentForm form) {
    switch (form) {
        case DocCommentForm::Line:     return "line";
        case DocCommentForm::DocLine:  return "doc-line";
        case DocCommentForm::Block:    return "block";
        case DocCommentForm::DocBlock: return "doc-block";
        default:                       return "none";
    }
}

DocCommentExtractor::DocCommentExtractor(
        BufferedTokenStream     *toks,
        int32_t                 file_id,
        const DocCommentOptions &opts) :
    m_tokens(toks), m_file_id(file_id), m_opts(opts) {
}

DocCommentExtractor::~DocCommentExtractor() {
}

// --------------------------------------------------------------------------
// Classification
// --------------------------------------------------------------------------

DocCommentForm DocCommentExtractor::classify(const std::string &raw) {
    if (raw.size() < 2 || raw[0] != '/') {
        return DocCommentForm::None;
    }
    if (raw[1] == '/') {
        if (raw.size() >= 3 && (raw[2] == '/' || raw[2] == '!')) {
            return DocCommentForm::DocLine;
        }
        return DocCommentForm::Line;
    }
    if (raw[1] == '*') {
        // `/**/` and `/***/` are empty block comments, not doc blocks: there
        // is no room for a body between the marker and the terminator.
        if (raw.size() >= 5 && (raw[2] == '*' || raw[2] == '!')) {
            return DocCommentForm::DocBlock;
        }
        return DocCommentForm::Block;
    }
    return DocCommentForm::None;
}

bool DocCommentExtractor::isComment(Token *t) {
    const std::string &txt = t->getText();
    return txt.size() >= 2 && txt[0] == '/' && (txt[1] == '/' || txt[1] == '*');
}

int32_t DocCommentExtractor::lastContentLine(Token *t) {
    const std::string &txt = t->getText();
    int32_t line = (int32_t)t->getLine();
    for (size_t i=0; i<txt.size(); i++) {
        if (txt[i] == '\n') {
            line++;
        }
    }
    if (!txt.empty() && txt[txt.size()-1] == '\n') {
        // The newline terminates the last content line rather than opening a
        // new one.
        line--;
    }
    return line;
}

// --------------------------------------------------------------------------
// Normalization helpers
// --------------------------------------------------------------------------

namespace {

bool isBlankLine(const std::string &s) {
    for (size_t i=0; i<s.size(); i++) {
        if (!isspace((unsigned char)s[i])) {
            return false;
        }
    }
    return true;
}

/** Replace the leading whitespace run with the equivalent number of spaces. */
std::string expandLeading(const std::string &line, int32_t tab_width) {
    size_t i = 0;
    int32_t col = 0;
    while (i < line.size() && (line[i] == ' ' || line[i] == '\t')) {
        if (line[i] == '\t') {
            col += (tab_width > 0) ? (tab_width - (col % tab_width)) : 1;
        } else {
            col++;
        }
        i++;
    }
    return std::string((size_t)col, ' ') + line.substr(i);
}

size_t leadingSpaces(const std::string &line) {
    size_t i = 0;
    while (i < line.size() && line[i] == ' ') {
        i++;
    }
    return i;
}

std::string lstrip(const std::string &s) {
    size_t i = 0;
    while (i < s.size() && isspace((unsigned char)s[i])) {
        i++;
    }
    return s.substr(i);
}

void splitLines(const std::string &s, std::vector<std::string> &lines) {
    std::string cur;
    for (size_t i=0; i<s.size(); i++) {
        if (s[i] == '\n') {
            if (!cur.empty() && cur[cur.size()-1] == '\r') {
                cur.erase(cur.size()-1);
            }
            lines.push_back(cur);
            cur.clear();
        } else {
            cur += s[i];
        }
    }
    lines.push_back(cur);
}

/**
 * Body of a single-line comment token: marker, an optional Doxygen `<`, and
 * the terminating newline removed.
 */
std::string stripLineMarker(const std::string &tok, DocCommentForm form) {
    std::string s = tok;
    if (!s.empty() && s[s.size()-1] == '\n') {
        s.erase(s.size()-1);
    }
    if (!s.empty() && s[s.size()-1] == '\r') {
        s.erase(s.size()-1);
    }
    size_t open = (form == DocCommentForm::DocLine) ? 3 : 2;
    if (s.size() < open) {
        return "";
    }
    s = s.substr(open);
    // `///<` / `//!<` mark a Doxygen trailing comment.  Only the marked forms
    // define it, so a plain `//<...>` keeps its `<`.
    if (form == DocCommentForm::DocLine && !s.empty() && s[0] == '<') {
        s = s.substr(1);
    }
    return s;
}

//! Body of a block comment token: opening marker, Doxygen `<`, and the
//! closing marker removed.
std::string stripBlockMarkers(const std::string &tok, DocCommentForm form) {
    size_t open = (form == DocCommentForm::DocBlock) ? 3 : 2;
    size_t close = 2;
    if (tok.size() < open + close) {
        return "";
    }
    std::string s = tok.substr(open, tok.size() - open - close);
    if (form == DocCommentForm::DocBlock && !s.empty() && s[0] == '<') {
        s = s.substr(1);
    }
    return s;
}

/**
 * Remove the decorative `*` that opens a continuation line of a block comment:
 * any amount of leading whitespace, the `*`, and one following space.
 *
 * The old implementation handled exactly zero or one whitespace character
 * before the `*`, so any real indentation left the marker in the text.
 */
void stripContinuationStar(std::string &line) {
    size_t i = 0;
    while (i < line.size() && (line[i] == ' ' || line[i] == '\t')) {
        i++;
    }
    if (i >= line.size() || line[i] != '*') {
        return;
    }
    i++;
    if (i < line.size() && line[i] == ' ') {
        i++;
    }
    line = line.substr(i);
}

} /* anonymous namespace */

std::string DocCommentExtractor::normalize(
        const std::vector<std::string>  &raws,
        DocCommentForm                  form,
        const DocCommentOptions         &opts) {
    if (raws.empty()) {
        return "";
    }

    std::vector<std::string> lines;
    bool block = isBlockForm(form);

    if (block) {
        // A block comment is a complete doc block by itself, so there is
        // exactly one token.
        std::string body = stripBlockMarkers(raws.front(), form);
        splitLines(body, lines);
        for (size_t i=1; i<lines.size(); i++) {
            stripContinuationStar(lines[i]);
        }
    } else {
        for (size_t i=0; i<raws.size(); i++) {
            lines.push_back(stripLineMarker(raws[i], classify(raws[i])));
        }
    }

    for (size_t i=0; i<lines.size(); i++) {
        lines[i] = expandLeading(lines[i], opts.tab_width);
    }

    // Dedent.  Relative indentation is preserved because the consumer reads the
    // body as reStructuredText, where indentation is syntax.
    //
    // For a block comment the first line sits after the opening marker on the
    // same source line, so its indentation says nothing about the body: strip
    // it and leave it out of the common-prefix computation (the semantics of
    // Python's inspect.cleandoc).  In a run of line comments every line is an
    // equal citizen and the first line's indentation counts like any other.
    size_t start = 0;
    if (block && !lines.empty()) {
        lines[0] = lstrip(lines[0]);
        start = 1;
    }

    size_t common = std::string::npos;
    for (size_t i=start; i<lines.size(); i++) {
        if (isBlankLine(lines[i])) {
            continue;
        }
        size_t ind = leadingSpaces(lines[i]);
        if (common == std::string::npos || ind < common) {
            common = ind;
        }
    }
    if (common != std::string::npos && common > 0) {
        for (size_t i=start; i<lines.size(); i++) {
            if (isBlankLine(lines[i])) {
                // A blank line may be shorter than the common prefix.
                lines[i].clear();
            } else {
                lines[i] = lines[i].substr(common);
            }
        }
    }

    // Drop leading blank lines, then join.
    size_t first = 0;
    while (first < lines.size() && isBlankLine(lines[first])) {
        first++;
    }

    std::string text;
    for (size_t i=first; i<lines.size(); i++) {
        if (i > first) {
            text += "\n";
        }
        text += lines[i];
    }

    // Trailing blank lines and any trailing whitespace on the final line are
    // noise from the closing marker's indentation.  Whitespace *inside* the
    // body is left alone.
    size_t end = text.size();
    while (end > 0 && isspace((unsigned char)text[end-1])) {
        end--;
    }
    text.erase(end);

    return text;
}

// --------------------------------------------------------------------------
// Association
// --------------------------------------------------------------------------

bool DocCommentExtractor::finish(
        const std::vector<Token *>  &run,
        DocComment                  &out) const {
    out.clear();
    if (run.empty()) {
        return false;
    }

    // `run` is in reverse source order.
    Token *first = run.back();
    Token *last = run.front();

    std::vector<std::string> raws;
    raws.reserve(run.size());
    for (std::vector<Token *>::const_reverse_iterator
            it=run.rbegin(); it!=run.rend(); it++) {
        raws.push_back((*it)->getText());
    }

    out.form = classify(raws.front());
    out.text = normalize(raws, out.form, m_opts);

    CharStream *cs = first->getInputStream();
    if (cs) {
        // Span the whole block so `raw` is byte-identical to the source,
        // including the whitespace between consecutive line comments.
        out.raw = cs->getText(misc::Interval(
            (ssize_t)first->getStartIndex(),
            (ssize_t)last->getStopIndex()));
    } else {
        for (size_t i=0; i<raws.size(); i++) {
            out.raw += raws[i];
        }
    }

    out.location.fileid = m_file_id;
    out.location.lineno = (int32_t)first->getLine();
    out.location.linepos = (int32_t)first->getCharPositionInLine()+1;
    out.location.extent = (int32_t)out.raw.size();

    return true;
}

bool DocCommentExtractor::extractLeading(Token *anchor, DocComment &out) const {
    out.clear();
    if (!anchor || !m_tokens) {
        return false;
    }

    // One list, in source order, covering every hidden token between the
    // previous on-channel token and the anchor.  Reconstructing this order
    // from three channel-filtered lists is what produced the association bugs
    // this class replaces.
    std::vector<Token *> hidden =
        m_tokens->getHiddenTokensToLeft(anchor->getTokenIndex());
    if (hidden.empty()) {
        return false;
    }

    int32_t next_line = (int32_t)anchor->getLine();
    std::vector<Token *> run;

    for (std::vector<Token *>::const_reverse_iterator
            it=hidden.rbegin(); it!=hidden.rend(); it++) {
        Token *t = *it;
        if (!isComment(t)) {
            // Whitespace carries no information the line numbers do not.
            continue;
        }
        DocCommentForm form = classify(t->getText());
        if (!isDoc(form)) {
            break;
        }
        if (next_line - lastContentLine(t) >= 2) {
            // A blank line separates the comment from what follows it.  This
            // is the single association rule, and it applies to line comments
            // exactly as it does to block comments.
            break;
        }
        if (isBlockForm(form) && !run.empty()) {
            break;
        }
        run.push_back(t);
        next_line = (int32_t)t->getLine();
        if (isBlockForm(form)) {
            // A block comment is a complete doc block by itself.
            break;
        }
    }

    // A comment beginning on the same line as the token that precedes the
    // whole hidden run trails *that* construct; it does not lead this one.
    //
    // Unless it also ends on the anchor's own line -- `f(/** a */ int a)`, or
    // any block comment written inline ahead of the thing it describes.  There
    // the comment is positionally leading whatever follows it on that line, and
    // excluding it would silently drop the documentation of every parameter
    // written in the usual one-line form.  A line comment can never satisfy
    // this, since it consumes the newline that ends its line.
    size_t first_hidden = hidden.front()->getTokenIndex();
    if (!run.empty() && first_hidden > 0) {
        Token *prev = m_tokens->get(first_hidden-1);
        bool same_line_as_prev =
            prev && (int32_t)prev->getLine() == (int32_t)run.back()->getLine();
        bool ends_on_anchor_line =
            lastContentLine(run.back()) == (int32_t)anchor->getLine();
        if (same_line_as_prev && !ends_on_anchor_line) {
            run.pop_back();
        }
    }

    return finish(run, out);
}

bool DocCommentExtractor::extractTrailing(Token *stop, DocComment &out) const {
    out.clear();
    if (!stop || !m_tokens) {
        return false;
    }

    std::vector<Token *> hidden =
        m_tokens->getHiddenTokensToRight(stop->getTokenIndex());
    int32_t stop_line = lastContentLine(stop);

    for (size_t i=0; i<hidden.size(); i++) {
        Token *t = hidden[i];
        if (!isComment(t)) {
            if (t->getText().find('\n') != std::string::npos) {
                // The line ended before any comment appeared.
                return false;
            }
            continue;
        }
        DocCommentForm form = classify(t->getText());
        if (!isDoc(form) || (int32_t)t->getLine() != stop_line) {
            return false;
        }
        std::vector<Token *> run;
        run.push_back(t);
        if (!finish(run, out)) {
            return false;
        }
        out.trailing = true;
        return true;
    }

    return false;
}

} /* namespace pssp */
