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
#include <set>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskFindPathElem : public virtual ast::VisitorBase {
public:
    struct Result {
        ast::IScopeChild        *sym;
        int32_t                 idx;
        int32_t                 super_idx;
    };

    TaskFindPathElem(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root);

    virtual ~TaskFindPathElem();

    Result find(
        ast::ISymbolScope       *src,
        ast::IExprId            *id);

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

private:
    static dmgr::IDebug             *m_dbg;
    dmgr::IDebugMgr                 *m_dmgr;
    ast::ISymbolScope               *m_root;
    ast::IExprId                    *m_id;
    Result                          m_ret;
    int32_t                         m_super_depth;

    /**
     * Type scopes on the current super-type chain.
     *
     * The search walks from a type to its base and keeps going until it finds
     * the name or runs out of bases. "Runs out of bases" assumes the chain
     * ends, and inheritance is a reference the user wrote, so it need not:
     * `struct A : B {}; struct B : A {};` is a ring.
     *
     * Note that only a search that FAILS goes round it -- one that finds the
     * name stops at the scope holding it. So the crash this prevents is not
     * reached by the cyclic declaration itself, but by the first typo against
     * a type that participates in one, which is why it survived so long.
     *
     * m_super_depth is not this guard and cannot become it: it is reported to
     * the caller as `super_idx`, the number of hops the name was found at.
     */
    std::set<ast::IScopeChild *>    m_super_chain;

};

}
