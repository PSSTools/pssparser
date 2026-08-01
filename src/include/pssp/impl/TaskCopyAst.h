/**
 * TaskCopyAst.h
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
#include <typeinfo>
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ast/IExprRefPathStatic.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/ITemplateParamValueList.h"
#include "pssp/ast/ITemplateParamValue.h"
#include "pssp/IFactory.h"

namespace pssp {

/**
 * Deep-copies a subtree of the AST.
 *
 * Used when specializing a parameterized type: the generic declaration's AST
 * is copied so the specialization can be resolved against its own bound
 * arguments without disturbing the generic.
 *
 * Two invariants matter here, and getting either wrong is silent:
 *
 * - **Every node kind reachable from a type body must be handled.**  Dispatch
 *   is by node type, and an unhandled kind leaves the result slot null.  The
 *   caller then dereferences that null.  When a visitor is missing, say so
 *   loudly (see ``unhandled()``) rather than returning null and letting the
 *   crash happen somewhere else.
 * - **Source locations must come along.**  A copied node with no location
 *   produces diagnostics at ``<unknown>:-1:0``, which cannot be shown in an
 *   editor or attributed to a file.  ``fin()`` carries them, so route every
 *   newly-built ``IScopeChild`` through it.
 *
 * Symbol tables *are* copied verbatim.  For exec scopes and the procedural
 * loop scopes, the symtab is populated by AstBuilderInt rather than by
 * TaskBuildSymbolTree, and the tree builder does not descend into them when
 * rebuilding a specialization -- so dropping the map would leave every local
 * declaration in an exec block unresolvable.  Child order is preserved, so the
 * name->index mapping stays valid.
 */
class TaskCopyAst : public ast::VisitorBase {
public:
    TaskCopyAst(IFactory    *factory) :
        m_factory(factory->getAstFactory()), m_dbg(0) {
        DEBUG_INIT("pssp::TaskCopyAst", factory->getDebugMgr());
    }

    virtual ~TaskCopyAst() { }

    ast::IConstraintStmt *copy(ast::IConstraintStmt *i) {
        DEBUG_ENTER("copy(IConstraintStmt)");
        m_constraint = 0;
        i->accept(m_this);

        if (!m_constraint) {
            DEBUG_ERROR("copy(IConstraintStmt) failed: no visitor for %s",
                typeid(*i).name());
        }
        DEBUG_LEAVE("copy(IConstraintStmt)");
        return m_constraint;
    }

    ast::ITemplateParamValue *copy(ast::ITemplateParamValue *i) {
        DEBUG_ENTER("copy(ITemplateParamValue)");
        m_param_val = 0;
        i->accept(m_this);

        if (!m_param_val) {
            DEBUG_ERROR("copy(ITemplateParamValue) failed: no visitor for %s",
                typeid(*i).name());
        }
        DEBUG_LEAVE("copy(ITemplateParamValue)");
        return m_param_val;
    }

    template <class T> T *copyT(ast::IConstraintStmt *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("copyT(IConstraintStmt) failed for %s", typeid(*i).name());
        }
        return ret;
    }

    ast::IScopeChild *copy(ast::IScopeChild *i) {
        DEBUG_ENTER("copy(IScopeChild)");
        m_sc = 0;
        i->accept(m_this);
        if (!m_sc) {
            DEBUG_ERROR("copy(IScopeChild) failed: no visitor for %s",
                typeid(*i).name());
        }
        DEBUG_LEAVE("copy(IScopeChild)");
        return m_sc;
    };

    template <class T> T *copyT(ast::IScopeChild *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("copyT(IScopeChild) failed for %s", typeid(*i).name());
        }
        return ret;
    }

    ast::IExpr *copy(ast::IExpr *i) {
        DEBUG_ENTER("copy(IExpr)");
        m_expr = 0;
        i->accept(m_this);
        if (!m_expr) {
            DEBUG_ERROR("copy(IExpr) failed: no visitor for %s", typeid(*i).name());
        }
        DEBUG_LEAVE("copy(IExpr)");
        return m_expr;
    };

    template <class T> T *copyT(ast::IExpr *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("copyT(IExpr) failed for %s", typeid(*i).name());
        }
        return ret;
    }

    ast::IDataType *copy(ast::IDataType *i) {
        DEBUG_ENTER("copy(IDataType)");
        m_dt = 0;
        i->accept(m_this);
        if (!m_dt) {
            DEBUG_ERROR("copy(IDataType) failed: no visitor for %s", typeid(*i).name());
        }
        DEBUG_LEAVE("copy(IDataType)");
        return m_dt;
    }

    template <class T> T *copyT(ast::IDataType *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("copyT(IDataType) failed for %s", typeid(*i).name());
        }
        return ret;
    }

    ast::ISymbolRefPath *copy(const ast::ISymbolRefPath *i) {
        ast::ISymbolRefPath *ret = m_factory->mkSymbolRefPath();
        ret->getPath().insert(
            ret->getPath().begin(),
            i->getPath().begin(),
            i->getPath().end()
        );
        return ret;
    }

private:

    /**
     * Reports a node kind this copier does not know how to duplicate.
     *
     * Called from the visitors that remain deliberately unimplemented.  The
     * result slot stays null, so the caller still fails -- but it fails naming
     * the construct, rather than segfaulting several frames away.
     */
    void unhandled(const char *what) {
        DEBUG_ERROR("TaskCopyAst: no copy support for %s", what);
    }

    /**
     * Carries the properties every ``IScopeChild`` has onto its copy.
     *
     * Deliberately called *before* the result slot is assigned, since copying
     * annotations recurses and would otherwise clobber it.
     */
    template <class T> T *fin(ast::IScopeChild *i, T *ic) {
        ic->setLocation(i->getLocation());
        ic->setDocstring(i->getDocstring());
        ic->setIndex(i->getIndex());

        for (std::vector<ast::IAnnotationUP>::const_iterator
            it=i->getAnnotations().begin();
            it!=i->getAnnotations().end(); it++) {
            ic->getAnnotations().push_back(ast::IAnnotationUP(
                copyT<ast::IAnnotation>(it->get())));
        }

        // Associated data is shared, not duplicated: it is keyed on the
        // declaration, and the specialization hook wants to see the same one.
        if (i->getAssocData()) {
            ic->setAssocData(i->getAssocData(), false);
        }

        return ic;
    }

    void copyChildren(
        const std::vector<ast::IScopeChildUP>   &src,
        std::vector<ast::IScopeChildUP>         &dst) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=src.begin(); it!=src.end(); it++) {
            dst.push_back(ast::IScopeChildUP(copy(it->get())));
        }
    }

    void copyConstraints(
        const std::vector<ast::IConstraintStmtUP>   &src,
        std::vector<ast::IConstraintStmtUP>         &dst) {
        for (std::vector<ast::IConstraintStmtUP>::const_iterator
            it=src.begin(); it!=src.end(); it++) {
            dst.push_back(ast::IConstraintStmtUP(copy(it->get())));
        }
    }

    void copyExprs(
        const std::vector<ast::IExprUP> &src,
        std::vector<ast::IExprUP>       &dst) {
        for (std::vector<ast::IExprUP>::const_iterator
            it=src.begin(); it!=src.end(); it++) {
            dst.push_back(ast::IExprUP(copy(it->get())));
        }
    }

    void copyHierIds(
        const std::vector<ast::IExprHierarchicalIdUP>   &src,
        std::vector<ast::IExprHierarchicalIdUP>         &dst) {
        for (std::vector<ast::IExprHierarchicalIdUP>::const_iterator
            it=src.begin(); it!=src.end(); it++) {
            dst.push_back(ast::IExprHierarchicalIdUP(
                copyT<ast::IExprHierarchicalId>(it->get())));
        }
    }

    /**
     * Copies the scope state of an ``ISymbolScope``.
     *
     * The symtab map is carried over verbatim -- see the class comment.
     */
    template <class T> T *finSymbolScope(ast::ISymbolScope *i, T *ic) {
        copyChildren(i->getChildren(), ic->getChildren());
        ic->getSymtab().insert(i->getSymtab().begin(), i->getSymtab().end());
        ic->setSynthetic(i->getSynthetic());
        ic->setOpaque(i->getOpaque());
        ic->setId(i->getId());
        return fin(i, ic);
    }

    ast::ITemplateParamDeclList *copyParamDeclList(ast::ITemplateParamDeclList *i) {
        ast::ITemplateParamDeclList *ic = m_factory->mkTemplateParamDeclList();
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=i->getParams().begin(); it!=i->getParams().end(); it++) {
            ic->getParams().push_back(ast::ITemplateParamDeclUP(
                copyT<ast::ITemplateParamDecl>(it->get())));
        }
        ic->setSpecialized(i->getSpecialized());
        return ic;
    }

    ast::IMethodParameterList *copyMethodParamList(ast::IMethodParameterList *i) {
        ast::IMethodParameterList *ic = m_factory->mkMethodParameterList();
        copyExprs(i->getParameters(), ic->getParameters());
        return ic;
    }

    void copyInitializers(
        const std::vector<ast::IActionFieldInitializerUP>    &src,
        std::vector<ast::IActionFieldInitializerUP>          &dst) {
        for (std::vector<ast::IActionFieldInitializerUP>::const_iterator
            it=src.begin(); it!=src.end(); it++) {
            dst.push_back(ast::IActionFieldInitializerUP(
                copyT<ast::IActionFieldInitializer>(it->get())));
        }
    }

