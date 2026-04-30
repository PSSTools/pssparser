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

    virtual void visitExecScope(ast::IExecScope *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitField(ast::IField *i) override;

    virtual void visitFieldCompRef(ast::IFieldCompRef *i) override;

    virtual void visitFunctionPrototype(ast::IFunctionPrototype *i) override;

    virtual void visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) override;

//    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

//    virtual void visitSymbolExecScope(ast::ISymbolExecScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

//    virtual void visitSymbolStmtScope(ast::ISymbolStmtScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;
    
    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

    virtual void visitStruct(ast::IStruct *i) override;

    virtual void visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) override;

    virtual void visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) override;

protected:
    ast::IScopeChild *resolvePath(ast::ISymbolRefPath *path);

    bool isGenericConstraintParam(const std::string &name) const;

private:
    static dmgr::IDebug                 *m_dbg;
    std::set<std::string>               m_generic_constraint_params;

};

}
