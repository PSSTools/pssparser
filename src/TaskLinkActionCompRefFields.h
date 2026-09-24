/**
 * TaskLinkActionCompRefFields.h
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
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {




class TaskLinkActionCompRefFields : public ast::VisitorBase {
public:
    TaskLinkActionCompRefFields(IFactory *factory);

    virtual ~TaskLinkActionCompRefFields();

    void link(ast::ISymbolScope *root);

    /**
     * Link the actions inside `scope`, using `it` -- which is already
     * positioned at `scope` -- to build the paths. A specialization is
     * reached through an ElemKind_TypeSpec step that only the resolver's own
     * iterator knows; an iterator rooted at the specialization would build
     * paths relative to it (B C2). Takes ownership of `it`.
     */
    void link(ISymbolTableIterator *it, ast::ISymbolTypeScope *scope);

    virtual void visitAction(ast::IAction *i) override;

    virtual void visitConstraintBlock(ast::IConstraintBlock *i) override { }

    virtual void visitComponent(ast::IComponent *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;


    
private:
    /**
     * Target a state's built-in `prev` (TaskBuildSymbolTree::addBuiltinFields)
     * at the state itself. `m_symtab` must be positioned at `ts`.
     */
    void linkPrev(ast::ISymbolTypeScope *ts);

private:
    static dmgr::IDebug             *m_dbg;
    IFactory                        *m_factory;
    ISymbolTableIteratorUP          m_symtab;

};

}
