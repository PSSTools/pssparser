/*
 * Walker.h
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
 * The lint walk and dispatch (lint-core-plan.md C5.1; pss-rules-format.md
 * §3.2).
 *
 * - Rules are indexed by node kind once, when a Dispatch is built: a rule
 *   matching class K is listed under K and every class deriving from it
 *   (the reflection `super` chains), at most once per kind.
 * - One walk visits each node of the owned trees once, in pre-order, base
 *   class fields first and in declaration order. Only owning fields are
 *   followed (a reference to a declaration elsewhere is not a child), so a
 *   node outside the roots given is never visited.
 * - At each node, the rules listed for its kind are offered in load order,
 *   after their `inside:` / `not_inside:` tests, which read the ancestor
 *   stack the walk keeps.
 * - A parent map (node -> parent) is recorded as the walk goes, for
 *   parent() and ancestors() (C6.1): expressions have no parent pointer.
 */
#pragma once
#include <cstdint>
#include <functional>
#include <unordered_map>
#include <vector>
#include "Reflect.h"
#include "pssp/ast/Location.h"

namespace pssp {
namespace lint {
namespace rules {
class Rule;
struct AncestorTest;
}
namespace run {

namespace rf = pssp::ast::reflect;

/**
 * `inside:` or `not_inside:` as class tables indexed by node kind, the
 * subclasses of each named kind included.
 */
struct AncestorClasses {
    bool                    present = false;
    std::vector<bool>       kind;
    std::vector<bool>       stop;

    void build(const rules::AncestorTest &t);

    /**
     * Whether an ancestor in `stack` (root first, the node's parent last)
     * has one of the kinds, searching nearest first. The search ends at an
     * ancestor of a `stop:` kind, which is tested itself first: with
     * `{kind: Action, stop: Action}` the nearest action is found.
     */
    bool found(const std::vector<rf::Node> &stack) const;
};

/** Rules indexed by node kind. Holds pointers; the rules must outlive it. */
class Dispatch {
public:
    struct Entry {
        const rules::Rule   *rule;
        AncestorClasses     inside;
        AncestorClasses     notInside;
    };

    /** `rules` in the order they are offered at a node (load order). */
    explicit Dispatch(const std::vector<const rules::Rule *> &rules);

    /** The entries for a node of class `kind`, in rule order. */
    const std::vector<const Entry *> &forKind(uint16_t kind) const {
        return m_byKind[kind <= rf::NumClasses ? kind : 0];
    }

    size_t numRules() const { return m_entries.size(); }

private:
    std::vector<Entry>                          m_entries;
    std::vector<std::vector<const Entry *>>     m_byKind;   // [NumClasses + 1]
};

class Walker {
public:
    using MatchFn = std::function<void(const rules::Rule &, const rf::Node &)>;

    explicit Walker(const Dispatch &dispatch) : m_dispatch(dispatch) { }

    /**
     * Walks the tree under `root`, calling `fn` for each (rule, node) match
     * in walk order. Call once per owned root; a node reached a second time
     * (through another root) is not visited again.
     */
    void walk(const rf::Node &root, const MatchFn &fn);

    /** The node's parent, or a null node for a root or a node not walked. */
    rf::Node parentOf(const rf::Node &n) const;

    /** Whether the walk has visited `n`. */
    bool visited(const rf::Node &n) const { return m_parent.count(n.ptr) != 0; }

    /** The node's ancestors, nearest first; empty for a root. */
    std::vector<rf::Node> ancestorsOf(const rf::Node &n) const;

    /** The ancestors of the node being visited, root first. Valid during `fn`. */
    const std::vector<rf::Node> &stack() const { return m_stack; }

    uint64_t numVisited() const { return m_parent.size(); }

    /**
     * The owned children of `n`, in walk order: base class fields first,
     * each class's in declaration order, list elements in order.
     */
    static void children(const rf::Node &n, std::vector<rf::Node> &out);

    /**
     * The node's `location` (1-based line and column), or false when its
     * class has none or it is unset (line -1).
     */
    static bool location(const rf::Node &n, int32_t &fileid, int32_t &line, int32_t &col);

    /** location() with the extent too: the whole Location, unset if false. */
    static bool location(const rf::Node &n, ast::Location &loc);

private:
    const Dispatch                                  &m_dispatch;
    std::vector<rf::Node>                           m_stack;
    std::unordered_map<const void *, rf::Node>      m_parent;
};

}
}
}
