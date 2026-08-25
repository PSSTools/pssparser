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
            DEBUG_ERROR("Error: copy(constraint) failed");
        }
        DEBUG_LEAVE("copy(IConstraintStmt)");
        return m_constraint;
    }

    ast::ITemplateParamValue *copy(ast::ITemplateParamValue *i) {
        DEBUG_ENTER("copy(ITemplateParamValue)");
        m_param_val = 0;
        i->accept(m_this);

        if (!m_param_val) {
            DEBUG_ERROR("copy(paramvalue) failed");
        }
        DEBUG_LEAVE("copy(ITemplateParamValue)");
        return m_param_val;
    }

    template <class T> T *copyT(ast::IConstraintStmt *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("Error: copyT(constraint) failed");
        }
        return ret;
    }

    ast::IScopeChild *copy(ast::IScopeChild *i) {
        DEBUG_ENTER("copy(IScopeChild)");
        m_sc = 0;
        i->accept(m_this);
        if (!m_sc) {
            DEBUG_ERROR("Error: copy(ScopeChild) failed");
        }
        DEBUG_LEAVE("copy(IScopeChild)");
        return m_sc;
    };

    template <class T> T *copyT(ast::IScopeChild *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("Error: copyT(ScopeChild) failed");
        }
        return ret;
    }

    ast::IExpr *copy(ast::IExpr *i) {
        DEBUG_ENTER("copy(IExpr)");
        m_expr = 0;
        i->accept(m_this);
        if (!m_expr) {
            DEBUG_ERROR("Error: copy(Expr) failed");
        }
        DEBUG_LEAVE("copy(IExpr)");
        return m_expr;
    };

    template <class T> T *copyT(ast::IExpr *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("Error: copyT(Expr) failed");
        }
        return ret;
    }

    ast::IDataType *copy(ast::IDataType *i) {
        DEBUG_ENTER("copy(IDataType)");
        m_dt = 0;
        i->accept(m_this);
        if (!m_dt) {
            DEBUG_ERROR("Error: copy(DataType) failed");
        }
        DEBUG_LEAVE("copy(IDataType)");
        return m_dt;
    }

    template <class T> T *copyT(ast::IDataType *i) {
        T *ret = dynamic_cast<T *>(copy(i));
        if (!ret) {
            DEBUG_ERROR("Error: copyT(Expr) failed");
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

    virtual void visitActivityJoinSpec(ast::IActivityJoinSpec *i) { }
    
    virtual void visitSymbolImportSpec(ast::ISymbolImportSpec *i) { }
    
    virtual void visitScopeChild(ast::IScopeChild *i) { }
    
    virtual void visitSymbolRefPath(ast::ISymbolRefPath *i) { }
    
    virtual void visitRefExpr(ast::IRefExpr *i) { }
    
    virtual void visitActivitySelectBranch(ast::IActivitySelectBranch *i) { }
    
    virtual void visitTemplateParamDeclList(ast::ITemplateParamDeclList *i) { }
    
    virtual void visitActivityMatchChoice(ast::IActivityMatchChoice *i) { }
    
    virtual void visitTemplateParamValueList(ast::ITemplateParamValueList *i) { }
    
    virtual void visitTemplateParamValue(ast::ITemplateParamValue *i) { }
    
    virtual void visitConstraintStmt(ast::IConstraintStmt *i) { }

    virtual void visitExprRefPathElem(ast::IExprRefPathElem *i) { 
        DEBUG_ENTER("visitExprRefPathElem");
        DEBUG("TODO: visitExprRefPathElem");
        DEBUG_LEAVE("visitExprRefPathElem");
    }
    
    virtual void visitExprStaticRefPath(ast::IExprStaticRefPath *i) {
        DEBUG_ENTER("visitExprStaticRefPath");
        ast::IExprStaticRefPath *ic = m_factory->mkExprStaticRefPath(
            i->getIs_global(),
            copyT<ast::IExprMemberPathElem>(i->getLeaf())
        );
        m_expr = ic;
        DEBUG_LEAVE("visitExprStaticRefPath");
    }
    
    virtual void visitExprString(ast::IExprString *i) { 
        m_expr = m_factory->mkExprString(i->getValue(), i->getIs_raw());
    }
    
    virtual void visitExprSubscript(ast::IExprSubscript *i) { }
    
    virtual void visitExprUnary(ast::IExprUnary *i) { }
    
    virtual void visitScope(ast::IScope *i) { }
    
    virtual void visitMethodParameterList(ast::IMethodParameterList *i) { }
    
    virtual void visitScopeChildRef(ast::IScopeChildRef *i) { }
    
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
    
    virtual void visitNamedScopeChild(ast::INamedScopeChild *i) { }
    
    virtual void visitFunctionDefinition(ast::IFunctionDefinition *i) { }
    
    virtual void visitPackageImportStmt(ast::IPackageImportStmt *i) { }
    
    virtual void visitFunctionParamDecl(ast::IFunctionParamDecl *i) override {
        ast::IFunctionParamDecl *ic = m_factory->mkFunctionParamDecl(
            i->getKind(),
            copyT<ast::IExprId>(i->getName()),
            copy(i->getType()),
            i->getDir(),
            (i->getDflt())?copy(i->getDflt()):0
        );
        ic->setIs_varargs(i->getIs_varargs());
        ic->setDocstring(i->getDocstring());
        m_sc = ic;
    }
    
    virtual void visitFunctionImport(ast::IFunctionImport *i) { }
    
    virtual void visitDataType(ast::IDataType *i) { }
    
    virtual void visitExtendEnum(ast::IExtendEnum *i) { }
    
    virtual void visitSymbolScope(ast::ISymbolScope *i) { }
    
    virtual void visitRefExprTypeScopeGlobal(ast::IRefExprTypeScopeGlobal *i) { }
    
    virtual void visitRefExprTypeScopeContext(ast::IRefExprTypeScopeContext *i) { }
    
    virtual void visitRefExprScopeIndex(ast::IRefExprScopeIndex *i) { }
    
    virtual void visitTemplateParamDecl(ast::ITemplateParamDecl *i) { }
    
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
    
    virtual void visitActivityStmt(ast::IActivityStmt *i) { }
    
    virtual void visitActivitySchedulingConstraint(ast::IActivitySchedulingConstraint *i) { }
    
    virtual void visitActivityJoinSpecBranch(ast::IActivityJoinSpecBranch *i) { }
    
    virtual void visitActivityJoinSpecSelect(ast::IActivityJoinSpecSelect *i) { }
    
    virtual void visitActivityJoinSpecNone(ast::IActivityJoinSpecNone *i) { }
    
    virtual void visitActivityJoinSpecFirst(ast::IActivityJoinSpecFirst *i) { }
    
    virtual void visitExecStmt(ast::IExecStmt *i) { }
    
    /**
     * 20.5.3/20.5.4 -- a target exec block.
     *
     * This used to be an empty stub, so specializing a parameterized type
     * silently dropped the target code entirely. That was already a defect
     * (P3-X3's class); it became a worse one when the block stopped being a
     * leaf and started carrying a scanned template.
     */
    virtual void visitExecTargetTemplateBlock(ast::IExecTargetTemplateBlock *i) override {
        DEBUG_ENTER("visitExecTargetTemplateBlock");
        ast::IExecTargetTemplateBlock *ic = m_factory->mkExecTargetTemplateBlock(
            i->getKind(),
            i->getData());
        ic->setLanguage(i->getLanguage());
        ic->setFilename(i->getFilename());
        ic->setTemplate(copyTemplate(i->getTemplate()));
        ic->setFilename_template(copyTemplate(i->getFilename_template()));
        if (i->getTag()) {
            ic->setTag(copyT<ast::IExecBlockTag>(i->getTag()));
        }
        ic->setDocstring(i->getDocstring());
        ic->setLocation(i->getLocation());
        m_sc = ic;
        DEBUG_LEAVE("visitExecTargetTemplateBlock");
    }

    /**
     * 4.7.1 -- deep-copy a scanned template, or return 0 if there is none.
     *
     * Written as a plain recursive walk rather than through the visitor: the
     * element types form a small closed set, and threading them through
     * m_sc/copy() would need a visitor override per type for no benefit.
     *
     * Template-local declarations are *not* copied here. They live on the
     * scope node's `children`, which the symbol tree owns; a specialized copy
     * is re-linked from scratch, so re-registering them is the linker's job,
     * not this one's.
     */
    ast::ITemplateString *copyTemplate(ast::ITemplateString *i) {
        if (!i) {
            return 0;
        }
        ast::ITemplateString *ic = m_factory->mkTemplateString(
            i->getName(), i->getRaw());
        ic->setIs_const(i->getIs_const());
        ic->setLocation(i->getLocation());
        for (std::vector<ast::ITemplateElemUP>::const_iterator
            it=i->getElems().begin(); it!=i->getElems().end(); it++) {
            ast::ITemplateElem *e = copyTemplateElem(it->get());
            if (e) {
                e->setIndex((int32_t)ic->getElems().size());
                ic->getElems().push_back(ast::ITemplateElemUP(e));
            }
        }
        return ic;
    }

    ast::ITemplateElem *copyTemplateElem(ast::ITemplateElem *i) {
        ast::ITemplateElem *ret = 0;

        if (ast::ITemplateText *t = dynamic_cast<ast::ITemplateText *>(i)) {
            ret = m_factory->mkTemplateText(
                t->getName(), t->getOffset(), t->getExtent(), t->getText());
        } else if (ast::ITemplateExpr *t = dynamic_cast<ast::ITemplateExpr *>(i)) {
            ret = m_factory->mkTemplateExpr(
                t->getName(), t->getOffset(), t->getExtent(),
                t->getExpr() ? copy(t->getExpr()) : 0);
        } else if (ast::ITemplateComment *t = dynamic_cast<ast::ITemplateComment *>(i)) {
            ast::ITemplateComment *c = m_factory->mkTemplateComment(
                t->getName(), t->getOffset(), t->getExtent(), t->getText());
            c->setIs_line(t->getIs_line());
            ret = c;
        } else if (ast::ITemplateIf *t = dynamic_cast<ast::ITemplateIf *>(i)) {
            ast::ITemplateIf *n = m_factory->mkTemplateIf(
                t->getName(), t->getOffset(), t->getExtent());
            for (std::vector<ast::ITemplateIfClauseUP>::const_iterator
                it=t->getClauses().begin(); it!=t->getClauses().end(); it++) {
                ast::ITemplateIfClause *c = m_factory->mkTemplateIfClause(
                    (*it)->getName(), (*it)->getOffset(), (*it)->getExtent());
                if ((*it)->getCond()) {
                    c->setCond(copy((*it)->getCond()));
                }
                copyTemplateBody(it->get(), c);
                c->setIs_own_line((*it)->getIs_own_line());
                c->setLocation((*it)->getLocation());
                c->setIndex((int32_t)n->getClauses().size());
                n->getClauses().push_back(ast::ITemplateIfClauseUP(c));
            }
            ret = n;
        } else if (ast::ITemplateForeach *t = dynamic_cast<ast::ITemplateForeach *>(i)) {
            ast::ITemplateForeach *n = m_factory->mkTemplateForeach(
                t->getName(), t->getOffset(), t->getExtent(),
                t->getExpr() ? copy(t->getExpr()) : 0);
            if (t->getIt()) {
                n->setIt(copyT<ast::IExprId>(t->getIt()));
            }
            if (t->getIdx()) {
                n->setIdx(copyT<ast::IExprId>(t->getIdx()));
            }
            copyTemplateBody(t, n);
            ret = n;
        } else if (ast::ITemplateRepeat *t = dynamic_cast<ast::ITemplateRepeat *>(i)) {
            ast::ITemplateRepeat *n = m_factory->mkTemplateRepeat(
                t->getName(), t->getOffset(), t->getExtent(),
                t->getExpr() ? copy(t->getExpr()) : 0);
            if (t->getIdx()) {
                n->setIdx(copyT<ast::IExprId>(t->getIdx()));
            }
            copyTemplateBody(t, n);
            ret = n;
        } else if (ast::ITemplateVarDecl *t = dynamic_cast<ast::ITemplateVarDecl *>(i)) {
            ast::ITemplateVarDecl *n = m_factory->mkTemplateVarDecl(
                t->getName(), t->getOffset(), t->getExtent());
            for (std::vector<ast::IProceduralStmtDataDeclarationUP>::const_iterator
                it=t->getDecls().begin(); it!=t->getDecls().end(); it++) {
                n->getDecls().push_back(ast::IProceduralStmtDataDeclarationUP(
                    copyT<ast::IProceduralStmtDataDeclaration>(it->get()), false));
            }
            ret = n;
        } else if (ast::ITemplateAssign *t = dynamic_cast<ast::ITemplateAssign *>(i)) {
            ret = m_factory->mkTemplateAssign(
                t->getName(), t->getOffset(), t->getExtent(),
                copyT<ast::IExprId>(t->getLhs()),
                t->getRhs() ? copy(t->getRhs()) : 0);
        } else {
            DEBUG_ERROR("Error: unhandled template element in copy");
            return 0;
        }

        ret->setIs_own_line(i->getIs_own_line());
        ret->setLocation(i->getLocation());
        return ret;
    }

    void copyTemplateBody(ast::ITemplateBlock *src, ast::ITemplateBlock *dst) {
        for (std::vector<ast::ITemplateElemUP>::const_iterator
            it=src->getBody().begin(); it!=src->getBody().end(); it++) {
            ast::ITemplateElem *e = copyTemplateElem(it->get());
            if (e) {
                e->setIndex((int32_t)dst->getBody().size());
                dst->getBody().push_back(ast::ITemplateElemUP(e));
            }
        }
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
    
    virtual void visitExprDomainOpenRangeList(ast::IExprDomainOpenRangeList *i) { }
    
    virtual void visitExprDomainOpenRangeValue(ast::IExprDomainOpenRangeValue *i) { }
    
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
        m_expr = m_factory->mkExprId(
            i->getId(),
            i->getIs_escaped()
        );
    }
    
    virtual void visitExprIn(ast::IExprIn *i) { }
    
    virtual void visitExprMemberPathElem(ast::IExprMemberPathElem *i) { 
        ast::IMethodParameterList *plist = 0;

        if (i->getParams()) {
            plist = m_factory->mkMethodParameterList();
            for (std::vector<ast::IExprUP>::const_iterator
                it=i->getParams()->getParameters().begin();
                it!=i->getParams()->getParameters().end(); it++) {
                plist->getParameters().push_back(ast::IExprUP(copy(it->get())));
            }
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
    
//    virtual void visitExprAggregateLiteral(ast::IExprAggregateLiteral *i) { }
    
    virtual void visitExprOpenRangeList(ast::IExprOpenRangeList *i) { }
    
    virtual void visitExprOpenRangeValue(ast::IExprOpenRangeValue *i) { }
    
    virtual void visitExprRefPath(ast::IExprRefPath *i) { 
        DEBUG_ENTER("visitExprRefPath");
        DEBUG("TODO: visitExprRefPath");
        DEBUG_LEAVE("visitExprRefPath");
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
    
    virtual void visitConstraintScope(ast::IConstraintScope *i) {
        // Was a no-op, which silently emptied every nested constraint block on
        // a template specialization -- visitConstraintStmtIf already delegates
        // here for both of its branches.
        ast::IConstraintScope *ic = m_factory->mkConstraintScope();
        copyConstraints(i, ic);
        m_constraint = ic;
    }

    virtual void visitConstraintStmtSoft(ast::IConstraintStmtSoft *i) override {
        m_constraint = m_factory->mkConstraintStmtSoft(copy(i->getExpr()));
    }

    virtual void visitConstraintStmtDist(ast::IConstraintStmtDist *i) override {
        ast::IConstraintStmtDist *ic = m_factory->mkConstraintStmtDist(
            copy(i->getLhs()));
        for (std::vector<ast::IDistItemUP>::const_iterator
            it=i->getItems().begin();
            it!=i->getItems().end(); it++) {
            ic->getItems().push_back(ast::IDistItemUP(
                copyT<ast::IDistItem>(it->get())));
        }
        m_constraint = ic;
    }

    virtual void visitDistItem(ast::IDistItem *i) override {
        m_sc = m_factory->mkDistItem(
            copyT<ast::IExprOpenRangeValue>(i->getRange()),
            (i->getWeight())?copyT<ast::IDistWeight>(i->getWeight()):0);
    }

    virtual void visitDistWeight(ast::IDistWeight *i) override {
        m_sc = m_factory->mkDistWeight(
            i->getIs_dividing(),
            copy(i->getExpr()));
    }

    virtual void visitExprSliceRange(ast::IExprSliceRange *i) override {
        ast::IExprSliceRange *ic = m_factory->mkExprSliceRange();
        if (i->getLower()) { ic->setLower(copy(i->getLower())); }
        if (i->getUpper()) { ic->setUpper(copy(i->getUpper())); }
        m_expr = ic;
    }

    virtual void visitExprFloatLiteral(ast::IExprFloatLiteral *i) override {
        m_expr = m_factory->mkExprFloatLiteral(
            i->getValue(),
            i->getImage(),
            i->getIs_scientific());
    }

    virtual void visitDataTypeFloat(ast::IDataTypeFloat *i) override {
        m_dt = m_factory->mkDataTypeFloat(i->getIs_float64());
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
    
    virtual void visitConstraintStmtExpr(ast::IConstraintStmtExpr *i) { 
        m_constraint = m_factory->mkConstraintStmtExpr(
            copy(i->getExpr())
        );
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
    
    virtual void visitConstraintStmtField(ast::IConstraintStmtField *i) override {
        ast::IConstraintStmtField *ic = m_factory->mkConstraintStmtField(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copy(i->getType()):0
        );
        ic->setIndex(i->getIndex());
        ic->setLocation(i->getLocation());
        // Reached both as a constraint (forall's constraints[0]) and as a plain
        // scope child (a foreach iterator, which lives only in the symbol scope),
        // so both results have to be set.
        m_constraint = ic;
        m_sc = ic;
    }

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) { 
        DEBUG_ENTER("visitExprRefPathStaticRooted");
        ast::IExprRefPathStaticRooted *ic = m_factory->mkExprRefPathStaticRooted(
            copyT<ast::IExprRefPathStatic>(i->getRoot()),
            (i->getLeaf())?copyT<ast::IExprHierarchicalId>(i->getLeaf()):0
        );
        m_expr = ic;
        DEBUG_LEAVE("visitExprRefPathStaticRooted");
    }
    
    virtual void visitConstraintStmtIf(ast::IConstraintStmtIf *i) { 
        m_constraint = m_factory->mkConstraintStmtIf(
            copy(i->getCond()),
            copyT<ast::IConstraintScope>(i->getTrue_c()),
            (i->getFalse_c())?copyT<ast::IConstraintScope>(i->getFalse_c()):0
        );
    }
    
    virtual void visitConstraintStmtUnique(ast::IConstraintStmtUnique *i) {
        ast::IConstraintStmtUnique *ic = m_factory->mkConstraintStmtUnique();
        ic->setIs_braced(i->getIs_braced());
        for (std::vector<ast::IExprHierarchicalIdUP>::const_iterator
            it=i->getList().begin();
            it!=i->getList().end(); it++) {
            ic->getList().push_back(ast::IExprHierarchicalIdUP(
                copyT<ast::IExprHierarchicalId>(it->get())));
        }
        m_constraint = ic;
    }
    
    virtual void visitConstraintStmtDefault(ast::IConstraintStmtDefault *i) { }
    
    virtual void visitConstraintStmtDefaultDisable(ast::IConstraintStmtDefaultDisable *i) { }
    
    virtual void visitPackageScope(ast::IPackageScope *i) { }
    
    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override {
        DEBUG_ENTER("visitFunctionPrototype %s", i->getName()->getId().c_str());
        ast::IFunctionPrototype *ic = m_factory->mkFunctionPrototype(
            copyT<ast::IExprId>(i->getName()),
            (i->getRtype())?copy(i->getRtype()):0,
            i->getIs_target(),
            i->getIs_solve());
        ic->setIs_pure(i->getIs_pure());
        for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getParameters().begin();
            it!=i->getParameters().end(); it++) {
            ic->getParameters().push_back(
                ast::IFunctionParamDeclUP(copyT<ast::IFunctionParamDecl>(it->get())));
        }

        ic->setDocstring(i->getDocstring());
        m_sc = ic;
        DEBUG_ENTER("visitFunctionPrototype");
    }
    
    virtual void visitTargetTemplateFunction(ast::ITargetTemplateFunction *i) override {
        DEBUG_ENTER("visitTargetTemplateFunction %s", i->getProto()->getName()->getId().c_str());
        ast::ITargetTemplateFunction *ic = m_factory->mkTargetTemplateFunction(
            copyT<ast::IFunctionPrototype>(i->getProto()),
            i->getLanguage(),
            i->getData());
        ic->setIs_static(i->getIs_static());
        ic->setDocstring(i->getDocstring());
        m_sc = ic;
        DEBUG_LEAVE("visitTargetTemplateFunction");
    }

    virtual void visitFunctionImportType(ast::IFunctionImportType *i) {
        DEBUG_ENTER("visitFunctionImportType");
        DEBUG("TODO: visitFunctionImportType");
        DEBUG_LEAVE("visitFunctionImportType");
    }
    
    virtual void visitFunctionImportProto(ast::IFunctionImportProto *i) { 
        DEBUG_ENTER("visitFunctionImportProto");
        DEBUG("TODO: visitFunctionImportProto");
        DEBUG_LEAVE("visitFunctionImportProto");
    }
    
    virtual void visitDataTypeBool(ast::IDataTypeBool *i) { 
        m_dt = m_factory->mkDataTypeBool();
    }
    
    virtual void visitDataTypeChandle(ast::IDataTypeChandle *i) { 
        m_dt = m_factory->mkDataTypeChandle();
    }
    
    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) { 

    }
    
    virtual void visitEnumItem(ast::IEnumItem *i) { 

    }
    
    virtual void visitEnumDecl(ast::IEnumDecl *i) { }
    
    virtual void visitDataTypeInt(ast::IDataTypeInt *i) { 
        m_dt = m_factory->mkDataTypeInt(
            i->getIs_signed(),
            (i->getWidth())?copy(i->getWidth()):0,
            (i->getIn_range())?copyT<ast::IExprDomainOpenRangeList>(i->getIn_range()):0
        );
    }
    
    virtual void visitDataTypeRef(ast::IDataTypeRef *i) override {
        m_dt = m_factory->mkDataTypeRef(
            copyT<ast::IDataTypeUserDefined>(i->getType()));
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

        m_dt = ci;
    }
    
    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) { 
        m_dt = m_factory->mkDataTypeUserDefined(
            i->getIs_global(),
            copyT<ast::ITypeIdentifier>(i->getType_id())
        );
    }
    
    virtual void visitExtendType(ast::IExtendType *i) { }
    
    virtual void visitField(ast::IField *i) { 
        m_sc = m_factory->mkField(
            copyT<ast::IExprId>(i->getName()),
            copy(i->getType()),
            i->getAttr(),
            (i->getInit())?copy(i->getInit()):0
        );
    }
    
    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override {
        // Every action carries one of these -- the implicit `comp` handle --
        // so leaving it uncopied dropped a null into the specialization's
        // child list, which TaskBuildSymbolTree then walked into.
        m_sc = m_factory->mkFieldCompRef(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0
        );
        m_sc->setIndex(i->getIndex());
        m_sc->setLocation(i->getLocation());
    }

    virtual void visitFieldRef(ast::IFieldRef *i) override {
        m_sc = m_factory->mkFieldRef(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0,
            i->getIs_input()
        );
        m_sc->setIndex(i->getIndex());
        m_sc->setLocation(i->getLocation());
    }

    virtual void visitFieldClaim(ast::IFieldClaim *i) override {
        m_sc = m_factory->mkFieldClaim(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0,
            i->getIs_lock()
        );
        m_sc->setIndex(i->getIndex());
        m_sc->setLocation(i->getLocation());
    }

    virtual void visitFieldPool(ast::IFieldPool *i) override {
        m_sc = m_factory->mkFieldPool(
            copyT<ast::IExprId>(i->getName()),
            (i->getType())?copyT<ast::IDataTypeUserDefined>(i->getType()):0,
            (i->getSize())?copy(i->getSize()):0
        );
        m_sc->setIndex(i->getIndex());
        m_sc->setLocation(i->getLocation());
    }
    
    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) { }
    
    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) { }
    
    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) { 
        DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
        DEBUG("TODO: visitSymbolTypeScope %s", i->getName().c_str());
        DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
    }
    
    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) { 
        DEBUG_ENTER("visitSymbolFunctionScope %s", i->getName().c_str());
        DEBUG("TODO: visitSymbolFunctionScope %s", i->getName().c_str());
        DEBUG_LEAVE("visitSymbolFunctionScope %s", i->getName().c_str());
    }
    
    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) { }
    
    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) { }
    
    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) { }
    
    virtual void visitActivityDecl(ast::IActivityDecl *i) { }
    
    virtual void visitActivityBindStmt(ast::IActivityBindStmt *i) { }
    
    virtual void visitActivityConstraint(ast::IActivityConstraint *i) { }
    
    virtual void visitActivityLabeledStmt(ast::IActivityLabeledStmt *i) { }
    
    virtual void visitActivityLabeledScope(ast::IActivityLabeledScope *i) { }
    
    virtual void visitExecScope(ast::IExecScope *i) { }
    
    virtual void visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) { }
    
    virtual void visitProceduralStmtExpr(ast::IProceduralStmtExpr *i) { }
    
    virtual void visitProceduralStmtFunctionCall(ast::IProceduralStmtFunctionCall *i) { }
    
    virtual void visitProceduralStmtReturn(ast::IProceduralStmtReturn *i) { }
    
    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) { }
    
    virtual void visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) { }
    
    virtual void visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) { }
    
    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) { }
    
    virtual void visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) { }
    
    virtual void visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) { }
    
    virtual void visitProceduralStmtMatchChoice(ast::IProceduralStmtMatchChoice *i) { }
    
    virtual void visitProceduralStmtBreak(ast::IProceduralStmtBreak *i) { }
    
    virtual void visitProceduralStmtContinue(ast::IProceduralStmtContinue *i) { }
    
    virtual void visitProceduralStmtDataDeclaration(ast::IProceduralStmtDataDeclaration *i) { }
    
    virtual void visitConstraintBlock(ast::IConstraintBlock *i) { 
        ast::IConstraintBlock *ic = m_factory->mkConstraintBlock(
            i->getName(),
            i->getIs_dynamic());
        copyConstraints(i, ic);
        m_sc = ic;
    }
    
    virtual void visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) override {
        DEBUG_ENTER("visitConstraintStmtForeach");
        ast::IConstraintStmtForeach *ic = m_factory->mkConstraintStmtForeach(
            copy(i->getExpr()));
        ic->setIndex(i->getIndex());
        ic->setLocation(i->getLocation());
        copyConstraints(i, ic);

        // it/idx are non-owning aliases into the foreach's own symbol scope
        // (AstBuilderInt::visitForeach_constraint_item). Copy the scope, then
        // re-point them at the copies by position -- the scope may also hold a
        // null placeholder where no index variable was written, so matching by
        // position rather than by name is what keeps the two lined up.
        ic->setSymtab(copyConstraintSymtab(i->getSymtab(), i, ic));
        ic->setIt(symtabAlias(i, ic, i->getIt()));
        ic->setIdx(symtabAlias(i, ic, i->getIdx()));

        m_constraint = ic;
        DEBUG_LEAVE("visitConstraintStmtForeach");
    }

    virtual void visitExprRefPathStaticFunc(ast::IExprRefPathStaticFunc *i) { 
        DEBUG_ENTER("visitExprRefPathStaticFunc");
        DEBUG("TODO: visitExprRefPathStaticFunc");
        DEBUG_LEAVE("visitExprRefPathStaticFunc");
    }
    
    virtual void visitConstraintStmtForall(ast::IConstraintStmtForall *i) override {
        DEBUG_ENTER("visitConstraintStmtForall");
        ast::IConstraintStmtForall *ic = m_factory->mkConstraintStmtForall(
            copyT<ast::IExprId>(i->getIterator_id()),
            copyT<ast::IDataTypeUserDefined>(i->getType_id()),
            (i->getRef_path())?copyT<ast::IExprRefPath>(i->getRef_path()):0);
        ic->setIndex(i->getIndex());
        ic->setLocation(i->getLocation());

        // The quantified iterator is constraints[0] here, owned by the
        // constraint list and merely referenced from the symbol scope, so the
        // constraints must be copied before the scope that aliases them.
        copyConstraints(i, ic);
        ic->setSymtab(copyConstraintSymtab(i->getSymtab(), i, ic));

        m_constraint = ic;
        DEBUG_LEAVE("visitConstraintStmtForall");
    }

    virtual void visitExprRefPathSuper(ast::IExprRefPathSuper *i) { 
        DEBUG_ENTER("visitExprRefPathSuper");
        DEBUG("TODO: visitExprRefPathSuper");
        DEBUG_LEAVE("visitExprRefPathSuper");
    }
    
    virtual void visitConstraintStmtImplication(ast::IConstraintStmtImplication *i) override {
        ast::IConstraintStmtImplication *ic = m_factory->mkConstraintStmtImplication(
            copy(i->getCond()));
        ic->setIndex(i->getIndex());
        ic->setLocation(i->getLocation());
        copyConstraints(i, ic);
        m_constraint = ic;
    }

    virtual void visitTypeScope(ast::ITypeScope *i) { }
    
    virtual void visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) { }
    
    virtual void visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) { }
    
    virtual void visitActivitySequence(ast::IActivitySequence *i) { }
    
    virtual void visitActivityParallel(ast::IActivityParallel *i) { }
    
    virtual void visitActivitySchedule(ast::IActivitySchedule *i) { }
    
    virtual void visitActivityRepeatCount(ast::IActivityRepeatCount *i) { }
    
    virtual void visitActivityRepeatWhile(ast::IActivityRepeatWhile *i) { }
    
    virtual void visitActivityForeach(ast::IActivityForeach *i) { }
    
    virtual void visitActivitySelect(ast::IActivitySelect *i) { }
    
    virtual void visitActivityIfElse(ast::IActivityIfElse *i) { }
    
    virtual void visitActivityMatch(ast::IActivityMatch *i) { }
    
    virtual void visitActivityReplicate(ast::IActivityReplicate *i) { }
    
    virtual void visitActivitySuper(ast::IActivitySuper *i) { }
    
    virtual void visitExecBlock(ast::IExecBlock *i) { }
    
    virtual void visitStruct(ast::IStruct *i) {
        ast::IStruct *ic = m_factory->mkStruct(
            copyT<ast::IExprId>(i->getName()),
            (i->getSuper_t())?copyT<ast::ITypeIdentifier>(i->getSuper_t()):0,
            i->getKind()
        );

        if (i->getParams()) {

        }

        copyChildren(i, ic);

        if (i->getAssocData()) {
            ic->setAssocData(i->getAssocData(), false);
        }

        ic->setDocstring(i->getDocstring());
        m_sc = ic;
    }

    virtual void visitAction(ast::IAction *i) {
        ast::IAction *ic = m_factory->mkAction(
            copyT<ast::IExprId>(i->getName()),
            (i->getSuper_t())?copyT<ast::ITypeIdentifier>(i->getSuper_t()):0,
            i->getIs_abstract()
        );

        copyChildren(i, ic);

        ic->setDocstring(i->getDocstring());
        m_sc = ic;
    }

    virtual void visitComponent(ast::IComponent *i) {
        ast::IComponent *ic = m_factory->mkComponent(
            copyT<ast::IExprId>(i->getName()),
            (i->getSuper_t())?copyT<ast::ITypeIdentifier>(i->getSuper_t()):0
        );

        copyChildren(i, ic);

        if (i->getAssocData()) {
            ic->setAssocData(i->getAssocData(), false);
        }

        ic->setDocstring(i->getDocstring());
        m_sc = ic;
    }




