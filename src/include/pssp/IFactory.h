/**
 * IFactory.h
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
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IFactory.h"
#include "pssp/IAstBuilder.h"
#include "pssp/ILinker.h"
#include "pssp/ILookupLocationResult.h"
#include "pssp/IMarkerCollector.h"
#include "pssp/IMarkerListener.h"
#include "pssp/INameResolver.h"
#include "pssp/ISymbolTable.h"
#include "pssp/ITaskFindElementByLocation.h"
#include "pssp/IValFactory.h"

namespace pssp {


class IAstBuilder;
class IMarkerListener;

class IFactory;
using IFactoryUP=std::unique_ptr<IFactory>;
class IFactory : public virtual IValFactory {
public:

    virtual ~IFactory() { }

    virtual void init(
        dmgr::IDebugMgr     *dmgr,
        ast::IFactory       *ast_factory) = 0;

    virtual ast::IFactory *getAstFactory() = 0;

    virtual dmgr::IDebugMgr *getDebugMgr() = 0;

    virtual void loadStandardLibrary(
        IAstBuilder             *ast_builder,
        ast::IGlobalScope       *global) = 0;

    virtual ILookupLocationResult *lookupLocation(
        ast::IRootSymbolScope   *root,
        ast::IScope             *scope,
        int32_t                 lineno,
        int32_t                 linepos) = 0;

    virtual IAstBuilder *mkAstBuilder(IMarkerListener *marker_l) = 0;

    virtual ILinker *mkAstLinker() = 0;

    virtual ISymbolTableIterator *mkAstSymbolTableIterator(
        ast::ISymbolScope       *root) = 0;

    virtual IMarker *mkMarker(
        const std::string           &msg,
        MarkerSeverityE             severity,
        const ast::Location         &loc) = 0;

    virtual IMarkerCollector *mkMarkerCollector() = 0;

    virtual INameResolver *mkNameResolver(
        ISymbolTable            *symtab,
        IMarkerListener         *marker_l) = 0;


    virtual ISymbolTable *mkSymbolTable() = 0;

    virtual ITaskFindElementByLocation *mkTaskFindElementByLocation() = 0;

};

}
