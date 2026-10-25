/****************************************************************************
 * pssparser_c.h -- a flat C interface to the parse-and-link session
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
 * pssp::IParserSession (pssp/IParserSession.h) for a host that cannot call
 * C++: the Rust binding first (docs/design/rust-binding.md), anything with a
 * C FFI after it. Shipped as its own library, libpssparser_c, which links
 * libpssparser and libast.
 *
 * Conventions:
 *  - A session is an opaque handle from pssp_session_new(), freed with
 *    pssp_session_free(). Nothing here is thread-safe; use one session per
 *    thread.
 *  - Booleans are int: 1 true, 0 false. A call that can fail for a reason
 *    other than the PSS source returns -1, and pssp_session_last_error()
 *    says why. (Errors in the source are markers, not failures.)
 *  - A returned `const char *` is UTF-8, owned by the session, and valid
 *    until the next call on that session that returns a string. Copy it.
 *  - Structured results cross as JSON, in the shapes IParserSession's
 *    *Json() methods document -- the same text the WASM build hands to
 *    TypeScript.
 *  - The session owns the units and the linked root. The tree itself does
 *    not cross yet; serialising it is the Rust plan's R3.
 */
#ifndef PSSP_PSSPARSER_C_H
#define PSSP_PSSPARSER_C_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
#  if defined(PSSPARSER_C_BUILD_DLL)
#    define PSSPARSER_C_API __declspec(dllexport)
#  else
#    define PSSPARSER_C_API __declspec(dllimport)
#  endif
#else
#  define PSSPARSER_C_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

/** The version of this interface. Bumped when a function changes; adding
 *  one does not. */
#define PSSP_C_ABI_VERSION 1

typedef struct pssp_session pssp_session;

/** PSSP_C_ABI_VERSION as the library was built. */
PSSPARSER_C_API int32_t pssp_c_abi_version(void);

/** A new session, or NULL if one could not be made. */
PSSPARSER_C_API pssp_session *pssp_session_new(void);

/** Frees the session, its units and its root. NULL is ignored. */
PSSPARSER_C_API void pssp_session_free(pssp_session *s);

/** Why the last call that returned -1 failed; "" if none has. */
PSSPARSER_C_API const char *pssp_session_last_error(pssp_session *s);

/* -- Options; each applies from the next parse or link on ---------------- */

/** 0 (the default) is unlimited. */
PSSPARSER_C_API void pssp_session_set_max_errors(pssp_session *s, int32_t n);
PSSPARSER_C_API void pssp_session_set_collect_docstrings(pssp_session *s, int c);
PSSPARSER_C_API int pssp_session_get_collect_docstrings(pssp_session *s);
/** Implies docstring collection. */
PSSPARSER_C_API void pssp_session_set_collect_comments(pssp_session *s, int c);
PSSPARSER_C_API int pssp_session_get_collect_comments(pssp_session *s);
PSSPARSER_C_API void pssp_session_set_enable_profiling(pssp_session *s, int e);

/* -- Parse and link ------------------------------------------------------- */

/** Opens a parse call; the first one loads the core library as unit 0.
 *  Returns 1, or -1. */
PSSPARSER_C_API int pssp_session_begin_parse(pssp_session *s);

/**
 * Parses `len` bytes of `text` as the source `name`. Returns 1 when it
 * parsed, 0 when the call has produced an error marker (the source then does
 * not join the units), -1 on misuse -- no pssp_session_begin_parse() first.
 */
PSSPARSER_C_API int pssp_session_parse_source(
    pssp_session        *s,
    const char          *name,
    const char          *text,
    size_t              len);

/** The fileid the next pssp_session_parse_source() will assign. */
PSSPARSER_C_API int32_t pssp_session_next_fileid(pssp_session *s);

/** Units accepted since the last link, core library included. */
PSSPARSER_C_API int32_t pssp_session_num_units(pssp_session *s);

/** Links every unit parsed so far. Returns 1, 0 when the link produced an
 *  error marker (the root is recorded anyway), or -1. */
PSSPARSER_C_API int pssp_session_link(pssp_session *s);

PSSPARSER_C_API int pssp_session_has_root(pssp_session *s);

/** The user files' units in the linked root. */
PSSPARSER_C_API int32_t pssp_session_num_user_units(pssp_session *s);

/* -- Markers and names ---------------------------------------------------- */

/** Every marker since pssp_session_clear_markers(), resolved and sorted. */
PSSPARSER_C_API int32_t pssp_session_num_markers(pssp_session *s);
/** The markers of the last parse or link call. */
PSSPARSER_C_API int32_t pssp_session_num_call_markers(pssp_session *s);
PSSPARSER_C_API const char *pssp_session_markers_json(pssp_session *s);
PSSPARSER_C_API const char *pssp_session_call_markers_json(pssp_session *s);
PSSPARSER_C_API void pssp_session_clear_markers(pssp_session *s);

/** Whether the current call has produced an error marker. */
PSSPARSER_C_API int pssp_session_has_errors(pssp_session *s);
PSSPARSER_C_API int pssp_session_max_errors_exceeded(pssp_session *s);

/** fileid -> name, as JSON objects: the last link's files, and the sources
 *  parsed since. */
PSSPARSER_C_API const char *pssp_session_file_map_json(pssp_session *s);
PSSPARSER_C_API const char *pssp_session_source_names_json(pssp_session *s);

/** The display file of a location; `*line_out`, when not NULL, gets the
 *  display line. A core-library line maps to the library file it is in. */
PSSPARSER_C_API const char *pssp_session_resolve_location(
    pssp_session        *s,
    int32_t             fileid,
    int32_t             line,
    int32_t             *line_out);

/* -- Queries -------------------------------------------------------------- */

/** The regions a `compile if` left out, as JSON. */
PSSPARSER_C_API const char *pssp_session_inactive_regions_json(pssp_session *s);

/** The last parse's profile as JSON; "" when there is none. */
PSSPARSER_C_API const char *pssp_session_profile_info_json(pssp_session *s);

#ifdef __cplusplus
}
#endif

#endif /* PSSP_PSSPARSER_C_H */
