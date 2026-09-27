/**
 * ExprTypeOf.h
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
 *
 * The type of an already-resolved expression, as far as the expected-type
 * rules of LRM 8.4.3 need it (symbol-resolution plan 8.1). Only enumeration
 * types are answered for now: step a of 18.3 is the one consumer. This is the
 * seed of I-1 in the semantic-checks review.
 */
#pragma once
#include "pssp/ast/IDataType.h"
#include "pssp/ast/IDataTypeUserDefined.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/IExprCast.h"
#include "pssp/ast/IExprCond.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprRefPathStatic.h"
#include "pssp/ast/IExprHierarchicalId.h"
#include "pssp/ast/IExprMemberPathElem.h"
#include "pssp/ast/IExprRefPathStaticRooted.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/IStruct.h"
#include "pssp/ast/ITemplateParamDecl.h"
#include "pssp/ast/ITypedefDeclaration.h"
#include "pssp/impl/BuiltinCollectionUtil.h"
#include "pssp/impl/TaskGetElemSymbolScope.h"
#include "pssp/impl/TaskGetSubscriptSymbolScope.h"
#include "ResolveContext.h"
#include "pssp/impl/NodeKind.h"

namespace pssp {

class ExprTypeOf {
public:
    ExprTypeOf(ResolveContext *ctxt) : m_ctxt(ctxt) { }

    /**
     * The enumeration type of `e`, or null when it has another type or its
     * type is not known. `e` must already be resolved: a reference reads the
     * declaration its elements are bound to.
     *
     * - a reference: the declared type of what its last element names -- a
     *   field, variable, parameter or constant, the return type of a call,
     *   the element type after a subscript -- or, for an enum item, its enum;
     * - a cast: the casting type;
     * - `?:`: the type of either arm.
     */
    ast::ISymbolEnumScope *enumOf(ast::IExpr *e) {
        if (!e) {
            return 0;
        }
        if (ast::IExprRefPathContext *r = NodeKind::cast<ast::IExprRefPathContext>(e)) {
            if (!r->getTarget() || r->getSlice()
                    || !r->getHier_id()->getElems().size()) {
                return 0;
            }
            ast::IExprMemberPathElem *last = r->getHier_id()->getElems().back().get();
            ast::IScopeChild *decl = last->getId()->getDecl();
            if (NodeKind::cast<ast::IEnumItem>(decl)) {
                return (r->getHier_id()->getElems().size() == 1)
                    ? enumOfItemPath(r->getTarget()) : 0;
            }
            return enumOfDecl(decl, last->getSubscript().size());
        }
        if (ast::IExprRefPathStatic *r = NodeKind::cast<ast::IExprRefPathStatic>(e)) {
            return (r->getSlice()) ? 0 : enumOfPath(r->getTarget());
        }
        if (ast::IExprRefPathStaticRooted *r = NodeKind::cast<ast::IExprRefPathStaticRooted>(e)) {
            // The leaf carries the binding; the root only locates it.
            if (!r->getTarget() || r->getSlice() || !r->getLeaf()
                    || !r->getLeaf()->getElems().size()) {
                return 0;
            }
            ast::IExprMemberPathElem *last = r->getLeaf()->getElems().back().get();
            return enumOfDecl(last->getId()->getDecl(), last->getSubscript().size());
        }
        if (ast::IExprCast *c = NodeKind::cast<ast::IExprCast>(e)) {
            return enumOfType(c->getCasting_type());
        }
        if (ast::IExprCond *c = NodeKind::cast<ast::IExprCond>(e)) {
            ast::ISymbolEnumScope *ret = enumOf(c->getTrue_e());
            return (ret) ? ret : enumOf(c->getFalse_e());
        }
        return 0;
    }

    /**
     * The enumeration type of an *element* of `e`, a reference to an array or
     * a collection: what an aggregate literal assigned to it expects of each
     * value (8.4.2, 8.4.3). Null otherwise.
     */
    ast::ISymbolEnumScope *elemEnumOf(ast::IExpr *e) {
        ast::IExprMemberPathElem *last = 0;
        if (ast::IExprRefPathContext *r = NodeKind::cast<ast::IExprRefPathContext>(e)) {
            if (r->getTarget() && !r->getSlice() && r->getHier_id()->getElems().size()) {
                last = r->getHier_id()->getElems().back().get();
            }
        } else if (ast::IExprRefPathStaticRooted *r = NodeKind::cast<ast::IExprRefPathStaticRooted>(e)) {
            if (r->getTarget() && !r->getSlice() && r->getLeaf()
                    && r->getLeaf()->getElems().size()) {
                last = r->getLeaf()->getElems().back().get();
            }
        }
        return (last)
            ? enumOfDecl(last->getId()->getDecl(), last->getSubscript().size()+1) : 0;
    }

