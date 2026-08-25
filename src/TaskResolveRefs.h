/**
 * TaskResolveRefs.h
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
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include <set>
#include "ResolveContext.h"
#include "TaskResolveBase.h"

namespace pssp {




class TaskResolveRefs : public TaskResolveBase {
public:
    TaskResolveRefs(ResolveContext      *ctxt);

    virtual ~TaskResolveRefs();

    void resolve(ast::ISymbolScope *root);

    void resolve(ast::ISymbolTypeScope *scope);

    virtual void visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) override;
    
    virtual void visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) override;

    virtual void visitActivityDecl(ast::IActivityDecl *i) override;

    virtual void visitActivitySequence(ast::IActivitySequence *i) override;

    virtual void visitActivityForeach(ast::IActivityForeach *i) override;
    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override;

    virtual void visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) override;

    virtual void visitConstraintStmtForall(ast::IConstraintStmtForall *i) override;

    virtual void visitExecScope(ast::IExecScope *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitField(ast::IField *i) override;

    /** §9.1.6 b) -- `mutable` is not permitted on a component field. */
    void checkMutableField(ast::IField *i);

    /** PSS115 -- `e` is a template string that is not a constant expression. */
    void checkConstTemplate(ast::IExpr *e, const ast::Location &loc);

    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

    virtual void visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) override;

    // 4.7.1 -- template scopes. The generated visitors walk a block's body
    // *after* visitTemplateElem has already pushed and popped the scope, so a
    // foreach iterator would not be visible inside its own block. These push
    // the scope around the body instead.
    virtual void visitTemplateString(ast::ITemplateString *i) override;

    virtual void visitTemplateBlock(ast::ITemplateBlock *i) override;

    virtual void visitTemplateForeach(ast::ITemplateForeach *i) override;

    virtual void visitTemplateRepeat(ast::ITemplateRepeat *i) override;

    virtual void visitTemplateIfClause(ast::ITemplateIfClause *i) override;

    virtual void visitTemplateAssign(ast::ITemplateAssign *i) override;

//    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

//    virtual void visitSymbolExecScope(ast::ISymbolExecScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

//    virtual void visitSymbolStmtScope(ast::ISymbolStmtScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitAnnotation(ast::IAnnotation *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;
    
    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

    virtual void visitExecBlockTag(ast::IExecBlockTag *i) override;

    virtual void visitStruct(ast::IStruct *i) override;

    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) override;

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override;

protected:
    /**
     * Check every annotation that belongs directly to `scope` -- that is, all
     * annotations reachable from its children without crossing into a nested
     * symbol scope, plus any attached to the declaration `scope` wraps.
     *
     * Annotations are not reachable from the ordinary traversal: most of the
     * visitors overridden here (visitField, visitFunctionPrototype, the
     * activity/constraint statements) recurse into the members they care about
     * rather than chaining to visitScopeChild, which is what carries the
     * annotation list. Collecting per symbol scope keeps the symbol-table stack
     * correct for name resolution while reaching them all.
     */
    void checkScopeAnnotations(ast::ISymbolScope *scope);

    ast::IScopeChild *resolvePath(ast::ISymbolRefPath *path);

    bool isGenericConstraintParam(const std::string &name) const;

private:
    static dmgr::IDebug                 *m_dbg;
    std::set<std::string>               m_generic_constraint_params;
    std::set<ast::IAnnotation *>        m_checked_annotations;

    // Same reason as m_checked_annotations: a declaration is reachable both
    // through its symbol scope and through the scope's target, so a node with
    // no dedicated visitor override is resolved twice. That is invisible while
    // resolution succeeds -- `getTarget()` short-circuits the second pass --
    // and shows up only as a duplicated diagnostic when it fails.
    std::set<ast::IExecBlockTag *>      m_checked_exec_tags;

    // Non-zero while resolving inside a triple-quoted template string.
    //
    // PSS114 -- §4.7.1.1's "any function called shall be pure" -- has to be
    // checked where the callee is resolved: for `a.b.f()` that happens deep in
    // the ref-path walk, and only there is the declaration in hand. Rather
    // than duplicate that walk, the call sites ask this counter whether the
    // call they just resolved is inside a template.
    int32_t                             m_template_depth = 0;

};

}
