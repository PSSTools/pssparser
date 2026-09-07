/****************************************************************************
 * bindings.cpp -- Embind surface for the pssparser WASM build
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

/*
 * This is the C++ half of `ts-api-design.md` §3. It is deliberately *not* a
 * transliteration of `python/pssparser/parser.py`: that file's job is split in
 * two here, and the split is the design decision worth recording.
 *
 *   - Everything that must touch a C++ object lives here: the builder, the
 *     unit list, the marker collectors, the load-stdlib-once rule.
 *   - Everything that is bookkeeping over values lives in TypeScript:
 *     fileid -> name, marker sorting, error-message formatting, and the
 *     decision to throw.
 *
 * The line falls where it does because of `_pathOf` (parser.py:276-287).
 * Markers carry a fileid, and turning a fileid into a path is pure bookkeeping
 * that the TypeScript side can do without a boundary crossing -- and *must*
 * do, because the sort key is the resolved *name*, not the fileid
 * (parser.py:352). Sorting here would sort by the wrong key.
 *
 * So the marker JSON below carries `fileid`, never `file`. Resolution and
 * sorting happen in Marker.ts.
 */

#include <emscripten/bind.h>

#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "pssp/FactoryExt.h"
#include "pssp/IFactory.h"
#include "pssp/IAstBuilder.h"
#include "pssp/IMarkerCollector.h"
#include "pssp/ast/FactoryExt.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IGlobalScope.h"
#include "AstSerializer.h"

namespace {

/****************************************************************************
 * JSON emission
 *
 * Hand-rolled rather than pulled in from a library: the only things that
 * cross this boundary as JSON are markers, the shape is fixed by
 * `ts-api-design.md` §5, and a dependency here would have to be built for
 * wasm32 as well as for the host.
 ****************************************************************************/
void jsonEscape(std::ostream &os, const std::string &s) {
    os << '"';
    for (unsigned char c : s) {
        switch (c) {
            case '"':  os << "\\\""; break;
            case '\\': os << "\\\\"; break;
            case '\b': os << "\\b"; break;
            case '\f': os << "\\f"; break;
            case '\n': os << "\\n"; break;
            case '\r': os << "\\r"; break;
            case '\t': os << "\\t"; break;
            default:
                if (c < 0x20) {
                    // Control characters must be escaped; everything at 0x20
                    // and above is passed through as-is, which keeps valid
                    // UTF-8 in the source text intact (JSON is UTF-8).
                    static const char *hex = "0123456789abcdef";
                    os << "\\u00" << hex[(c >> 4) & 0xF] << hex[c & 0xF];
                } else {
                    os << static_cast<char>(c);
                }
        }
    }
    os << '"';
}

const char *severityName(pssp::MarkerSeverityE s) {
    switch (s) {
        case pssp::MarkerSeverityE::Error: return "error";
        case pssp::MarkerSeverityE::Warn:  return "warning";
        case pssp::MarkerSeverityE::Info:  return "info";
        case pssp::MarkerSeverityE::Hint:  return "hint";
        default: break;
    }
    // Python maps an unrecognised enum to "unknown" and hands it to the
    // caller. TypeScript does not: `MarkerSeverity` has no 'unknown' member,
    // because a consumer forced to handle that case is handling a core bug
    // rather than a source condition (ts-api-design.md §5). Throwing turns it
    // into one clear failure at the boundary instead.
    throw std::runtime_error("unrecognised MarkerSeverityE crossing the WASM boundary");
}

void emitLocation(std::ostream &os, const pssp::ast::Location &loc) {
    // `col` is 1-based and `linepos` is 0-based, exactly as parser.py:305,331.
    // `extent` is passed through raw, including the -1 that Location.h
    // defaults it to; the Python API does the same (core.pyx:371-373) and
    // clamping here would invent information the core did not supply.
    os << "\"fileid\":" << loc.fileid
       << ",\"line\":" << loc.lineno
       << ",\"col\":" << (loc.linepos + 1)
       << ",\"extent\":" << loc.extent;
}

} // namespace

