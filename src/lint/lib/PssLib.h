/*
 * PssLib.h
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
 * The PSS function library (lint-core-plan.md C6; lint-rule-expressions.md
 * §3, "PSS function library"): the functions that give rules their PSS
 * vocabulary, registered in the same registry as CEL's standard library
 * (CelFunctions.h), so the checker, level/scope inference and the generated
 * reference read them from one table.
 *
 * Functions that need more than their operands (a node's parent, later the
 * linker's indexes) read the run's Context, which the runner passes to the
 * evaluator as its cel::Host. Called without one, they return an error.
 */
#pragma once
#include <cstdint>
#include <set>
#include <string>
#include <utility>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include "Reflect.h"
#include "../cel/CelFunctions.h"

namespace pssp {
namespace ast {
class IRootSymbolScope;
class IScopeChild;
class ITypeIdentifier;
}
namespace lint {
namespace lib {

namespace rf = pssp::ast::reflect;

/**
 * What the library knows about the model a run covers.
 *
 * - Parents: expressions, statements and constraint items have no parent
 *   pointer, so index() records every node's parent under a root before
 *   any rule runs there. A root (a file's GlobalScope) has none. With a
 *   model, a node in a file not indexed yet (another file, the standard
 *   library) has its file indexed when first asked about.
 * - Ownership (C6.2): the roots index()ed are the files the run owns; the
 *   model's other units are not owned. The standard library is fileid 0,
 *   the linker's built-in units -1.
 * - Symbols (C6.2): what each identifier names, from the linker through
 *   OccurrenceCollector, collected once, the first time a rule asks.
 * - Declaration paths (C6.2): lint/declpath.py's paths, memoised.
 */
/**
 * The identifier a reference names: an ExprId itself, or the last name of a
 * path or type (`a.b.c` -> c, `p::S` -> S); null for another node.
 */
rf::Node refIdent(rf::Node n);

/** A TypeIdentifier as written (`p::S`, `::S`), or "" for another node. */
std::string spelledType(const rf::Node &n);

class Context : public cel::Host {
public:
    Context();
    virtual ~Context();

    /**
     * The linked model the run's files belong to, or null (unlinked): the
     * symbol functions then return an error.
     */
    void setModel(ast::IRootSymbolScope *model) { m_model = model; }

    ast::IRootSymbolScope *model() const { return m_model; }

    /**
     * Records the parents of the nodes under `root`, a file the run owns;
     * again for the same root does nothing.
     */
    void index(const rf::Node &root) { indexTree(root, true); }

    /** Whether `n` is under an indexed root (a root is). */
    bool indexed(const rf::Node &n) const { return m_parent.count(n.ptr) != 0; }

    /** The node's parent: null for a root, or a node in no indexed tree. */
    rf::Node parentOf(const rf::Node &n) const;

    /** The file (GlobalScope) a node is in, or null if it is in none known. */
    rf::Node rootOf(const rf::Node &n) const;

    /** Whether the node is in one of the files the run owns. */
    bool owned(const rf::Node &n) const;

    /** The fileid of the file the node is in; -2 when it is in none known. */
    int32_t fileidOf(const rf::Node &n) const;

    /**
     * The declaration an identifier names, as the linker bound it; null
     * when it is unbound or a built-in. False when there is no model.
     */
    bool declOf(const rf::Node &id, rf::Node &decl) const;

    /**
     * The identifiers naming `decl` in the model's user files, in (file,
     * line, column) order, its own name not included (C6.3). Null when
     * there is no model.
     */
    const std::vector<rf::Node> *usesOf(const rf::Node &decl) const;

    /**
     * Folds `n` to a constant (C6.4; ConstEval.h): an expression, a `const`
     * field (its initializer) or a bound template value parameter. False
     * when it does not fold, or folds to an integer wider than 64 bits or
     * an unsigned one above INT64_MAX. `isBool` is set for a 1-bit unsigned
     * result, which is how the folder carries a bool. Needs the model.
     */
    bool constFold(const rf::Node &n, int64_t &v, bool &isBool) const;

    /** Whether `n` is `anc` or under it. */
    bool within(const rf::Node &n, const rf::Node &anc) const;

    /**
     * The node's declaration path (lint/declpath.py): `p::C::A`,
     * `p::C::A::constraint c`, `p::C::A::f` for a field. A node that
     * declares nothing has the path of the declaration it is in; "" at file
     * level. `steps` is set to the ancestors visited.
     */
    const std::string &declPath(const rf::Node &n, uint64_t &steps) const;

