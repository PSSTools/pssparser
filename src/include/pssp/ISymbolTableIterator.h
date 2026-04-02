/**
 * ISymbolTableIterator.h
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
#include <string>
#include "pssp/ast/IScopeChild.h"
#include "pssp/ast/ISymbolRefPath.h"

namespace pssp {


class ISymbolTableIterator;
using ISymbolTableIteratorUP=std::unique_ptr<ISymbolTableIterator>;
class ISymbolTableIterator {
public:

    virtual ~ISymbolTableIterator() { }

    virtual int32_t findLocalSymbol(const std::string &name) = 0;

    virtual ast::ISymbolRefPath *findLocalSymbolPath(const std::string &name) = 0;

    virtual ast::ISymbolRefPath *getScopeSymbolPath(int off=0) const = 0;

    virtual ast::ISymbolScope *getRootScope() const = 0;

    virtual ast::ISymbolScope *getScope(int32_t off=0) = 0;

    virtual ast::IScopeChild *getScopeChild(int32_t idx) = 0;

    virtual ast::IScopeChild *resolveAbsPath(const ast::ISymbolRefPath *path) = 0;

    /**
     * @brief Finds and pushes a named scope.
     * 
     * @param name 
     * @return int32_t <index> on success and -1 on failure
     */
    virtual int32_t pushNamedScope(const std::string &name) = 0;

    virtual void pushScope(
        ast::IScopeChild            *s,
        ast::SymbolRefPathElemKind  kind=ast::SymbolRefPathElemKind::ElemKind_ChildIdx) = 0;

    virtual void popScope() = 0;

    virtual bool hasScopes() = 0;

    virtual ISymbolTableIterator *clone() const = 0;

};

}