/****************************************************************************
 * ParserSession
 *
 * One of these backs one TypeScript `Parser`. Its lifetime is managed
 * explicitly from JavaScript -- `Parser.dispose()` deletes it -- because the
 * WASM heap is not reachable by the JS garbage collector
 * (ts-api-design.md §1).
 ****************************************************************************/
class ParserSession {
public:
    ParserSession() : m_builder(0), m_max_errors(0),
                      m_collect_docstrings(false), m_collect_comments(false) {
        m_ast_factory = ast_getFactory();
        m_factory = pssparser_getFactory();
        // No debug manager. Every DEBUG_* macro in the core is null-guarded --
        // DEBUG_INIT stores `mgr ? mgr->findDebug(scope) : 0` and the rest test
        // m_dbg before dereferencing (dmgr/impl/DebugMacros.h) -- so passing
        // null disables tracing and costs nothing else. This is what lets the
        // WASM build skip debug_mgr, which ships as a prebuilt host .so with
        // no source to compile for wasm32.
        m_factory->init(0, m_ast_factory);
    }

    ~ParserSession() {
        // Units the linker never took are ours to free. After link() the
        // vector is empty, because ownership moved into the root
        // (parser.py:211-217 records the same rule on the Python side).
        for (pssp::ast::IGlobalScope *u : m_units) {
            delete u;
        }
    }

    void setMaxErrors(int32_t n) { m_max_errors = n; }

    /*
     * Collection flags are stored, not applied. They are pushed into the
     * builder by ensureBuilder() on every call rather than once at
     * construction, because link() drops the builder and a session reused
     * across a link boundary builds a fresh one that would otherwise come back
     * with collection off (parser.py:74-81).
     */
    void setCollectDocstrings(bool c) { m_collect_docstrings = c; }
    void setCollectComments(bool c) { m_collect_comments = c; }
    void setEnableProfiling(bool e) { m_enable_profiling = e; }

    /*
     * Open a parse call. One marker collector serves the whole call, matching
     * `parses()` (parser.py:120), so markers accumulate across the sources in
     * a single parseSources() and are reported together.
     */
    void beginParse() {
        m_collector.reset(m_factory->mkMarkerCollector());
        m_collector->setMaxErrors(m_max_errors);
        pssp::IAstBuilder *builder = ensureBuilder();
        if (m_enable_profiling) {
            builder->setEnableProfile(true);
        }
        loadStandardLibraryIfNeeded(builder);
    }

    /*
     * Build one source into a fresh GlobalScope and return whether the call
     * has produced an error-severity marker *so far*.
     *
     * Returning the flag rather than throwing is deliberate. The caller has to
     * collect markers before reporting failure (parser.py:106-109) -- a caught
     * ParseException carries them -- and an exception thrown from here would
     * cross the Embind boundary before the TypeScript side could do that.
     * Reporting is TypeScript's job; this reports only the fact.
     */
    bool parseSource(const std::string &content) {
        if (!m_collector) {
            throw std::runtime_error("parseSource() without beginParse()");
        }
        int32_t fileid = static_cast<int32_t>(m_units.size());
        pssp::ast::IGlobalScope *unit = m_ast_factory->mkGlobalScope(fileid);

        std::istringstream in(content);
        m_builder->build(unit, &in);

        if (m_collector->hasSeverity(pssp::MarkerSeverityE::Error)) {
            // The failed unit does not join m_units: parser.py appends to
            // self._files only after the error check (parser.py:111), so a unit
            // that failed to parse is not part of the environment a later parse
            // or a link sees, and does not consume its fileid.
            //
            // Freeing it here is safe, and that is worth stating explicitly
            // because it was got wrong once. AstBuilderInt::build registers a
            // unit in m_prior_units -- the borrowed-pointer list that
            // resolvePathTargetInPriorUnits walks on every cross-unit lookup --
            // but the push at AstBuilderInt.cpp:153 sits *inside* the
            // `if (!m_marker_l->hasSeverity(Error))` guard at :142. A unit
            // whose parse produced an error is therefore never registered, and
            // nothing outlives this call holding a pointer to it.
            //
            // Phase 1 read that guard wrong and retired failed units instead of
            // freeing them, on the theory that the builder still referenced
            // them. It does not. Retiring them was not merely unnecessary: a
            // language server re-parsing on each keystroke fails many times per
            // second, and every failure would have leaked a GlobalScope for the
            // life of the session.
            //
            // Checked, not reasoned: wasm/asan-probe.mjs runs this exact
            // sequence -- fail a parse, churn the heap, then force a cross-unit
            // resolve -- under an ASan build, and reports nothing. The same
            // probe reports a heap-use-after-free within one round if a
            // *successful* unit is freed, which is the case where the pointer
            // really is registered.
            delete unit;
            return true;
        }

        m_units.push_back(unit);
        return false;
    }

