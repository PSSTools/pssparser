/****************************************************************************
 * ParserSession.cpp
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
#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <tuple>
#include "pssp/ILinker.h"
#include "pssp/ast/IScope.h"
#include "pssp/ast/IScopeChild.h"
#include "pssp/ast/ICompileCond.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/InternalError.h"
#include "Marker.h"
#include "ParserSession.h"

namespace pssp {

ParserSession::ParserSession(IFactory *factory) :
        m_factory(factory), m_ast_factory(factory->getAstFactory()) {
}

ParserSession::~ParserSession() {
    // Units the linker never took are ours to free. After link() the vector
    // is empty, because ownership moved into the root.
    for (size_t i=m_released; i<m_units.size(); i++) {
        delete m_units[i];
    }
    if (m_root_owned) {
        delete m_root;
    }
    delete m_builder;
}

void ParserSession::beginCall() {
    m_collector.reset(m_factory->mkMarkerCollector());
    m_collector->setMaxErrors(m_max_errors);
    m_absorbed = 0;
    m_call_markers.clear();
}

void ParserSession::beginParse() {
    beginCall();
    IAstBuilder *builder = ensureBuilder();
    // Set unconditionally: the builder outlives the call, and setting it only
    // when true could never turn profiling back off.
    builder->setEnableProfile(m_enable_profiling);
    try {
        loadStandardLibraryIfNeeded(builder);
    } catch (const std::exception &e) {
        internalError("while loading the core library", e.what(), 0);
    }
    absorbMarkers();
}

bool ParserSession::parseSource(
        const std::string       &name,
        const std::string       &text) {
    if (!m_collector) {
        throw std::runtime_error("parseSource() without beginParse()");
    }
    int32_t fileid = nextFileid();
    // Recorded before the parse: the markers it emits carry the fileid, and
    // resolving them needs the name.
    m_names[fileid] = name;
    ast::IGlobalScope *unit = m_ast_factory->mkGlobalScope(fileid);

    try {
        std::istringstream in(text);
        m_builder->build(unit, &in);
    } catch (const std::exception &e) {
        internalError("while parsing", e.what(), fileid);
    } catch (...) {
        internalError("while parsing", "unknown exception", fileid);
    }

    absorbMarkers();

    if (m_collector->hasSeverity(MarkerSeverityE::Error)) {
        // The failed unit does not join m_units and does not consume its
        // fileid. Freeing it is safe: the builder registers a unit as part of
        // its compile-time environment only when the unit parsed without
        // error (AstBuilderInt::build), so nothing holds a pointer to it.
        // wasm/asan-probe.mjs checks this under ASan.
        delete unit;
        return false;
    }

    m_units.push_back(unit);
    return true;
}

bool ParserSession::link() {
    beginCall();

    ast::IRootSymbolScope *root = 0;
    try {
        ILinkerUP linker(m_factory->mkAstLinker());
        root = linker->link(m_collector.get(), m_units);
    } catch (const std::exception &e) {
        internalError("while linking", e.what(), -1);
    } catch (...) {
        internalError("while linking", "unknown exception", -1);
    }

    // Resolved while m_names still holds the fileids the link saw.
    absorbMarkers();

    // The root is recorded whether or not the link failed: the units are
    // already its, and a caller that catches the failure still needs them.
    // AstLinker::link has one return and reports errors only as markers.
    if (m_root_owned) {
        delete m_root;
    }
    m_root = root;
    m_root_owned = true;

    // Cleared, not freed: link(..., own_scopes) gave them to the root. (If
    // the link threw, where they went is unknown, and leaking them is the
    // safe choice.)
    m_units.clear();
    m_released = 0;

    // The next parse restarts the unit list, so fileid 1 will name another
    // file. The snapshot keeps this link's names.
    m_file_map = m_names;
    m_names.clear();

    // The builder holds the units as borrowed pointers -- its compile-time
    // environment -- and they are the root's now. A later link() replaces the
    // root and frees them; a parse after that would read freed memory.
    delete m_builder;
    m_builder = 0;

    return !m_collector->hasSeverity(MarkerSeverityE::Error);
}

ast::IRootSymbolScope *ParserSession::releaseRoot() {
    m_root_owned = false;
    return m_root;
}

std::vector<ast::IGlobalScope *> ParserSession::userUnits() const {
    std::vector<ast::IGlobalScope *> ret;
    if (m_root) {
        for (const ast::IGlobalScopeUP &u : m_root->getUnits()) {
            if (m_file_map.find(u->getFileid()) != m_file_map.end()) {
                ret.push_back(u.get());
            }
        }
    }
    return ret;
}

std::string ParserSession::pathOf(int32_t fileid) const {
    // The live names win: after a link() the next parse reuses the fileids
    // for other files. The snapshot still resolves a marker from before it.
    std::map<int32_t, std::string>::const_iterator it = m_names.find(fileid);
    if (it != m_names.end()) {
        return it->second;
    }
    it = m_file_map.find(fileid);
    if (it != m_file_map.end()) {
        return it->second;
    }
    if (fileid == -1) {
        return FILE_BUILTIN;
    }
    return FILE_UNKNOWN;
}

SessionLocation ParserSession::resolveLocation(int32_t fileid, int32_t line) const {
    SessionLocation ret;
    if (fileid == 0) {
        const CoreLibrarySource *f = m_factory->getCoreLibrarySources();
        for (int32_t i=0; f[i].name; i++) {
            if (line >= f[i].first_line && line < f[i].first_line + f[i].num_lines) {
                ret.file = std::string(FILE_STDLIB_PREFIX) + f[i].name;
                ret.line = line - f[i].first_line + 1;
                return ret;
            }
        }
        ret.file = FILE_STDLIB;
        ret.line = line;
        return ret;
    }
    ret.file = pathOf(fileid);
    ret.line = line;
    return ret;
}

void ParserSession::absorbMarkers() {
    const std::vector<IMarkerUP> &markers = m_collector->markers();
    if (m_absorbed == markers.size()) {
        return;
    }

    std::vector<SessionMarker> fresh;
    for (; m_absorbed<markers.size(); m_absorbed++) {
        const IMarker *m = markers[m_absorbed].get();
        SessionMarker sm;
        sm.severity = m->severity();
        sm.message = m->msg();
        sm.code = m->id();
        sm.fileid = m->loc().fileid;
        sm.raw_line = m->loc().lineno;
        SessionLocation at = resolveLocation(m->loc().fileid, m->loc().lineno);
        sm.file = at.file;
        sm.line = at.line;
        // `linepos` is already 1-based (the invariant in ast/coretypes.yaml).
        sm.col = m->loc().linepos;
        sm.extent = m->loc().extent;
        if (sm.code == INTERNAL_ERROR_ID && sm.fileid < 0) {
            // An internal error with no source location is a tool-level
            // diagnostic, not one at "<builtin>:-1".
            sm.file = FILE_TOOL;
        }
        for (const MarkerRelation &r : m->related()) {
            SessionLocation rat = resolveLocation(r.loc.fileid, r.loc.lineno);
            SessionMarkerRelation sr;
            sr.file = rat.file;
            sr.line = rat.line;
            sr.col = r.loc.linepos;
            sr.label = r.label;
            sm.related.push_back(sr);
        }
        if (!m->fixes().empty()) {
            // Its span is its own: an insertion has extent 0, which the
            // diagnostic's span never does.
            const MarkerFix &f = m->fixes()[0];
            SessionLocation fat = resolveLocation(f.span.fileid, f.span.lineno);
            sm.has_fix = true;
            sm.fix.file = fat.file;
            sm.fix.line = fat.line;
            sm.fix.col = f.span.linepos;
            sm.fix.extent = f.span.extent;
            sm.fix.replacement = f.replacement;
        }
        fresh.push_back(sm);
    }

    // Stable, by the resolved *name*: the fileid order and the name order
    // are not the same order. Different passes emit in their own encounter
    // order, and markers that share a location keep their emission order, so
    // a cascade at one point still reads as one. Merging two sorted lists
    // does not give a sorted list, which is why the whole of each is
    // re-sorted.
    struct Before {
        bool operator()(const SessionMarker &a, const SessionMarker &b) const {
            return std::tie(a.file, a.line, a.col) < std::tie(b.file, b.line, b.col);
        }
    };
    m_call_markers.insert(m_call_markers.end(), fresh.begin(), fresh.end());
    std::stable_sort(m_call_markers.begin(), m_call_markers.end(), Before());
    m_markers.insert(m_markers.end(), fresh.begin(), fresh.end());
    std::stable_sort(m_markers.begin(), m_markers.end(), Before());
}

void ParserSession::internalError(
        const char              *phase,
        const std::string       &what,
        int32_t                 fileid) {
    ast::Location loc;
    loc.fileid = fileid;
    // A file's internal error points at its start; one with no file has no
    // location at all.
    loc.lineno = (fileid >= 0) ? 0 : -1;
    loc.linepos = (fileid >= 0) ? 0 : -1;
    loc.extent = 0;
    Marker m(
        std::string("internal error ") + phase + ": " + what + "; please report this",
        MarkerSeverityE::Error,
        loc,
        INTERNAL_ERROR_ID);
    m_collector->marker(&m);
}

bool ParserSession::hasErrors() const {
    return m_collector && m_collector->hasSeverity(MarkerSeverityE::Error);
}

bool ParserSession::maxErrorsExceeded() const {
    return m_collector && m_collector->maxErrorsExceeded();
}

namespace {

class InactiveRegionCollector : public ast::VisitorBase {
public:
    InactiveRegionCollector(std::vector<ast::SourceRange> &out) : m_out(out) { }

    virtual void visitScope(ast::IScope *i) override {
        for (const ast::ICompileCondUP &c : i->getCompile_conds()) {
            for (const ast::SourceRange &r : c->getInactive()) {
                m_out.push_back(r);
            }
        }
        VisitorBase::visitScope(i);
    }

private:
    std::vector<ast::SourceRange> &m_out;
};

}

std::vector<ast::SourceRange> ParserSession::inactiveRegions() const {
    std::vector<ast::SourceRange> ret;
    InactiveRegionCollector v(ret);
    for (ast::IGlobalScope *u : userUnits()) {
        u->accept(&v);
    }
    std::sort(ret.begin(), ret.end(),
        [](const ast::SourceRange &a, const ast::SourceRange &b) {
            return std::tie(a.fileid, a.start_line, a.start_col, a.end_line, a.end_col)
                < std::tie(b.fileid, b.start_line, b.start_col, b.end_line, b.end_col);
        });
    return ret;
}

IParseProfileInfo *ParserSession::profileInfo() {
    // None after link(), which drops the builder that holds it: the answer is
    // honestly nothing rather than the profile of a released builder.
    if (!m_builder) {
        return 0;
    }
    return m_builder->getProfileInfo();
}

lint::ILintEngine *ParserSession::lintEngine() {
    if (!m_lint) {
        m_lint.reset(m_factory->mkLintEngine());
        m_lint->loadBuiltinRules();
    }
    return m_lint.get();
}

IAstBuilder *ParserSession::ensureBuilder() {
    // One builder per session, reused: compile-time expressions may
    // reference types and constants of an earlier unit (PSS 3.1 19.1.2), and
    // a builder per call would restart that environment.
    if (!m_builder) {
        m_builder = m_factory->mkAstBuilder(m_collector.get());
    } else {
        m_builder->setMarkerListener(m_collector.get());
    }
    // Re-applied on every call, because link() drops the builder. Docstrings
    // first: setCollectComments(true) turns docstring collection on as a side
    // effect, and the reverse order would undo it.
    m_builder->setCollectDocStrings(m_collect_docstrings);
    m_builder->setCollectComments(m_collect_comments);
    return m_builder;
}

void ParserSession::loadStandardLibraryIfNeeded(IAstBuilder *builder) {
    if (!m_units.empty()) {
        return;
    }
    ast::IGlobalScope *stdlib = m_ast_factory->mkGlobalScope(0);
    m_factory->loadStandardLibrary(builder, stdlib);
    m_units.push_back(stdlib);
}

}

