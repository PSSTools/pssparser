/**
 * TaskFindPathElem.h
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
 * Created on:
 *     Author: 
 */
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/ISymbolScope.h"
#include "NameLookup.h"

namespace pssp {

/**
 * A qualified step: `id` as a member of `src`, its base types included.
 * Kept so that callers need not change; see NameLookup::lookupMember.
 */
class TaskFindPathElem {
public:
    struct Result {
        ast::IScopeChild        *sym;
        int32_t                 idx;
        int32_t                 super_idx;
        /** See NameLookup::Member::fwd_pkg. */
        int32_t                 fwd_pkg;
        /** See NameLookup::Member::item_idx and abs_path (`enum_items`). */
        int32_t                 item_idx = -1;
        std::vector<ast::SymbolRefPathElem> abs_path;

        /** Append this step to `path`, the path to the scope searched. */
        void appendTo(ast::ISymbolRefPath *path) const {
            NameLookup::Member m;
            m.idx = idx;
            m.super_depth = super_idx;
            m.fwd_pkg = fwd_pkg;
            m.item_idx = item_idx;
            m.abs_path = abs_path;
            m.appendTo(path);
        }
    };

    TaskFindPathElem(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root) : m_dmgr(dmgr), m_root(root) { }

    virtual ~TaskFindPathElem() { }

    /**
     * `sym` is null on a miss, and also when the model is incomplete and a
     * caller has no scope to search. `super_idx` is the number of base types
     * crossed. `enum_items`: see NameLookup::lookupMember; only for a
     * caller that appends the result with appendTo().
     */
    Result find(
        ast::ISymbolScope       *src,
        ast::IExprId            *id,
        bool                    enum_items=false) {
        if (!src || !id) {
            return {0, -1, -1, -1};
        }
        NameLookup::Member m = NameLookup::lookupMember(
            m_dmgr, m_root, src, id->getId(), enum_items);
        return {m.sym, m.idx, m.super_depth, m.fwd_pkg, m.item_idx, m.abs_path};
    }

private:
    dmgr::IDebugMgr             *m_dmgr;
    ast::ISymbolScope           *m_root;
};

}
