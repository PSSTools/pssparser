/*
 * LintRequest.h
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
 * Plain inputs to the lint engine. The core never reads files
 * (lint-core-plan.md §1): every entry point takes (name, text) pairs, and the
 * host does the I/O. That is what lets the browser build work unchanged.
 */
#pragma once
#include <string>
#include <vector>

namespace pssp {
namespace lint {

/** One input text: a rule file, or (later) a config table as JSON. */
struct LintSource {
    std::string     name;   // shown in diagnostics; a path, a URI, anything
    std::string     text;
};

/**
 * What one lint run is asked to do (C5). Grows as the runner lands; until
 * then it carries only what the host already knows how to supply.
 */
struct LintRequest {
    std::vector<std::string>    enabledIds;     // rule IDs the host selected
    std::string                 optionsJson;    // per-rule options, as JSON
};

}
}
