/*
 * YamlDoc.h
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
 * The YAML layer of the pss-rules loader (lint-core-plan.md C1.2, D-C2).
 *
 * rapidyaml parses; this layer gives the result the meaning pss-rules
 * needs, which rapidyaml deliberately leaves to the application:
 *
 *  - scalars are typed by the YAML 1.2 core schema, here, in our code. Only
 *    plain scalars are typed; `yes`/`no`/`on`/`off` are strings, so the
 *    YAML 1.1 `on:` trap (pss-rules-format.md §6.1) cannot happen;
 *  - every node carries a 1-based line and column;
 *  - multiple documents, tags and duplicate mapping keys are errors;
 *  - anchors and aliases are resolved.
 *
 * The result is our own small tree, independent of rapidyaml's, so nothing
 * above this layer includes a rapidyaml header.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace pssp {
namespace lint {
namespace yaml {

/** 1-based line and column; byte offset into the source text. */
struct Mark {
    uint32_t    line = 0;
    uint32_t    col = 0;
    uint32_t    offset = 0;
};

class YamlError : public std::runtime_error {
public:
    YamlError(const Mark &m, const std::string &msg) :
        std::runtime_error(msg), m_mark(m) { }

    const Mark &mark() const { return m_mark; }

    /** A second location the message refers to (e.g. a duplicate key). */
    Mark            related;
    bool            hasRelated = false;

private:
    Mark            m_mark;
};

struct Node;
using NodeUP = std::unique_ptr<Node>;

struct Node {
    enum class Kind { Null, Bool, Int, Float, String, Map, Seq };
    enum class Style { None, Plain, SingleQuoted, DoubleQuoted, Literal, Folded, Flow, Block };

    Kind            kind = Kind::Null;
    Style           style = Style::None;
    Mark            mark;           // where the value starts

    bool            b = false;
    int64_t         i = 0;
    double          d = 0.0;
    std::string     s;              // String: the value. Any scalar: its text

    // String: where each byte of `s` is in the source (SourceMap.h).
    // srcMap[i] is the offset of s[i]; srcMap[s.size()] is just past the
    // value. srcExact is false when the source did not line up and every
    // entry is the scalar's start.
    std::vector<uint32_t>   srcMap;
    bool                    srcExact = true;

    struct Member {
        std::string     key;
        Mark            keyMark;
        NodeUP          value;
    };
    std::vector<Member>     members;    // Map, in source order
    std::vector<NodeUP>     items;      // Seq

    const Node *get(const std::string &key) const;
};

/**
 * Parses one YAML document. `name` is used in messages only. Throws
 * YamlError. An empty document gives a Null root.
 */
NodeUP parse(const std::string &name, const std::string &text);

const char *kindName(Node::Kind k);
const char *styleName(Node::Style s);

}
}
}
