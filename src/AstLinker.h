/**
 * AstLinker.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include <vector>
#include <unordered_set>
#include "dmgr/IDebugMgr.h"
#include "pssp/IFactory.h"
#include "pssp/ILinker.h"
#include "pssp/ast/IFactory.h"

namespace pssp {




class AstLinker : public virtual ILinker {
public:
    AstLinker(
        dmgr::IDebugMgr     *dmgr,
        IFactory            *factory);

    virtual ~AstLinker();

    virtual ast::IRootSymbolScope *link(
        IMarkerListener                         *marker_l,
        const std::vector<ast::IGlobalScope *>  &scopes,
        bool                                    own_scopes) override;

    virtual ast::IRootSymbolScope *linkOverlay(
        IMarkerListener                         *marker_l,
        ast::IRootSymbolScope                   *base_symtab,
        ast::IGlobalScope                       *overlay,
        bool                                    own_scopes) override;

private:
    static dmgr::IDebug                         *m_dbg;
    dmgr::IDebugMgr                             *m_dmgr;
    IFactory                                    *m_factory;
    ast::IFactory                               *m_ast_factory;
    ast::IGlobalScope                           *m_file;
    std::vector<std::unordered_set<int32_t>>    m_inbound_refs;
    std::vector<std::unordered_set<int32_t>>    m_outbound_refs;
};

}
