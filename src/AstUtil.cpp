/*
 * AstUtil.cpp
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
#include "AstUtil.h"


namespace pssp {



AstUtil::AstUtil(ast::IFactory *ast_f) : m_ast_f(ast_f) {

}

AstUtil::~AstUtil() {

}

ast::IDataTypeUserDefined *AstUtil::mkDataTypeUserDefined(const std::string &name) {
    ast::ITypeIdentifier *type_id = m_ast_f->mkTypeIdentifier();
    type_id->getElems().push_back(ast::ITypeIdentifierElemUP(m_ast_f->mkTypeIdentifierElem(
        m_ast_f->mkExprId(name, false),
        0)));
    ast::IDataTypeUserDefined *ret = m_ast_f->mkDataTypeUserDefined(false, type_id);

    return ret;
}

}