    /** The enumeration type `t` names, through typedefs; null otherwise. */
    ast::ISymbolEnumScope *enumOfType(ast::IDataType *t) {
        // An enum is always named: only a user-defined type -- which is also
        // how a typedef or a type parameter is written -- can be one. The
        // general walk is costly, and parameter defaults are common.
        ast::IDataTypeUserDefined *udt = NodeKind::cast<ast::IDataTypeUserDefined>(t);
        if (!udt || !udt->getType_id() || !udt->getType_id()->getTarget()) {
            return 0;
        }
        // The name itself, first: it is an enum, or a type that is plainly
        // not one. Only a typedef or a type parameter needs the full walk.
        ast::IScopeChild *named = m_ctxt->resolveSymbolPathRef(
            udt->getType_id()->getTarget());
        if (ast::ISymbolEnumScope *e = NodeKind::cast<ast::ISymbolEnumScope>(named)) {
            return e;
        }
        if (!NodeKind::cast<ast::ITypedefDeclaration>(named)
                && !NodeKind::cast<ast::ITemplateParamDecl>(named)) {
            return 0;
        }
        return NodeKind::cast<ast::ISymbolEnumScope>(TaskGetElemSymbolScope(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(t));
    }

    /**
     * The enumeration type of a value of declaration `decl`, `n_subscript`
     * subscripts in. An enum item's enum is not answered here: an item is
     * not reachable from its declaration alone -- see enumOfItemPath().
     */
    ast::ISymbolEnumScope *enumOfDecl(ast::IScopeChild *decl, uint32_t n_subscript=0) {
        return NodeKind::cast<ast::ISymbolEnumScope>(scopeOfDecl(decl, n_subscript));
    }

    /**
     * The scope of the type of a value of `decl` -- a declaration or a data
     * type -- `n_subscript` subscripts in; null when it is not known.
     */
    ast::ISymbolScope *scopeOfDecl(ast::IScopeChild *decl, uint32_t n_subscript=0) {
        if (!decl) {
            return 0;
        }
        return (n_subscript)
            ? TaskGetSubscriptSymbolScope(
                m_ctxt->getDebugMgr(), m_ctxt->root(), n_subscript).resolve(decl)
            : TaskGetElemSymbolScope(
                m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(decl);
    }

    /**
     * The struct type a value of `decl` has, `n_subscript` subscripts in: the
     * context type of a struct literal written for it (8.4.4, 8.7.1). Null
     * for any other type, or an unknown one. The built-in collections are
     * structs in the core library, but not ones a struct literal can build.
     */
    ast::ISymbolTypeScope *structOfDecl(ast::IScopeChild *decl, uint32_t n_subscript=0) {
        ast::ISymbolTypeScope *s = NodeKind::cast<ast::ISymbolTypeScope>(
            scopeOfDecl(decl, n_subscript));
        return (s && NodeKind::cast<ast::IStruct>(s->getTarget())
                && builtinCollectionKind(s) == CollectionKind::None) ? s : 0;
    }

    /**
     * The struct type of `e`, a reference -- what a struct literal assigned
     * to it is written for -- `n_extra` subscripts past the reference's own
     * (1 for the elements of an array literal). Null otherwise.
     */
    ast::ISymbolTypeScope *structOf(ast::IExpr *e, uint32_t n_extra=0) {
        ast::IExprMemberPathElem *last = 0;
        if (ast::IExprRefPathContext *r = NodeKind::cast<ast::IExprRefPathContext>(e)) {
            if (r->getTarget() && !r->getSlice() && r->getHier_id()->getElems().size()) {
                last = r->getHier_id()->getElems().back().get();
            }
        } else if (ast::IExprRefPathStaticRooted *r = NodeKind::cast<ast::IExprRefPathStaticRooted>(e)) {
            if (r->getTarget() && !r->getSlice() && r->getLeaf()
                    && r->getLeaf()->getElems().size()) {
                last = r->getLeaf()->getElems().back().get();
            }
        }
        return (last)
            ? structOfDecl(last->getId()->getDecl(), last->getSubscript().size()+n_extra)
            : 0;
    }

    /** The enumeration type of what `path` binds to. */
    ast::ISymbolEnumScope *enumOfPath(ast::ISymbolRefPath *path) {
        if (!path) {
            return 0;
        }
        ast::IScopeChild *decl = m_ctxt->resolveSymbolPathRef(path);
        return (NodeKind::cast<ast::IEnumItem>(decl))
            ? enumOfItemPath(path) : enumOfDecl(decl);
    }

    /**
     * The enum a path to one of its items leads through: every path to an
     * item ends in the item's index in its enum.
     */
    ast::ISymbolEnumScope *enumOfItemPath(ast::ISymbolRefPath *path) {
        if (!path || path->getPath().size() < 2) {
            return 0;
        }
        ast::ISymbolRefPathUP prefix(
            m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath());
        prefix->getPath().insert(
            prefix->getPath().end(),
            path->getPath().begin(),
            path->getPath().end()-1);
        return NodeKind::cast<ast::ISymbolEnumScope>(
            m_ctxt->resolveSymbolPathRef(prefix.get()));
    }

private:
    ResolveContext                  *m_ctxt;
};

}
