/**
 * ISymbolTable.h
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
#include "pssp/ast/ITypeScope.h"
#include "pssp/INameResolver.h"
#include "pssp/ISymbolTableIterator.h"

namespace pssp {


/*
enum class SymbolKindE {
    Package,
    Type
};
 */

class ISymbolTable;
using ISymbolTableUP=std::unique_ptr<ISymbolTable>;
class ISymbolTable {
public:

    virtual ~ISymbolTable() { }

    virtual void init(INameResolver *resolver) = 0;

    virtual ISymbolTableIterator *mkIterator() = 0;

//    virtual ast::INamedScopeChild *enterNamedScope(
//        ast::INamedScopeChild *) = 0;

    virtual void enterPackage(const std::string &name) = 0;

    /**
     * @brief Declares a new 
     * 
     * @param t 
     * @return ast::IScopeChild* if a duplicate type exists
     */
    virtual ast::IScopeChild *defineSymbol(
        const std::string       &name, 
        ast::IScopeChild        *t) = 0;
        
    virtual ast::IScopeChild *defineSymbolScope(
        const std::string       &name, 
        ast::IScopeChild        *t) = 0;


    virtual void leaveSymbolScope() = 0;

    virtual void enterParamsScope() = 0;

    virtual void leaveParamsScope() = 0;

    /**
     * @brief Declares a new field
     * 
     * @param s 
     * @return ast::IField* if a duplicate field exists
     */
    virtual ast::IField *declareField(ast::IField *f) = 0;

    virtual void enterTypeScope(ast::ITypeScope *s) = 0;

    virtual void leaveTypeScope(ast::ITypeScope *s) = 0;

    virtual void leavePackage(const std::string &name) = 0;

};

}
