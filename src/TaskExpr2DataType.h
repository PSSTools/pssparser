/**
 * TaskExpr2DataType.h
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
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "ResolveContext.h"

namespace pssp {




class TaskExpr2DataType : public ast::VisitorBase {
public:
    TaskExpr2DataType(ResolveContext *ctxt);

    virtual ~TaskExpr2DataType();

    ast::IDataType *expr2dt(ast::IExpr *e);

    virtual void visitExpr(ast::IExpr *i) override;

    virtual void visitExprId(ast::IExprId *i) override;

    virtual void visitExprHierarchicalId(ast::IExprHierarchicalId *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) override;

    virtual void visitExprStaticRefPath(ast::IExprStaticRefPath *i) override;

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

private:
    static dmgr::IDebug             *m_dbg;
    ResolveContext                  *m_ctxt;
    ast::IDataType                  *m_ret;

};

}
