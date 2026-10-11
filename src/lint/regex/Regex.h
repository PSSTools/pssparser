/*
 * Regex.h
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
 * Linear-time regular expressions for CEL `matches` (lint-core-plan.md C1.4,
 * lint-rule-expressions.md §3).
 *
 * CEL specifies RE2 syntax and RE2's linear-time guarantee. std::regex
 * backtracks, so a pattern in a rule file could exhaust any budget; RE2 itself
 * brings in abseil. This is a Thompson NFA over a subset of RE2 syntax, run as
 * a breadth-first simulation: time is O(pattern x text), whatever the pattern.
 *
 * Supported: literals and escapes, `.`, classes (incl. ranges, negation,
 * \d \w \s and their negations, [[:name:]]), anchors ^ $ \A \z \b \B, groups
 * ( ) (?: ) (?P<n> ) (?<n> ), alternation, * + ? {n} {n,} {n,m} and their lazy
 * forms, and the flags (?i) (?s) (?m) (?U). Case folding is ASCII only.
 *
 * Rejected, at compile time, with a message: backreferences, lookaround,
 * possessive quantifiers, \p{...} Unicode classes, and any other syntax RE2
 * does not accept.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace pssp {
namespace lint {
namespace regex {

class RegexError : public std::runtime_error {
public:
    RegexError(uint32_t offset, const std::string &msg) :
        std::runtime_error(msg), m_offset(offset) { }

    /** Byte offset of the problem in the pattern. */
    uint32_t offset() const { return m_offset; }

private:
    uint32_t        m_offset;
};

struct Inst;

class Regex {
public:
    ~Regex();

    /** Compiles `pattern`. Throws RegexError. */
    static Regex *compile(const std::string &pattern);

    /**
     * Unanchored search, as CEL `matches` requires: true if any substring of
     * `text` matches. `steps`, when given, receives the number of NFA state
     * visits, which is what a budget should charge.
     */
    bool search(const std::string &text, uint64_t *steps=nullptr) const;

    /** Number of instructions in the compiled program. */
    size_t size() const;

private:
    Regex();

    std::vector<Inst>       m_prog;
    uint32_t                m_start;
};

}
}
}
