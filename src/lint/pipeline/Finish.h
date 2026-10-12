/*
 * Finish.h
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
 * What happens to a run's diagnostics between the run and the output
 * (lint-core-plan.md C7.4): the CLI's `_finish` sequence in
 * python/pssparser/cli/commands.py, which stays as the test oracle.
 *
 *   select    a lint finding not enabled for its file, or outside the
 *             host's own files, is dropped
 *   severity  `[severity]`; `off` drops
 *   waive     source waivers, whose hygiene markers join the diagnostics
 *   policy    --no-warnings, then -Wno-error, -Werror=..., -Werror
 *
 * The stages run in that order; a host may run some of them, as the CLI
 * does around its baseline.
 */
#pragma once
#include <cstdint>
#include <set>
#include <string>
#include <vector>
#include "Selection.h"
#include "Waivers.h"

namespace pssp {
namespace lint {
namespace pipeline {

/** A diagnostic as finish() reads and rewrites it. */
struct FinishDiag {
    std::string     code;
    std::string     severity;
    std::string     file;
    int32_t         line = 0;
    int32_t         col = 0;
    std::string     message;            // the hygiene markers' only
    int64_t         index = -1;         // into the request; -1 for a hygiene marker
    std::string     originalSeverity;   // before -Werror promoted it
    std::string     werror;             // the flag that promoted it
    int64_t         waiver = -1;        // a waived diagnostic's waiver
};

struct FinishRequest {
    bool                        select = true;
    bool                        severity = true;
    bool                        waive = true;
    bool                        policy = true;
    bool                        haveOwned = false;
    std::set<std::string>       owned;
    std::vector<Waiver>         waivers;
    const std::set<std::string> *ran = nullptr;
};

struct FinishResult {
    std::vector<FinishDiag>     diagnostics;    // kept, then the hygiene markers
    std::vector<FinishDiag>     waived;
    uint32_t                    outside = 0;    // lint findings outside the owned files
    std::vector<std::string>    problems;
};

/**
 * Runs the requested stages over `diags` with the resolved `sel` (its
 * groups, `[severity]` and `-W` policy) and `pol`, which is `sel`'s policy
 * unless the host gave its own.
 */
FinishResult finish(const Catalogue &cat, Selection &sel, const Selection::Warnings &pol,
    std::vector<FinishDiag> diags, FinishRequest &req);

/**
 * The codes whose rule ran, when the host does not say (`"ran": "auto"`):
 * the core's active markers and the loaded rules some of `paths` enables
 * (group 0 with no paths), less `[severity]`'s `off`.
 */
std::set<std::string> codesThatRan(const Catalogue &cat, Selection &sel,
    const std::vector<std::string> &paths);

}
}
}
