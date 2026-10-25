/****************************************************************************
 * IParserSession.h
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
 ****************************************************************************/
#pragma once
#include <map>
#include <memory>
#include <string>
#include <vector>
#include "pssp/IMarker.h"
#include "pssp/IParseProfileInfo.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/SourceRange.h"

namespace pssp {

namespace lint {
class ILintEngine;
}

/** The display name of fileid -1: types the core synthesises, with no
 *  source text. */
static constexpr const char *FILE_BUILTIN = "<builtin>";
/** The display name of fileid 0 at a line in no core-library file. */
static constexpr const char *FILE_STDLIB = "<stdlib>";
/** The prefix of a core-library file's display name: `<stdlib>/std_pkg.pss`. */
static constexpr const char *FILE_STDLIB_PREFIX = "<stdlib>/";
/** The display name of a fileid with no recorded name. */
static constexpr const char *FILE_UNKNOWN = "<unknown>";
/** The display name of a tool-level diagnostic: an internal error with no
 *  source location. */
static constexpr const char *FILE_TOOL = "<pssparser>";

/** A display location: a file name and its own 1-based line. */
struct SessionLocation {
    std::string     file;
    int32_t         line = -1;
};

struct SessionMarkerRelation {
    std::string     file;
    int32_t         line = -1;
    int32_t         col = -1;
    std::string     label;
};

struct SessionMarkerFix {
    std::string     file;
    int32_t         line = -1;
    int32_t         col = -1;
    int32_t         extent = 0;
    std::string     replacement;
};

/**
 * A marker with its location resolved to a display file and line.
 *
 * `fileid` and `raw_line` are the core's own coordinates, kept so a host can
 * still find the unit; `file` and `line` are what a reader is shown. A
 * core-library location is mapped to the library file it falls in.
 */
struct SessionMarker {
    MarkerSeverityE                     severity = MarkerSeverityE::Error;
    std::string                         message;
    /** The stable marker id; "" when none was assigned. */
    std::string                         code;
    int32_t                             fileid = -1;
    int32_t                             raw_line = -1;
    std::string                         file;
    int32_t                             line = -1;
    /** 1-based, as `Location.linepos` is. */
    int32_t                             col = -1;
    /** -1 when the core does not know it. */
    int32_t                             extent = -1;
    std::vector<SessionMarkerRelation>  related;
    /** The first machine-applicable repair, when `has_fix`. */
    bool                                has_fix = false;
    SessionMarkerFix                    fix;
};

class IParserSession;
using IParserSessionUP=std::unique_ptr<IParserSession>;

/**
 * One parse-and-link lifecycle: the units, the linked root, the file names,
 * and the markers of every call, resolved and sorted.
 *
 * This is what every binding wraps (core-in-leaf-plan.md CF1). The rules it
 * keeps are the ones each binding used to keep for itself:
 *
 *  - The standard library is unit 0, loaded on the first parse; user fileids
 *    start at 1.
 *  - One builder is reused across parse calls, because compile-time
 *    expressions may reference constants of an earlier unit (PSS 3.1 19.1.2).
 *    link() drops it, since ownership of the units it holds has moved.
 *  - A source that fails to parse does not join the units and does not
 *    consume its fileid.
 *  - link() records the root whether or not it failed.
 *  - A C++ exception never escapes: it becomes a PSSP000 marker.
 *
 * Markers accumulate across calls until clearMarkers(), and are kept sorted
 * by (file, line, col), stably, so a cascade at one point keeps its order.
 */
class IParserSession {
public:

    virtual ~IParserSession() { }

    /** 0 (the default) is unlimited. Applies from the next call on. */
    virtual void setMaxErrors(int32_t n) = 0;

    virtual void setCollectDocstrings(bool c) = 0;

    virtual bool getCollectDocstrings() const = 0;

    /** Implies docstring collection. */
    virtual void setCollectComments(bool c) = 0;

    virtual bool getCollectComments() const = 0;

    virtual void setEnableProfiling(bool e) = 0;

    /**
     * Open a parse call. One marker collector serves the whole call, and the
     * standard library is loaded here when there are no units yet.
     */
    virtual void beginParse() = 0;

