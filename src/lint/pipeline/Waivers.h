/*
 * Waivers.h
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
 *
 * Source waivers in the core (lint-core-plan.md C7.2): a port of
 * python/pssparser/waivers.py, which stays as the test oracle. Same forms,
 * spans, messages and order (docs/waivers.rst):
 *
 * - `// pssparser waive <id>[, <id>...]: <reason>`: trailing code on a line,
 *   it covers that line; alone on its line, the next line that holds code.
 * - `@lint_pkg::waive {.id = "...", .reason = "..."}`: as an element
 *   annotation, from the annotation to the element's end; standalone, from
 *   the annotation to the end of the enclosing scope (at file scope, the
 *   rest of the file).
 *
 * apply() splits diagnostics into kept and waived and reports on the
 * waivers themselves (PSSP202-205, PSSP004). Core errors and those hygiene
 * markers are never waived.
 */
#pragma once
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace pssp {
namespace ast { class IScopeChild; }
namespace lint {
class JsonWriter;
namespace yaml { struct Node; }
namespace pipeline {

class Catalogue;

/** A line or column past any real one: a span that runs to a line's end. */
constexpr int32_t WaiverEol = 1 << 30;

/** (line, col), 1-based. */
using LineCol = std::pair<int32_t, int32_t>;

struct Waiver {
    std::string                 form;       // "pragma" or "annotation"
    std::string                 file;
    int32_t                     line = 0;   // where the waiver is written
    int32_t                     col = 0;
    std::vector<std::string>    selectors;  // as written
    std::string                 reason;
    LineCol                     start;      // the covered span; `end` exclusive
    LineCol                     end;
    std::set<std::string>       ids;        // filled in by apply()
    uint32_t                    used = 0;

    bool covers(const std::string &f, int32_t l, int32_t c) const {
        return f == file && start <= LineCol(l, c) && LineCol(l, c) < end;
    }

    /** collect()'s JSON for the waiver; `withResult` adds ids and used. */
    void toJson(JsonWriter &w, bool withResult) const;

    /** A waiver from toJson()'s JSON; false when `n` is not one. */
    static bool fromJson(const yaml::Node &n, Waiver &out);
};

/** The `// pssparser waive` comments in `text` (the lexer's comment tokens). */
void collectPragmas(const std::string &path, const std::string &text,
    std::vector<Waiver> &out);

/** The `@lint_pkg::waive` annotations in the tree under `root`. */
void collectAnnotations(ast::IScopeChild *root, const std::string &path,
    std::vector<Waiver> &out);

/** Sorts waivers by (file, line, col), as collect() returns them. */
void sortWaivers(std::vector<Waiver> &waivers);

/** A diagnostic as apply() reads it. */
struct WaiverDiag {
    std::string     code;
    std::string     file;
    int32_t         line = 0;
    int32_t         col = 0;
};

/** A hygiene marker (PSSP202-205, PSSP004). */
struct WaiverMarker {
    std::string     code;
    std::string     severity;
    std::string     message;
    std::string     file;
    int32_t         line = 0;
    int32_t         col = 0;
};

struct WaiverResult {
    std::vector<uint32_t>                       kept;       // diagnostic indexes
    std::vector<std::pair<uint32_t, uint32_t>>  waived;     // (diagnostic, waiver)
    std::vector<WaiverMarker>                   markers;    // sorted
};

/**
 * Splits `diags` into kept and waived, and reports on `waivers` (whose
 * `ids` and `used` it fills in). `ran` is the codes whose rule ran; null
 * means unknown, and no waiver is then reported unused. A diagnostic's
 * file and a waiver's are compared as given: the host spells them alike.
 */
WaiverResult applyWaivers(const Catalogue &cat, const std::vector<WaiverDiag> &diags,
    std::vector<Waiver> &waivers, const std::set<std::string> *ran);

}
}
}
