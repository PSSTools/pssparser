/*
 * Paths.cpp
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
#include <algorithm>
#include <cctype>
#include "Paths.h"

namespace pssp {
namespace lint {
namespace util {

// A path's steps, '/' or '\\' separated, with '.' and empty steps dropped
// and '..' folded into the step before it where there is one. `root` is the
// leading "/" or "C:/" of an absolute path, "" for a relative one.
std::vector<std::string> pathSteps(const std::string &path, std::string &root) {
    std::string p = path;
    std::replace(p.begin(), p.end(), '\\', '/');
    root.clear();
    size_t at = 0;
    if (p.size() >= 2 && std::isalpha(static_cast<unsigned char>(p[0])) && p[1] == ':') {
        root = p.substr(0, 2) + "/";
        at = 2;
    }
    if (at < p.size() && p[at] == '/') {
        root = root.empty() ? "/" : root;
        at++;
    }
    std::vector<std::string> steps;
    while (at <= p.size()) {
        size_t end = p.find('/', at);
        std::string step = p.substr(at, (end == std::string::npos) ? std::string::npos : end - at);
        if (step == "..") {
            if (!steps.empty() && steps.back() != "..") {
                steps.pop_back();
            } else if (root.empty()) {
                steps.push_back(step);      // above a relative start: kept
            }
        } else if (!step.empty() && step != ".") {
            steps.push_back(step);
        }
        if (end == std::string::npos) {
            break;
        }
        at = end + 1;
    }
    return steps;
}

std::string joinSteps(const std::string &root, const std::vector<std::string> &steps,
        size_t from) {
    std::string out = root;
    for (size_t i=from; i<steps.size(); i++) {
        if (i > from) {
            out += "/";
        }
        out += steps[i];
    }
    return out;
}

// `path` normalized and, when it and `base` are both absolute or both
// relative, relative to `base` ("../" for a path outside it).
std::string normalPath(const std::string &path, const std::string &base) {
    std::string root, broot;
    std::vector<std::string> steps = pathSteps(path, root);
    if (base.empty()) {
        return joinSteps(root, steps);
    }
    std::vector<std::string> bsteps = pathSteps(base, broot);
    if (root != broot) {
        return joinSteps(root, steps);
    }
    size_t common = 0;
    while (common < steps.size() && common < bsteps.size()
            && steps[common] == bsteps[common]) {
        common++;
    }
    std::vector<std::string> rel(bsteps.size() - common, "..");
    rel.insert(rel.end(), steps.begin() + common, steps.end());
    return joinSteps("", rel);
}

}
}
}
