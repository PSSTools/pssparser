/*
 * Paths.h
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
 * Lexical path handling shared by the lint engine: file_of() (C6.9) and
 * the per-path overrides (C7.1). Nothing touches the file system.
 */
#pragma once
#include <string>
#include <vector>

namespace pssp {
namespace lint {
namespace util {

/**
 * A path's steps, '/' or '\\' separated, with '.' and empty steps dropped
 * and '..' folded into the step before it where there is one. `root` is set
 * to the leading "/" or "C:/" of an absolute path, "" for a relative one.
 */
std::vector<std::string> pathSteps(const std::string &path, std::string &root);

/** `root` then `steps[from:]`, '/' separated. */
std::string joinSteps(const std::string &root, const std::vector<std::string> &steps,
    size_t from=0);

/**
 * `path` normalized and, when it and `base` are both absolute or both
 * relative, relative to `base` ("../" for a path outside it). An empty
 * `base`: normalized only.
 */
std::string normalPath(const std::string &path, const std::string &base);

}
}
}
