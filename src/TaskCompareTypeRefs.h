/**
 * TaskCompareTypeRefs.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IFactory.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "TaskCompareVal.h"

namespace pssp {




class TaskCompareTypeRefs : public virtual ast::VisitorBase {
public:
    TaskCompareTypeRefs(
        IFactory                *factory,
        ast::ISymbolScope       *root);

    virtual ~TaskCompareTypeRefs();

    bool equal(
        ast::IDataType          *tref1,
        ast::IDataType          *tref2);

    virtual void visitExprRefPath(ast::IExprRefPath *i) override;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;

    virtual void visitExprRefPathStatic(ast::IExprRefPathStatic *i) override;

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) override;

    virtual void visitDataTypeRef(ast::IDataTypeRef *i) override;

    virtual void visitDataTypeString(ast::IDataTypeString *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;


private:
    static dmgr::IDebug             *m_dbg;
    ast::ISymbolScope               *m_root;
    TaskEvalExpr                    m_expr_eval;
    TaskCompareVal                  m_comp_val;
    ast::IDataTypeInt               *m_type_int;
    ast::IDataTypeString            *m_type_str;

};

}
