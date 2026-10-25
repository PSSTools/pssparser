/****************************************************************************
 * pssparser_c.cpp -- the C interface over pssp::IParserSession
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
 * Marshalling only: each function forwards to the session. The one thing
 * added here is the boundary rule that no C++ exception crosses into C --
 * the session already turns its own into markers, so what is left to catch
 * is misuse, which becomes -1 and pssp_session_last_error().
 */
#include <exception>
#include <memory>
#include <string>
#include "pssp/FactoryExt.h"
#include "pssp/IParserSession.h"
#include "pssp/ast/FactoryExt.h"
#include "pssp/pssparser_c.h"

struct pssp_session {
    pssp::IParserSessionUP  session;
    /** The backing store of every returned string. */
    std::string             str;
    std::string             last_error;

    const char *ret(const std::string &s) {
        str = s;
        return str.c_str();
    }
};

namespace {

/** Runs `f`, turning an exception into -1 and a last_error. */
template <class F> int guarded(pssp_session *s, F f) {
    try {
        return f();
    } catch (const std::exception &e) {
        s->last_error = e.what();
    } catch (...) {
        s->last_error = "unknown exception";
    }
    return -1;
}

}

extern "C" {

int32_t pssp_c_abi_version(void) {
    return PSSP_C_ABI_VERSION;
}

pssp_session *pssp_session_new(void) {
    try {
        pssp::IFactory *factory = pssparser_getFactory();
        if (!factory->getAstFactory()) {
            // No debug manager: every DEBUG_* macro in the core is
            // null-guarded, so null disables tracing and costs nothing else.
            // A host that loaded the factory through another binding has
            // initialised it already, and that is left alone.
            factory->init(0, ast_getFactory());
        }
        std::unique_ptr<pssp_session> s(new pssp_session());
        s->session.reset(factory->mkParserSession());
        return s.release();
    } catch (...) {
        return 0;
    }
}

void pssp_session_free(pssp_session *s) {
    delete s;
}

const char *pssp_session_last_error(pssp_session *s) {
    return s->last_error.c_str();
}

void pssp_session_set_max_errors(pssp_session *s, int32_t n) {
    s->session->setMaxErrors(n);
}

void pssp_session_set_collect_docstrings(pssp_session *s, int c) {
    s->session->setCollectDocstrings(c != 0);
}

int pssp_session_get_collect_docstrings(pssp_session *s) {
    return s->session->getCollectDocstrings();
}

void pssp_session_set_collect_comments(pssp_session *s, int c) {
    s->session->setCollectComments(c != 0);
}

int pssp_session_get_collect_comments(pssp_session *s) {
    return s->session->getCollectComments();
}

void pssp_session_set_enable_profiling(pssp_session *s, int e) {
    s->session->setEnableProfiling(e != 0);
}

int pssp_session_begin_parse(pssp_session *s) {
    return guarded(s, [&] { s->session->beginParse(); return 1; });
}

int pssp_session_parse_source(
        pssp_session        *s,
        const char          *name,
        const char          *text,
        size_t              len) {
    return guarded(s, [&] {
        return s->session->parseSource(name, std::string(text, len)) ? 1 : 0;
    });
}

int32_t pssp_session_next_fileid(pssp_session *s) {
    return s->session->nextFileid();
}

int32_t pssp_session_num_units(pssp_session *s) {
    return static_cast<int32_t>(s->session->units().size());
}

int pssp_session_link(pssp_session *s) {
    return guarded(s, [&] { return s->session->link() ? 1 : 0; });
}

int pssp_session_has_root(pssp_session *s) {
    return s->session->root() != 0;
}

int32_t pssp_session_num_user_units(pssp_session *s) {
    return static_cast<int32_t>(s->session->userUnits().size());
}

int32_t pssp_session_num_markers(pssp_session *s) {
    return static_cast<int32_t>(s->session->markers().size());
}

int32_t pssp_session_num_call_markers(pssp_session *s) {
    return static_cast<int32_t>(s->session->callMarkers().size());
}

const char *pssp_session_markers_json(pssp_session *s) {
    return s->ret(s->session->markersJson());
}

const char *pssp_session_call_markers_json(pssp_session *s) {
    return s->ret(s->session->callMarkersJson());
}

void pssp_session_clear_markers(pssp_session *s) {
    s->session->clearMarkers();
}

int pssp_session_has_errors(pssp_session *s) {
    return s->session->hasErrors();
}

int pssp_session_max_errors_exceeded(pssp_session *s) {
    return s->session->maxErrorsExceeded();
}

const char *pssp_session_file_map_json(pssp_session *s) {
    return s->ret(s->session->fileMapJson());
}

const char *pssp_session_source_names_json(pssp_session *s) {
    return s->ret(s->session->sourceNamesJson());
}

const char *pssp_session_resolve_location(
        pssp_session        *s,
        int32_t             fileid,
        int32_t             line,
        int32_t             *line_out) {
    pssp::SessionLocation loc = s->session->resolveLocation(fileid, line);
    if (line_out) {
        *line_out = loc.line;
    }
    return s->ret(loc.file);
}

const char *pssp_session_inactive_regions_json(pssp_session *s) {
    return s->ret(s->session->inactiveRegionsJson());
}

const char *pssp_session_profile_info_json(pssp_session *s) {
    return s->ret(s->session->profileInfoJson());
}

}
