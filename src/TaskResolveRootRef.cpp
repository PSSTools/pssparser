/*
 * TaskResolveRootRef.cpp
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
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/impl/TaskGetSymbolRefPathKind.h"
#include "TaskResolveRootRef.h"
#include "TaskResolveEnumRef.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"


namespace pssp {



TaskResolveRootRef::TaskResolveRootRef(
    ResolveContext      *ctxt,
    bool                search_imp) : TaskResolveBase(ctxt), m_search_imp(search_imp) {
    DEBUG_INIT("TaskResolveRootRef", ctxt->getDebugMgr());
}

TaskResolveRootRef::~TaskResolveRootRef() {

}

ast::ISymbolRefPath *TaskResolveRootRef::resolve(const ast::IExprId *id) {
    DEBUG_ENTER("resolve %s", id->getId().c_str());
    m_ref = 0;

    // Push a clone of the active symbol table, since we
    // will be traversing it
    m_ctxt->pushCloneSymtab();
    m_id    = id;

    int32_t count = 0;
    while (!m_ref && m_ctxt->symtab()->hasScopes()) {
        DEBUG_ENTER("processing scope %s", m_ctxt->symtab()->getScope()->getName().c_str());
        m_ctxt->symtab()->getScope()->accept(m_this);
        DEBUG_LEAVE("processing scope %s", m_ctxt->symtab()->getScope()->getName().c_str());

        if (!m_ref) {
            m_ctxt->symtab()->popScope();
        }
    }
    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve %p (%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);

    return m_ref;
}

void TaskResolveRootRef::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    DEBUG_ENTER("visitProceduralStmtRepeat");
    visitSymbolScope(i);
    DEBUG_LEAVE("visitProceduralStmtRepeat");
}

void TaskResolveRootRef::visitRootSymbolScope(ast::IRootSymbolScope *i) {
    DEBUG_ENTER("visitRootSymbolScope %s %d %p", i->getName().c_str(), i->getSymtab().size(), i);
    visitSymbolScope(i);
    DEBUG_LEAVE("visitRootSymbolScope %s %d %p", i->getName().c_str(), i->getSymtab().size(), i);
}

void TaskResolveRootRef::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope id=%s (%s) %d (%p)", 
        m_id->getId().c_str(), i->getName().c_str(),
        i->getSymtab().size(),
        i);
    std::unordered_map<std::string,int32_t>::const_iterator it = i->getSymtab().find(m_id->getId());

    DEBUG("imports: %p", i->getImports());
    if (it != i->getSymtab().end()) {
        DEBUG("Found symbol %s @ index %d", m_id->getId().c_str(), it->second);
        ast::IScopeChild *c = i->getChildren().at(it->second).get();

        if (dynamic_cast<ast::ISymbolTypeScope *>(c)) {
            DEBUG("Is a type scope");
            if (dynamic_cast<ast::ISymbolTypeScope *>(c)->getPlist()) {
                DEBUG("Is parameterized");
            }
        }
        m_ref = m_ctxt->symtab()->getScopeSymbolPath(); // Path to 'i'

        // Now, add in the child element that we just found
        m_ref->getPath().push_back({
            TaskGetSymbolRefPathKind(m_ctxt->getDebugMgr()).get(c),
            it->second});
    // If we're inside a typed context, and the type is Enum,
    // then search that enum
    } else if ((m_ref=TaskResolveEnumRef(m_ctxt).resolve(m_id))) {
        // Found in this scope
        DEBUG("Found symbol as an enumerator");
    } else if (m_search_imp && i->getImports() && (m_ref=searchImports(m_id, i->getImports()))) {
        // Found in imports
        DEBUG("Found symbol via imports");
    } else {
        DEBUG("Failed to find symbol");
    }

    DEBUG_LEAVE("visitSymbolScope m_ref=%p (sz=%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);
}

//void TaskResolveRootRef::visitSymbolExecScope(ast::ISymbolExecScope *i) {
//    DEBUG_ENTER("visitSymbolExecScope");
//    visitSymbolScope(i);
//    DEBUG_LEAVE("visitSymbolExecScope");
//}

void TaskResolveRootRef::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    DEBUG_ENTER("visitSymbolTypeScope id=%s (%s)", 
        m_id->getId().c_str(), i->getName().c_str());
    visitSymbolScope(i); // Look in primary declaration scope

    DEBUG("TypeScope: m_ref=%p plist=%p", m_ref, i->getPlist());
    if (!m_ref && i->getPlist()) {
        std::unordered_map<std::string,int32_t>::const_iterator it;

        if (DEBUG_EN) {
        for (std::unordered_map<std::string,int32_t>::const_iterator
            it=i->getPlist()->getSymtab().begin();
            it!=i->getPlist()->getSymtab().end(); it++) {
            DEBUG("Sym: %s", it->first.c_str());
        }
        }

        if ((it=i->getPlist()->getSymtab().find(m_id->getId())) != i->getPlist()->getSymtab().end()) {
            // Target is a parameter value
            m_ref = m_ctxt->symtab()->getScopeSymbolPath();
            DEBUG("Found %s as a parameter (%d)", 
                m_id->getId().c_str(), it->second);

            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ParamIdx, 
                it->second
            });

            DEBUG("Full path:");
            for (uint32_t i=0; i<m_ref->getPath().size(); i++) {
                DEBUG("  [%d] %d %d", i, m_ref->getPath().at(i).kind, m_ref->getPath().at(i).idx);
            }
        }
    }

    if (!m_ref) {
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
        if (ts && ts->getSuper_t() && ts->getSuper_t()->getTarget()) {
            DEBUG("Searching super-type chain for %s", m_id->getId().c_str());
            ast::IScopeChild *super_sc = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(), m_ctxt->root()
            ).resolve(ts->getSuper_t()->getTarget());
            if (super_sc) {
                super_sc->accept(m_this);
            }
        }
    }

    DEBUG_LEAVE("visitSymbolTypeScope %p", m_ref);
}

void TaskResolveRootRef::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
    DEBUG_ENTER("visitSymbolFunctionScope %s (searching for %s)", i->getName().c_str(), m_id->getId().c_str());

    std::unordered_map<std::string,int32_t>::const_iterator it = i->getPlist()->getSymtab().find(m_id->getId());

    if (it != i->getPlist()->getSymtab().end()) {
        ast::IScopeChild *c = i->getPlist()->getChildren().at(it->second).get();
        DEBUG("Found as a function parameter @ %d", it->second);
        m_ref = m_ctxt->symtab()->getScopeSymbolPath(); // Path to 'i'
        m_ref->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ArgIdx,
            it->second});
    } else {
        DEBUG("Delegate to SymbolScope");
        visitSymbolScope(i);
    }

    DEBUG_LEAVE("visitSymbolFunctionScope");
}

ast::ISymbolRefPath *TaskResolveRootRef::searchImports(
    const ast::IExprId          *id,
    ast::ISymbolImportSpec      *imp) {
    DEBUG_ENTER("searchImports - %d statements", imp->getImports().size());
    ast::ISymbolRefPath *ret = 0;
	for (std::vector<ast::IPackageImportStmt *>::const_iterator
		imp_it=imp->getImports().begin();
		imp_it!=imp->getImports().end(); imp_it++) {
        ast::ISymbolRefPath *ret_t = 0;
		if ((ret_t=searchImport(id, *imp_it))) {
			// Found it.
			if (ret) {
				// Uh-oh. We have ambiguity...
                m_ctxt->addErrorMarker(
                    id->getLocation(),
				    "Ambiguous symbol resolution when looking up %s",
                    id->getId().c_str());
				delete ret_t;
				break;
			} else {
				ret = ret_t;
			}
		}
    }

    DEBUG_LEAVE("searchImports %p", ret);
    return ret;
}

ast::ISymbolRefPath *TaskResolveRootRef::searchImport(
        const ast::IExprId          *id,
        ast::IPackageImportStmt     *imp) {
	DEBUG_ENTER("searchImport sym=%s", id->getId().c_str());
    ast::ISymbolRefPath *ret = 0;

	// ast::ISymbolRefPath *ret = 0;
	if (!imp->getPath()->getTarget()) {
		DEBUG("Skipping, due to unset import target");
		return 0;
	}
	for (uint32_t i=0; i<imp->getPath()->getTarget()->getPath().size(); i++) {
		DEBUG("Imp Path[%d] %d", i, imp->getPath()->getTarget()->getPath().at(i));
	}
	ast::IScopeChild *target_c = m_ctxt->symtab()->resolveAbsPath(imp->getPath()->getTarget());
	ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(target_c);
	DEBUG("target_c: %p ; target_s: %p", target_c, target_s);

	if (target_s) {
		DEBUG("Have a symbol scope (%s)", target_s->getName().c_str());
		std::unordered_map<std::string, int32_t>::const_iterator it;
		it = target_s->getSymtab().find(id->getId());

		if (it != target_s->getSymtab().end()) {
			DEBUG("Found the symbol (%s)", id->getId().c_str());
			ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
			ret->getPath().insert(
				ret->getPath().begin(),
				imp->getPath()->getTarget()->getPath().begin(),
				imp->getPath()->getTarget()->getPath().end());
			ret->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second
            });
		} else {
            ret = TaskResolveEnumRef(m_ctxt, target_s).resolve(id);
        }
	}

	DEBUG_LEAVE("searchImport %s %p", id->getId().c_str(), ret);
	return ret;
}

dmgr::IDebug *TaskResolveRootRef::m_dbg = 0;

}
