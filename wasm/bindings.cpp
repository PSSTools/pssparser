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
 * This is the C++ half of `ts-api-design.md` §3: Embind over the core's
 * parse-and-link session (pssp::IParserSession, core-in-leaf-plan.md CF1).
 * The session keeps the lifecycle rules, resolves and sorts markers, and
 * turns escaped exceptions into PSSP000 markers, for every binding alike.
 * What is left here is the WASM-only part: serialising the tree for the
 * TypeScript reader, and JSON for everything else that crosses.
 */

#include <emscripten/bind.h>

#include <algorithm>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "pssp/FactoryExt.h"
#include "pssp/IFactory.h"
#include "pssp/IAstBuilder.h"
#include "pssp/ILinker.h"
#include "pssp/IMarkerCollector.h"
#include "pssp/IParseProfileInfo.h"
#include "pssp/IParserSession.h"
#include "pssp/ast/FactoryExt.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/IScopeChild.h"
#include "pssp/lint/ILintEngine.h"
#include "AstSerializer.h"
#include "pssp/impl/TaskCollectRefTargets.h"

namespace {

/* Sort flat (key, value) int32 pairs by key, in place. */
void sortPairs(std::vector<int32_t> &flat) {
    std::vector<std::pair<int32_t, int32_t>> pairs;
    pairs.reserve(flat.size() / 2);
    for (size_t i = 0; i + 1 < flat.size(); i += 2) {
        pairs.push_back({flat[i], flat[i + 1]});
    }
    std::sort(pairs.begin(), pairs.end());
    for (size_t i = 0; i < pairs.size(); i++) {
        flat[2 * i] = pairs[i].first;
        flat[2 * i + 1] = pairs[i].second;
    }
}

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
    ParserSession() {
        pssp::IFactory *factory = pssparser_getFactory();
        // No debug manager. Every DEBUG_* macro in the core is null-guarded --
        // DEBUG_INIT stores `mgr ? mgr->findDebug(scope) : 0` and the rest test
        // m_dbg before dereferencing (dmgr/impl/DebugMacros.h) -- so passing
        // null disables tracing and costs nothing else. This is what lets the
        // WASM build skip debug_mgr, which ships as a prebuilt host .so with
        // no source to compile for wasm32.
        factory->init(0, ast_getFactory());
        m_session.reset(factory->mkParserSession());
    }

    void setMaxErrors(int32_t n) { m_session->setMaxErrors(n); }
    void setCollectDocstrings(bool c) { m_session->setCollectDocstrings(c); }
    bool getCollectDocstrings() const { return m_session->getCollectDocstrings(); }
    void setCollectComments(bool c) { m_session->setCollectComments(c); }
    bool getCollectComments() const { return m_session->getCollectComments(); }
    void setEnableProfiling(bool e) { m_session->setEnableProfiling(e); }
    void beginParse() { m_session->beginParse(); }

    /*
     * Returns whether the call has produced an error *so far* -- the inverse
     * of IParserSession::parseSource. Returning the flag rather than throwing
     * lets the TypeScript side read the markers before reporting failure.
     */
    bool parseSource(const std::string &name, const std::string &content) {
        return !m_session->parseSource(name, content);
    }

    int32_t nextFileid() const { return m_session->nextFileid(); }

    /* Every marker since clearMarkers(), resolved and sorted by the core:
     * IParserSession::markersJson(), the shape of Marker.ts's `Marker`. */
    std::string markersJson() const { return m_session->markersJson(); }

    /* The last parse or link call's markers, in markersJson()'s shape. */
    std::string callMarkersJson() const { return m_session->callMarkersJson(); }

    void clearMarkers() { m_session->clearMarkers(); }

    bool hasErrors() const { return m_session->hasErrors(); }

    bool maxErrorsExceeded() const { return m_session->maxErrorsExceeded(); }

