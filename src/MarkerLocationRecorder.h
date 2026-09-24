/**
 * MarkerLocationRecorder.h
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
 */
#pragma once
#include <set>
#include <tuple>
#include "pssp/IMarkerListener.h"

namespace pssp {

/**
 * Forwards every marker to another listener, and remembers where each error
 * was reported.
 *
 * The linker's passes each make their own ResolveContext, and a context
 * remembers only its own reports (ResolveContext::wasReported). The
 * completeness gate needs to know about all of them -- an `extend` of an
 * unknown type is reported by TaskApplyTypeExtensions, long before the gate's
 * context exists -- so AstLinker hands every pass this listener instead.
 */
class MarkerLocationRecorder : public virtual IMarkerListener {
public:
    MarkerLocationRecorder(IMarkerListener *next) : m_next(next) { }

    virtual ~MarkerLocationRecorder() { }

    virtual void marker(const IMarker *m) override {
        const ast::Location &loc = m->loc();
        std::tuple<int32_t,int32_t,int32_t> key =
            std::make_tuple(loc.fileid, loc.lineno, loc.linepos);
        if (m->severity() == MarkerSeverityE::Error) {
            m_errors.insert(key);
        }
        m_any.insert(key);
        m_next->marker(m);
    }

    virtual bool hasSeverity(MarkerSeverityE s) override {
        return m_next->hasSeverity(s);
    }

    /** An error was reported at `loc`. */
    bool wasReported(const ast::Location &loc) const {
        return m_errors.find(std::make_tuple(
            loc.fileid, loc.lineno, loc.linepos)) != m_errors.end();
    }

    /** A marker of any severity was reported at `loc`. */
    bool wasNoted(const ast::Location &loc) const {
        return m_any.find(std::make_tuple(
            loc.fileid, loc.lineno, loc.linepos)) != m_any.end();
    }

private:
    IMarkerListener                                 *m_next;
    std::set<std::tuple<int32_t,int32_t,int32_t>>   m_errors;
    std::set<std::tuple<int32_t,int32_t,int32_t>>   m_any;
};

}
