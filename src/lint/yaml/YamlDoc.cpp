/*
 * YamlDoc.cpp
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
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <map>
#include <utility>
#include <vector>
#include "ryml.hpp"
#include "ryml_std.hpp"
#include "SourceMap.h"
#include "YamlDoc.h"

namespace pssp {
namespace lint {
namespace yaml {

const char *kindName(Node::Kind k) {
    switch (k) {
        case Node::Kind::Null: return "null";
        case Node::Kind::Bool: return "bool";
        case Node::Kind::Int: return "int";
        case Node::Kind::Float: return "float";
        case Node::Kind::String: return "string";
        case Node::Kind::Map: return "map";
        case Node::Kind::Seq: return "seq";
    }
    return "?";
}

const char *styleName(Node::Style s) {
    switch (s) {
        case Node::Style::None: return "none";
        case Node::Style::Plain: return "plain";
        case Node::Style::SingleQuoted: return "single-quoted";
        case Node::Style::DoubleQuoted: return "double-quoted";
        case Node::Style::Literal: return "literal";
        case Node::Style::Folded: return "folded";
        case Node::Style::Flow: return "flow";
        case Node::Style::Block: return "block";
    }
    return "?";
}

const Node *Node::get(const std::string &key) const {
    for (const Member &m : members) {
        if (m.key == key) {
            return m.value.get();
        }
    }
    return nullptr;
}

namespace {

// rapidyaml decodes each half of an escaped JSON surrogate pair (D83D DC31) as a
// code point of its own, giving CESU-8 rather than UTF-8. JSON is accepted
// as YAML (pss-rules-format.md §2), so join each encoded pair into the one
// code point it stands for. Escapes occur only in double-quoted scalars.
void joinSurrogates(std::string &s) {
    auto unit = [&s](size_t i) -> uint32_t {
        return ((static_cast<uint8_t>(s[i]) & 0x0F) << 12)
            | ((static_cast<uint8_t>(s[i+1]) & 0x3F) << 6)
            | (static_cast<uint8_t>(s[i+2]) & 0x3F);
    };
    auto isHalf = [&s](size_t i, uint8_t lo, uint8_t hi) {
        return i + 3 <= s.size() && static_cast<uint8_t>(s[i]) == 0xED
            && static_cast<uint8_t>(s[i+1]) >= lo && static_cast<uint8_t>(s[i+1]) <= hi;
    };
    if (s.find('\xED') == std::string::npos) {
        return;
    }
    std::string out;
    out.reserve(s.size());
    for (size_t i=0; i<s.size(); ) {
        if (isHalf(i, 0xA0, 0xAF) && isHalf(i + 3, 0xB0, 0xBF)) {
            uint32_t cp = 0x10000 + ((unit(i) - 0xD800) << 10) + (unit(i + 3) - 0xDC00);
            out += static_cast<char>(0xF0 | (cp >> 18));
            out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
            i += 6;
        } else {
            out += s[i++];
        }
    }
    s.swap(out);
}


// rapidyaml reports errors through callbacks that must not return. Ours
// throw, and parse() turns the exception into a YamlError.
//
// Only a parse error carries a YAML location, and it is 1-based in both line
// and column -- unlike node locations (Tree::location), which are 0-based
// (checked against rapidyaml v0.16.0, C0). Basic and visit errors carry a
// location in rapidyaml's own C++ source, which means nothing to a rule
// author, so they are reported without one.
struct RymlFailure {
    std::string     msg;
    ryml::Location  loc;
    bool            has_yaml_loc;
};

[[noreturn]] void onErrorBasic(ryml::csubstr msg, ryml::ErrorDataBasic const &, void *) {
    throw RymlFailure{std::string(msg.str, msg.len), ryml::Location(), false};
}

[[noreturn]] void onErrorParse(ryml::csubstr msg, ryml::ErrorDataParse const &d, void *) {
    throw RymlFailure{std::string(msg.str, msg.len), d.ymlloc, true};
}

[[noreturn]] void onErrorVisit(ryml::csubstr msg, ryml::ErrorDataVisit const &, void *) {
    throw RymlFailure{std::string(msg.str, msg.len), ryml::Location(), false};
}

ryml::Callbacks callbacks() {
    ryml::Callbacks cb;
    cb.set_error_basic(&onErrorBasic);
    cb.set_error_parse(&onErrorParse);
    cb.set_error_visit(&onErrorVisit);
    return cb;
}

Mark toMark(const ryml::Location &l) {
    Mark m;
    m.line = (l.line == ryml::npos) ? 0 : static_cast<uint32_t>(l.line + 1);
    m.col = (l.col == ryml::npos) ? 0 : static_cast<uint32_t>(l.col + 1);
    m.offset = (l.offset == ryml::npos) ? 0 : static_cast<uint32_t>(l.offset);
    return m;
}

bool allDigits(const std::string &s, size_t b, size_t e, int base) {
    if (b >= e) {
        return false;
    }
    for (size_t i=b; i<e; i++) {
        char c = s[i];
        bool ok = (base == 8) ? (c >= '0' && c <= '7') :
            (base == 10) ? (c >= '0' && c <= '9') :
            ((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'));
        if (!ok) {
            return false;
        }
    }
    return true;
}

// [-+]? ( \. [0-9]+ | [0-9]+ ( \. [0-9]* )? ) ( [eE] [-+]? [0-9]+ )?
bool isCoreFloat(const std::string &s) {
    size_t i = 0, n = s.size();
    if (i < n && (s[i] == '-' || s[i] == '+')) i++;
    size_t int_b = i;
    while (i < n && s[i] >= '0' && s[i] <= '9') i++;
    bool int_digits = (i > int_b);
    bool frac_digits = false;
    if (i < n && s[i] == '.') {
        i++;
        size_t fb = i;
        while (i < n && s[i] >= '0' && s[i] <= '9') i++;
        frac_digits = (i > fb);
    }
    if (!int_digits && !frac_digits) {
        return false;
    }
    if (i < n && (s[i] == 'e' || s[i] == 'E')) {
        i++;
        if (i < n && (s[i] == '-' || s[i] == '+')) i++;
        size_t eb = i;
        while (i < n && s[i] >= '0' && s[i] <= '9') i++;
        if (i == eb) {
            return false;
        }
    }
    return i == n;
}

// Types a plain scalar by the YAML 1.2 core schema (YAML 1.2.2 §10.3.2).
void typePlain(Node &n) {
    const std::string &s = n.s;
    if (s.empty() || s == "~" || s == "null" || s == "Null" || s == "NULL") {
        n.kind = Node::Kind::Null;
        return;
    }
    if (s == "true" || s == "True" || s == "TRUE") {
        n.kind = Node::Kind::Bool;
        n.b = true;
        return;
    }
    if (s == "false" || s == "False" || s == "FALSE") {
        n.kind = Node::Kind::Bool;
        n.b = false;
        return;
    }

    size_t sign = (s[0] == '-' || s[0] == '+') ? 1 : 0;
    if (allDigits(s, sign, s.size(), 10)) {
        errno = 0;
        long long v = std::strtoll(s.c_str(), nullptr, 10);
        if (errno == ERANGE) {
            throw YamlError(n.mark, "integer '" + s + "' is out of the 64-bit range");
        }
        n.kind = Node::Kind::Int;
        n.i = static_cast<int64_t>(v);
        return;
    }
    if (s.size() > 2 && s[0] == '0' && (s[1] == 'o' || s[1] == 'x')) {
        int base = (s[1] == 'o') ? 8 : 16;
        if (allDigits(s, 2, s.size(), base)) {
            errno = 0;
            unsigned long long v = std::strtoull(s.c_str() + 2, nullptr, base);
            if (errno == ERANGE || v > static_cast<unsigned long long>(INT64_MAX)) {
                throw YamlError(n.mark, "integer '" + s + "' is out of the 64-bit range");
            }
            n.kind = Node::Kind::Int;
            n.i = static_cast<int64_t>(v);
            return;
        }
    }
    if (isCoreFloat(s)) {
        n.kind = Node::Kind::Float;
        n.d = std::strtod(s.c_str(), nullptr);
        return;
    }
    {
        std::string body = s.substr(sign);
        if (body == ".inf" || body == ".Inf" || body == ".INF") {
            n.kind = Node::Kind::Float;
            n.d = (s[0] == '-') ? -std::numeric_limits<double>::infinity()
                                : std::numeric_limits<double>::infinity();
            return;
        }
        if (sign == 0 && (s == ".nan" || s == ".NaN" || s == ".NAN")) {
            n.kind = Node::Kind::Float;
            n.d = std::numeric_limits<double>::quiet_NaN();
            return;
        }
    }
    n.kind = Node::Kind::String;
}

// Nesting limit for the converted tree. rapidyaml's own parser does not
// recurse, but conversion (and every later walk) does, at about 160 bytes of
// WASM stack per level (C0). Rule files nest a handful of levels.
constexpr int MaxNesting = 64;

// Upper bound on the converted tree, aliases expanded. A YAML alias can
// point at a sequence of aliases ("billion laughs"): nine levels of nine-fold
// fan-out is 387 million nodes from a few hundred bytes. rapidyaml's
// resolve() expands without limit, so the expanded size is computed first.
constexpr uint64_t MaxNodes = 100000;

// The node count of `root` once aliases are expanded, computed without
// expanding them, saturating at MaxNodes + 1. Iterative: the tree has not
// been depth-checked yet.
uint64_t expandedSize(const ryml::Tree &t, ryml::id_type root) {
    std::vector<ryml::id_type> order;           // post-order
    std::vector<std::pair<ryml::id_type, bool>> stack{{root, false}};
    while (!stack.empty()) {
        auto [id, done] = stack.back();
        stack.pop_back();
        if (done) {
            order.push_back(id);
            continue;
        }
        stack.push_back({id, true});
        // Children are pushed last-first so they pop, and finish, in
        // document order: an anchor must be sized before a later alias to it.
        size_t mark = stack.size();
        for (ryml::id_type c=t.first_child(id); c!=ryml::NONE; c=t.next_sibling(c)) {
            stack.push_back({c, false});
        }
        std::reverse(stack.begin() + mark, stack.end());
    }

    auto sat = [](uint64_t a, uint64_t b) {
        uint64_t r = a + b;
        return (r > MaxNodes + 1) ? MaxNodes + 1 : r;
    };
    auto refName = [](ryml::csubstr r) {
        std::string n(r.str ? r.str : "", r.len);
        return (!n.empty() && n[0] == '*') ? n.substr(1) : n;
    };

    std::map<std::string, uint64_t> anchors;
    std::map<ryml::id_type, uint64_t> size;
    for (ryml::id_type id : order) {
        uint64_t n = 1;
        if (t.is_val_ref(id)) {
            auto it = anchors.find(refName(t.val(id)));
            n = (it != anchors.end()) ? it->second : 1;
        }
        if (t.has_key(id) && t.is_key_ref(id)) {
            auto it = anchors.find(refName(t.key(id)));
            n = sat(n, (it != anchors.end()) ? it->second : 1);
        }
        for (ryml::id_type c=t.first_child(id); c!=ryml::NONE; c=t.next_sibling(c)) {
            n = sat(n, size[c]);
        }
        size[id] = n;
        if (t.has_val_anchor(id)) {
            ryml::csubstr a = t.val_anchor(id);
            anchors[std::string(a.str, a.len)] = n;
        }
        if (t.has_key_anchor(id)) {
            ryml::csubstr a = t.key_anchor(id);
            anchors[std::string(a.str, a.len)] = n;
        }
    }
    return size[root];
}

class Converter {
public:
    Converter(const ryml::Tree &t, const ryml::Parser &p, const std::string &text) :
        m_t(t), m_p(p), m_text(text), m_lines(text), m_depth(0) { }

    Mark nodeMark(ryml::id_type id) {
        return toMark(m_t.location(m_p, id));
    }

    // Where a value starts. For a key/value pair, rapidyaml's node location
    // is the key's, container or not; the value's own position is found from
    // its text pointer instead:
    //  - a scalar: the first character of its content (inside the quotes of
    //    a quoted scalar; the start of the first content line of a block
    //    scalar, F-4);
    //  - a container: the '[' or '{' of a flow container, the first key or
    //    '-' of a block one. rapidyaml stores that pointer in the container's
    //    val, as Tree::_location_from_cont does.
    Mark valMark(ryml::id_type id) {
        const char *start = nullptr;
        if (m_t.is_container(id)) {
            start = m_t.get(id)->m_val.scalar.str;
            ryml::id_type c = m_t.first_child(id);
            if (c != ryml::NONE && m_t.has_key(c)) {
                // A map's start is recorded after its first key is read.
                const char *k = m_t.key(c).str;
                if (k && (!start || k < start)) {
                    start = k;
                }
            }
        } else if (m_t.has_val(id)) {
            start = m_t.val(id).str;
        }
        ryml::csubstr src = m_p.source();
        if (start && start >= src.str && start <= src.str + src.len) {
            ryml::Location l = m_p.val_location(start);
            if (l) {
                return toMark(l);
            }
        }
        return nodeMark(id);
    }

    NodeUP convert(ryml::id_type id) {
        struct Guard {
            Guard(int &d) : m_d(d) { m_d++; }
            ~Guard() { m_d--; }
            int &m_d;
        } guard(m_depth);

        ryml::NodeType ty = m_t.type(id);
        NodeUP n(new Node());
        n->mark = valMark(id);

        if (m_depth > MaxNesting) {
            throw YamlError(n->mark, "YAML nests too deeply (more than "
                + std::to_string(MaxNesting) + " levels)");
        }

        if (m_t.has_val_tag(id)) {
            throw YamlError(n->mark, "YAML tags ('!...') are not supported in rule files");
        }

        if (m_t.is_map(id)) {
            n->kind = Node::Kind::Map;
            n->style = ty.is_flow() ? Node::Style::Flow : Node::Style::Block;
            std::map<std::string, Mark> seen;
            for (ryml::id_type c=m_t.first_child(id); c!=ryml::NONE; c=m_t.next_sibling(c)) {
                Node::Member m;
                if (m_t.has_key_tag(c)) {
                    throw YamlError(nodeMark(c), "YAML tags ('!...') are not supported in rule files");
                }
                ryml::csubstr k = m_t.key(c);
                m.key = std::string(k.str ? k.str : "", k.len);
                m.keyMark = nodeMark(c);
                auto it = seen.find(m.key);
                if (it != seen.end()) {
                    YamlError err(m.keyMark, "duplicate key '" + m.key
                        + "' (first defined on line " + std::to_string(it->second.line) + ")");
                    err.related = it->second;
                    err.hasRelated = true;
                    throw err;
                }
                seen[m.key] = m.keyMark;
                m.value = convert(c);
                n->members.push_back(std::move(m));
            }
            return n;
        }

        if (m_t.is_seq(id)) {
            n->kind = Node::Kind::Seq;
            n->style = ty.is_flow() ? Node::Style::Flow : Node::Style::Block;
            for (ryml::id_type c=m_t.first_child(id); c!=ryml::NONE; c=m_t.next_sibling(c)) {
                n->items.push_back(convert(c));
            }
            return n;
        }

        // Scalar
        ryml::csubstr v = m_t.has_val(id) ? m_t.val(id) : ryml::csubstr();
        n->s = std::string(v.str ? v.str : "", v.len);
        if (ty.is_val_squo()) {
            n->style = Node::Style::SingleQuoted;
        } else if (ty.is_val_dquo()) {
            n->style = Node::Style::DoubleQuoted;
            joinSurrogates(n->s);
        } else if (ty.is_val_literal()) {
            n->style = Node::Style::Literal;
        } else if (ty.is_val_folded()) {
            n->style = Node::Style::Folded;
        } else {
            n->style = Node::Style::Plain;
        }

        if (n->style == Node::Style::Plain) {
            if (!v.str) {
                n->kind = Node::Kind::Null;
            } else {
                typePlain(*n);
            }
        } else {
            n->kind = Node::Kind::String;
        }

        if (n->kind == Node::Kind::String) {
            // The value's start, as rapidyaml placed it: inside the quotes,
            // or for a block scalar the start of the line after its header.
            // A block scalar's line and column from rapidyaml are not
            // reliable (column 0 when the body opens with a blank line), so
            // its mark is recomputed from the map: the first content byte.
            uint32_t begin = n->mark.offset;
            n->srcExact = mapScalar(m_text, begin, n->style, n->s, n->srcMap);
            if (n->style == Node::Style::Literal || n->style == Node::Style::Folded) {
                size_t i = 0;
                while (i < n->s.size() && n->s[i] == '\n') {
                    i++;
                }
                n->mark = m_lines.at(n->srcMap[i < n->s.size() ? i : 0]);
            }
        }
        return n;
    }

private:
    const ryml::Tree    &m_t;
    const ryml::Parser  &m_p;
    const std::string   &m_text;
    LineIndex           m_lines;
    int                 m_depth;
};

}

NodeUP parse(const std::string &name, const std::string &text) {
    ryml::Callbacks cb = callbacks();

    // Also install them process-wide. Some rapidyaml paths (allocation
    // failure inside Tree::resolve(), found in C0) report through the global
    // callbacks rather than the tree's, and the default global handler
    // aborts the process -- the Python interpreter or the editor's language
    // server with it. pssparser is the only rapidyaml user in its process.
    static bool global_set = false;
    if (!global_set) {
        ryml::set_callbacks(cb);
        global_set = true;
    }
    ryml::EventHandlerTree handler(cb);
    ryml::Parser parser(&handler, ryml::ParserOptions().locations(true));
    ryml::Tree tree(cb);

    try {
        ryml::parse_in_arena(&parser, ryml::to_csubstr(name), ryml::to_csubstr(text), &tree);

        ryml::id_type root = tree.root_id();
        if (tree.is_stream(root)) {
            ryml::id_type ndocs = tree.num_children(root);
            if (ndocs == 0) {
                return NodeUP(new Node());
            }
            if (ndocs > 1) {
                ryml::id_type second = tree.next_sibling(tree.first_child(root));
                throw YamlError(toMark(tree.location(parser, second)),
                    "a rule file holds one YAML document; found "
                    + std::to_string(ndocs) + " ('---' separates documents)");
            }
            root = tree.first_child(root);
        }

        // Anchors and aliases (including `<<` merge keys) are expanded before
        // conversion, so nothing downstream ever sees a reference -- once the
        // expansion is known to be bounded.
        if (expandedSize(tree, root) > MaxNodes) {
            throw YamlError(toMark(tree.location(parser, root)),
                "YAML aliases expand this file to more than "
                + std::to_string(MaxNodes) + " nodes");
        }
        tree.resolve();

        Converter conv(tree, parser, text);
        return conv.convert(root);
    } catch (const RymlFailure &f) {
        Mark m;
        if (f.has_yaml_loc) {
            m.line = (f.loc.line == ryml::npos) ? 0 : static_cast<uint32_t>(f.loc.line);
            m.col = (f.loc.col == ryml::npos) ? 0 : static_cast<uint32_t>(f.loc.col);
            m.offset = (f.loc.offset == ryml::npos) ? 0 : static_cast<uint32_t>(f.loc.offset);
        }
        std::string msg = f.msg;
        // rapidyaml prefixes its messages with the location; strip a leading
        // "file:line:col: " so the message reads once at our location.
        size_t p = msg.find(": ");
        if (!name.empty() && msg.compare(0, name.size(), name) == 0 && p != std::string::npos) {
            msg = msg.substr(p + 2);
        }
        throw YamlError(m, "YAML syntax error: " + msg);
    }
}

}
}
}
