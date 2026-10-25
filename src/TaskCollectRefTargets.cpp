/**
 * TaskCollectRefTargets.cpp
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
#include <sstream>
#include "pssp/ast/IExprHierarchicalId.h"
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/ITypeIdentifierElem.h"
#include "pssp/impl/NodeKind.h"
#include "pssp/impl/TaskCollectRefTargets.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {

std::string RefTargetStats::toJson() const {
    std::stringstream ss;
    ss << "{\"total\":" << total
       << ",\"resolved\":" << resolved
       << ",\"unresolved\":" << unresolved
       << ",\"inline_total\":" << inline_total
       << ",\"inline_resolved\":" << inline_resolved
       << ",\"decl_agree\":" << decl_agree
       << ",\"decl_generic\":" << decl_generic
       << ",\"decl_disagree\":" << decl_disagree
       << "}";
    return ss.str();
}

TaskCollectRefTargets::TaskCollectRefTargets(ast::IRootSymbolScope *root) :
    m_root(root) { }

TaskCollectRefTargets::~TaskCollectRefTargets() { }

const std::vector<RefTarget> &TaskCollectRefTargets::collect() {
    m_targets.clear();
    m_seen.clear();
    m_stats = RefTargetStats();
    if (m_root) {
        m_root->accept(this);
    }
    return m_targets;
}

void TaskCollectRefTargets::visitExprRefPath(ast::IExprRefPath *i) {
    // The target names the path's first element; the rest of the path is
    // resolved relative to it.
    ast::IScopeChild *recorded = 0;
    if (ast::IExprRefPathContext *c = NodeKind::cast<ast::IExprRefPathContext>(i)) {
        if (c->getHier_id() && c->getHier_id()->getElems().size()
                && c->getHier_id()->getElems().front()->getId()) {
            recorded = c->getHier_id()->getElems().front()->getId()->getDecl();
        }
    }
    record(i->getTarget(), recorded);
    VisitorBase::visitExprRefPath(i);
}

void TaskCollectRefTargets::visitExprRefName(ast::IExprRefName *i) {
    record(i->getTarget(), i->getId() ? i->getId()->getDecl() : 0);
    VisitorBase::visitExprRefName(i);
}

void TaskCollectRefTargets::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    // The target names the whole qualified name: its last element.
    ast::IScopeChild *recorded = 0;
    if (i->getElems().size() && i->getElems().back()->getId()) {
        recorded = i->getElems().back()->getId()->getDecl();
    }
    record(i->getTarget(), recorded);
    // VisitorBase does not walk `target` (visit: false), and a path has no
    // children worth walking, so the base visit is enough.
    VisitorBase::visitTypeIdentifier(i);
}

bool TaskCollectRefTargets::isSpecializationOf(
        ast::IScopeChild        *spec,
        ast::IScopeChild        *generic) {
    ast::ISymbolTypeScope *g = NodeKind::cast<ast::ISymbolTypeScope>(generic);
    if (!g) {
        return false;
    }
    for (std::vector<ast::ISymbolTypeScopeUP>::const_iterator
            it=g->getSpec_types().begin(); it!=g->getSpec_types().end(); it++) {
        if (static_cast<ast::IScopeChild *>(it->get()) == spec) {
            return true;
        }
    }
    return false;
}

void TaskCollectRefTargets::record(
        ast::ISymbolRefPath     *path,
        ast::IScopeChild        *recorded) {
    if (!path || !m_seen.insert(path).second) {
        return;
    }
    m_stats.total++;

    // Not only the first step: a reference in a `with` block is recorded
    // through the enclosing scopes, then the Inline frame, then the member
    // (TaskResolveRefs pushes the frame onto the scope stack).
    bool is_inline = false;
    for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=path->getPath().begin(); it!=path->getPath().end(); it++) {
        if (it->kind == ast::SymbolRefPathElemKind::ElemKind_Inline) {
            is_inline = true;
            break;
        }
    }

    ast::IScopeChild *target = 0;
    if (is_inline) {
        m_stats.inline_total++;
        target = recorded;
        if (target) {
            m_stats.inline_resolved++;
        }
    } else {
        // No debug manager: this runs after linking, outside any task that
        // owns one, as OccurrenceCollector's fallback does.
        target = TaskResolveSymbolPathRef(0, m_root).resolve(path);
        if (target && recorded) {
            if (target == recorded) {
                m_stats.decl_agree++;
            } else if (isSpecializationOf(target, recorded)) {
                // `list<int>`: the identifier names the generic type, the
                // path its specialization. Both are right.
                m_stats.decl_generic++;
            } else {
                m_stats.decl_disagree++;
            }
        }
    }

    if (target) {
        m_stats.resolved++;
        m_targets.push_back({path, target});
    } else {
        m_stats.unresolved++;
    }
}

}
