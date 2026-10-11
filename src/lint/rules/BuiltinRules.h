/*
 * BuiltinRules.h
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
 * The built-in rule files (lint-core-plan.md C4.3; pss-rules-format.md
 * §6.2): the files in rules/, embedded at build time by mk_builtin_rules.py, which
 * generates the definition of builtinRuleFiles().
 */
#pragma once
#include <cstddef>

namespace pssp {
namespace lint {
namespace rules {

struct BuiltinRuleFile {
    const char      *name;      // "pssparser:rules/<file>", or null at the end
    const char      *text;      // NUL-terminated
    size_t          size;       // bytes, less the NUL
};

/** Every built-in rule file, in name order, ending with a null name. */
const BuiltinRuleFile *builtinRuleFiles();

}
}
}