    /* Units accepted so far, standard library included. */
    int32_t unitCount() const {
        return static_cast<int32_t>(m_session->units().size());
    }

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
        const std::vector<pssp::ast::IGlobalScope *> &units = m_session->units();
        if (idx < 0 || static_cast<size_t>(idx) >= units.size()) {
            throw std::runtime_error("serializeUnit(): unit index out of range");
        }
        m_buf = pssp::ast::serializeAst(units[idx]);
        return emscripten::val(emscripten::typed_memory_view(
            m_buf.size(), reinterpret_cast<const uint8_t *>(m_buf.data())));
    }

    /* Returns whether the link produced an error-severity marker. */
    bool link() { return !m_session->link(); }

    bool hasRoot() const { return m_session->root() != 0; }

    std::string fileMapJson() const { return m_session->fileMapJson(); }

    std::string sourceNamesJson() const { return m_session->sourceNamesJson(); }

    std::string inactiveRegionsJson() const { return m_session->inactiveRegionsJson(); }

    /*
     * Serialise the linked root. Same view-not-copy contract as
     * serializeUnit().
     *
     * The units come with it: RootSymbolScope holds them as
     * `list<UP<GlobalScope>>`, and the serialiser descends through owning
     * pointers, so one buffer carries the whole linked program.
     *
     * Also builds the resolved-reference table refTargets() returns. It has to
     * be built here: it is keyed by the ids this serialisation assigns, and
     * the indexer that holds them is gone once the buffer is taken.
     */
    emscripten::val serializeRoot() {
        pssp::ast::IRootSymbolScope *root = m_session->root();
        if (!root) {
            throw std::runtime_error("serializeRoot(): no root; link() first");
        }
        pssp::ast::IVisitor *indexer = pssp::ast::mkAstIndexer();
        root->accept(indexer);
        pssp::ast::IVisitor *writer = pssp::ast::mkAstWriter(indexer);
        root->accept(writer);

        pssp::TaskCollectRefTargets refs(root);
        const std::vector<pssp::RefTarget> &targets = refs.collect();
        m_refTargets.clear();
        m_refTargets.reserve(2 * targets.size());
        int32_t path_unshipped = 0, target_unshipped = 0;
        for (std::vector<pssp::RefTarget>::const_iterator
                it=targets.begin(); it!=targets.end(); it++) {
            int32_t path_id = pssp::ast::astIdOf(indexer, it->path);
            int32_t target_id = pssp::ast::astIdOf(indexer, it->target);
            if (path_id < 0 || target_id < 0) {
                // Nothing on the other side could name it. A path outside the
                // serialised graph is one the visitor reached through a
                // non-owning edge (template parameter declarations); a target
                // outside it would be a node the tree does not own.
                (path_id < 0) ? path_unshipped++ : target_unshipped++;
                continue;
            }
            m_refTargets.push_back(path_id);
            m_refTargets.push_back(target_id);
        }
        sortPairs(m_refTargets);
        std::string stats = refs.stats().toJson();
        stats.insert(stats.size() - 1,
            ",\"path_unshipped\":" + std::to_string(path_unshipped)
            + ",\"target_unshipped\":" + std::to_string(target_unshipped));
        m_refTargetStats = stats;

        m_buf = pssp::ast::takeAstBuffer(indexer, writer);
        return emscripten::val(emscripten::typed_memory_view(
            m_buf.size(), reinterpret_cast<const uint8_t *>(m_buf.data())));
    }

    /*
     * The resolved references of the last serializeRoot(), as flat
     * (path id, target id) pairs sorted by path id: for each SymbolRefPath in
     * the buffer, the node TaskResolveSymbolPathRef resolves it to
     * (docs/design/rust-binding.md §1a). A path with no entry did not
     * resolve. Same view-not-copy contract as serializeRoot().
     */
    emscripten::val refTargets() const {
        return emscripten::val(emscripten::typed_memory_view(
            m_refTargets.size(), m_refTargets.data()));
    }

    /* Counts from the last serializeRoot()'s reference table, as JSON. */
    std::string refTargetStatsJson() const { return m_refTargetStats; }

    /*
     * Profiling data from the last parse as JSON, or "" if there is none --
     * "" rather than "null" so the TypeScript side has one cheap test. There
     * is none after link(), which drops the builder that holds it.
     */
    std::string profileInfoJson() { return m_session->profileInfoJson(); }

    /*
     * The session's lint engine, as JSON: {"rule_format_version":N,
     * "rule_sets":N}. Created on first use and kept for the session's life,
     * so rules loaded once (C4.3) serve every later runLint (C5.4).
     */
    std::string lintEngineInfoJson() {
        pssp::lint::ILintEngine *e = m_session->lintEngine();
        std::ostringstream out;
        out << "{\"rule_format_version\":" << e->ruleFormatVersion()
            << ",\"rule_sets\":" << e->numRuleSets() << "}";
        return out.str();
    }

    /*
     * Loads one rule file into the session's engine (lint-core-plan.md C4.3).
     * Returns false when the file as a whole was refused; the reasons, and
     * any bad rules left out, are in ruleDiagnosticsJson().
     */
    bool loadRuleFile(const std::string &name, const std::string &text) {
        pssp::lint::LintSource src;
        src.name = name;
        src.text = text;
        return m_session->lintEngine()->loadRules(src, false) != nullptr;
    }

    /*
     * Whether `text` is a rule file, for a host listing a directory:
     * "rule-file", "empty", "not-yaml", "not-mapping" or "no-key".
     */
    std::string probeRules(const std::string &text) {
        switch (m_session->lintEngine()->probeRules(text)) {
        case pssp::lint::RuleProbe::RuleFile:   return "rule-file";
        case pssp::lint::RuleProbe::Empty:      return "empty";
        case pssp::lint::RuleProbe::NotYaml:    return "not-yaml";
        case pssp::lint::RuleProbe::NotMapping: return "not-mapping";
        case pssp::lint::RuleProbe::NoKey:      break;
        }
        return "no-key";
    }

    /* Every rule-file diagnostic of the session, built-in files included. */
    std::string ruleDiagnosticsJson() {
        return m_session->lintEngine()->diagnosticsJson();
    }

    /* Every rule loaded in the session, built-in rules first. */
    std::string rulesJson() {
        return m_session->lintEngine()->rulesJson();
    }

    /*
     * Runs the session's rules over the linked model's user files
     * (lint-core-plan.md C5.4). The request and result are ILintEngine::run()'s
     * JSON; markers carry fileids. Before link() there is no model, and the
     * result has no markers.
     */
    std::string runLint(const std::string &requestJson) {
        return m_session->lintEngine()->run(userRoots(), requestJson, m_session->root());
    }

    /*
     * Collects the source waivers (lint-core-plan.md C7.2): comments in the
     * request's texts, annotations in the linked model's user files.
     */
    std::string collectWaivers(const std::string &requestJson) {
        return m_session->lintEngine()->collectWaivers(userRoots(), requestJson);
    }

    /* Applies waivers to diagnostics: ILintEngine::applyWaivers()'s JSON (C7.2). */
    std::string applyWaivers(const std::string &requestJson) {
        return m_session->lintEngine()->applyWaivers(requestJson);
    }

    /* Finishes diagnostics as the CLI does before printing them (C7.4). */
    std::string finishDiagnostics(const std::string &requestJson) {
        return m_session->lintEngine()->finish(requestJson);
    }

    /* The host's own markers for selection (C7.1). Returns the problems. */
    std::string setHostMarkers(const std::string &json) {
        return m_session->lintEngine()->setHostMarkers(json);
    }

    /* The marker catalogue (C7.3), for hover, `codeDescription` and quick-info. */
    std::string catalogJson() {
        return m_session->lintEngine()->catalogJson();
    }

    /*
     * The core library's files, as IFactory::getCoreLibrarySources(): a JSON
     * array of {name, firstLine, numLines, text}. The library is unit 0, and
     * each file has its own band of that unit's lines.
     */
    std::string coreLibrarySourcesJson() {
        std::ostringstream os;
        os << "[";
        const pssp::CoreLibrarySource *f = pssparser_getFactory()->getCoreLibrarySources();
        for (int32_t i=0; f[i].name; i++) {
            os << ((i)?",":"") << "{\"name\":";
            jsonEscape(os, f[i].name);
            os << ",\"firstLine\":" << f[i].first_line
               << ",\"numLines\":" << f[i].num_lines
               << ",\"text\":";
            jsonEscape(os, f[i].text);
            os << "}";
        }
        os << "]";
        return os.str();
    }

    /* Resolves a rule selection: ILintEngine::resolveSelection()'s JSON (C7.1). */
    std::string resolveSelection(const std::string &json) {
        return m_session->lintEngine()->resolveSelection(json);
    }

