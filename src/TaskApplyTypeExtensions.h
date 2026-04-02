/**
 * TaskApplyTypeExtensions.h
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
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/IFactory.h"
#include "pssp/ast/impl/VisitorBase.h"

namespace pssp {



class TaskApplyTypeExtensions : public ast::VisitorBase {
public:
    TaskApplyTypeExtensions(
        dmgr::IDebugMgr     *dmgr,
        IFactory            *factory,
        IMarkerListener     *marker_l);

    virtual ~TaskApplyTypeExtensions();

    void apply(ast::IRootSymbolScope *root);

    virtual void visitExtendEnum(ast::IExtendEnum *i) override;

    virtual void visitExtendType(ast::IExtendType *i) override;

    virtual void visitRootSymbolScope(ast::IRootSymbolScope *i) override;

    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override;

    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override;

    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitEnumItem(ast::IEnumItem *i) override;

    virtual void visitTypeScope(ast::ITypeScope *i) override;

protected:
    void addChild(
        ast::ISymbolScope       *target,
        ast::IScopeChild        *child,
        const std::string       &name);


private:
    static dmgr::IDebug                     *m_dbg;
    IFactory                                *m_factory;
    IMarkerListener                         *m_marker_l;
    ast::IRootSymbolScope                   *m_root;
    ISymbolTableIteratorUP                  m_symtab_it;
    ast::ISymbolScope                       *m_target_s;

};

}
