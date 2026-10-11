/*
 * SourceMap.h
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
 * Where each byte of a YAML scalar's value came from in the rule file
 * (lint-core-plan.md C2.2, risk R-3).
 *
 * A CEL expression is the *decoded* value of a scalar, and its error offsets
 * are offsets into that value. The value differs from the source text in
 * every style but a one-line plain scalar: quotes are removed, escapes
 * decoded (`\t` is two bytes of source, one of value), line breaks folded to
 * spaces, block indentation stripped. A source map records, for each value
 * byte, the source byte it came from, so an error lands on the right line
 * and column of the rule file.
 *
 * The map is built by walking the source again beside the value rapidyaml
 * produced, not by re-implementing YAML's scalar rules. The walk knows which
 * source bytes a style can drop (indentation, the break of a folded line,
 * the second quote of '') and which it rewrites (escapes); anything else that
 * fails to line up marks the map inexact, and every offset falls back to the
 * scalar's start: a coarser position, never a wrong one.
 */
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "YamlDoc.h"

namespace pssp {
namespace lint {
namespace yaml {

/** Line starts of a text, for byte offset -> 1-based line and column. */
class LineIndex {
public:
    explicit LineIndex(const std::string &text);

    Mark at(uint32_t offset) const;

private:
    std::vector<uint32_t>   m_starts;
};

/**
 * Maps `value`, the decoded text of a scalar of `style` whose source starts
 * at `begin` in `text`, back to source offsets. `begin` is where rapidyaml
 * places the value: the first content byte of a plain or quoted scalar (just
 * inside the quote), the start of the line after the header of a block
 * scalar.
 *
 * On return `out` has value.size() + 1 entries: out[i] is the source offset
 * of value byte i, and the last entry the offset just past the value's last
 * source byte. Returns false, with every entry set to `begin`, when the
 * source does not line up with the value.
 */
bool mapScalar(
    const std::string           &text,
    uint32_t                    begin,
    Node::Style                 style,
    const std::string           &value,
    std::vector<uint32_t>       &out);

/**
 * The source offset of byte `off` of string node `n`'s value (clamped to the
 * value). An offset in the value's trailing whitespace -- where an "end of
 * input" error lands, and a block scalar's value ends with a line break --
 * maps to just past the last non-blank byte instead: the end of the
 * expression as the reader sees it, not the start of the next line.
 */
uint32_t sourceOffset(const Node &n, uint32_t off);

}
}
}
