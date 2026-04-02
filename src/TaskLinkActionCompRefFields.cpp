/*
 * TaskLinkActionCompRefFields.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskLinkActionCompRefFields.h"


namespace pssp {



TaskLinkActionCompRefFields::TaskLinkActionCompRefFields(
    IFactory *factory) : m_factory(factory) {
    DEBUG_INIT("TaskLinkActionCompRefFields", factory->getDebugMgr());
}

TaskLinkActionCompRefFields::~TaskLinkActionCompRefFields() {

}

void TaskLinkActionCompRefFields::link(ast::ISymbolScope *root) {
    m_symtab = ISymbolTableIteratorUP(m_factory->mkAstSymbolTableIterator(root));
    root->accept(m_this);
}

void TaskLinkActionCompRefFields::visitAction(ast::IAction *i) {
    DEBUG_ENTER("visitAction %s", i->getName()->getId().c_str());

    if (!i->getIs_abstract()) {
        ast::ISymbolScope *comp_s = m_symtab->getScope(1);
        ast::IFieldCompRef *comp_f = dynamic_cast<ast::IFieldCompRef *>(
            i->getChildren().at(0).get());
        ast::ITypeIdentifier *comp_tid = m_factory->getAstFactory()->mkTypeIdentifier();
        comp_tid->getElems().push_back(ast::ITypeIdentifierElemUP(
            m_factory->getAstFactory()->mkTypeIdentifierElem(
                m_factory->getAstFactory()->mkExprId(comp_s->getName(), false), 0
            )
        ));
        ast::IDataTypeUserDefined *type = m_factory->getAstFactory()->mkDataTypeUserDefined(
            false,
            comp_tid);

        comp_f->setType(type);
        // Create a reference path to locate the type again
        type->getType_id()->setTarget(m_symtab->getScopeSymbolPath(1));
        DEBUG("Parent scope: %s", comp_s->getName().c_str());
    }

    DEBUG_LEAVE("visitAction %s", i->getName()->getId().c_str());
}

void TaskLinkActionCompRefFields::visitComponent(ast::IComponent *i) {
    DEBUG_ENTER("visitComponent %s", i->getName()->getId().c_str());

    DEBUG_LEAVE("visitComponent %s", i->getName()->getId().c_str());
}

void TaskLinkActionCompRefFields::visitExtendType(ast::IExtendType *i) {
    DEBUG_ENTER("visitExtendType");
    if (i->getTarget() && i->getTarget()->getTarget()) {
        ast::IScopeChild *ext_target = m_symtab->resolveAbsPath(
            i->getTarget()->getTarget());
        ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(ext_target);
        if (target_s) {
            m_symtab->pushScope(target_s);
            VisitorBase::visitExtendType(i);
            m_symtab->popScope();
        }
    }
    DEBUG_LEAVE("visitExtendType");
}

void TaskLinkActionCompRefFields::visitPackageScope(ast::IPackageScope *i) {
    DEBUG_ENTER("visitPackageScope");
    DEBUG_LEAVE("visitPackageScope");
}

void TaskLinkActionCompRefFields::visitRootSymbolScope(ast::IRootSymbolScope *i) {
    DEBUG_ENTER("visitRootSymbolScope");
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("visitRootSymbolScope");
}

void TaskLinkActionCompRefFields::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
    m_symtab->pushScope(i);

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }

    m_symtab->popScope();
    DEBUG_LEAVE("visitSymbolScope %s", i->getName().c_str());
}

void TaskLinkActionCompRefFields::visitSymbolExtendScope(ast::ISymbolExtendScope *i) {
    DEBUG_ENTER("visitSymbolExtendScope");
    ast::IExtendType *ext = dynamic_cast<ast::IExtendType *>(i->getTarget());
    if (ext && ext->getTarget() && ext->getTarget()->getTarget()) {
        ast::IScopeChild *ext_target = m_symtab->resolveAbsPath(ext->getTarget()->getTarget());
        ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(ext_target);
        if (target_s) {
            m_symtab->pushScope(target_s);
            for (std::vector<ast::IScopeChildUP>::const_iterator
                it=i->getChildren().begin();
                it!=i->getChildren().end(); it++) {
                (*it)->accept(m_this);
            }
            m_symtab->popScope();
        }
    }
    DEBUG_LEAVE("visitSymbolExtendScope");
}

void TaskLinkActionCompRefFields::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    DEBUG_ENTER("visitSymbolTypeScope %s", i->getName().c_str());
    m_symtab->pushScope(i);
    i->getTarget()->accept(m_this);

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }

    m_symtab->popScope();
    DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
}

dmgr::IDebug *TaskLinkActionCompRefFields::m_dbg = 0;

}
