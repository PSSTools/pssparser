/****************************************************************************
 * ParserSession.h
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
#include "pssp/IAstBuilder.h"
#include "pssp/IFactory.h"
#include "pssp/IMarkerCollector.h"
#include "pssp/IParserSession.h"
#include "pssp/lint/ILintEngine.h"

namespace pssp {

class ParserSession : public virtual IParserSession {
public:
    ParserSession(IFactory *factory);

    virtual ~ParserSession();

    virtual void setMaxErrors(int32_t n) override { m_max_errors = n; }

    virtual void setCollectDocstrings(bool c) override { m_collect_docstrings = c; }

    virtual bool getCollectDocstrings() const override { return m_collect_docstrings; }

    virtual void setCollectComments(bool c) override { m_collect_comments = c; }

    virtual bool getCollectComments() const override { return m_collect_comments; }

    virtual void setEnableProfiling(bool e) override { m_enable_profiling = e; }

    virtual void beginParse() override;

    virtual bool parseSource(
        const std::string       &name,
        const std::string       &text) override;

    virtual int32_t nextFileid() const override {
        return static_cast<int32_t>(m_units.size());
    }

    virtual const std::vector<ast::IGlobalScope *> &units() const override {
        return m_units;
    }

    virtual void releaseUnits() override { m_released = m_units.size(); }

    virtual bool link() override;

    virtual ast::IRootSymbolScope *root() const override { return m_root; }

    virtual ast::IRootSymbolScope *releaseRoot() override;

    virtual std::vector<ast::IGlobalScope *> userUnits() const override;

    virtual const std::map<int32_t, std::string> &sourceNames() const override {
        return m_names;
    }

    virtual const std::map<int32_t, std::string> &fileMap() const override {
        return m_file_map;
    }

    virtual SessionLocation resolveLocation(int32_t fileid, int32_t line) const override;

    virtual const std::vector<SessionMarker> &markers() const override {
        return m_markers;
    }

    virtual const std::vector<SessionMarker> &callMarkers() const override {
        return m_call_markers;
    }

    virtual void clearMarkers() override { m_markers.clear(); }

    virtual bool hasErrors() const override;

    virtual bool maxErrorsExceeded() const override;

    virtual std::vector<ast::SourceRange> inactiveRegions() const override;

    virtual IParseProfileInfo *profileInfo() override;

    virtual lint::ILintEngine *lintEngine() override;

private:
    /** Open a call: a fresh collector, and no call markers yet. */
    void beginCall();

    /** Resolve the collector's markers not yet taken, and merge them in. */
    void absorbMarkers();

    /** Report an exception that reached the session as a PSSP000 marker. */
    void internalError(
        const char              *phase,
        const std::string       &what,
        int32_t                 fileid);

    std::string pathOf(int32_t fileid) const;

    IAstBuilder *ensureBuilder();

    void loadStandardLibraryIfNeeded(IAstBuilder *builder);

private:
    IFactory                            *m_factory;
    ast::IFactory                       *m_ast_factory;
    IAstBuilder                         *m_builder = 0;
    IMarkerCollectorUP                  m_collector;
    /** How many of m_collector's markers absorbMarkers() has taken. */
    size_t                              m_absorbed = 0;
    std::vector<ast::IGlobalScope *>    m_units;
    /** m_units[0, m_released) are the caller's (releaseUnits()). */
    size_t                              m_released = 0;
    ast::IRootSymbolScope               *m_root = 0;
    bool                                m_root_owned = false;
    /** fileid -> name of the sources parsed since the last link(). */
    std::map<int32_t, std::string>      m_names;
    /** m_names as the last link() left it. */
    std::map<int32_t, std::string>      m_file_map;
    std::vector<SessionMarker>          m_markers;
    std::vector<SessionMarker>          m_call_markers;
    lint::ILintEngineUP                 m_lint;
    int32_t                             m_max_errors = 0;
    bool                                m_collect_docstrings = false;
    bool                                m_collect_comments = false;
    bool                                m_enable_profiling = false;
};

}