private:
    /* The user files' units, as the lint engine's roots. */
    std::vector<pssp::ast::IScopeChild *> userRoots() {
        std::vector<pssp::ast::IScopeChild *> roots;
        for (pssp::ast::IGlobalScope *u : m_session->userUnits()) {
            roots.push_back(dynamic_cast<pssp::ast::IScopeChild *>(u));
        }
        return roots;
    }

private:
    pssp::IParserSessionUP              m_session;
    /** Backing store for the views serializeUnit()/serializeRoot() return. */
    std::string                         m_buf;
    std::vector<int32_t>                m_refTargets;
    std::string                         m_refTargetStats;
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

/****************************************************************************
 * Lint engine test hooks -- PRIVATE (lint-core-plan.md §5)
 *
 * The same entry points the Cython module exposes as LintTestHooks, so the
 * parity tests can feed both builds the same input and compare the JSON text.
 * Underscore-prefixed: not part of the TypeScript API.
 ****************************************************************************/
static pssp::lint::ILintTestHooks *lintTestHooks() {
    static std::unique_ptr<pssp::lint::ILintTestHooks> hooks(
        pssparser_getFactory()->mkLintTestHooks());
    return hooks.get();
}

std::string lintYamlLoad(const std::string &name, const std::string &text) {
    return lintTestHooks()->yamlLoad(name, text);
}

