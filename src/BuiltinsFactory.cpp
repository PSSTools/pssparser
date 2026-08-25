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

    /****************************************************************
     * string - PSS 3.1 7.6
     ****************************************************************/
    ast::IStruct *string_t = buildString();
    string_t->setParent(m_builtins.get());
    m_builtins->getChildren().push_back(ast::IScopeChildUP(string_t));

    return m_builtins.release();
}

/**
 * `string` is spelled as a keyword, so the grammar never produces a reference
 * to this type and a user cannot declare one that collides with it.  It exists
 * only to give the methods of 7.6.3 real signatures, which is what lets a call
 * on a string variable be arity- and argument-checked like any other call.
 */
ast::IStruct *BuiltinsFactory::buildString() {
    ast::IStruct *s = m_ast_f->mkStruct(
        m_ast_f->mkExprId("string", false),
        0,
        ast::StructKind::Struct);

    // -- PSS 3.1 7.6.3, in the order the LRM lists them ------------------
    mkMethod(s, "size", mkInt());

    ast::IFunctionPrototype *find = mkMethod(s, "find", mkInt());
    addParam(find, "sub_str", mkString());
    addParam(find, "first_pos", mkInt(), mkIntLit(0));

    ast::IFunctionPrototype *find_last = mkMethod(s, "find_last", mkInt());
    addParam(find_last, "sub_str", mkString());
    addParam(find_last, "first_pos", mkInt(), mkIntLit(-1));

    ast::IFunctionPrototype *find_all = mkMethod(s, "find_all", mkList(mkInt()));
    addParam(find_all, "sub_str", mkString());

    mkMethod(s, "lower", mkString());
    mkMethod(s, "upper", mkString());

    ast::IFunctionPrototype *split = mkMethod(s, "split", mkList(mkString()));
    addParam(split, "sep", mkString());

    mkMethod(s, "chars", mkList(mkBit(8)));

    // -- Non-LRM methods retained for compatibility ----------------------
    // These predate the 3.1 alignment and are not in 7.6.3.  They are kept
    // so that source written against earlier releases still parses; giving
    // them signatures here is what allows the name allow-list they used to
    // live on to be deleted.  Whether to deprecate them is P3-X6f.
    mkMethod(s, "len", mkInt());

    ast::IFunctionPrototype *rfind = mkMethod(s, "rfind", mkInt());
    addParam(rfind, "sub_str", mkString());
    addParam(rfind, "first_pos", mkInt(), mkIntLit(-1));

    ast::IFunctionPrototype *substr = mkMethod(s, "substr", mkString());
    addParam(substr, "first_pos", mkInt());
    addParam(substr, "len", mkInt(), mkIntLit(-1));

    mkMethod(s, "to_lower", mkString());
    mkMethod(s, "to_upper", mkString());
    mkMethod(s, "trim", mkString());

    ast::IFunctionPrototype *starts_with = mkMethod(s, "starts_with", mkBool());
    addParam(starts_with, "prefix", mkString());

    ast::IFunctionPrototype *ends_with = mkMethod(s, "ends_with", mkBool());
    addParam(ends_with, "suffix", mkString());

    return s;
}

ast::IFunctionPrototype *BuiltinsFactory::mkMethod(
        ast::IScope             *owner,
        const std::string       &name,
        ast::IDataType          *rtype) {
    ast::IFunctionPrototype *proto = m_ast_f->mkFunctionPrototype(
        m_ast_f->mkExprId(name, false),
        rtype,
        false,
        false);
    owner->getChildren().push_back(ast::IScopeChildUP(proto));
    return proto;
}

void BuiltinsFactory::addParam(
        ast::IFunctionPrototype *proto,
        const std::string       &name,
        ast::IDataType          *type,
        ast::IExpr              *dflt) {
    proto->getParameters().push_back(ast::IFunctionParamDeclUP(
        m_ast_f->mkFunctionParamDecl(
            ast::FunctionParamDeclKind::ParamKind_DataType,
            m_ast_f->mkExprId(name, false),
            type,
            ast::ParamDir::ParamDir_In,
            dflt)));
}

ast::IDataType *BuiltinsFactory::mkInt() {
    return m_ast_f->mkDataTypeInt(true, 0, 0);
}

ast::IDataType *BuiltinsFactory::mkBit(int32_t width) {
    char image[16];
    snprintf(image, sizeof(image), "%d", width);
    return m_ast_f->mkDataTypeInt(
        false,
        m_ast_f->mkExprUnsignedNumber(image, 32, width),
        0);
}

ast::IDataType *BuiltinsFactory::mkString() {
    return m_ast_f->mkDataTypeString(false);
}

ast::IDataType *BuiltinsFactory::mkBool() {
    return m_ast_f->mkDataTypeBool();
}

ast::IDataType *BuiltinsFactory::mkList(ast::IDataType *elem) {
    ast::ITemplateParamValueList *params = m_ast_f->mkTemplateParamValueList();
    params->getValues().push_back(ast::ITemplateParamValueUP(
        m_ast_f->mkTemplateParamTypeValue(elem)));
    ast::ITypeIdentifier *type_id = m_ast_f->mkTypeIdentifier();
    type_id->getElems().push_back(ast::ITypeIdentifierElemUP(
        m_ast_f->mkTypeIdentifierElem(
            m_ast_f->mkExprId("list", false),
            params)));
    return m_ast_f->mkDataTypeUserDefined(false, type_id);
}

ast::IExpr *BuiltinsFactory::mkIntLit(int32_t v) {
    char image[16];
    snprintf(image, sizeof(image), "%d", v);
    return m_ast_f->mkExprSignedNumber(image, 32, v);
}

}
