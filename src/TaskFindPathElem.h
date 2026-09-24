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
    };

    TaskFindPathElem(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root) : m_dmgr(dmgr), m_root(root) { }

    virtual ~TaskFindPathElem() { }

    /**
     * `sym` is null on a miss, and also when the model is incomplete and a
     * caller has no scope to search. `super_idx` is the number of base types
     * crossed.
     */
    Result find(
        ast::ISymbolScope       *src,
        ast::IExprId            *id) {
        if (!src || !id) {
            return {0, -1, -1};
        }
        NameLookup::Member m = NameLookup::lookupMember(
            m_dmgr, m_root, src, id->getId());
        return {m.sym, m.idx, m.super_depth};
    }

private:
    dmgr::IDebugMgr             *m_dmgr;
    ast::ISymbolScope           *m_root;
};

}
