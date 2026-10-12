/*
 * Glob.h
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
 * The `files` patterns of `[[lint.overrides]]` (lint-core-plan.md C7.1).
 *
 * `*` and `?` do not cross '/'; `**` does, and `**` followed by '/' also
 * matches no directory at all; `[abc]`, `[a-z]` and `[!a]` are classes.
 * A pattern without '/' matches one step of the path, a file or directory
 * name at any depth (`*_test.pss`, `vendor`); one with '/' is anchored at the
 * base directory (a leading '/' is allowed and means the same). Either way,
 * a pattern that matches a directory takes everything under it. A path
 * outside the base (`../x`, or absolute) matches only patterns without '/'.
 * Matching is case-sensitive.
 */
#pragma once
#include <string>

namespace pssp {
namespace lint {
namespace pipeline {

/** `text` against the whole of `pattern`. */
bool globMatch(const std::string &pattern, const std::string &text);

/**
 * Whether `pattern` takes `relPath`: a path normalized, '/' separated and
 * relative to the base directory (util::normalPath).
 */
bool globMatchesPath(const std::string &pattern, const std::string &relPath);

}
}
}
