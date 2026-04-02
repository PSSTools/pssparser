/**
 * INamespace.h
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
#include "pssp/ISymbol.h"
#include "pssp/ISymbolRef.h"

namespace pssp {


class ITypeDecl;

class INamespace;
using INamespaceUP=std::unique_ptr<INamespace>;
class INamespace : public virtual ISymbol {
public:

    virtual ~INamespace() { }

    /**
     * @brief Finds a named symbol in this namespace if it exists
     * 
     * @param name 
     * @return ISymbolRef* relative to this namespace
     */
    virtual ISymbolRef *findSymbol(const std::string &name) = 0;

    /**
     * @brief Finds a named type in this namespace
     * 
     */
    virtual ITypeDecl *findTypeDecl(const std::string &name) = 0;


};

}