private:

    /**
     * Copy the children of a type scope into its copy.
     *
     * A child whose kind still has no visitor here comes back null. Pushing
     * that null was how an unimplemented visitor turned into a segfault rather
     * than a diagnosable gap: TaskBuildSymbolTree runs over the copy straight
     * afterwards and dereferences every child. Dropping it instead leaves the
     * specialization incomplete, which is the honest consequence, and copy()
     * has already reported which kind was missing.
     */
    void copyChildren(
        ast::IScope                 *src,
        ast::IScope                 *dst) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=src->getChildren().begin();
            it!=src->getChildren().end(); it++) {
            if (!it->get()) {
                continue;
            }
            ast::IScopeChild *c = copy(it->get());
            if (!c) {
                continue;
            }
            // Set here rather than in each visitor, for the same reason as in
            // copyConstraints -- and it is load-bearing beyond ordering:
            // `index` is how TaskGetItemIndex addresses a child, so a copied
            // constraint block with the default -1 cannot be named by a symbol
            // path at all, and every reference recorded beneath it pointed
            // somewhere else.
            c->setIndex((*it)->getIndex());
            c->setLocation((*it)->getLocation());
            dst->getChildren().push_back(ast::IScopeChildUP(c));
        }
    }

    /**
     * Copy the constraint statements of a constraint scope into its copy,
     * preserving position -- both the soft-constraint priority rule and the
     * symbol scopes built by foreach/forall address constraints by index.
     */
    void copyConstraints(
        ast::IConstraintScope       *src,
        ast::IConstraintScope       *dst) {
        for (std::vector<ast::IConstraintStmtUP>::const_iterator
            it=src->getConstraints().begin();
            it!=src->getConstraints().end(); it++) {
            ast::IConstraintStmt *c = copy(it->get());
            if (!c) {
                // copy() has already reported. Dropping the statement loses a
                // restriction, which is bad, but pushing the null is worse:
                // every later walk of this list dereferences it unguarded.
                continue;
            }
            // Set here rather than in each visitor so that every constraint
            // list -- block, scope, foreach, forall, implication -- carries it.
            c->setIndex((*it)->getIndex());
            c->setLocation((*it)->getLocation());
            dst->getConstraints().push_back(ast::IConstraintStmtUP(c));
        }
    }

    /**
     * Copy the ConstraintSymbolScope that a foreach/forall hangs its iteration
     * variables from.
     *
     * A child of that scope is either an alias of one of the constraint scope's
     * own statements (forall's iterator, which is constraints[0]) or a node the
     * scope is the sole holder of (a foreach iterator, which nothing else
     * owns). The two cases differ only in ownership, so they are told apart the
     * way the builder created them: by looking for the child in the source
     * constraint list. Null placeholders are preserved as null.
     */
    ast::IConstraintSymbolScope *copyConstraintSymtab(
        ast::IConstraintSymbolScope *src,
        ast::IConstraintScope       *src_c,
        ast::IConstraintScope       *dst_c) {
        if (!src) {
            return 0;
        }
        ast::IConstraintSymbolScope *ret = m_factory->mkConstraintSymbolScope(
            src->getName());
        ret->setConstraint(dst_c);
        ret->getSymtab() = src->getSymtab();

        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=src->getChildren().begin();
            it!=src->getChildren().end(); it++) {
            ast::IScopeChild *c = 0;
            bool own = true;

            if (it->get()) {
                int32_t idx = constraintIndexOf(src_c, it->get());
                if (idx >= 0 && idx < dst_c->getConstraints().size()) {
                    c = dst_c->getConstraints().at(idx).get();
                    own = false;
                } else {
                    c = copy(it->get());
                }
            }

            ret->getChildren().push_back(ast::IScopeChildUP(c, own));
        }

        return ret;
    }

    /**
     * Position of `c` in `src`'s constraint list, or -1 if it is not one of them.
     */
    int32_t constraintIndexOf(
        ast::IConstraintScope       *src,
        ast::IScopeChild            *c) {
        for (int32_t i=0; i<src->getConstraints().size(); i++) {
            if (static_cast<ast::IScopeChild *>(
                src->getConstraints().at(i).get()) == c) {
                return i;
            }
        }
        return -1;
    }

    /**
     * Given a node held by `src`'s symbol scope, return the corresponding node
     * in `dst`'s -- matched by position, since a foreach scope may hold
     * same-named or null entries.
     */
    ast::IConstraintStmtField *symtabAlias(
        ast::IConstraintStmtForeach *src,
        ast::IConstraintStmtForeach *dst,
        ast::IConstraintStmtField   *c) {
        if (!c || !src->getSymtab() || !dst->getSymtab()) {
            return 0;
        }
        const std::vector<ast::IScopeChildUP> &children = src->getSymtab()->getChildren();
        for (int32_t i=0; i<children.size(); i++) {
            if (children.at(i).get() == static_cast<ast::IScopeChild *>(c)) {
                return dynamic_cast<ast::IConstraintStmtField *>(
                    dst->getSymtab()->getChildren().at(i).get());
            }
        }
        return 0;
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
