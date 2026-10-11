/*
 * Walker.cpp
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
#include <string>
#include "Walker.h"
#include "../cel/CelNode.h"
#include "../rules/Rule.h"

namespace pssp {
namespace lint {
namespace run {

namespace {

// Kinds named in `names`, with every class deriving from one of them.
void classTable(const std::vector<uint16_t> &named, std::vector<bool> &out) {
    out.assign(rf::NumClasses + 1, false);
    for (uint16_t k=1; k<=rf::NumClasses; k++) {
        for (uint16_t c : named) {
            if (cel::isSubclass(k, c)) {
                out[k] = true;
                break;
            }
        }
    }
}

bool isChildField(const rf::FieldInfo &f) {
    return f.owned && (f.type == rf::FieldType::Node
        || (f.type == rf::FieldType::List && f.elem == rf::FieldType::Node));
}

// Per class: the owning node fields, inherited ones first, as children()
// reads them. Built once.
const std::vector<std::vector<uint16_t>> &childFields() {
    static const std::vector<std::vector<uint16_t>> table = [] {
        std::vector<std::vector<uint16_t>> t(rf::NumClasses + 1);
        for (uint16_t k=1; k<=rf::NumClasses; k++) {
            std::vector<uint16_t> chain;
            for (uint16_t c=k; c; c=rf::classes[c].super) {
                chain.push_back(c);
            }
            for (auto it=chain.rbegin(); it!=chain.rend(); it++) {
                const rf::ClassInfo &ci = rf::classes[*it];
                for (uint16_t f=ci.firstField; f<ci.firstField+ci.numFields; f++) {
                    if (isChildField(rf::fields[f])) {
                        t[k].push_back(f);
                    }
                }
            }
        }
        return t;
    }();
    return table;
}

// Per class: the index of its `location` field (inherited or declared), or -1.
const std::vector<int32_t> &locationFields() {
    static const std::vector<int32_t> table = [] {
        std::vector<int32_t> t(rf::NumClasses + 1, -1);
        for (uint16_t k=1; k<=rf::NumClasses; k++) {
            for (uint16_t c=k; c && t[k] < 0; c=rf::classes[c].super) {
                const rf::ClassInfo &ci = rf::classes[c];
                for (uint16_t f=ci.firstField; f<ci.firstField+ci.numFields; f++) {
                    if (rf::fields[f].type == rf::FieldType::Struct
                            && std::string(rf::fields[f].name) == "location") {
                        t[k] = f;
                        break;
                    }
                }
            }
        }
        return t;
    }();
    return table;
}

int32_t structMember(const rf::Value &st, const char *name) {
    const rf::StructInfo &si = rf::structs[st.type];
    for (uint16_t i=0; i<si.numFields; i++) {
        if (std::string(si.fields[i].name) == name) {
            return static_cast<int32_t>(si.fields[i].get(st.st).i);
        }
    }
    return -1;
}

}

void AncestorClasses::build(const rules::AncestorTest &t) {
    present = t.present;
    if (!present) {
        return;
    }
    classTable(t.kind.classes, kind);
    classTable(t.stop.classes, stop);
}

bool AncestorClasses::found(const std::vector<rf::Node> &stack) const {
    for (auto it=stack.rbegin(); it!=stack.rend(); it++) {
        if (kind[it->kind]) {
            return true;
        }
        if (stop[it->kind]) {
            return false;
        }
    }
    return false;
}

Dispatch::Dispatch(const std::vector<const rules::Rule *> &rules)
        : m_byKind(rf::NumClasses + 1) {
    // Entries first, then the index: the index points into m_entries.
    m_entries.reserve(rules.size());
    for (const rules::Rule *r : rules) {
        Entry e;
        e.rule = r;
        e.inside.build(r->m_inside);
        e.notInside.build(r->m_notInside);
        m_entries.push_back(std::move(e));
    }
    std::vector<bool> matched;
    for (const Entry &e : m_entries) {
        classTable(e.rule->m_match.classes, matched);
        for (uint16_t k=1; k<=rf::NumClasses; k++) {
            if (matched[k]) {
                m_byKind[k].push_back(&e);
            }
        }
    }
}

void Walker::children(const rf::Node &n, std::vector<rf::Node> &out) {
    if (!n || n.kind > rf::NumClasses) {
        return;
    }
    for (uint16_t fi : childFields()[n.kind]) {
        const rf::FieldInfo &f = rf::fields[fi];
        if (f.type == rf::FieldType::Node) {
            rf::Value v = f.get(n.ptr, n.kind);
            if (v.n) {
                out.push_back(v.n);
            }
        } else {
            uint32_t sz = f.size(n.ptr, n.kind);
            for (uint32_t i=0; i<sz; i++) {
                rf::Value v = f.at(n.ptr, n.kind, i);
                if (v.n) {
                    out.push_back(v.n);
                }
            }
        }
    }
}

void Walker::walk(const rf::Node &root, const MatchFn &fn) {
    // Iterative, so a deep expression cannot overflow the (WASM) stack. A
    // frame is a visited node and the children it has left to visit.
    struct Frame {
        rf::Node                n;
        std::vector<rf::Node>   kids;
        size_t                  next = 0;
    };
    std::vector<Frame> frames;
    m_stack.clear();

    auto visit = [&](const rf::Node &n, const rf::Node &parent) {
        if (!n || n.kind > rf::NumClasses || m_parent.count(n.ptr)) {
            return;
        }
        m_parent.emplace(n.ptr, parent);
        for (const Dispatch::Entry *e : m_dispatch.forKind(n.kind)) {
            if (e->inside.present && !e->inside.found(m_stack)) {
                continue;
            }
            if (e->notInside.present && e->notInside.found(m_stack)) {
                continue;
            }
            fn(*e->rule, n);
        }
        frames.emplace_back();
        frames.back().n = n;
        children(n, frames.back().kids);
        m_stack.push_back(n);
    };

    visit(root, rf::Node());
    while (!frames.empty()) {
        Frame &f = frames.back();
        if (f.next < f.kids.size()) {
            // Copies: visit() may grow `frames`, which moves `f`.
            rf::Node kid = f.kids[f.next++];
            rf::Node parent = f.n;
            visit(kid, parent);
        } else {
            frames.pop_back();
            m_stack.pop_back();
        }
    }
}

bool Walker::location(const rf::Node &n, int32_t &fileid, int32_t &line, int32_t &col) {
    ast::Location loc;
    bool ok = location(n, loc);
    fileid = loc.fileid;
    line = loc.lineno;
    col = loc.linepos;
    return ok;
}

bool Walker::location(const rf::Node &n, ast::Location &loc) {
    loc = ast::Location();
    if (!n || n.kind > rf::NumClasses || locationFields()[n.kind] < 0) {
        return false;
    }
    const rf::FieldInfo &f = rf::fields[locationFields()[n.kind]];
    rf::Value v = f.get(n.ptr, n.kind);
    if (v.kind != rf::Value::Kind::Struct) {
        return false;
    }
    loc.fileid = structMember(v, "fileid");
    loc.lineno = structMember(v, "lineno");
    loc.linepos = structMember(v, "linepos");
    loc.extent = structMember(v, "extent");
    return loc.lineno > 0;
}

rf::Node Walker::parentOf(const rf::Node &n) const {
    auto it = m_parent.find(n.ptr);
    return (it != m_parent.end()) ? it->second : rf::Node();
}

std::vector<rf::Node> Walker::ancestorsOf(const rf::Node &n) const {
    std::vector<rf::Node> out;
    for (rf::Node p=parentOf(n); p; p=parentOf(p)) {
        out.push_back(p);
    }
    return out;
}

}
}
}
