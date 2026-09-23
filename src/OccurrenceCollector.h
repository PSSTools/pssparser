/**
 * OccurrenceCollector.h
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
#pragma once
#include <map>
#include <string>
#include <tuple>
#include <unordered_map>
#include "dmgr/IDebugMgr.h"
#include "pssp/IOccurrenceCollector.h"

namespace pssp {

/**
 * Implements IOccurrenceCollector (pss-scrambler FR-001).
 *
 * The linker records what each reference element binds to in ExprId::decl,
 * and whole references carry a SymbolRefPath. This pass only reads those; it
 * resolves nothing itself, so it cannot disagree with the linker.
 *
 * A declaration is identified by the location of its name. Everything a
 * reference can bind to -- a symbol-tree wrapper, a member of a template
 * specialization (a copy of the generic's member, with the same location), a
 * loop variable the builder synthesized from the written one -- is mapped
 * back to the declaration whose name is at that location. That is what makes
 * `decl` the same object for every occurrence of one declaration.
 */
class OccurrenceCollector : public virtual IOccurrenceCollector {
public:
    OccurrenceCollector(dmgr::IDebugMgr *dmgr);

    virtual ~OccurrenceCollector();

    virtual void collect(
        ast::IRootSymbolScope       *root,
        std::vector<Occurrence>     &out) override;

    using LocKey = std::tuple<int32_t,int32_t,int32_t>;

    static LocKey key(const ast::Location &loc) {
        return LocKey(loc.fileid, loc.lineno, loc.linepos);
    }

    static bool hasLocation(const ast::IExprId *id) {
        return id && id->getLocation().lineno > 0
            && id->getLocation().linepos > 0;
    }

    /**
     * Whether a location identifies one name. Every standard-library file
     * has fileid 0 and every built-in -1, so their locations collide across
     * files; only user files (fileid >= 1) are keyed by location.
     */
    static bool isKeyable(const ast::IExprId *id) {
        return hasLocation(id) && id->getLocation().fileid >= 1;
    }

    /** The name a declaration is declared by, or null. */
    ast::IExprId *nameOf(ast::IScopeChild *c);

    /** Unwrap a symbol-tree node to the AST declaration it stands for. */
    ast::IScopeChild *unwrap(ast::IScopeChild *c);

    /** A package's qualified name, from the AST or from the symbol tree. */
    static std::string qname(ast::IPackageScope *p);
    static std::string qname(ast::ISymbolScope *s);

    /** The declaration `c` stands for, identified by its name's location. */
    ast::IScopeChild *canonical(ast::IScopeChild *c);

    /** The declaration `d` overrides or shadows in a base type, or null. */
    ast::IScopeChild *baseDecl(ast::IScopeChild *d);

    void addDecl(ast::IScopeChild *c);

    void addPackage(ast::IPackageScope *p);

    std::map<LocKey, ast::IScopeChild *> &decls() { return m_decls; }

    /** Record what a copy of `id` in a specialization binds to. */
    void addSpecBinding(ast::IExprId *id, ast::IScopeChild *decl);

    /**
     * What every specialization binds `id` to, or null: none bound it, or
     * they disagree (`conflict`).
     */
    ast::IScopeChild *specBinding(ast::IExprId *id, bool &conflict);

    /** The declaration whose name is `id`, or null. */
    ast::IScopeChild *lookupDecl(ast::IExprId *id) const;

    ast::IRootSymbolScope *root() const { return m_root; }

    OccurrenceResolution classify(ast::IScopeChild *decl);

private:
    dmgr::IDebugMgr                                 *m_dmgr;
    ast::IRootSymbolScope                           *m_root;
    std::map<LocKey, ast::IScopeChild *>            m_decls;
    // A package's symbol scope has no AST target: it stands for every
    // `package` block of that name. The first block is the declaration.
    std::map<std::string, ast::IPackageScope *>     m_packages;
    struct SpecBinding {
        ast::IScopeChild    *decl;
        bool                conflict;
    };
    std::map<LocKey, SpecBinding>                   m_spec_bindings;
};

}