std::string lintYamlSourceMaps(const std::string &name, const std::string &text) {
    return lintTestHooks()->yamlSourceMaps(name, text);
}

std::string lintYamlCelParse(const std::string &name, const std::string &text,
                             const std::string &key) {
    return lintTestHooks()->yamlCelParse(name, text, key);
}

std::string lintReflectSchema() {
    return lintTestHooks()->reflectSchema();
}

std::string lintCelParse(const std::string &text) {
    return lintTestHooks()->celParse(text);
}

std::string lintCelEval(const std::string &text, const std::string &bindings, double max_steps) {
    return lintTestHooks()->celEval(text, bindings, static_cast<uint64_t>(max_steps));
}

std::string lintCelFunctions() {
    return lintTestHooks()->celFunctions();
}

std::string lintCelCheck(const std::string &name, const std::string &text) {
    return lintTestHooks()->celCheck(name, text);
}

std::string lintRegexSearch(const std::string &pattern, const std::string &text) {
    return lintTestHooks()->regexSearch(pattern, text);
}

std::string lintRuleLoad(const std::string &name, const std::string &text, int builtin) {
    return lintTestHooks()->ruleLoad(name, text, builtin != 0);
}

EMSCRIPTEN_BINDINGS(pssparser) {
    emscripten::function("schemaHash", &schemaHash);
    emscripten::function("_lintYamlLoad", &lintYamlLoad);
    emscripten::function("_lintYamlSourceMaps", &lintYamlSourceMaps);
    emscripten::function("_lintYamlCelParse", &lintYamlCelParse);
    emscripten::function("_lintReflectSchema", &lintReflectSchema);
    emscripten::function("_lintCelParse", &lintCelParse);
    emscripten::function("_lintCelEval", &lintCelEval);
    emscripten::function("_lintCelFunctions", &lintCelFunctions);
    emscripten::function("_lintCelCheck", &lintCelCheck);
    emscripten::function("_lintRegexSearch", &lintRegexSearch);
    emscripten::function("_lintRuleLoad", &lintRuleLoad);

    emscripten::class_<ParserSession>("ParserSession")
        .constructor<>()
        .function("setMaxErrors", &ParserSession::setMaxErrors)
        .function("setCollectDocstrings", &ParserSession::setCollectDocstrings)
        .function("getCollectDocstrings", &ParserSession::getCollectDocstrings)
        .function("setCollectComments", &ParserSession::setCollectComments)
        .function("getCollectComments", &ParserSession::getCollectComments)
        .function("setEnableProfiling", &ParserSession::setEnableProfiling)
        .function("beginParse", &ParserSession::beginParse)
        .function("parseSource", &ParserSession::parseSource)
        .function("nextFileid", &ParserSession::nextFileid)
        .function("markersJson", &ParserSession::markersJson)
        .function("callMarkersJson", &ParserSession::callMarkersJson)
        .function("clearMarkers", &ParserSession::clearMarkers)
        .function("hasErrors", &ParserSession::hasErrors)
        .function("maxErrorsExceeded", &ParserSession::maxErrorsExceeded)
        .function("unitCount", &ParserSession::unitCount)
        .function("serializeUnit", &ParserSession::serializeUnit)
        .function("link", &ParserSession::link)
        .function("hasRoot", &ParserSession::hasRoot)
        .function("fileMapJson", &ParserSession::fileMapJson)
        .function("sourceNamesJson", &ParserSession::sourceNamesJson)
        .function("inactiveRegionsJson", &ParserSession::inactiveRegionsJson)
        .function("serializeRoot", &ParserSession::serializeRoot)
        .function("refTargets", &ParserSession::refTargets)
        .function("refTargetStatsJson", &ParserSession::refTargetStatsJson)
        .function("profileInfoJson", &ParserSession::profileInfoJson)
        .function("lintEngineInfoJson", &ParserSession::lintEngineInfoJson)
        .function("loadRuleFile", &ParserSession::loadRuleFile)
        .function("probeRules", &ParserSession::probeRules)
        .function("ruleDiagnosticsJson", &ParserSession::ruleDiagnosticsJson)
        .function("rulesJson", &ParserSession::rulesJson)
        .function("runLint", &ParserSession::runLint)
        .function("setHostMarkers", &ParserSession::setHostMarkers)
        .function("resolveSelection", &ParserSession::resolveSelection)
        .function("collectWaivers", &ParserSession::collectWaivers)
        .function("applyWaivers", &ParserSession::applyWaivers)
        .function("finishDiagnostics", &ParserSession::finishDiagnostics)
        .function("catalogJson", &ParserSession::catalogJson)
        .function("coreLibrarySourcesJson", &ParserSession::coreLibrarySourcesJson);
}
