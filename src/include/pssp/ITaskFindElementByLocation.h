/**
 * ITaskFindElementByLocation.h
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
#include <memory>
#include <vector>
#include "pssp/ast/IScopeChild.h"
#include "pssp/ast/ISymbolScope.h"

namespace pssp {



class ITaskFindElementByLocation;
using ITaskFindElementByLocationUP=std::unique_ptr<ITaskFindElementByLocation>;
class ITaskFindElementByLocation {
public:
    enum class ElemKind {
        Expr,
        Field,
        Type
    };

    struct Position {
        int32_t         lineno;
        int32_t         linepos;
    };

    struct Range {
        Position        start;
        Position        end;
    };

    struct Result {
        bool                    isValid;
        union {
            struct {
                ast::IExpr      *ctxt;
                ast::IExpr      *elem;
            } e;
            ast::IScopeChild    *c;
        } source;
        ElemKind                sourceKind;
        Range                   sourceRange;
        ast::IScopeChild        *target;
        ElemKind                targetKind;
    };
public:

    virtual ~ITaskFindElementByLocation() { }

    virtual ITaskFindElementByLocation::Result find(
        ast::ISymbolScope                   *root,
        ast::IGlobalScope                   *file,
        int32_t                             lineno,
        int32_t                             linepos,
        int32_t                             fuzz=0) = 0;

};

} /* namespace pssp */


