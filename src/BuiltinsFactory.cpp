/*
 * BuiltinsFactory.cpp
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
#include "BuiltinsFactory.h"


namespace pssp {



BuiltinsFactory::BuiltinsFactory(ast::IFactory *ast_f) : m_ast_f(ast_f) {

}

BuiltinsFactory::~BuiltinsFactory() {

}

ast::IGlobalScope *BuiltinsFactory::build() {
    ast::ITemplateParamDeclList *params;
    AstUtil util(m_ast_f);

    m_builtins = ast::IGlobalScopeUP(m_ast_f->mkGlobalScope(-1));

    ast::ITypeScope *pyobj = m_ast_f->mkTypeScope(
        m_ast_f->mkExprId("pyobj", false),
        0);
    pyobj->setOpaque(true);
    pyobj->setParent(m_builtins.get());
    m_builtins->getChildren().push_back(ast::IScopeChildUP(pyobj));

    /****************************************************************
     * array
     ****************************************************************/
    ast::IStruct *array = m_ast_f->mkStruct(
        m_ast_f->mkExprId("array", false),
        0,
        ast::StructKind::Struct);
    params = m_ast_f->mkTemplateParamDeclList();
    params->getParams().push_back(ast::ITemplateParamDeclUP(
        m_ast_f->mkTemplateGenericTypeParamDecl(
            m_ast_f->mkExprId("T", false),
            0)));
    params->getParams().push_back(ast::ITemplateParamDeclUP(
        m_ast_f->mkTemplateValueParamDecl(
            m_ast_f->mkExprId("SZ", false),
            m_ast_f->mkDataTypeInt(
                false,
                m_ast_f->mkExprUnsignedNumber("32", 32, 32),
                0),
                0)));
    array->setParams(params);
    array->setParent(m_builtins.get());
    m_builtins->getChildren().push_back(ast::IScopeChildUP(array));

    /****************************************************************
     * list
     ****************************************************************/
    ast::IStruct *list = m_ast_f->mkStruct(
        m_ast_f->mkExprId("list", false),
        0,
        ast::StructKind::Struct);
    params = m_ast_f->mkTemplateParamDeclList();
    params->getParams().push_back(ast::ITemplateParamDeclUP(
        m_ast_f->mkTemplateGenericTypeParamDecl(
            m_ast_f->mkExprId("T", false),
            0)));
    list->setParams(params);
    list->setParent(m_builtins.get());

    // Add in methods
    ast::IFunctionPrototype *push_back = m_ast_f->mkFunctionPrototype(
        m_ast_f->mkExprId("push_back", false),
        0,
        false,
        false);
    push_back->getParameters().push_back(ast::IFunctionParamDeclUP(
        m_ast_f->mkFunctionParamDecl(
            ast::FunctionParamDeclKind::ParamKind_DataType,
            m_ast_f->mkExprId("t", false),
            util.mkDataTypeUserDefined("T"),
            ast::ParamDir::ParamDir_In,
            0)));
    list->getChildren().push_back(ast::IScopeChildUP(push_back));
    m_builtins->getChildren().push_back(ast::IScopeChildUP(list));

    /****************************************************************
     * set - PSS 3.0
     ****************************************************************/
    ast::IStruct *set = m_ast_f->mkStruct(
        m_ast_f->mkExprId("set", false),
        0,
        ast::StructKind::Struct);
    params = m_ast_f->mkTemplateParamDeclList();
    params->getParams().push_back(ast::ITemplateParamDeclUP(
        m_ast_f->mkTemplateGenericTypeParamDecl(
            m_ast_f->mkExprId("T", false),
            0)));
    set->setParams(params);
    set->setParent(m_builtins.get());
    m_builtins->getChildren().push_back(ast::IScopeChildUP(set));

    /****************************************************************
     * map - PSS 3.0
     ****************************************************************/
    ast::IStruct *map = m_ast_f->mkStruct(
        m_ast_f->mkExprId("map", false),
        0,
        ast::StructKind::Struct);
    params = m_ast_f->mkTemplateParamDeclList();
    params->getParams().push_back(ast::ITemplateParamDeclUP(
        m_ast_f->mkTemplateGenericTypeParamDecl(
            m_ast_f->mkExprId("K", false),
            0)));
    params->getParams().push_back(ast::ITemplateParamDeclUP(
        m_ast_f->mkTemplateGenericTypeParamDecl(
            m_ast_f->mkExprId("V", false),
            0)));
    map->setParams(params);
    map->setParent(m_builtins.get());
    m_builtins->getChildren().push_back(ast::IScopeChildUP(map));

    return m_builtins.release();
}

}