    /**
     * Parse one source into a fresh unit. Returns false when the call has
     * produced an error-severity marker so far; the source then does not join
     * the units. Markers are added to markers() before it returns.
     */
    virtual bool parseSource(
        const std::string       &name,
        const std::string       &text) = 0;

    /** The fileid the next parseSource() will assign. */
    virtual int32_t nextFileid() const = 0;

    /** Units accepted since the last link(), standard library first. */
    virtual const std::vector<ast::IGlobalScope *> &units() const = 0;

    /**
     * Hand ownership of every unit accepted so far to the caller. The session
     * still uses them -- as the builder's environment, and for link(), which
     * gives them to the root -- so the caller must keep them alive until
     * then. Units accepted later are the session's again until the next
     * call. For a binding whose own wrappers own the units, so that a caller
     * may link them with its own ILinker.
     */
    virtual void releaseUnits() = 0;

    /**
     * Link every unit parsed so far. Returns false when the link produced an
     * error-severity marker. The root is recorded either way; the units are
     * the root's after this.
     */
    virtual bool link() = 0;

    /** The last link()'s root, or null. */
    virtual ast::IRootSymbolScope *root() const = 0;

    /**
     * Hand ownership of the root to the caller. The session keeps it as a
     * borrowed pointer for its queries, so the caller must keep it alive as
     * long as it uses the session. The next link() replaces it without
     * freeing it.
     */
    virtual ast::IRootSymbolScope *releaseRoot() = 0;

    /** The user files' units in the linked root, in parse order. */
    virtual std::vector<ast::IGlobalScope *> userUnits() const = 0;

    /** fileid -> name of the sources parsed since the last link(). */
    virtual const std::map<int32_t, std::string> &sourceNames() const = 0;

    /** fileid -> name of the files the last link() took. */
    virtual const std::map<int32_t, std::string> &fileMap() const = 0;

    /**
     * The display file and line of a location. A user file's line is its
     * own; a core-library line maps to the library file it falls in.
     */
    virtual SessionLocation resolveLocation(int32_t fileid, int32_t line) const = 0;

    /** Every marker since the last clearMarkers(), sorted. */
    virtual const std::vector<SessionMarker> &markers() const = 0;

    /** The markers of the last parse or link call, sorted. */
    virtual const std::vector<SessionMarker> &callMarkers() const = 0;

    virtual void clearMarkers() = 0;

    /** Whether the current call has produced an error-severity marker. */
    virtual bool hasErrors() const = 0;

    virtual bool maxErrorsExceeded() const = 0;

    /**
     * The source regions a `compile if` left out, in the user files of the
     * linked root, sorted by position. A `compile if` inside a region is not
     * in the AST, so it is covered by that region. Empty before link().
     */
    virtual std::vector<ast::SourceRange> inactiveRegions() const = 0;

    /**
     * Profiling data from the last parse; null when profiling was off,
     * nothing was parsed, or link() has dropped the builder. The caller owns
     * the result.
     */
    virtual IParseProfileInfo *profileInfo() = 0;

    /**
     * markers() as JSON, for a binding that crosses as text: an array of
     * {severity, message, file, line, col, extent, related: [{file, line,
     * col, label}], code?, fix?: {file, line, col, extent, replacement}}.
     * Severity is "error", "warning", "info" or "hint".
     */
    virtual std::string markersJson() const = 0;

    /** callMarkers() as JSON, in markersJson()'s shape. */
    virtual std::string callMarkersJson() const = 0;

    /** fileMap() as a JSON object, fileid -> name. */
    virtual std::string fileMapJson() const = 0;

    /** sourceNames() as a JSON object, fileid -> name. */
    virtual std::string sourceNamesJson() const = 0;

    /** inactiveRegions() as a JSON array of
     *  {fileid, startLine, startCol, endLine, endCol}. */
    virtual std::string inactiveRegionsJson() const = 0;

    /** profileInfo() as JSON; "" when there is none. */
    virtual std::string profileInfoJson() = 0;

    /**
     * The session's lint engine, created on first use with the built-in rules
     * loaded. Rules loaded into it serve every later run.
     */
    virtual lint::ILintEngine *lintEngine() = 0;

};

}

