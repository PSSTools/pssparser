/*
 * RuleDiagnostic.h
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
 * A diagnostic about a rule file (lint-core-plan.md §6: PSSP210-PSSP219),
 * located in the rule file. The loader reports these; it never throws for a
 * problem in the input.
 */
#pragma once
#include <cstdint>
#include <string>

namespace pssp {
namespace lint {

struct RuleDiagnostic {
    enum class Severity { Error, Warning, Info };

    std::string     code;           // "PSSP212"
    Severity        severity = Severity::Error;
    std::string     message;
    std::string     file;           // the LintSource name
    uint32_t        line = 0;       // 1-based; 0 when the file has no position
    uint32_t        col = 0;
    std::string     rule;           // the rule's id, when the diagnostic is about one

    // A second location the message refers to (the other of two duplicates).
    bool            hasRelated = false;
    std::string     relatedFile;
    uint32_t        relatedLine = 0;
    uint32_t        relatedCol = 0;
};

}
}