    /** Whether the node declares something, so has a path of its own. */
    bool declares(const rf::Node &n) const;

    /**
     * Whether the node is a scope declpath.py indexes: one that adds a
     * segment to its own path (not under a function, exec, ... or a scope
     * with no location).
     */
    bool ownPath(const rf::Node &n) const;

    /**
     * The node's path, when the path names the node itself (a declaration
     * not inside a function, exec, ... block); false otherwise.
     */
    bool namedPath(const rf::Node &n, std::string &path) const;

    /**
     * The declaration a type reference names (C6.8): a DataTypeUserDefined
     * or a TypeIdentifier, through typedefs, to a type (TypeScope) or an
     * enum. A template use gives its specialization. Null for a built-in
     * type, an unresolved reference, a template parameter of a generic,
     * and any other node. False when there is no model.
     */
    bool typeDecl(const rf::Node &n, rf::Node &decl) const;

    /**
     * The type a PSS name (`p::S`, `::S`; cel::splitTypePath) names,
     * typedefs followed; null when the model has none (and the name is
     * recorded, see unknownTypes()). Memoised. False when there is no model.
     */
    bool typeNamed(const std::string &path, rf::Node &decl) const;

    /**
     * Whether type `t` is `base` or inherits from it, following `super_t`
     * from `t` itself. A specialization matches its generic, so a generic
     * `base` matches every specialization. `steps`: one per type visited.
     */
    bool derivesFrom(const rf::Node &t, const rf::Node &base, uint64_t &steps) const;

    /** A type name typeNamed() did not find, with the rule and node it was asked for. */
    struct UnknownType {
        const void      *rule;
        rf::Node        node;
        std::string     path;
    };

    /** What the runner is evaluating, recorded with an unknown type name. */
    void setCurrent(const void *rule, const rf::Node &node) const {
        m_curRule = rule;
        m_curNode = node;
    }

    /** Each (rule, unknown type name), once, in the order first asked. */
    const std::vector<UnknownType> &unknownTypes() const { return m_unknown; }

    uint64_t numIndexed() const { return m_parent.size(); }

private:
    void indexTree(const rf::Node &root, bool owned) const;
    void indexModel() const;
    void collectSymbols() const;
    // The type or enum `sc` stands for: a symbol-tree node unwrapped,
    // typedefs and bound template parameters followed; null for another.
    ast::IScopeChild *typeOf(ast::IScopeChild *sc) const;
    // What a type name names, unwrapped no further: its target path, else
    // (a generic's base) its identifier's binding.
    ast::IScopeChild *resolveTypeId(ast::ITypeIdentifier *tid) const;
    void mapGenerics() const;
    int32_t segmentNumber(const rf::Node &scope, const rf::Node &seg) const;
    // The path, and whether the walk down to `n` reached it as a segment.
    std::string buildPath(const rf::Node &n, uint64_t &steps, bool &reached) const;

private:
    ast::IRootSymbolScope                                       *m_model = nullptr;
    // Filled on demand from const queries: the context is the evaluator's
    // read-only Host, but what it knows grows as rules ask.
    mutable std::unordered_map<const void *, rf::Node>          m_parent;
    mutable std::unordered_set<const void *>                    m_owned;     // roots
    mutable bool                                                m_modelIndexed = false;
    mutable bool                                                m_symbols = false;
    mutable std::unordered_map<const void *, rf::Node>          m_decl;      // ExprId -> decl
    mutable std::unordered_map<const void *, std::vector<rf::Node>> m_uses; // decl -> ExprIds
    mutable std::unordered_map<const void *, std::string>       m_path;
    // A numbered segment ("constraint", "exec", ...) -> its #n, for every
    // numbered segment of each scope numbered so far.
    mutable std::unordered_map<const void *, int32_t>           m_segNum;
    mutable std::unordered_set<const void *>                    m_numbered;  // scopes done
    // C6.8: type_named() results by path, a specialization's generic, and
    // the unknown names asked for, by rule.
    mutable std::unordered_map<std::string, rf::Node>           m_named;
    mutable bool                                                m_genericsMapped = false;
    mutable std::unordered_map<const void *, rf::Node>          m_generic;
    mutable const void                                          *m_curRule = nullptr;
    mutable rf::Node                                            m_curNode;
    mutable std::vector<UnknownType>                            m_unknown;
    mutable std::set<std::pair<const void *, std::string>>      m_unknownSeen;
};

}
}
}
