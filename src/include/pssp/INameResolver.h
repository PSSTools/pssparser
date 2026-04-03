/**
 * INameResolver.h
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
#include "pssp/ast/ITypeScope.h"
#include "pssp/INamespace.h"
#include "pssp/ITypeDecl.h"

namespace pssp {



class INameResolver;
using INameResolverUP=std::unique_ptr<INameResolver>;
class INameResolver {
public:

    virtual ~INameResolver() { }

    virtual void resolve(ast::ISymbolScope *root) = 0;

    // /**
    //  * @brief Returns the active namespace stack
    //  * 
    //  * @return const std::vector<INamespace *>& 
    //  */
    // virtual const std::vector<INamespace *> &getNamespace() = 0;


};

}
