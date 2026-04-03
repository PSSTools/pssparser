/**
 * TaskFindElementByLocation.h
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
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/ITaskFindElementByLocation.h"

namespace pssp {


/**
 * @brief Locates information about the element at the specified location
 * 
 * 
 */
class TaskFindElementByLocation : 
    public virtual ITaskFindElementByLocation,
    public virtual ast::VisitorBase {
public:
    /**
     * @brief Construct a new Task Find Element By Location object
     * 
     * @param dmgr 
     */
    TaskFindElementByLocation(dmgr::IDebugMgr *dmgr);

    virtual ~TaskFindElementByLocation();

    /**
     * @brief asdf
     * 
     * @param path 
     * @param root 
     * @param lineno 
     * @param linepos 
     * @return true 
     * @return false 
     */
    virtual ITaskFindElementByLocation::Result find(
        ast::ISymbolScope                   *root,
        ast::IGlobalScope                   *file,
        int32_t                             lineno,
        int32_t                             linepos,
        int32_t                             fuzz=0) override;

    virtual void visitExprId(ast::IExprId *i) override;

    virtual void visitField(ast::IField *i) override;

//    virtual void visitExprRefPathContext *i) 

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;

private:
    struct CtxtElem {
        ast::IExpr          *expr;
        ast::IScopeChild    *child;
    };

private:
    bool hit(int32_t lineno, int32_t start, int32_t end);

private:
    static dmgr::IDebug                     *m_dbg;
    dmgr::IDebugMgr                         *m_dmgr;
    ast::ISymbolScope                       *m_root;
    ast::IGlobalScope                       *m_file;
    int32_t                                 m_lineno;
    int32_t                                 m_linepos;
    int32_t                                 m_fuzz;
    std::vector<CtxtElem>                   m_ctxt_s;
    Result                                  m_result;

};

}
