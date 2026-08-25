/**
 * BuiltinsFactory.h
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
#include "pssp/ast/IFactory.h"

namespace pssp {




class BuiltinsFactory {
public:
    BuiltinsFactory(ast::IFactory *ast_f);

    virtual ~BuiltinsFactory();

    ast::IGlobalScope *build();

private:
    /**
     * Adds a method prototype to `owner` and returns it, so that parameters
     * can be appended.  `rtype` may be null, meaning `void`.
     */
    ast::IFunctionPrototype *mkMethod(
        ast::IScope             *owner,
        const std::string       &name,
        ast::IDataType          *rtype);

    /** Appends an `in` parameter to `proto`.  `dflt` may be null. */
    void addParam(
        ast::IFunctionPrototype *proto,
        const std::string       &name,
        ast::IDataType          *type,
        ast::IExpr              *dflt=0);

    ast::IDataType *mkInt();                        ///< `int`
    ast::IDataType *mkBit(int32_t width);           ///< `bit[width]`
    ast::IDataType *mkString();                     ///< `string`
    ast::IDataType *mkBool();                       ///< `bool`
    ast::IDataType *mkList(ast::IDataType *elem);   ///< `list<elem>`
    ast::IExpr *mkIntLit(int32_t v);

    /** Builds the `string` pseudo-type that carries the methods of §7.6.3. */
    ast::IStruct *buildString();

private:
    ast::IFactory           *m_ast_f;
    ast::IGlobalScopeUP     m_builtins;

};

}
