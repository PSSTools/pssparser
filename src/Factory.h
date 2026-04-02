/**
 * Factory.h
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
#include "pssp/ast/IFactory.h"
#include "pssp/IFactory.h"
#include "pssp/ISymbolTable.h"

namespace pssp {




class Factory;
using FactoryUP=std::unique_ptr<Factory>;
class Factory : public virtual IFactory {
public:
    Factory();

    Factory(ast::IFactory *ast_factory);

    virtual ~Factory();

    virtual void init(
        dmgr::IDebugMgr     *dmgr,
        ast::IFactory       *ast_factory) override;

    virtual ast::IFactory *getAstFactory() override;

    virtual dmgr::IDebugMgr *getDebugMgr() override {
        return m_dmgr;
    }
    
    virtual void loadStandardLibrary(
        IAstBuilder             *ast_builder,
        ast::IGlobalScope       *global) override;

    virtual ILookupLocationResult *lookupLocation(
        ast::IRootSymbolScope   *root,
        ast::IScope             *scope,
        int32_t                 lineno,
        int32_t                 linepos) override;

    virtual IAstBuilder *mkAstBuilder(IMarkerListener *marker_l) override;

    virtual ILinker *mkAstLinker() override;

    virtual ISymbolTableIterator *mkAstSymbolTableIterator(
        ast::ISymbolScope       *root) override;

    virtual IMarker *mkMarker(
        const std::string           &msg,
        MarkerSeverityE             severity,
        const ast::Location         &loc) override;

    virtual IMarkerCollector *mkMarkerCollector() override;

    virtual INameResolver *mkNameResolver(
        ISymbolTable            *symtab,
        IMarkerListener         *marker_l) override;


    virtual ISymbolTable *mkSymbolTable() override;

    virtual ITaskFindElementByLocation *mkTaskFindElementByLocation() override;

    virtual IValInt *mkValInt(
        bool        is_signed,
        int32_t     width,
        int64_t     init=0) override;

    static IFactory *inst();

private:
    static FactoryUP                    m_inst;
    dmgr::IDebugMgr                     *m_dmgr;
    ast::IFactory                       *m_ast_factory;

};

}
