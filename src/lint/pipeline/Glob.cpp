/*
 * Glob.cpp
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
#include <vector>
#include "Glob.h"
#include "../util/Paths.h"

namespace pssp {
namespace lint {
namespace pipeline {

namespace {

// A class at p[pi] ('['): whether it takes `c`; `end` is set past the ']'.
// A '[' with no closing ']' is a literal.
bool matchClass(const std::string &p, size_t pi, char c, size_t &end, bool &literal) {
    size_t i = pi + 1;
    bool negate = false;
    if (i < p.size() && (p[i] == '!' || p[i] == '^')) {
        negate = true;
        i++;
    }
    bool hit = false;
    bool first = true;
    for (; i < p.size() && (first || p[i] != ']'); i++) {
        first = false;
        if (i + 2 < p.size() && p[i+1] == '-' && p[i+2] != ']') {
            hit = hit || (c >= p[i] && c <= p[i+2]);
            i += 2;
        } else {
            hit = hit || (c == p[i]);
        }
    }
    if (i >= p.size()) {
        literal = true;
        return c == '[';
    }
    literal = false;
    end = i + 1;
    return hit != negate;
}

bool match(const std::string &p, size_t pi, const std::string &s, size_t si) {
    while (pi < p.size()) {
        char pc = p[pi];
        if (pc == '*') {
            bool deep = (pi + 1 < p.size() && p[pi+1] == '*');
            size_t rest = pi + 1;
            while (rest < p.size() && p[rest] == '*') {
                rest++;
            }
            if (deep) {
                // `**/` may stand for no directory at all.
                if (rest < p.size() && p[rest] == '/' && match(p, rest + 1, s, si)) {
                    return true;
                }
                for (size_t k=si; k<=s.size(); k++) {
                    if (match(p, rest, s, k)) {
                        return true;
                    }
                }
                return false;
            }
            for (size_t k=si; k<=s.size(); k++) {
                if (match(p, rest, s, k)) {
                    return true;
                }
                if (k < s.size() && s[k] == '/') {
                    break;
                }
            }
            return false;
        }
        if (si >= s.size() || (s[si] == '/' && pc != '/')) {
            return false;
        }
        if (pc == '?') {
            pi++;
            si++;
            continue;
        }
        if (pc == '[') {
            size_t end = 0;
            bool literal = false;
            bool hit = matchClass(p, pi, s[si], end, literal);
            if (!hit) {
                return false;
            }
            pi = literal ? pi + 1 : end;
            si++;
            continue;
        }
        if (pc != s[si]) {
            return false;
        }
        pi++;
        si++;
    }
    return si == s.size();
}

}

bool globMatch(const std::string &pattern, const std::string &text) {
    return match(pattern, 0, text, 0);
}

bool globMatchesPath(const std::string &pattern, const std::string &relPath) {
    std::string pat = pattern;
    while (pat.size() > 1 && pat.back() == '/') {
        pat.pop_back();
    }
    std::string root;
    std::vector<std::string> steps = util::pathSteps(relPath, root);
    if (steps.empty()) {
        return false;
    }
    if (pat.find('/') == std::string::npos) {
        for (const std::string &s : steps) {
            if (s != ".." && globMatch(pat, s)) {
                return true;
            }
        }
        return false;
    }
    if (!root.empty() || steps[0] == "..") {
        return false;
    }
    if (pat[0] == '/') {
        pat.erase(0, 1);
    }
    // The path, then each directory above it.
    std::string prefix;
    for (size_t i=0; i<steps.size(); i++) {
        prefix += (i ? "/" : "") + steps[i];
        if (globMatch(pat, prefix)) {
            return true;
        }
    }
    return false;
}

}
}
}
