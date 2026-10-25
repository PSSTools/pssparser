/**
 * TaskCollectRefTargets.h
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
#include <stdint.h>
#include <string>
#include <unordered_set>
#include <vector>
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/ISymbolRefPath.h"

namespace pssp {

/** One resolved reference: a SymbolRefPath and the node it names. */
struct RefTarget {
    const ast::ISymbolRefPath   *path;
    ast::IScopeChild            *target;
};

/** What a collection found; see TaskCollectRefTargets. */
struct RefTargetStats {
    int32_t total = 0;              ///< paths seen
    int32_t resolved = 0;           ///< paths with a target
    int32_t unresolved = 0;         ///< total - resolved
    int32_t inline_total = 0;       ///< paths with an ElemKind_Inline step
    int32_t inline_resolved = 0;    ///< ... of which the linker recorded a decl
    int32_t decl_agree = 0;         ///< non-inline: resolver == recorded decl
    int32_t decl_generic = 0;       ///< non-inline: decl is the generic type, target its specialization
    int32_t decl_disagree = 0;      ///< non-inline: both present, otherwise different

    std::string toJson() const;
};

/**
 * Resolve every SymbolRefPath in a linked tree to the node it names.
 *
 * The bindings ship a linked tree as data (the WASM wire format), and a
 * resolved reference is stored as an index *path*, not a pointer
 * (docs/design/rust-binding.md §1a). Interpreting a path takes
 * TaskResolveSymbolPathRef, which no binding should re-implement. So this
 * runs it once per path, after linking, and the binding ships the answers as
 * a side table keyed by node id.
 *
 * Paths come from their three owners: ExprRefPath (and its subclasses),
 * ExprRefName and TypeIdentifier.
 *
 * A path with an ElemKind_Inline step (not necessarily the first, whatever
 * the enum's doc says) is relative to a context the linker held while
 * resolving it (the traversed handle's type), and that context is not
 * recorded in the tree. For those, the target is what the linker
 * recorded on the reference's identifier (ExprId.decl), or none. On every
 * other path the same comparison is counted (decl_agree/decl_disagree),
 * which is how to judge whether that substitute is faithful.
 */
class TaskCollectRefTargets : public ast::VisitorBase {
public:
    explicit TaskCollectRefTargets(ast::IRootSymbolScope *root);

    virtual ~TaskCollectRefTargets();

    /** Walks the root; the result is in source-walk order, one entry per path. */
    const std::vector<RefTarget> &collect();

    const RefTargetStats &stats() const { return m_stats; }

    virtual void visitExprRefPath(ast::IExprRefPath *i) override;

    virtual void visitExprRefName(ast::IExprRefName *i) override;

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

private:
    void record(ast::ISymbolRefPath *path, ast::IScopeChild *recorded);

    static bool isSpecializationOf(ast::IScopeChild *spec, ast::IScopeChild *generic);

private:
    ast::IRootSymbolScope                           *m_root;
    std::vector<RefTarget>                          m_targets;
    std::unordered_set<const ast::ISymbolRefPath *> m_seen;
    RefTargetStats                                  m_stats;
};

}