public:

    // -----------------------------------------------------------------
    // Nodes that are not part of the AST proper, or that are rebuilt
    // rather than copied.  These stay unimplemented on purpose, but now
    // name themselves when reached.
    // -----------------------------------------------------------------

    virtual void visitSymbolImportSpec(ast::ISymbolImportSpec *i) { }

    virtual void visitScopeChild(ast::IScopeChild *i) {
        unhandled("a bare ScopeChild");
    }

    virtual void visitSymbolRefPath(ast::ISymbolRefPath *i) { }

    virtual void visitRefExpr(ast::IRefExpr *i) { }

    virtual void visitTemplateParamDeclList(ast::ITemplateParamDeclList *i) { }

    virtual void visitTemplateParamValueList(ast::ITemplateParamValueList *i) { }

    virtual void visitTemplateParamValue(ast::ITemplateParamValue *i) { }

    virtual void visitConstraintStmt(ast::IConstraintStmt *i) {
        unhandled("a bare ConstraintStmt");
    }

    virtual void visitScope(ast::IScope *i) {
        unhandled("a bare Scope");
    }

    virtual void visitScopeChildRef(ast::IScopeChildRef *i) {
        // A reference, not a definition: the target belongs to the original
        // tree and is shared rather than duplicated.
        m_sc = fin(i, m_factory->mkScopeChildRef(i->getTarget()));
    }

    virtual void visitDataType(ast::IDataType *i) {
        unhandled("a bare DataType");
    }

    virtual void visitExecStmt(ast::IExecStmt *i) {
        unhandled("a bare ExecStmt");
    }

    virtual void visitActivityStmt(ast::IActivityStmt *i) {
        unhandled("a bare ActivityStmt");
    }

    virtual void visitActivityJoinSpec(ast::IActivityJoinSpec *i) {
        unhandled("a bare ActivityJoinSpec");
    }

    virtual void visitNamedScopeChild(ast::INamedScopeChild *i) {
        unhandled("a bare NamedScopeChild");
    }

    virtual void visitTemplateParamDecl(ast::ITemplateParamDecl *i) {
        unhandled("a bare TemplateParamDecl");
    }

    virtual void visitRefExprTypeScopeGlobal(ast::IRefExprTypeScopeGlobal *i) { }

    virtual void visitRefExprTypeScopeContext(ast::IRefExprTypeScopeContext *i) { }

    virtual void visitRefExprScopeIndex(ast::IRefExprScopeIndex *i) { }

    virtual void visitSymbolScope(ast::ISymbolScope *i) {
        unhandled("a bare SymbolScope");
    }

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) {
        unhandled("SymbolEnumScope");
    }

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) {
        unhandled("SymbolExtendScope");
    }

    virtual void visitPackageScope(ast::IPackageScope *i) {
        unhandled("PackageScope");
    }

    virtual void visitExtendType(ast::IExtendType *i) {
        unhandled("ExtendType");
    }

    virtual void visitExtendEnum(ast::IExtendEnum *i) {
        unhandled("ExtendEnum");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
        unhandled("SymbolTypeScope");
    }

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
        unhandled("SymbolFunctionScope");
    }

    virtual void visitPackageImportStmt(ast::IPackageImportStmt *i) {
        ast::IPackageImportStmt *ic = m_factory->mkPackageImportStmt(
            i->getWildcard(),
            (i->getAlias())?copyT<ast::IExprId>(i->getAlias()):0
        );
        if (i->getPath()) {
            ic->setPath(copyT<ast::ITypeIdentifier>(i->getPath()));
        }
        m_sc = fin(i, ic);
    }

    // -----------------------------------------------------------------
    // Expressions
    // -----------------------------------------------------------------

    virtual void visitExprRefPathElem(ast::IExprRefPathElem *i) {
        unhandled("a bare ExprRefPathElem");
    }

    virtual void visitExprStaticRefPath(ast::IExprStaticRefPath *i) {
        DEBUG_ENTER("visitExprStaticRefPath");
        ast::IExprStaticRefPath *ic = m_factory->mkExprStaticRefPath(
            i->getIs_global(),
            copyT<ast::IExprMemberPathElem>(i->getLeaf())
        );
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin(); it!=i->getBase().end(); it++) {
            ic->getBase().push_back(ast::ITypeIdentifierElemUP(
                copyT<ast::ITypeIdentifierElem>(it->get())));
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprStaticRefPath");
    }

    virtual void visitExprString(ast::IExprString *i) {
        m_expr = m_factory->mkExprString(i->getValue(), i->getIs_raw());
    }

    virtual void visitExprSubscript(ast::IExprSubscript *i) {
        m_expr = m_factory->mkExprSubscript(
            copy(i->getExpr()),
            copy(i->getSubscript())
        );
    }

    virtual void visitExprSubstring(ast::IExprSubstring *i) {
        m_expr = m_factory->mkExprSubstring(
            copy(i->getExpr()),
            (i->getStart())?copy(i->getStart()):0,
            (i->getEnd())?copy(i->getEnd()):0
        );
    }

    virtual void visitExprUnary(ast::IExprUnary *i) {
        m_expr = m_factory->mkExprUnary(
            i->getOp(),
            copy(i->getRhs())
        );
    }

    virtual void visitExprIn(ast::IExprIn *i) {
        m_expr = m_factory->mkExprIn(
            copy(i->getLhs()),
            (i->getRhs())?copyT<ast::IExprOpenRangeList>(i->getRhs()):0,
            (i->getCollection())?copy(i->getCollection()):0
        );
    }

    virtual void visitExprOpenRangeList(ast::IExprOpenRangeList *i) {
        ast::IExprOpenRangeList *ic = m_factory->mkExprOpenRangeList();
        for (std::vector<ast::IExprOpenRangeValueUP>::const_iterator
            it=i->getValues().begin(); it!=i->getValues().end(); it++) {
            ic->getValues().push_back(ast::IExprOpenRangeValueUP(
                copyT<ast::IExprOpenRangeValue>(it->get())));
        }
        m_expr = ic;
    }

    virtual void visitExprOpenRangeValue(ast::IExprOpenRangeValue *i) {
        m_expr = m_factory->mkExprOpenRangeValue(
            (i->getLhs())?copy(i->getLhs()):0,
            (i->getRhs())?copy(i->getRhs()):0
        );
    }

    virtual void visitExprDomainOpenRangeList(ast::IExprDomainOpenRangeList *i) {
        ast::IExprDomainOpenRangeList *ic = m_factory->mkExprDomainOpenRangeList();
        for (std::vector<ast::IExprDomainOpenRangeValueUP>::const_iterator
            it=i->getValues().begin(); it!=i->getValues().end(); it++) {
            ic->getValues().push_back(ast::IExprDomainOpenRangeValueUP(
                copyT<ast::IExprDomainOpenRangeValue>(it->get())));
        }
        m_expr = ic;
    }

    virtual void visitExprDomainOpenRangeValue(ast::IExprDomainOpenRangeValue *i) {
        m_expr = m_factory->mkExprDomainOpenRangeValue(
            i->getSingle(),
            (i->getLhs())?copy(i->getLhs()):0,
            (i->getRhs())?copy(i->getRhs()):0
        );
    }

    virtual void visitExprListLiteral(ast::IExprListLiteral *i) {
        ast::IExprListLiteral *ic = m_factory->mkExprListLiteral();
        copyExprs(i->getValue(), ic->getValue());
        m_expr = ic;
    }

    virtual void visitExprStructLiteral(ast::IExprStructLiteral *i) {
        ast::IExprStructLiteral *ic = m_factory->mkExprStructLiteral();
        for (std::vector<ast::IExprStructLiteralItemUP>::const_iterator
            it=i->getValues().begin(); it!=i->getValues().end(); it++) {
            ic->getValues().push_back(ast::IExprStructLiteralItemUP(
                copyT<ast::IExprStructLiteralItem>(it->get())));
        }
        m_expr = ic;
    }

    virtual void visitExprStructLiteralItem(ast::IExprStructLiteralItem *i) {
        m_expr = m_factory->mkExprStructLiteralItem(
            copyT<ast::IExprId>(i->getId()),
            copy(i->getValue())
        );
    }

    virtual void visitExprAggrLiteral(ast::IExprAggrLiteral *i) {
        unhandled("a bare ExprAggrLiteral");
    }

    virtual void visitExprAggrEmpty(ast::IExprAggrEmpty *i) {
        m_expr = m_factory->mkExprAggrEmpty();
    }

    virtual void visitExprAggrList(ast::IExprAggrList *i) {
        ast::IExprAggrList *ic = m_factory->mkExprAggrList();
        copyExprs(i->getElems(), ic->getElems());
        m_expr = ic;
    }

    virtual void visitExprAggrMap(ast::IExprAggrMap *i) {
        ast::IExprAggrMap *ic = m_factory->mkExprAggrMap();
        for (std::vector<ast::IExprAggrMapElemUP>::const_iterator
            it=i->getElems().begin(); it!=i->getElems().end(); it++) {
            ic->getElems().push_back(ast::IExprAggrMapElemUP(
                m_factory->mkExprAggrMapElem(
                    copy((*it)->getLhs()),
                    copy((*it)->getRhs()))));
        }
        m_expr = ic;
    }

    virtual void visitExprAggrStruct(ast::IExprAggrStruct *i) {
        ast::IExprAggrStruct *ic = m_factory->mkExprAggrStruct();
        for (std::vector<ast::IExprAggrStructElemUP>::const_iterator
            it=i->getElems().begin(); it!=i->getElems().end(); it++) {
            ast::IExprAggrStructElem *e = m_factory->mkExprAggrStructElem(
                copyT<ast::IExprId>((*it)->getName()),
                copy((*it)->getValue()));
            e->setTarget((*it)->getTarget());
            ic->getElems().push_back(ast::IExprAggrStructElemUP(e));
        }
        m_expr = ic;
    }

    virtual void visitExprAggrMapElem(ast::IExprAggrMapElem *i) { }

    virtual void visitExprAggrStructElem(ast::IExprAggrStructElem *i) { }

    virtual void visitMethodParameterList(ast::IMethodParameterList *i) {
        m_expr = copyMethodParamList(i);
    }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) {
        ast::ITypeIdentifier *ic = m_factory->mkTypeIdentifier();
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getElems().begin();
            it!=i->getElems().end(); it++) {
            ic->getElems().push_back(ast::ITypeIdentifierElemUP(
                copyT<ast::ITypeIdentifierElem>(it->get())
            ));
        }

        if (i->getTarget()) {
            ic->setTarget(copy(i->getTarget()));
        }

        m_expr = ic;
    }

    virtual void visitTypeIdentifierElem(ast::ITypeIdentifierElem *i) {
        ast::ITemplateParamValueList *plist = 0;

        if (i->getParams()) {
            plist = m_factory->mkTemplateParamValueList();
            for (std::vector<ast::ITemplateParamValueUP>::const_iterator
                it=i->getParams()->getValues().begin();
                it!=i->getParams()->getValues().end(); it++) {
                plist->getValues().push_back(ast::ITemplateParamValueUP(copy(it->get())));
            }
        }

        ast::ITypeIdentifierElem *ic = m_factory->mkTypeIdentifierElem(
            copyT<ast::IExprId>(i->getId()),
            plist
        );

        m_expr = ic;
    }

    virtual void visitExprBin(ast::IExprBin *i) {
        m_expr = m_factory->mkExprBin(
            copy(i->getLhs()),
            i->getOp(),
            copy(i->getRhs())
        );
    }

    virtual void visitExprBitSlice(ast::IExprBitSlice *i) {
        m_expr = m_factory->mkExprBitSlice(
            copy(i->getLhs()),
            copy(i->getRhs())
        );
    }

    virtual void visitExprBool(ast::IExprBool *i) {
        m_expr = m_factory->mkExprBool(i->getValue());
    }

    virtual void visitExprCast(ast::IExprCast *i) {
        m_expr = m_factory->mkExprCast(
            copy(i->getCasting_type()),
            copy(i->getExpr())
        );
    }

    virtual void visitExprCompileHas(ast::IExprCompileHas *i) {
        m_expr = m_factory->mkExprCompileHas(
            copyT<ast::IExprRefPathStatic>(i->getRef())
        );
    }

    virtual void visitExprCond(ast::IExprCond *i) {
        m_expr = m_factory->mkExprCond(
            copy(i->getCond_e()),
            copy(i->getTrue_e()),
            copy(i->getFalse_e())
        );
    }

    virtual void visitExprHierarchicalId(ast::IExprHierarchicalId *i) {
        ast::IExprHierarchicalId *ic = m_factory->mkExprHierarchicalId();
        for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
            it=i->getElems().begin();
            it!=i->getElems().end(); it++) {
            ic->getElems().push_back(ast::IExprMemberPathElemUP(
                copyT<ast::IExprMemberPathElem>(it->get())));
        }
        m_expr = ic;
    }

    virtual void visitExprId(ast::IExprId *i) {
        ast::IExprId *ic = m_factory->mkExprId(
            i->getId(),
            i->getIs_escaped()
        );
        ic->setLocation(i->getLocation());
        m_expr = ic;
    }

    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) {
        ast::IMethodParameterList *plist = 0;

        if (i->getParams()) {
            plist = copyMethodParamList(i->getParams());
        }

        ast::IExprMemberPathElem *elem = m_factory->mkExprMemberPathElem(
            copyT<ast::IExprId>(i->getId()),
            plist);

        for (std::vector<ast::IExprUP>::const_iterator
            it=i->getSubscript().begin();
            it!=i->getSubscript().end(); it++) {
            elem->getSubscript().push_back(ast::IExprUP(copyT<ast::IExpr>(it->get())));
        }
        m_expr = elem;
    }

    virtual void visitExprNull(ast::IExprNull *i) {
        m_expr = m_factory->mkExprNull();
    }

    virtual void visitExprRefPath(ast::IExprRefPath *i) {
        unhandled("a bare ExprRefPath");
    }

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) {
        DEBUG_ENTER("visitExprRefPathId");
        ast::IExprRefPathId *ic = m_factory->mkExprRefPathId(
            copyT<ast::IExprId>(i->getId()));
        if (i->getSlice()) {
            ic->setSlice(copyT<ast::IExprBitSlice>(i->getSlice()));
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathId");
    }

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) {
        DEBUG_ENTER("visitExprRefPathContext");
        ast::IExprRefPathContext *ic = m_factory->mkExprRefPathContext(
            copyT<ast::IExprHierarchicalId>(i->getHier_id())
        );
        ic->setIs_super(i->getIs_super());
        if (i->getSlice()) {
            ic->setSlice(copyT<ast::IExprBitSlice>(i->getSlice()));
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathContext");
    }

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
        DEBUG_ENTER("visitExprRefPathStatic");
        ast::IExprRefPathStatic *ic = m_factory->mkExprRefPathStatic(
            i->getIs_global());
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin();
            it!=i->getBase().end(); it++) {
            ic->getBase().push_back(ast::ITypeIdentifierElemUP(
                copyT<ast::ITypeIdentifierElem>(it->get())));
        }
        if (i->getSlice()) {
            ic->setSlice(copyT<ast::IExprBitSlice>(i->getSlice()), true);
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathStatic");
    }

    virtual void visitExprRefPathStaticFunc(ast::IExprRefPathStaticFunc *i) {
        DEBUG_ENTER("visitExprRefPathStaticFunc");
        ast::IExprRefPathStaticFunc *ic = m_factory->mkExprRefPathStaticFunc(
            i->getIs_global(),
            (i->getParams())?copyMethodParamList(i->getParams()):0);
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin();
            it!=i->getBase().end(); it++) {
            ic->getBase().push_back(ast::ITypeIdentifierElemUP(
                copyT<ast::ITypeIdentifierElem>(it->get())));
        }
        if (i->getSlice()) {
            ic->setSlice(copyT<ast::IExprBitSlice>(i->getSlice()), true);
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathStaticFunc");
    }

    virtual void visitExprRefPathSuper(ast::IExprRefPathSuper *i) {
        DEBUG_ENTER("visitExprRefPathSuper");
        ast::IExprRefPathSuper *ic = m_factory->mkExprRefPathSuper(
            copyT<ast::IExprHierarchicalId>(i->getHier_id()));
        ic->setIs_super(i->getIs_super());
        if (i->getSlice()) {
            ic->setSlice(copyT<ast::IExprBitSlice>(i->getSlice()));
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathSuper");
    }

    virtual void visitExprSignedNumber(ast::IExprSignedNumber *i) {
        m_expr = m_factory->mkExprSignedNumber(
            i->getImage(),
            i->getWidth(),
            i->getValue()
        );
    }

    virtual void visitExprUnsignedNumber(ast::IExprUnsignedNumber *i) {
        m_expr = m_factory->mkExprUnsignedNumber(
            i->getImage(),
            i->getWidth(),
            i->getValue()
        );
    }

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
        DEBUG_ENTER("visitExprRefPathStaticRooted");
        ast::IExprRefPathStaticRooted *ic = m_factory->mkExprRefPathStaticRooted(
            copyT<ast::IExprRefPathStatic>(i->getRoot()),
            (i->getLeaf())?copyT<ast::IExprHierarchicalId>(i->getLeaf()):0
        );
        if (i->getSlice()) {
            ic->setSlice(copyT<ast::IExprBitSlice>(i->getSlice()));
        }
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathStaticRooted");
    }

    // -----------------------------------------------------------------
    // Data types
    // -----------------------------------------------------------------

    virtual void visitDataTypeBool(ast::IDataTypeBool *i) {
        m_dt = fin(i, m_factory->mkDataTypeBool());
    }

    virtual void visitDataTypeChandle(ast::IDataTypeChandle *i) {
        m_dt = fin(i, m_factory->mkDataTypeChandle());
    }

    virtual void visitDataTypePyObj(ast::IDataTypePyObj *i) {
        m_dt = fin(i, m_factory->mkDataTypePyObj());
    }

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) {
        m_dt = fin(i, m_factory->mkDataTypeEnum(
            (i->getTid())?copyT<ast::IDataTypeUserDefined>(i->getTid()):0,
            (i->getIn_rangelist())?copyT<ast::IExprOpenRangeList>(i->getIn_rangelist()):0
        ));
    }

    virtual void visitDataTypeRef(ast::IDataTypeRef *i) {
        m_dt = fin(i, m_factory->mkDataTypeRef(
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0
        ));
    }

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) {
        m_dt = fin(i, m_factory->mkDataTypeInt(
            i->getIs_signed(),
            (i->getWidth())?copy(i->getWidth()):0,
            (i->getIn_range())?copyT<ast::IExprDomainOpenRangeList>(i->getIn_range()):0
        ));
    }

    virtual void visitDataTypeString(ast::IDataTypeString *i) {
        ast::IDataTypeString *ci = m_factory->mkDataTypeString(i->getHas_range());
        if (i->getHas_range()) {
            ci->getIn_range().insert(
                ci->getIn_range().begin(),
                i->getIn_range().begin(),
                i->getIn_range().end()
            );
        }

        m_dt = fin(i, ci);
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
        m_dt = fin(i, m_factory->mkDataTypeUserDefined(
            i->getIs_global(),
            copyT<ast::ITypeIdentifier>(i->getType_id())
        ));
    }

    // -----------------------------------------------------------------
    // Template parameter declarations
    //
    // A generic type nested inside another generic keeps its own parameter
    // list, so these have to survive the copy.  The outer specialization
    // replaces only the outer list.
    // -----------------------------------------------------------------

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) {
        m_sc = fin(i, m_factory->mkTemplateGenericTypeParamDecl(
            copyT<ast::IExprId>(i->getName()),
            (i->getDflt())?copy(i->getDflt()):0
        ));
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) {
        m_sc = fin(i, m_factory->mkTemplateCategoryTypeParamDecl(
            copyT<ast::IExprId>(i->getName()),
            i->getCategory(),
            (i->getRestriction())?copyT<ast::ITypeIdentifier>(i->getRestriction()):0,
            (i->getDflt())?copy(i->getDflt()):0
        ));
    }

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) {
        m_sc = fin(i, m_factory->mkTemplateValueParamDecl(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copy(i->getType()):0,
            (i->getDflt())?copy(i->getDflt()):0
        ));
    }

    virtual void visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) {
        DEBUG_ENTER("visitTemplateParamTypeValue");
        ast::ITemplateParamTypeValue *ic = m_factory->mkTemplateParamTypeValue(
            copyT<ast::IDataType>(i->getValue())
        );
        m_param_val = ic;
        DEBUG_LEAVE("visitTemplateParamTypeValue");
    }

    virtual void visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) {
        DEBUG_ENTER("visitTemplateParamExprValue");
        ast::ITemplateParamExprValue *ic = m_factory->mkTemplateParamExprValue(
            copyT<ast::IExpr>(i->getValue())
        );
        m_param_val = ic;
        DEBUG_LEAVE("visitTemplateParamExprValue");
    }

    // -----------------------------------------------------------------
    // Fields
    // -----------------------------------------------------------------

    virtual void visitField(ast::IField *i) {
        m_sc = fin(i, m_factory->mkField(
            copyT<ast::IExprId>(i->getName()),
            copy(i->getType()),
            i->getAttr(),
            (i->getInit())?copy(i->getInit()):0
        ));
    }

    /**
     * The implicit ``comp`` reference every action carries.
     *
     * Missing this is what made *any* generic action crash on specialization,
     * regardless of its body.
     */
    virtual void visitFieldCompRef(ast::IFieldCompRef *i) {
        m_sc = fin(i, m_factory->mkFieldCompRef(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0
        ));
    }

    virtual void visitFieldRef(ast::IFieldRef *i) {
        m_sc = fin(i, m_factory->mkFieldRef(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0,
            i->getIs_input()
        ));
    }

    virtual void visitFieldClaim(ast::IFieldClaim *i) {
        m_sc = fin(i, m_factory->mkFieldClaim(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0,
            i->getIs_lock()
        ));
    }

    virtual void visitFieldPool(ast::IFieldPool *i) {
        m_sc = fin(i, m_factory->mkFieldPool(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0,
            (i->getSize())?copy(i->getSize()):0
        ));
    }

    virtual void visitActionHandleField(ast::IActionHandleField *i) {
        ast::IActionHandleField *ic = m_factory->mkActionHandleField(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copy(i->getType()):0
        );
        copyInitializers(i->getInitializers(), ic->getInitializers());
        m_sc = fin(i, ic);
    }

    virtual void visitActionFieldInitializer(ast::IActionFieldInitializer *i) {
        m_sc = fin(i, m_factory->mkActionFieldInitializer(
            (i->getPath())?copyT<ast::IExprHierarchicalId>(i->getPath()):0,
            (i->getValue())?copy(i->getValue()):0
        ));
    }

    virtual void visitComponentBind(ast::IComponentBind *i) {
        ast::IComponentBind *ic = m_factory->mkComponentBind(
            i->getPool_path(),
            i->getIs_wildcard());
        ic->getTargets().insert(
            ic->getTargets().begin(),
            i->getTargets().begin(),
            i->getTargets().end());
        m_sc = fin(i, ic);
    }

    virtual void visitAnnotation(ast::IAnnotation *i) {
        ast::IAnnotation *ic = m_factory->mkAnnotation(
            (i->getType())?copyT<ast::ITypeIdentifier>(i->getType()):0);
        for (std::vector<ast::IAnnotationParamUP>::const_iterator
            it=i->getParameters().begin(); it!=i->getParameters().end(); it++) {
            ic->getParameters().push_back(ast::IAnnotationParamUP(
                copyT<ast::IAnnotationParam>(it->get())));
        }
        // Note: not routed through fin(), which copies annotations and would
        // recurse here.
        ic->setLocation(i->getLocation());
        ic->setIndex(i->getIndex());
        m_sc = ic;
    }

    virtual void visitAnnotationParam(ast::IAnnotationParam *i) {
        ast::IAnnotationParam *ic = m_factory->mkAnnotationParam(
            (i->getValue())?copy(i->getValue()):0);
        if (i->getName()) {
            ic->setName(copyT<ast::IExprId>(i->getName()));
        }
        ic->setLocation(i->getLocation());
        ic->setIndex(i->getIndex());
        m_sc = ic;
    }

    // -----------------------------------------------------------------
    // Enums and typedefs
    // -----------------------------------------------------------------

    virtual void visitEnumDecl(ast::IEnumDecl *i) {
        ast::IEnumDecl *ic = m_factory->mkEnumDecl(
            copyT<ast::IExprId>(i->getName()));
        for (std::vector<ast::IEnumItemUP>::const_iterator
            it=i->getItems().begin(); it!=i->getItems().end(); it++) {
            ic->getItems().push_back(ast::IEnumItemUP(
                copyT<ast::IEnumItem>(it->get())));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitEnumItem(ast::IEnumItem *i) {
        m_sc = fin(i, m_factory->mkEnumItem(
            copyT<ast::IExprId>(i->getName()),
            (i->getValue())?copy(i->getValue()):0
        ));
    }

    virtual void visitTypedefDeclaration(ast::ITypedefDeclaration *i) {
        m_sc = fin(i, m_factory->mkTypedefDeclaration(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copy(i->getType()):0
        ));
    }

    // -----------------------------------------------------------------
    // Functions
    // -----------------------------------------------------------------

    virtual void visitFunctionParamDecl(ast::IFunctionParamDecl *i) override {
        ast::IFunctionParamDecl *ic = m_factory->mkFunctionParamDecl(
            i->getKind(),
            copyT<ast::IExprId>(i->getName()),
            copy(i->getType()),
            i->getDir(),
            (i->getDflt())?copy(i->getDflt()):0
        );
        ic->setIs_varargs(i->getIs_varargs());
        m_sc = fin(i, ic);
    }

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override {
        DEBUG_ENTER("visitFunctionPrototype %s", i->getName()->getId().c_str());
        ast::IFunctionPrototype *ic = m_factory->mkFunctionPrototype(
            copyT<ast::IExprId>(i->getName()),
            (i->getRtype())?copy(i->getRtype()):0,
            i->getIs_target(),
            i->getIs_solve());
        ic->setIs_pure(i->getIs_pure());
        ic->setIs_core(i->getIs_core());
        for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getParameters().begin();
            it!=i->getParameters().end(); it++) {
            ic->getParameters().push_back(
                ast::IFunctionParamDeclUP(copyT<ast::IFunctionParamDecl>(it->get())));
        }

        m_sc = fin(i, ic);
        DEBUG_LEAVE("visitFunctionPrototype");
    }

    virtual void visitFunctionDefinition(ast::IFunctionDefinition *i) {
        DEBUG_ENTER("visitFunctionDefinition");
        ast::IFunctionDefinition *ic = m_factory->mkFunctionDefinition(
            copyT<ast::IFunctionPrototype>(i->getProto()),
            (i->getBody())?copyT<ast::IExecScope>(i->getBody()):0,
            i->getPlat()
        );
        ic->setEndLocation(i->getEndLocation());
        m_sc = fin(i, ic);
        DEBUG_LEAVE("visitFunctionDefinition");
    }

    virtual void visitFunctionImport(ast::IFunctionImport *i) {
        unhandled("a bare FunctionImport");
    }

    virtual void visitFunctionImportProto(ast::IFunctionImportProto *i) {
        m_sc = fin(i, m_factory->mkFunctionImportProto(
            i->getPlat(),
            i->getLang(),
            (i->getProto())?copyT<ast::IFunctionPrototype>(i->getProto()):0
        ));
    }

    virtual void visitFunctionImportType(ast::IFunctionImportType *i) {
        m_sc = fin(i, m_factory->mkFunctionImportType(
            i->getPlat(),
            i->getLang(),
            (i->getType())?copyT<ast::ITypeIdentifier>(i->getType()):0
        ));
    }

    virtual void visitExportFunction(ast::IExportFunction *i) {
        m_sc = fin(i, m_factory->mkExportFunction(
            i->getPlat(),
            (i->getName())?copyT<ast::IExprId>(i->getName()):0
        ));
    }

    // -----------------------------------------------------------------
    // Exec blocks and procedural statements
    // -----------------------------------------------------------------

    virtual void visitExecScope(ast::IExecScope *i) {
        DEBUG_ENTER("visitExecScope %s", i->getName().c_str());
        ast::IExecScope *ic = m_factory->mkExecScope(i->getName());
        ic->setEndLocation(i->getEndLocation());
        m_sc = finSymbolScope(i, ic);
        DEBUG_LEAVE("visitExecScope %s", i->getName().c_str());
    }

    virtual void visitExecBlock(ast::IExecBlock *i) {
        DEBUG_ENTER("visitExecBlock %s", i->getName().c_str());
        ast::IExecBlock *ic = m_factory->mkExecBlock(i->getName(), i->getKind());
        ic->setEndLocation(i->getEndLocation());
        m_sc = finSymbolScope(i, ic);
        DEBUG_LEAVE("visitExecBlock %s", i->getName().c_str());
    }

    virtual void visitExecTargetTemplateBlock(ast::IExecTargetTemplateBlock *i) {
        ast::IExecTargetTemplateBlock *ic = m_factory->mkExecTargetTemplateBlock(
            i->getKind(),
            i->getData());
        for (std::vector<ast::IExecTargetTemplateParamUP>::const_iterator
            it=i->getParameters().begin(); it!=i->getParameters().end(); it++) {
            ic->getParameters().push_back(ast::IExecTargetTemplateParamUP(
                m_factory->mkExecTargetTemplateParam(
                    copy((*it)->getExpr()),
                    (*it)->getStart(),
                    (*it)->getEnd())));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitExecTargetTemplateParam(ast::IExecTargetTemplateParam *i) { }

    virtual void visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtAssignment(
            copy(i->getLhs()),
            i->getOp(),
            copy(i->getRhs())
        ));
    }

    virtual void visitProceduralStmtExpr(ast::IProceduralStmtExpr *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtExpr(
            (i->getExpr())?copy(i->getExpr()):0
        ));
    }

    virtual void visitProceduralStmtFunctionCall(ast::IProceduralStmtFunctionCall *i) {
        ast::IProceduralStmtFunctionCall *ic = m_factory->mkProceduralStmtFunctionCall(
            (i->getPrefix())?copyT<ast::IExprRefPathStaticRooted>(i->getPrefix()):0);
        copyExprs(i->getParams(), ic->getParams());
        m_sc = fin(i, ic);
    }

    virtual void visitProceduralStmtReturn(ast::IProceduralStmtReturn *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtReturn(
            (i->getExpr())?copy(i->getExpr()):0
        ));
    }

    virtual void visitProceduralStmtBreak(ast::IProceduralStmtBreak *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtBreak());
    }

    virtual void visitProceduralStmtContinue(ast::IProceduralStmtContinue *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtContinue());
    }

    virtual void visitProceduralStmtYield(ast::IProceduralStmtYield *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtYield());
    }

    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtDataDeclaration(
            copyT<ast::IExprId>(i->getName()),
            (i->getDatatype())?copy(i->getDatatype()):0,
            (i->getInit())?copy(i->getInit()):0
        ));
    }

    virtual void visitProceduralStmtBody(ast::IProceduralStmtBody *i) {
        unhandled("a bare ProceduralStmtBody");
    }

    virtual void visitProceduralStmtRandomize(ast::IProceduralStmtRandomize *i) {
        ast::IProceduralStmtRandomize *ic = m_factory->mkProceduralStmtRandomize(
            (i->getTarget())?copy(i->getTarget()):0);
        copyConstraints(i->getConstraints(), ic->getConstraints());
        m_sc = fin(i, ic);
    }

    virtual void visitProceduralStmtIfClause(ast::IProceduralStmtIfClause *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtIfClause(
            (i->getCond())?copy(i->getCond()):0,
            (i->getBody())?copy(i->getBody()):0
        ));
    }

    virtual void visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) {
        ast::IProceduralStmtIfElse *ic = m_factory->mkProceduralStmtIfElse();
        for (std::vector<ast::IProceduralStmtIfClauseUP>::const_iterator
            it=i->getIf_then().begin(); it!=i->getIf_then().end(); it++) {
            ic->getIf_then().push_back(ast::IProceduralStmtIfClauseUP(
                copyT<ast::IProceduralStmtIfClause>(it->get())));
        }
        if (i->getElse_then()) {
            ic->setElse_then(copy(i->getElse_then()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) {
        ast::IProceduralStmtMatch *ic = m_factory->mkProceduralStmtMatch(
            (i->getExpr())?copy(i->getExpr()):0);
        for (std::vector<ast::IProceduralStmtMatchChoiceUP>::const_iterator
            it=i->getChoices().begin(); it!=i->getChoices().end(); it++) {
            ic->getChoices().push_back(ast::IProceduralStmtMatchChoiceUP(
                copyT<ast::IProceduralStmtMatchChoice>(it->get())));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitProceduralStmtMatchChoice(ast::IProceduralStmtMatchChoice *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtMatchChoice(
            i->getIs_default(),
            (i->getCond())?copyT<ast::IExprOpenRangeList>(i->getCond()):0,
            (i->getBody())?copy(i->getBody()):0
        ));
    }

    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtRepeatWhile(
            (i->getBody())?copy(i->getBody()):0,
            (i->getExpr())?copy(i->getExpr()):0
        ));
    }

    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) {
        m_sc = fin(i, m_factory->mkProceduralStmtWhile(
            (i->getBody())?copy(i->getBody()):0,
            (i->getExpr())?copy(i->getExpr()):0
        ));
    }

    virtual void visitProceduralStmtSymbolBodyScope(ast::IProceduralStmtSymbolBodyScope *i) {
        unhandled("a bare ProceduralStmtSymbolBodyScope");
    }

    /**
     * ``repeat`` carries its index variable in its own symbol scope, declared
     * by AstBuilderInt rather than by the symbol-tree builder.  The body sits
     * beside the children rather than in them, at index ``children.size()``.
     */
    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
        ast::IProceduralStmtRepeat *ic = m_factory->mkProceduralStmtRepeat(
            i->getName(),
            0,
            (i->getIt_id())?copyT<ast::IExprId>(i->getIt_id()):0,
            (i->getCount())?copy(i->getCount()):0);
        finSymbolScope(i, ic);
        if (i->getBody()) {
            ic->setBody(copy(i->getBody()));
        }
        m_sc = ic;
    }

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) {
        ast::IProceduralStmtForeach *ic = m_factory->mkProceduralStmtForeach(
            i->getName(),
            0,
            (i->getPath())?copyT<ast::IExprRefPath>(i->getPath()):0,
            (i->getIt_id())?copyT<ast::IExprId>(i->getIt_id()):0,
            (i->getIdx_id())?copyT<ast::IExprId>(i->getIdx_id()):0);
        finSymbolScope(i, ic);
        if (i->getBody()) {
            ic->setBody(copy(i->getBody()));
        }
        m_sc = ic;
    }

    // -----------------------------------------------------------------
    // Constraints
    // -----------------------------------------------------------------

    virtual void visitConstraintScope(ast::IConstraintScope *i) {
        ast::IConstraintScope *ic = m_factory->mkConstraintScope();
        ic->setEndLocation(i->getEndLocation());
        copyConstraints(i->getConstraints(), ic->getConstraints());
        m_constraint = fin(i, ic);
    }

    virtual void visitConstraintBlock(ast::IConstraintBlock *i) {
        ast::IConstraintBlock *ic = m_factory->mkConstraintBlock(
            i->getName(),
            i->getIs_dynamic());
        ic->setEndLocation(i->getEndLocation());
        copyConstraints(i->getConstraints(), ic->getConstraints());
        m_sc = fin(i, ic);
    }

    virtual void visitConstraintStmtExpr(ast::IConstraintStmtExpr *i) {
        m_constraint = fin(i, m_factory->mkConstraintStmtExpr(
            copy(i->getExpr())
        ));
    }

    virtual void visitConstraintStmtIf(ast::IConstraintStmtIf *i) {
        m_constraint = fin(i, m_factory->mkConstraintStmtIf(
            copy(i->getCond()),
            copyT<ast::IConstraintScope>(i->getTrue_c()),
            (i->getFalse_c())?copyT<ast::IConstraintScope>(i->getFalse_c()):0
        ));
    }

    virtual void visitConstraintStmtField(ast::IConstraintStmtField *i) {
        m_constraint = fin(i, m_factory->mkConstraintStmtField(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copy(i->getType()):0
        ));
    }

    virtual void visitConstraintStmtUnique(ast::IConstraintStmtUnique *i) {
        ast::IConstraintStmtUnique *ic = m_factory->mkConstraintStmtUnique();
        copyHierIds(i->getList(), ic->getList());
        m_constraint = fin(i, ic);
    }

    virtual void visitConstraintStmtDefault(ast::IConstraintStmtDefault *i) {
        m_constraint = fin(i, m_factory->mkConstraintStmtDefault(
            (i->getHid())?copyT<ast::IExprHierarchicalId>(i->getHid()):0,
            (i->getExpr())?copy(i->getExpr()):0
        ));
    }

    virtual void visitConstraintStmtDefaultDisable(ast::IConstraintStmtDefaultDisable *i) {
        m_constraint = fin(i, m_factory->mkConstraintStmtDefaultDisable(
            (i->getHid())?copyT<ast::IExprHierarchicalId>(i->getHid()):0
        ));
    }

    virtual void visitConstraintStmtImplication(ast::IConstraintStmtImplication *i) {
        ast::IConstraintStmtImplication *ic = m_factory->mkConstraintStmtImplication(
            (i->getCond())?copy(i->getCond()):0);
        ic->setEndLocation(i->getEndLocation());
        copyConstraints(i->getConstraints(), ic->getConstraints());
        m_constraint = fin(i, ic);
    }

    virtual void visitConstraintSymbolScope(ast::IConstraintSymbolScope *i) {
        // The owning statement re-points itself at the copy; see
        // visitConstraintStmtForeach.
        m_sc = finSymbolScope(i, m_factory->mkConstraintSymbolScope(i->getName()));
    }

    /**
     * The iteration and index variables live in the statement's own symbol
     * scope, which owns them; the ``it``/``idx`` slots are non-owning aliases
     * into that scope's children.  Copy the scope, then re-point the aliases
     * at the copies -- pointing them at the originals would leave the
     * specialization sharing declarations with the generic.
     */
    virtual void visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) {
        ast::IConstraintStmtForeach *ic = m_factory->mkConstraintStmtForeach(
            (i->getExpr())?copy(i->getExpr()):0);
        ic->setEndLocation(i->getEndLocation());
        copyConstraints(i->getConstraints(), ic->getConstraints());

        if (i->getSymtab()) {
            ast::IConstraintSymbolScope *st =
                copyT<ast::IConstraintSymbolScope>(i->getSymtab());
            ic->setSymtab(st);
            st->setConstraint(ic);
            ic->setIt(aliasField(st, i->getIt()));
            ic->setIdx(aliasField(st, i->getIdx()));
        }

        m_constraint = fin(i, ic);
    }

    virtual void visitConstraintStmtForall(ast::IConstraintStmtForall *i) {
        ast::IConstraintStmtForall *ic = m_factory->mkConstraintStmtForall(
            (i->getIterator_id())?copyT<ast::IExprId>(i->getIterator_id()):0,
            (i->getType_id())?copyT<ast::IDataTypeUserDefined>(i->getType_id()):0,
            (i->getRef_path())?copyT<ast::IExprRefPath>(i->getRef_path()):0);
        ic->setEndLocation(i->getEndLocation());
        copyConstraints(i->getConstraints(), ic->getConstraints());

        if (i->getSymtab()) {
            ast::IConstraintSymbolScope *st =
                copyT<ast::IConstraintSymbolScope>(i->getSymtab());
            ic->setSymtab(st);
            st->setConstraint(ic);
        }

        m_constraint = fin(i, ic);
    }

    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) {
        ast::IGenericConstraintDeclBool *ic = m_factory->mkGenericConstraintDeclBool(
            i->getName(),
            i->getIs_dynamic());
        ic->setIs_static(i->getIs_static());
        ic->setEndLocation(i->getEndLocation());
        for (std::vector<ast::IGenericConstraintParamUP>::const_iterator
            it=i->getParameters().begin(); it!=i->getParameters().end(); it++) {
            ic->getParameters().push_back(ast::IGenericConstraintParamUP(
                copyT<ast::IGenericConstraintParam>(it->get())));
        }
        copyConstraints(i->getConstraints(), ic->getConstraints());
        m_sc = fin(i, ic);
    }

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) {
        ast::IGenericConstraintDeclValue *ic = m_factory->mkGenericConstraintDeclValue();
        ic->setIs_static(i->getIs_static());
        ic->setIs_return_numeric(i->getIs_return_numeric());
        if (i->getReturn_type()) {
            ic->setReturn_type(copy(i->getReturn_type()));
        }
        if (i->getName()) {
            ic->setName(copyT<ast::IExprId>(i->getName()));
        }
        for (std::vector<ast::IGenericConstraintParamUP>::const_iterator
            it=i->getParameters().begin(); it!=i->getParameters().end(); it++) {
            ic->getParameters().push_back(ast::IGenericConstraintParamUP(
                copyT<ast::IGenericConstraintParam>(it->get())));
        }
        if (i->getExpr()) {
            ic->setExpr(copy(i->getExpr()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitGenericConstraintParam(ast::IGenericConstraintParam *i) {
        m_sc = fin(i, m_factory->mkGenericConstraintParam(
            (i->getName())?copyT<ast::IExprId>(i->getName()):0,
            i->getIs_const(),
            i->getIs_numeric(),
            (i->getType())?copy(i->getType()):0
        ));
    }

    // -----------------------------------------------------------------
    // Coverage
    // -----------------------------------------------------------------

    virtual void visitCovergroup(ast::ICovergroup *i) {
        ast::ICovergroup *ic = m_factory->mkCovergroup(
            (i->getName())?copyT<ast::IExprId>(i->getName()):0);
        for (std::vector<ast::ICovergroupCoverpointUP>::const_iterator
            it=i->getCoverpoints().begin(); it!=i->getCoverpoints().end(); it++) {
            ic->getCoverpoints().push_back(ast::ICovergroupCoverpointUP(
                copyT<ast::ICovergroupCoverpoint>(it->get())));
        }
        for (std::vector<ast::ICovergroupCrossUP>::const_iterator
            it=i->getCrosses().begin(); it!=i->getCrosses().end(); it++) {
            ic->getCrosses().push_back(ast::ICovergroupCrossUP(
                copyT<ast::ICovergroupCross>(it->get())));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitCovergroupCoverpoint(ast::ICovergroupCoverpoint *i) {
        m_sc = fin(i, m_factory->mkCovergroupCoverpoint(
            (i->getName())?copyT<ast::IExprId>(i->getName()):0,
            (i->getTarget())?copy(i->getTarget()):0
        ));
    }

    virtual void visitCovergroupCross(ast::ICovergroupCross *i) {
        ast::ICovergroupCross *ic = m_factory->mkCovergroupCross(
            (i->getName())?copyT<ast::IExprId>(i->getName()):0);
        for (std::vector<ast::IExprIdUP>::const_iterator
            it=i->getCoverpoint_names().begin();
            it!=i->getCoverpoint_names().end(); it++) {
            ic->getCoverpoint_names().push_back(ast::IExprIdUP(
                copyT<ast::IExprId>(it->get())));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitCoverStmtInline(ast::ICoverStmtInline *i) {
        m_sc = fin(i, m_factory->mkCoverStmtInline(
            (i->getBody())?copy(i->getBody()):0
        ));
    }

    virtual void visitCoverStmtReference(ast::ICoverStmtReference *i) {
        m_sc = fin(i, m_factory->mkCoverStmtReference(
            (i->getTarget())?copyT<ast::IExprRefPath>(i->getTarget()):0
        ));
    }

    // -----------------------------------------------------------------
    // Activities
    // -----------------------------------------------------------------

    virtual void visitActivityDecl(ast::IActivityDecl *i) {
        m_sc = finSymbolScope(i, m_factory->mkActivityDecl(i->getName()));
    }

    virtual void visitActivityLabeledScope(ast::IActivityLabeledScope *i) {
        unhandled("a bare ActivityLabeledScope");
    }

    virtual void visitActivitySequence(ast::IActivitySequence *i) {
        ast::IActivitySequence *ic = m_factory->mkActivitySequence(i->getName());
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = finSymbolScope(i, ic);
    }

    virtual void visitActivityParallel(ast::IActivityParallel *i) {
        ast::IActivityParallel *ic = m_factory->mkActivityParallel(
            i->getName(),
            (i->getJoin_spec())?copyT<ast::IActivityJoinSpec>(i->getJoin_spec()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = finSymbolScope(i, ic);
    }

    virtual void visitActivitySchedule(ast::IActivitySchedule *i) {
        ast::IActivitySchedule *ic = m_factory->mkActivitySchedule(
            i->getName(),
            (i->getJoin_spec())?copyT<ast::IActivityJoinSpec>(i->getJoin_spec()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = finSymbolScope(i, ic);
    }

    virtual void visitActivityLabeledStmt(ast::IActivityLabeledStmt *i) {
        unhandled("a bare ActivityLabeledStmt");
    }

    virtual void visitActivityBindStmt(ast::IActivityBindStmt *i) {
        ast::IActivityBindStmt *ic = m_factory->mkActivityBindStmt(
            (i->getLhs())?copyT<ast::IExprHierarchicalId>(i->getLhs()):0);
        copyHierIds(i->getRhs(), ic->getRhs());
        m_sc = fin(i, ic);
    }

    virtual void visitActivityConstraint(ast::IActivityConstraint *i) {
        m_sc = fin(i, m_factory->mkActivityConstraint(
            (i->getConstraint())?copy(i->getConstraint()):0
        ));
    }

    virtual void visitActivitySchedulingConstraint(ast::IActivitySchedulingConstraint *i) {
        ast::IActivitySchedulingConstraint *ic =
            m_factory->mkActivitySchedulingConstraint(i->getIs_parallel());
        copyHierIds(i->getTargets(), ic->getTargets());
        m_sc = fin(i, ic);
    }

    virtual void visitActivityJoinSpecBranch(ast::IActivityJoinSpecBranch *i) {
        ast::IActivityJoinSpecBranch *ic = m_factory->mkActivityJoinSpecBranch();
        for (std::vector<ast::IExprRefPathContextUP>::const_iterator
            it=i->getBranches().begin(); it!=i->getBranches().end(); it++) {
            ic->getBranches().push_back(ast::IExprRefPathContextUP(
                copyT<ast::IExprRefPathContext>(it->get())));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityJoinSpecFirst(ast::IActivityJoinSpecFirst *i) {
        m_sc = fin(i, m_factory->mkActivityJoinSpecFirst(
            (i->getCount())?copy(i->getCount()):0
        ));
    }

    virtual void visitActivityJoinSpecNone(ast::IActivityJoinSpecNone *i) {
        m_sc = fin(i, m_factory->mkActivityJoinSpecNone());
    }

    virtual void visitActivityJoinSpecSelect(ast::IActivityJoinSpecSelect *i) {
        m_sc = fin(i, m_factory->mkActivityJoinSpecSelect(
            (i->getCount())?copy(i->getCount()):0
        ));
    }

    virtual void visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) {
        ast::IActivityActionHandleTraversal *ic =
            m_factory->mkActivityActionHandleTraversal(
                (i->getTarget())?copyT<ast::IExprRefPathContext>(i->getTarget()):0,
                (i->getWith_c())?copy(i->getWith_c()):0);
        copyInitializers(i->getInitializers(), ic->getInitializers());
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) {
        ast::IActivityActionTypeTraversal *ic =
            m_factory->mkActivityActionTypeTraversal(
                (i->getTarget())?copyT<ast::IDataTypeUserDefined>(i->getTarget()):0,
                (i->getWith_c())?copy(i->getWith_c()):0);
        copyInitializers(i->getInitializers(), ic->getInitializers());
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityAtomicBlock(ast::IActivityAtomicBlock *i) {
        ast::IActivityAtomicBlock *ic = m_factory->mkActivityAtomicBlock(
            (i->getBody())?copy(i->getBody()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityForeach(ast::IActivityForeach *i) {
        ast::IActivityForeach *ic = m_factory->mkActivityForeach(
            (i->getIt_id())?copyT<ast::IExprId>(i->getIt_id()):0,
            (i->getIdx_id())?copyT<ast::IExprId>(i->getIdx_id()):0,
            (i->getTarget())?copyT<ast::IExprRefPathContext>(i->getTarget()):0,
            (i->getBody())?copy(i->getBody()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityIfElse(ast::IActivityIfElse *i) {
        ast::IActivityIfElse *ic = m_factory->mkActivityIfElse(
            (i->getCond())?copy(i->getCond()):0,
            (i->getTrue_s())?copyT<ast::IActivityStmt>(i->getTrue_s()):0,
            (i->getFalse_s())?copyT<ast::IActivityStmt>(i->getFalse_s()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityMatch(ast::IActivityMatch *i) {
        ast::IActivityMatch *ic = m_factory->mkActivityMatch(
            (i->getCond())?copy(i->getCond()):0);
        for (std::vector<ast::IActivityMatchChoiceUP>::const_iterator
            it=i->getChoices().begin(); it!=i->getChoices().end(); it++) {
            ic->getChoices().push_back(ast::IActivityMatchChoiceUP(
                m_factory->mkActivityMatchChoice(
                    (*it)->getIs_default(),
                    ((*it)->getCond())?copyT<ast::IExprOpenRangeList>((*it)->getCond()):0,
                    ((*it)->getBody())?copy((*it)->getBody()):0)));
        }
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityMatchChoice(ast::IActivityMatchChoice *i) { }

    virtual void visitActivitySelectBranch(ast::IActivitySelectBranch *i) { }

    virtual void visitActivityRepeatCount(ast::IActivityRepeatCount *i) {
        ast::IActivityRepeatCount *ic = m_factory->mkActivityRepeatCount(
            (i->getLoop_var())?copyT<ast::IExprId>(i->getLoop_var()):0,
            (i->getCount())?copy(i->getCount()):0,
            (i->getBody())?copy(i->getBody()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityRepeatWhile(ast::IActivityRepeatWhile *i) {
        ast::IActivityRepeatWhile *ic = m_factory->mkActivityRepeatWhile(
            (i->getCond())?copy(i->getCond()):0,
            (i->getBody())?copy(i->getBody()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivityReplicate(ast::IActivityReplicate *i) {
        ast::IActivityReplicate *ic = m_factory->mkActivityReplicate(
            (i->getIdx_id())?copyT<ast::IExprId>(i->getIdx_id()):0,
            (i->getIt_label())?copyT<ast::IExprId>(i->getIt_label()):0,
            (i->getBody())?copy(i->getBody()):0);
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivitySelect(ast::IActivitySelect *i) {
        ast::IActivitySelect *ic = m_factory->mkActivitySelect();
        for (std::vector<ast::IActivitySelectBranchUP>::const_iterator
            it=i->getBranches().begin(); it!=i->getBranches().end(); it++) {
            ic->getBranches().push_back(ast::IActivitySelectBranchUP(
                m_factory->mkActivitySelectBranch(
                    ((*it)->getGuard())?copy((*it)->getGuard()):0,
                    ((*it)->getWeight())?copy((*it)->getWeight()):0,
                    ((*it)->getBody())?copy((*it)->getBody()):0)));
        }
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    virtual void visitActivitySuper(ast::IActivitySuper *i) {
        ast::IActivitySuper *ic = m_factory->mkActivitySuper();
        if (i->getLabel()) {
            ic->setLabel(copyT<ast::IExprId>(i->getLabel()));
        }
        m_sc = fin(i, ic);
    }

    // -----------------------------------------------------------------
    // Type scopes
    // -----------------------------------------------------------------

    virtual void visitTypeScope(ast::ITypeScope *i) {
        unhandled("a bare TypeScope");
    }

    virtual void visitStruct(ast::IStruct *i) {
        ast::IStruct *ic = m_factory->mkStruct(
            copyT<ast::IExprId>(i->getName()),
            (i->getSuper_t())?copyT<ast::ITypeIdentifier>(i->getSuper_t()):0,
            i->getKind()
        );

        if (i->getParams()) {
            ic->setParams(copyParamDeclList(i->getParams()));
        }
        ic->setOpaque(i->getOpaque());
        ic->setEndLocation(i->getEndLocation());

        copyChildren(i->getChildren(), ic->getChildren());

        m_sc = fin(i, ic);
    }

    virtual void visitAction(ast::IAction *i) {
        ast::IAction *ic = m_factory->mkAction(
            copyT<ast::IExprId>(i->getName()),
            (i->getSuper_t())?copyT<ast::ITypeIdentifier>(i->getSuper_t()):0,
            i->getIs_abstract()
        );

        if (i->getParams()) {
            ic->setParams(copyParamDeclList(i->getParams()));
        }
        ic->setOpaque(i->getOpaque());
        ic->setEndLocation(i->getEndLocation());

        copyChildren(i->getChildren(), ic->getChildren());

        m_sc = fin(i, ic);
    }

    virtual void visitComponent(ast::IComponent *i) {
        ast::IComponent *ic = m_factory->mkComponent(
            copyT<ast::IExprId>(i->getName()),
            (i->getSuper_t())?copyT<ast::ITypeIdentifier>(i->getSuper_t()):0
        );

        if (i->getParams()) {
            ic->setParams(copyParamDeclList(i->getParams()));
        }
        ic->setOpaque(i->getOpaque());
        ic->setEndLocation(i->getEndLocation());

        copyChildren(i->getChildren(), ic->getChildren());

        m_sc = fin(i, ic);
    }

private:

    /**
     * Returns the copy of ``src`` held by ``scope``, matched by the index the
     * original recorded when it was registered.
     */
    ast::IConstraintStmtField *aliasField(
        ast::IConstraintSymbolScope *scope,
        ast::IConstraintStmtField   *src) {
        if (!src) {
            return 0;
        }
        int32_t idx = src->getIndex();
        if (idx < 0 || idx >= (int32_t)scope->getChildren().size()) {
            DEBUG_ERROR("constraint iteration variable index %d out of range", idx);
            return 0;
        }
        return dynamic_cast<ast::IConstraintStmtField *>(
            scope->getChildren().at(idx).get());
    }

    ast::IFactory                   *m_factory;
    dmgr::IDebug                    *m_dbg;

    ast::IConstraintStmt            *m_constraint;
    ast::IDataType                  *m_dt;
    ast::IExpr                      *m_expr;
    ast::ITemplateParamValue        *m_param_val;
    ast::IScopeChild                *m_sc;

};

}
