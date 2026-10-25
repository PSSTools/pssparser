/****************************************************************************
 * ParserSessionJson.cpp -- the session's results as JSON
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
 * The JSON forms every non-C++ binding reads: the WASM build crosses to
 * TypeScript with them, and the C ABI (pssparser_c.h) hands them to Rust.
 * One copy, here, so the two cannot drift. Hand-rolled rather than pulled
 * in from a library: the shapes are small and fixed (ts-api-design.md §5),
 * and a dependency would have to be built for wasm32 as well as the host.
 */
#include <sstream>
#include <stdexcept>
#include "pssp/IParseProfileInfo.h"
#include "ParserSession.h"

namespace pssp {

namespace {

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


const char *severityName(MarkerSeverityE s) {
    switch (s) {
        case MarkerSeverityE::Error: return "error";
        case MarkerSeverityE::Warn:  return "warning";
        case MarkerSeverityE::Info:  return "info";
        case MarkerSeverityE::Hint:  return "hint";
        default: break;
    }
    // No "unknown": a reader forced to handle that case is handling a core
    // bug rather than a source condition (ts-api-design.md §5). Throwing
    // turns it into one clear failure instead.
    throw std::runtime_error("unrecognised MarkerSeverityE in a session marker");
}

/****************************************************************************
 * Profiling
 *
 * `IParseProfileInfo` is a diagnostic aid, not part of the AST, so it crosses
 * as JSON rather than through the serialiser: the shape is small, it is read
 * once by a human or a report script, and `ts-api-design.md` §9 Q4 keeps it
 * deliberately untyped on the TypeScript side so that changing what the
 * profiler reports is not a breaking API change.
 *
 * Decisions with no invocations are omitted. ANTLR reports every decision in
 * the ATN -- some 800 for this grammar -- and the ones never reached during a
 * parse carry nothing but zeroes. The *totals* are computed by
 * `ParseProfileInfo` over the full set, so dropping the empty entries here
 * costs no information.
 ****************************************************************************/
void emitEvent(std::ostream &os, IDecisionEventInfo *ev) {
    os << "{\"kind\":";
    jsonEscape(os, ev->getKindName());
    os << ",\"startLine\":" << ev->getStartLine()
       << ",\"startColumn\":" << ev->getStartColumn()
       << ",\"stopLine\":" << ev->getStopLine()
       << ",\"stopColumn\":" << ev->getStopColumn()
       << ",\"tokenCount\":" << ev->getTokenCount()
       << ",\"text\":";
    jsonEscape(os, ev->getText());
    os << '}';
}

void emitDecision(std::ostream &os, IDecisionProfileInfo *d) {
    os << "{\"decision\":" << d->getDecision()
       << ",\"ruleIndex\":" << d->getRuleIndex()
       << ",\"ruleName\":";
    jsonEscape(os, d->getRuleName());
    os << ",\"invocations\":" << d->getInvocations()
       << ",\"timeInPrediction\":" << d->getTimeInPrediction()
       << ",\"sllLookaheadOps\":" << d->getSLLLookaheadOps()
       << ",\"llLookaheadOps\":" << d->getLLLookaheadOps()
       << ",\"sllATNTransitions\":" << d->getSLLATNTransitions()
       << ",\"llATNTransitions\":" << d->getLLATNTransitions()
       << ",\"llFallback\":" << d->getLLFallback()
       << ",\"ambiguityCount\":" << d->getAmbiguityCount()
       << ",\"contextSensitivityCount\":" << d->getContextSensitivityCount()
       << ",\"errorCount\":" << d->getErrorCount()
       << ",\"predicateEvalCount\":" << d->getPredicateEvalCount()
       << ",\"sllMinLookahead\":" << d->getSLLMinLookahead()
       << ",\"sllMaxLookahead\":" << d->getSLLMaxLookahead()
       << ",\"llMinLookahead\":" << d->getLLMinLookahead()
       << ",\"llMaxLookahead\":" << d->getLLMaxLookahead()
       << ",\"events\":[";
    for (size_t i = 0; i < d->getNumEvents(); i++) {
        if (i) {
            os << ',';
        }
        emitEvent(os, d->getEvent(i));
    }
    os << "]}";
}

std::string profileJson(IParseProfileInfo *info) {
    std::ostringstream os;
    os << "{\"totalTimeInPrediction\":" << info->getTotalTimeInPrediction()
       << ",\"totalSLLLookaheadOps\":" << info->getTotalSLLLookaheadOps()
       << ",\"totalLLLookaheadOps\":" << info->getTotalLLLookaheadOps()
       << ",\"totalSLLATNLookaheadOps\":" << info->getTotalSLLATNLookaheadOps()
       << ",\"totalLLATNLookaheadOps\":" << info->getTotalLLATNLookaheadOps()
       << ",\"totalATNLookaheadOps\":" << info->getTotalATNLookaheadOps()
       << ",\"dfaSize\":" << info->getDFASize()
       << ",\"tokenCount\":" << info->getTokenCount()
       << ",\"llDecisions\":[";
    const std::vector<size_t> ll = info->getLLDecisions();
    for (size_t i = 0; i < ll.size(); i++) {
        if (i) {
            os << ',';
        }
        os << ll[i];
    }
    os << "],\"decisions\":[";
    bool first = true;
    for (IDecisionProfileInfo *d : info->getDecisionInfo()) {
        if (!d->getInvocations()) {
            continue;
        }
        if (!first) {
            os << ',';
        }
        first = false;
        emitDecision(os, d);
    }
    os << "]}";
    return os.str();
}

} // namespace

static std::string markersToJson(const std::vector<SessionMarker> &markers) {
    std::ostringstream os;
    os << '[';
    for (size_t i = 0; i < markers.size(); i++) {
        const SessionMarker &m = markers[i];
        if (i) {
            os << ',';
        }
        os << "{\"severity\":";
        jsonEscape(os, severityName(m.severity));
        os << ",\"message\":";
        jsonEscape(os, m.message);
        os << ",\"file\":";
        jsonEscape(os, m.file);
        // `extent` is passed through raw, including the -1 that Location.h
        // defaults it to: clamping it would invent information the core did
        // not supply.
        os << ",\"line\":" << m.line
           << ",\"col\":" << m.col
           << ",\"extent\":" << m.extent;

        os << ",\"related\":[";
        for (size_t j = 0; j < m.related.size(); j++) {
            const SessionMarkerRelation &r = m.related[j];
            if (j) {
                os << ',';
            }
            os << "{\"file\":";
            jsonEscape(os, r.file);
            os << ",\"line\":" << r.line << ",\"col\":" << r.col
               << ",\"label\":";
            jsonEscape(os, r.label);
            os << '}';
        }
        os << ']';

        // `code` is omitted rather than emitted empty when the core assigned
        // none, so a reader's optional `code` is absent rather than "".
        if (!m.code.empty()) {
            os << ",\"code\":";
            jsonEscape(os, m.code);
        }
        if (m.has_fix) {
            os << ",\"fix\":{\"file\":";
            jsonEscape(os, m.fix.file);
            os << ",\"line\":" << m.fix.line << ",\"col\":" << m.fix.col
               << ",\"extent\":" << m.fix.extent << ",\"replacement\":";
            jsonEscape(os, m.fix.replacement);
            os << '}';
        }
        os << '}';
    }
    os << ']';
    return os.str();
}

std::string ParserSession::markersJson() const {
    return markersToJson(m_markers);
}

std::string ParserSession::callMarkersJson() const {
    return markersToJson(m_call_markers);
}

static std::string namesJson(const std::map<int32_t, std::string> &names) {
    std::ostringstream os;
    os << '{';
    bool first = true;
    for (const std::pair<const int32_t, std::string> &e : names) {
        os << (first ? "" : ",") << '"' << e.first << "\":";
        jsonEscape(os, e.second);
        first = false;
    }
    os << '}';
    return os.str();
}

std::string ParserSession::fileMapJson() const {
    return namesJson(m_file_map);
}

std::string ParserSession::sourceNamesJson() const {
    return namesJson(m_names);
}

std::string ParserSession::inactiveRegionsJson() const {
    std::ostringstream os;
    os << '[';
    const std::vector<ast::SourceRange> regions = inactiveRegions();
    for (size_t i = 0; i < regions.size(); i++) {
        const ast::SourceRange &r = regions[i];
        os << (i ? "," : "")
           << "{\"fileid\":" << r.fileid
           << ",\"startLine\":" << r.start_line
           << ",\"startCol\":" << r.start_col
           << ",\"endLine\":" << r.end_line
           << ",\"endCol\":" << r.end_col << '}';
    }
    os << ']';
    return os.str();
}

std::string ParserSession::profileInfoJson() {
    IParseProfileInfoUP info(profileInfo());
    if (!info) {
        return "";
    }
    return profileJson(info.get());
}

}