    /* The fileid the next parseSource() will assign. */
    int32_t nextFileid() const { return static_cast<int32_t>(m_units.size()); }

    /* Markers accumulated by the current collector, as JSON. */
    std::string markersJson() const {
        std::ostringstream os;
        os << '[';
        if (m_collector) {
            const std::vector<pssp::IMarkerUP> &markers = m_collector->markers();
            for (size_t i = 0; i < markers.size(); i++) {
                const pssp::IMarker *m = markers[i].get();
                if (i) {
                    os << ',';
                }
                os << "{\"severity\":";
                jsonEscape(os, severityName(m->severity()));
                os << ",\"message\":";
                jsonEscape(os, m->msg());
                os << ',';
                emitLocation(os, m->loc());

                os << ",\"related\":[";
                const std::vector<pssp::MarkerRelation> &rel = m->related();
                for (size_t j = 0; j < rel.size(); j++) {
                    if (j) {
                        os << ',';
                    }
                    os << '{';
                    emitLocation(os, rel[j].loc);
                    os << ",\"label\":";
                    jsonEscape(os, rel[j].label);
                    os << '}';
                }
                os << ']';

                // `code` is omitted rather than emitted empty when the core
                // assigned none, so the TypeScript `Marker.code?` is absent
                // rather than "". parser.py:343-344 does the same.
                if (!m->id().empty()) {
                    os << ",\"code\":";
                    jsonEscape(os, m->id());
                }
                os << '}';
            }
        }
        os << ']';
        return os.str();
    }

    bool hasErrors() const {
        return m_collector &&
               m_collector->hasSeverity(pssp::MarkerSeverityE::Error);
    }

    bool maxErrorsExceeded() const {
        return m_collector && m_collector->maxErrorsExceeded();
    }

    /* Units accepted so far, standard library included. */
    int32_t unitCount() const { return static_cast<int32_t>(m_units.size()); }

    /*
     * Serialise one unit and expose the bytes as a view over the WASM heap.
     *
     * A view rather than a return-by-value, because Embind marshals
     * std::string as *text*: it decodes the bytes as UTF-8 on the way out, and
     * this buffer is binary -- every 0x80..0xFF byte in a length prefix or a
     * negative id would be replaced. (markersJson() returns a std::string
     * safely for the opposite reason: it really is UTF-8 text.)
     *
     * The buffer is a member so it outlives the call. The view is only valid
     * until the next serializeUnit() on this session, and the caller must copy
     * it -- ALLOW_MEMORY_GROWTH can also detach it, since growing the heap
     * replaces the underlying ArrayBuffer. Parser.ts copies immediately.
     */
    emscripten::val serializeUnit(int32_t idx) {
        if (idx < 0 || static_cast<size_t>(idx) >= m_units.size()) {
            throw std::runtime_error("serializeUnit(): unit index out of range");
        }
        m_buf = pssp::ast::serializeAst(m_units[idx]);
        return emscripten::val(emscripten::typed_memory_view(
            m_buf.size(), reinterpret_cast<const uint8_t *>(m_buf.data())));
    }

private:
    /*
     * One builder per session, created once and reused.
     *
     * Not an optimisation. The builder accumulates the units it has processed:
     * compile-time expressions are evaluated during AST construction and may
     * reference types and constants declared by a previously-processed unit
     * (PSS 3.1 19.1.2). A builder per parse call would restart that
     * environment, so a second call could not see the first call's constants.
     * Each call still gets a fresh marker collector, because markers are
     * reported per call. (parser.py:59-82.)
     */
    pssp::IAstBuilder *ensureBuilder() {
        if (!m_builder) {
            m_builder = m_factory->mkAstBuilder(m_collector.get());
        } else {
            m_builder->setMarkerListener(m_collector.get());
        }
        // Docstrings first: setCollectComments(true) turns docstring
        // collection on as a side effect, and the reverse order would undo it.
        m_builder->setCollectDocStrings(m_collect_docstrings);
        m_builder->setCollectComments(m_collect_comments);
        return m_builder;
    }

