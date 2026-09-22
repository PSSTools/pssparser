/*
 * CoreLibraryLookup.h
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
#include <string>
#include "pssp/ast/ISymbolScope.h"

namespace pssp {

/**
 * The core-library package that declares `name` at its top level, or an empty
 * string if none of the four does.
 *
 * PSS 3.1 clause 21 gives the core library no implicit visibility: a model
 * that says `print(...)` without `import std_pkg::*;` is not conforming, and
 * the name genuinely does not resolve. "unknown identifier 'print'" is
 * therefore correct but unhelpful, because the name does exist -- just not
 * where the model looked. This turns that one case into an actionable
 * diagnostic naming the import to add.
 *
 * `root` is the global symbol scope; a null or non-scope root yields "".
 */
std::string findCoreLibraryPackage(
    ast::ISymbolScope       *root,
    const std::string       &name);

}
