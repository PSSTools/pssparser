/**
 * InternalError.h
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
#include <cstdarg>
#include <cstdio>
#include <stdexcept>
#include <string>
#include "pssp/ast/Location.h"

namespace pssp {

/**
 * A defect in pssparser itself, not in the model: a state the code believed
 * could not happen. Thrown rather than printed, so that the catch-all at the
 * linker and parser boundaries turns it into a PSS000 marker -- a diagnostic
 * every consumer sees -- instead of a line on stdout that corrupts --json, or
 * an abort (symbol-resolution-plan.md INV-1/INV-2).
 *
 * Carries a source location when the thrower has one; the boundary falls
 * back to a location-less marker otherwise.
 */
class InternalError : public std::runtime_error {
public:
    explicit InternalError(const std::string &msg) :
        std::runtime_error(msg), m_has_loc(false) { }

    InternalError(const ast::Location &loc, const std::string &msg) :
        std::runtime_error(msg), m_has_loc(true), m_loc(loc) { }

    bool hasLoc() const { return m_has_loc; }

    const ast::Location &loc() const { return m_loc; }

    /**
     * printf-style construction, for the sites that used to hand the same
     * arguments to fprintf or DEBUG_ERROR.
     */
    static InternalError fmt(const char *fmt, ...)
#ifdef __GNUC__
        __attribute__((format(printf, 1, 2)))
#endif
    {
        char tmp[1024];
        va_list ap;
        va_start(ap, fmt);
        vsnprintf(tmp, sizeof(tmp), fmt, ap);
        va_end(ap);
        return InternalError(std::string(tmp));
    }

private:
    bool                m_has_loc;
    ast::Location       m_loc;
};

/**
 * The marker ID every internal error carries. Assigned on the C++ side
 * rather than recovered from the message text, so that it cannot be
 * shadowed by a message pattern belonging to another code.
 */
static constexpr const char *INTERNAL_ERROR_ID = "PSS000";

/**
 * Keeps recursive resolution from exhausting the stack. A stack overflow
 * cannot be caught, so the only way to turn runaway recursion into a
 * diagnostic is to stop it first and throw. One counter per walk; the RAII
 * guard is placed at each recursive entry point.
 */
class DepthGuard {
public:
    static constexpr int32_t DEFAULT_LIMIT = 1000;

    DepthGuard(int32_t &depth, const char *what, int32_t limit=DEFAULT_LIMIT) :
            m_depth(depth) {
        if (++m_depth > limit) {
            m_depth--;
            throw InternalError::fmt(
                "recursion limit (%d) exceeded in %s", limit, what);
        }
    }

    ~DepthGuard() { m_depth--; }

    DepthGuard(const DepthGuard &) = delete;
    DepthGuard &operator=(const DepthGuard &) = delete;

private:
    int32_t             &m_depth;
};

}
