/**
 * TaskGetCollectionElemType.h
 *
 * Copyright 2026 Matthew Ballance and Contributors
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
 */
#pragma once
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/BuiltinCollectionUtil.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {

/**
 * The element *type* a collection iterates over.
 *
 * This is the type-level counterpart of TaskGetSubscriptSymbolScope, which
 * answers the same question in terms of scopes. A scope is enough to continue
 * a member path; it is not enough to give a declaration a type, which is what
 * a `foreach` iterator variable needs -- the AST builder creates it with no
 * type at all, because the collection is not resolved yet at that point.
 *
 * The bound argument is read from the *specialized* parameter list, where the
 * `dflt` slot holds it (see TaskGetElemSymbolScope). Reading the written
 * `list<T>` arguments instead would miss a collection reached through a
 * defaulted or inherited parameter.
 *
 * `map<K,V>` iterates over its **keys** (21.5.4), unlike a subscript, which
 * yields a value -- hence the separate parameter-index mapping here.
 */
class TaskGetCollectionElemType : public virtual ast::VisitorBase {
public:
    TaskGetCollectionElemType(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root) :
        m_dbg(0), m_path_resolver(dmgr, root), m_ret(0) {
        DEBUG_INIT("pssp::TaskGetCollectionElemType", dmgr);
    }

    virtual ~TaskGetCollectionElemType() { }

    ast::IDataType *resolve(ast::IScopeChild *c) {
        m_ret = 0;
        if (c) {
            c->accept(m_this);
        }
        return m_ret;
    }

    virtual void visitField(ast::IField *i) override {
        if (i->getType()) {
            i->getType()->accept(m_this);
        }
    }

    virtual void visitProceduralStmtDataDeclaration(
            ast::IProceduralStmtDataDeclaration *i) override {
        if (i->getDatatype()) {
            i->getDatatype()->accept(m_this);
        }
    }

    virtual void visitFunctionParamDecl(ast::IFunctionParamDecl *i) override {
        if (i->getType()) {
            i->getType()->accept(m_this);
        }
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        if (i->getType_id()) {
            i->getType_id()->accept(m_this);
        }
    }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override {
        if (i->getTarget()) {
            ast::IScopeChild *c = m_path_resolver.resolve(i->getTarget());
            if (c) {
                c->accept(m_this);
            }
        }
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope \"%s\"", i->getName().c_str());
        ast::ITypeScope *type = dynamic_cast<ast::ITypeScope *>(i->getTarget());
        int32_t param_idx = collectionIterParam(builtinCollectionKind(type));

        if (param_idx >= 0 && type->getParams() &&
            param_idx < (int32_t)type->getParams()->getParams().size()) {
            type->getParams()->getParams().at(param_idx)->accept(m_this);
        }
        DEBUG_LEAVE("visitSymbolTypeScope");
    }

    // On a specialized parameter list the `dflt` slot holds the bound
    // argument. On an unspecialized one it holds the declared default, which
    // may be absent -- a null answer means "no element type known", which
    // leaves the iterator untyped exactly as it was before.

    virtual void visitTemplateGenericTypeParamDecl(
            ast::ITemplateGenericTypeParamDecl *i) override {
        m_ret = i->getDflt();
    }

    virtual void visitTemplateCategoryTypeParamDecl(
            ast::ITemplateCategoryTypeParamDecl *i) override {
        m_ret = i->getDflt();
    }

protected:

    /**
     * The template parameter `foreach` iterates over, or -1 for a type that
     * is not an iterable built-in.
     */
    static int32_t collectionIterParam(CollectionKind k) {
        switch (k) {
            case CollectionKind::Array:
            case CollectionKind::List:
            case CollectionKind::Set:
            case CollectionKind::Map:    // iterates keys
                return 0;
            default:
                return -1;
        }
    }

protected:
    dmgr::IDebug                *m_dbg;
    TaskResolveSymbolPathRef    m_path_resolver;
    ast::IDataType              *m_ret;

};

}