    /*
     * The standard library is unit 0, loaded lazily on first parse.
     *
     * A caller never asks for this and must never have to: both Python parse
     * paths open with `if len(self._files) == 0:` and load the stdlib before
     * touching user input (parser.py:93-97, 127-131). Which is why user
     * fileids start at 1 -- see ts-api-design.md §3.2.6.
     */
    void loadStandardLibraryIfNeeded(pssp::IAstBuilder *builder) {
        if (!m_units.empty()) {
            return;
        }
        pssp::ast::IGlobalScope *stdlib = m_ast_factory->mkGlobalScope(0);
        m_factory->loadStandardLibrary(builder, stdlib);
        m_units.push_back(stdlib);
    }

private:
    pssp::ast::IFactory                 *m_ast_factory;
    pssp::IFactory                      *m_factory;
    pssp::IAstBuilder                   *m_builder;
    pssp::IMarkerCollectorUP            m_collector;
    std::vector<pssp::ast::IGlobalScope *> m_units;
    /** Backing store for the view returned by serializeUnit(). */
    std::string                         m_buf;
    int32_t                             m_max_errors;
    bool                                m_collect_docstrings;
    bool                                m_collect_comments;
    bool                                m_enable_profiling = false;
};

/****************************************************************************
 * The schema hash
 *
 * Reported so the TypeScript loader can compare it against the hash compiled
 * into the generated AST classes and fail loudly on a mismatch
 * (ts-api-design.md §7). A .wasm and a .ts built from different `ast/*.yaml`
 * put fields in different slots, and every downstream symptom of that is
 * baffling; this turns it into one clear startup error.
 ****************************************************************************/
#include "pssparser_schema_hash.h"

std::string schemaHash() { return PSSPARSER_AST_SCHEMA_HASH; }

/*
 * `benchBoundaryOut` lived here through Phase 1. It returned arbitrary bytes so
 * a harness could time the boundary alone, which was a *lower bound* on
 * materialisation cost -- the best available answer to Phase 0 step 5 before a
 * serialiser existed. serializeUnit() measures the real thing now, so it has
 * been removed rather than left as a second, weaker number that a reader would
 * have to know to disregard. wasm/spike.mjs times all three parts instead.
 */

EMSCRIPTEN_BINDINGS(pssparser) {
    emscripten::function("schemaHash", &schemaHash);

    emscripten::class_<ParserSession>("ParserSession")
        .constructor<>()
        .function("setMaxErrors", &ParserSession::setMaxErrors)
        .function("setCollectDocstrings", &ParserSession::setCollectDocstrings)
        .function("setCollectComments", &ParserSession::setCollectComments)
        .function("setEnableProfiling", &ParserSession::setEnableProfiling)
        .function("beginParse", &ParserSession::beginParse)
        .function("parseSource", &ParserSession::parseSource)
        .function("nextFileid", &ParserSession::nextFileid)
        .function("markersJson", &ParserSession::markersJson)
        .function("hasErrors", &ParserSession::hasErrors)
        .function("maxErrorsExceeded", &ParserSession::maxErrorsExceeded)
        .function("unitCount", &ParserSession::unitCount)
        .function("serializeUnit", &ParserSession::serializeUnit);
}
