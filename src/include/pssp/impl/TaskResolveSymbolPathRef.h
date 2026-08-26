/**
 * TaskResolveSymbolPathRef.h
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
#include "dmgr/impl/DebugMacros.h"
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/ISymbolRefPath.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/impl/ScopeUtil.h"
#include "pssp/impl/TaskIndexTemplateScope.h"
#include "pssp/impl/TaskGetName.h"
#include "pssp/impl/TaskResolveSymbolPathRefResult.h"

namespace pssp {



class TaskResolveSymbolPathRef : public ast::VisitorBase {
public:
    TaskResolveSymbolPathRef(
        dmgr::IDebugMgr             *dmgr,
        ast::ISymbolChildrenScope   *root,
        ast::ISymbolChildrenScope   *inline_ctxt=0) : 
        m_dbg(0), m_root(root), m_inline_ctxt(inline_ctxt) { 
        DEBUG_INIT("TaskResolveSymbolPathRef", dmgr);
    }

    virtual ~TaskResolveSymbolPathRef() { }

    ast::IScopeChild *resolve(const ast::ISymbolRefPath *ref) {
        DEBUG_ENTER("resolve root=%p", m_root);
        ast::IScopeChild *ret = 0;

        // A null path means the reference was never resolved -- normal when
        // the model is incomplete, or when this runs before the reference's
        // own resolution pass. Every caller already handles a null return;
        // walking getPath() on a null ref is an immediate fault.
        if (!ref) {
            DEBUG_LEAVE("resolve -- null ref");
            return ret;
        }

        ScopeUtil scope(m_root);

        if (DEBUG_EN) {
            for (std::vector<ast::SymbolRefPathElem>::const_iterator
                it=ref->getPath().begin();
                it!=ref->getPath().end(); it++) {
                DEBUG("Path: %d %d", it->kind, it->idx);
            }
        }

        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=ref->getPath().begin();
            it!=ref->getPath().end(); it++) {
            
            switch (it->kind) {
                case ast::SymbolRefPathElemKind::ElemKind_ChildIdx: {
                    DEBUG("Elem: ChildIdx %d", it->idx);
                    // A negative index means the recorder had no way to name
                    // this scope. It is deliberately left in the path (see
                    // AstSymbolTableIterator::getScopeSymbolPath) so that the
                    // reference resolves to nothing rather than to whatever
                    // child of the *enclosing* scope the rest of the path
                    // happens to land on.
                    if (it->idx >= 0 && it->idx < scope.getNumChildren()) {
                        ret = scope.getChild(it->idx);
                    } else {
                        DEBUG("Index %d out-of-range (%d)", it->idx, scope.getNumChildren());
                        ret = 0;
                    }
                    DEBUG("  scope %p => %p", scope.get(), ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_TemplateScope: {
                    // 4.7.1. A template scope is not a child of the scope that
                    // encloses it, so it is named by position among that
                    // scope's template scopes instead -- the same walk that
                    // assigned the position assigns it again here.
                    DEBUG("Elem: TemplateScope %d", it->idx);
                    ret = TaskIndexTemplateScope().get(scope.get(), it->idx);
                    DEBUG("  scope %p => %p", scope.get(), ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_ArgIdx: {
                    DEBUG("Elem: ArgIdx %d", it->idx);
                    ast::ISymbolFunctionScope *fs = scope.getT<ast::ISymbolFunctionScope>();
                    // `plist` is checked, not assumed: a function scope built
                    // from a bare prototype used to have none at all, and a
                    // stale path recorded against one is better reported as
                    // unresolved than dereferenced.
                    if (fs && fs->getPlist() &&
                        it->idx < fs->getPlist()->getChildren().size()) {
                        ret = fs->getPlist()->getChildren().at(it->idx).get();
                    } else {
                        DEBUG("Out-of-range");
                    }
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_Inline: {
                    DEBUG("Elem: Inline %d", it->idx);
                    ret = m_inline_ctxt;
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_ParamIdx: {
                    DEBUG("Elem: ParamIdx %d", it->idx);
                    ast::ISymbolTypeScope *scope_ts = scope.getT<ast::ISymbolTypeScope>();
                    if (scope_ts && scope_ts->getPlist() &&
                        it->idx < scope_ts->getPlist()->getChildren().size()) {
                        ret = scope_ts->getPlist()->getChildren().at(it->idx).get();
                    } else {
                        DEBUG("Out-of-range");
                    }
                    DEBUG("  scope %p => %p", scope_ts, ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_Super: {
                    ast::ISymbolTypeScope *scope_ts = scope.getT<ast::ISymbolTypeScope>();
                    DEBUG_ERROR("TODO: handle super ref");
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_TypeSpec: {
                    ast::ISymbolTypeScope *scope_ts = scope.getT<ast::ISymbolTypeScope>();
                    DEBUG("Elem: TypeSpec %d", it->idx);
                    DEBUG("Scope: %s (%d specializations)",
                        scope_ts->getName().c_str(),
                        scope_ts->getSpec_types().size());
                    if (it->idx < scope_ts->getSpec_types().size()) {
                        ret = scope_ts->getSpec_types().at(it->idx).get();
                    } else {
                        DEBUG("Out-of-range");
                    }
                    DEBUG("  scope %p => %p", scope_ts, ret);
                } break;
                default:
                    DEBUG_ERROR("TODO: handle ElemKind %d", (int)it->kind);
                    break;
            }
            
            if (it+1 != ref->getPath().end()) {
                ScopeUtil scope_t(ret);

                if (!scope_t.valid()) {
                    DEBUG_ERROR("Failed to get scope @ %d/%d",
                        (it-ref->getPath().begin()), ref->getPath().size());
                    ret = 0;
                    break;
                } else {
                    scope.init(ret);
                }
            }
        }

        DEBUG_LEAVE("resolve");

        return ret;
    }

    template <class T> T *resolveT(const ast::ISymbolRefPath *ref) {
        return dynamic_cast<T *>(resolve(ref));
    }

    TaskResolveSymbolPathRefResult resolveFull(const ast::ISymbolRefPath *ref) {
        TaskResolveSymbolPathRefResult ret;

        ast::IScopeChild *ref_t = resolve(ref);
        m_ts = 0;
        m_ss = 0;
        m_dt = 0;
        ref_t->accept(m_this);

        if (m_ts) {
            ret.kind = TaskResolveSymbolPathRefResult::SymbolTypeScope;
            ret.val.ts = m_ts;
        } else if (m_ss) {
            ret.kind = TaskResolveSymbolPathRefResult::SymbolScope;
            ret.val.ss = m_ss;
        } else if (m_dt) {
            ret.kind = TaskResolveSymbolPathRefResult::DataType;
            ret.val.dt = m_dt;
        } else {
            fprintf(stdout, "DEBUG_ERROR: unhandled resolveFull case\n");
            *((uint32_t *)0) = 1;
        }
        return ret;
    }

    ISymbolTableIterator *mkIterator(
            ISymbolTableIterator    *ret,
            const ast::ISymbolRefPath       *ref) {
        DEBUG_ENTER("mkIterator root=%p", m_root);
        ast::ISymbolChildrenScope *scope = m_root;

        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=ref->getPath().begin();
            it!=ref->getPath().end(); it++) {
            
            switch (it->kind) {
                case ast::SymbolRefPathElemKind::ElemKind_ChildIdx: {
                    DEBUG("Elem: ChildIdx %d", it->idx);
                    ast::IScopeChild *c = scope->getChildren().at(it->idx).get();
                    if ((scope=dynamic_cast<ast::ISymbolScope *>(c))) {
                        ret->pushScope(dynamic_cast<ast::ISymbolScope *>(scope));
                    } else {
                        break;
                    }
                    DEBUG("  scope %p => %p", scope, ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_ParamIdx: {
                    DEBUG("Elem: ParamIdx %d", it->idx);
//                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
//                    ret = scope_ts->getPlist()->getChildren().at(it->idx);
//                    DEBUG("  scope %p => %p", scope_ts, ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_Super: {
                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
                    DEBUG_ERROR("TODO: handle super ref");
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_TypeSpec: {
                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
                    DEBUG("Elem: TypeSpec %d", it->idx);
                    ast::ISymbolTypeScope *c = scope_ts->getSpec_types().at(it->idx).get();
                    ret->pushScope(c, ast::SymbolRefPathElemKind::ElemKind_TypeSpec);
                    scope = c;
                    DEBUG("  scope %p => %p", scope_ts, ret);
                } break;
                default:
                    DEBUG_ERROR("TODO: handle ElemKind %d", it->kind);
                    break;
            }
            
//            if (it+1 != ref->getPath().end()) {
//                scope = dynamic_cast<ast::ISymbolScope *>(ret);
//            }
        }

        DEBUG_LEAVE("mkIterator");

        return ret;
    }

    ISymbolTableIterator *mkIterator(
            ISymbolTableIterator    *ret,
            ast::ISymbolScope               *target) {
        DEBUG_ENTER("mkIterator root=%p", m_root);
        ast::ISymbolChildrenScope *scope = m_root;

        std::vector<ast::ISymbolScope *> scopes;

        ast::ISymbolScope *c = target;
        while (c && c != m_root) {
            DEBUG("Scope: %s", c->getName().c_str());
            scopes.push_back(c);
            c = c->getUpper();
        }

        for (std::vector<ast::ISymbolScope *>::const_reverse_iterator
            it=scopes.rbegin();
            it!=scopes.rend(); it++) {
            DEBUG("pushScope");
            // A scope is pushed as a specialization only when it demonstrably
            // is one. Both steps to that conclusion can come back null and
            // used not to be checked: a SymbolTypeScope's target need not be a
            // TypeScope (an annotation declaration is one such), and a type
            // that takes no template parameters has a null parameter list.
            // The latter is the common case -- it is every ordinary component
            // and struct -- so walking out of a parameterized type nested in a
            // component dereferenced null and crashed the linker.
            bool is_spec = false;
            ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(*it);
            if (ts) {
                ast::ITypeScope *tst = dynamic_cast<ast::ITypeScope *>(ts->getTarget());
                is_spec = (tst && tst->getParams() && tst->getParams()->getSpecialized());
            }

            if (is_spec) {
                ret->pushScope(*it, ast::SymbolRefPathElemKind::ElemKind_TypeSpec);
            } else {
                ret->pushScope(*it);
            }
        }

        DEBUG_LEAVE("mkIterator");

        return ret;
    }

    std::string mkName(
            const ast::ISymbolRefPath       *ref) {
        DEBUG_ENTER("mkName root=%p", m_root);
        std::string ret;
        ast::IScopeChild *item;
        ast::ISymbolChildrenScope *scope = m_root;

        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=ref->getPath().begin();
            it!=ref->getPath().end(); it++) {
            
            switch (it->kind) {
                case ast::SymbolRefPathElemKind::ElemKind_ChildIdx: {
                    DEBUG("Elem: ChildIdx %d", it->idx);
                    item = scope->getChildren().at(it->idx).get();
                    ret = TaskGetName().get(item);
                    if (!(scope=dynamic_cast<ast::ISymbolScope *>(item))) {
                        break;
                    }
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_ParamIdx: {
                    DEBUG("Elem: ParamIdx %d", it->idx);
//                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
//                    ret = scope_ts->getPlist()->getChildren().at(it->idx);
//                    DEBUG("  scope %p => %p", scope_ts, ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_Super: {
                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
                    DEBUG_ERROR("TODO: handle super ref");
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_TypeSpec: {
                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
                    DEBUG("Elem: TypeSpec %d", it->idx);
//                    ast::ISymbolTypeScope *c = scope_ts->getSpec_types().at(it->idx).get();
//                    ret->pushScope(c);
                    DEBUG("  scope %p => %p", scope_ts, ret.c_str());
                } break;
                default:
                    DEBUG_ERROR("TODO: handle ElemKind %d", (int)it->kind);
                    break;
            }
            
//            if (it+1 != ref->getPath().end()) {
//                scope = dynamic_cast<ast::ISymbolScope *>(i);
//            }
        }

        DEBUG_LEAVE("mkName");

        return ret;
    }

    std::string mkQName(
            const ast::ISymbolRefPath       *ref) {
        DEBUG_ENTER("mkQName root=%p", m_root);
        std::string ret;
        ast::IScopeChild *item;
        ast::ISymbolChildrenScope *scope = m_root;

        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=ref->getPath().begin();
            it!=ref->getPath().end(); it++) {
            
            switch (it->kind) {
                case ast::SymbolRefPathElemKind::ElemKind_ChildIdx: {
                    DEBUG("Elem: ChildIdx %d", it->idx);
                    item = scope->getChildren().at(it->idx).get();
                    if (ret.size()) {
                        ret += "::";
                    }
                    ret += TaskGetName().get(item);
                    if (!(scope=dynamic_cast<ast::ISymbolScope *>(item))) {
                        break;
                    }
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_ParamIdx: {
                    DEBUG("Elem: ParamIdx %d", it->idx);
//                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
//                    ret = scope_ts->getPlist()->getChildren().at(it->idx);
//                    DEBUG("  scope %p => %p", scope_ts, ret);
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_Super: {
                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
                    DEBUG_ERROR("TODO: handle super ref");
                } break;
                case ast::SymbolRefPathElemKind::ElemKind_TypeSpec: {
                    ast::ISymbolTypeScope *scope_ts = dynamic_cast<ast::ISymbolTypeScope *>(scope);
                    DEBUG("Elem: TypeSpec %d", it->idx);
//                    ast::ISymbolTypeScope *c = scope_ts->getSpec_types().at(it->idx).get();
//                    ret->pushScope(c);
                    DEBUG("  scope %p => %p", scope_ts, ret.c_str());
                } break;
                default:
                    DEBUG_ERROR("TODO: handle ElemKind %d", (int)it->kind);
                    break;
            }
            
//            if (it+1 != ref->getPath().end()) {
//                scope = dynamic_cast<ast::ISymbolScope *>(i);
//            }
        }

        DEBUG_LEAVE("mkQName");

        return ret;
    }

    virtual void visitDataTypeBool(ast::IDataTypeBool *i) override {
        m_dt = i;
    }

    virtual void visitDataTypeChandle(ast::IDataTypeChandle *i) override {
        m_dt = i;
    }

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) override {
        m_dt = i;
    }

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) override {
        m_dt = i;
    }

    virtual void visitDataTypeString(ast::IDataTypeString *i) override {
        m_dt = i;
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        // See where this redirects
        ast::IScopeChild *ref_t = resolve(i->getType_id()->getTarget());
        ref_t->accept(m_this);
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override {
        DEBUG_ENTER("visitSymbolEnumScope %s", i->getName().c_str());
        m_ss = i;
        DEBUG_LEAVE("visitSymbolEnumScope");
    }

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override {
        DEBUG_ENTER("visitSymbolExtendScope");
        m_ss = i;
        DEBUG_LEAVE("visitSymbolExtendScope");
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
        DEBUG_ERROR("Should not hit symbol scope when resolving a ref");
        DEBUG_LEAVE("visitSymbolScope");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope");
        m_ss = i;
        m_ts = i;
        DEBUG_LEAVE("visitSymbolTypeScope");
    }

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
        i->getDflt()->accept(m_this);
        DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
        i->getDflt()->accept(m_this);
        DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
    }

private:
    dmgr::IDebug                         *m_dbg;
    ast::ISymbolChildrenScope            *m_root;
    ast::ISymbolChildrenScope            *m_inline_ctxt;
    ast::ISymbolTypeScope                *m_ts;
    ast::ISymbolScope                    *m_ss;
    ast::IDataType                       *m_dt;


};

}
