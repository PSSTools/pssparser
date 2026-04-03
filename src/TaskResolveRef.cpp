/*
 * TaskResolveRef.cpp
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
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskBuildParamValList.h"
#include "TaskGetSpecializedTemplateType.h"
#include "TaskSpecializeParameterizedRef.h"
#include "TaskResolveRef.h"
#include "TaskResolveRefs.h"
#include "TaskResolveRootRef.h"
#include "TaskResolveFieldRef.h"
#include "Marker.h"

#include <algorithm>

namespace pssp {


static int editDistance(const std::string &a, const std::string &b) {
    int m = a.size(), n = b.size();
    std::vector<std::vector<int>> dp(m+1, std::vector<int>(n+1, 0));
    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            int cost = (a[i-1] != b[j-1]) ? 1 : 0;
            dp[i][j] = std::min({dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost});
        }
    }
    return dp[m][n];
}

static std::string findCloseMatch(
        const std::string &name,
        ast::ISymbolScope *scope,
        int maxDist = 2) {
    std::string best;
    int bestDist = maxDist + 1;
    if (!scope) return best;
    for (auto &entry : scope->getSymtab()) {
        int d = editDistance(name, entry.first);
        if (d > 0 && d < bestDist) {
            bestDist = d;
            best = entry.first;
        }
    }
    return best;
}



TaskResolveRef::TaskResolveRef(
    ResolveContext                  *ctxt,
    bool                            search_imp) : 
        TaskResolveBase(ctxt), m_search_imp(search_imp) {
    DEBUG_INIT("TaskResolveRef", ctxt->getDebugMgr());
    m_ref = 0;
}

TaskResolveRef::~TaskResolveRef() {

}

ast::ISymbolRefPath *TaskResolveRef::resolve(ast::ITypeIdentifier *type_id) {
    DEBUG_ENTER("resolve");

    // Push a copy of the symbol iterator
    type_id->accept(m_this);

    if (m_ref) {
        DEBUG("Result:");
        for (std::vector<ast::SymbolRefPathElem>::const_iterator
            it=m_ref->getPath().begin();
            it!=m_ref->getPath().end(); it++) {
            DEBUG("  %d %d", it->kind, it->idx);
        }
    } else {
        DEBUG("Failed to resolve");
    }

    DEBUG_LEAVE("resolve %p (%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);
    return m_ref;
}

ast::ISymbolRefPath *TaskResolveRef::resolve(ast::IExpr *ref) {
    DEBUG_ENTER("resolve (RefPath)");
    ref->accept(m_this);
    DEBUG_LEAVE("resolve (RefPath) %p (%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);
    return m_ref;
}

void TaskResolveRef::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    DEBUG_ENTER("visitDataTypeUserDefined");
    if (i->getType_id()->getTarget()) {
        DEBUG("Symbol already resolved");
        DEBUG_LEAVE("visitDataTypeUserDefined");
        return;
    }
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i->getType_id());

    if (target) {
        DEBUG("Success");
        i->getType_id()->setTarget(target);
    } else {
        DEBUG("Failed");
        // char tmp[1024];
        // sprintf(tmp, "failed to find user-defined datatype");
        // IMarkerUP marker(m_factory->mkMarker(
        //     tmp,
        //     MarkerSeverityE::Error,
        //     i->getLocation()
        // ));
        // m_marker_l->marker(marker.get());
    }
    DEBUG_LEAVE("visitDataTypeUserDefined");
}

void TaskResolveRef::visitExprId(ast::IExprId *i) {
    DEBUG_ENTER("visitExprId %s", i->getId().c_str());

    ast::ISymbolRefPath *root = findRoot(i);

    m_ref = root;
    DEBUG_LEAVE("visitExprId %s (%p %d)", i->getId().c_str(), m_ref, (m_ref)?m_ref->getPath().size():-1);
}

void TaskResolveRef::visitExprMemberPathElem(ast::IExprMemberPathElem *i) {
    DEBUG_ENTER("visitExprMemberPathElem");
    DEBUG("TODO: visitExprMemberPathElem");
    DEBUG_LEAVE("visitExprMemberPathElem");
}

void TaskResolveRef::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("visitExprRefPathStaticRooted");
    DEBUG("TODO: visitExprRefPathStaticRooted");
    DEBUG_LEAVE("visitExprRefPathStaticRooted");
}

void TaskResolveRef::visitExprRefPathId(ast::IExprRefPathId *i) {
    DEBUG_ENTER("visitExprRefPathId id=%s", i->getId()->getId().c_str());

	// Find the first element

    ast::ISymbolRefPath *root = findRoot(i->getId());

    m_ref = root;

    DEBUG_LEAVE("visitExprRefPathId");
}

void TaskResolveRef::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext");
    DEBUG("Searching for root element (%s)", 
        i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
    ast::ISymbolRefPath *root = findRoot(i->getHier_id()->getElems().at(0)->getId());
    if (root) {
        if (i->getHier_id()->getElems().size() > 1) {
            DEBUG_ERROR("Handle paths greater than 1 length");
        }
        m_ref = root;
    } else {
        DEBUG_ERROR("Failed to find root element (%s)",
            i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
        return;
    }

    DEBUG_LEAVE("visitExprRefPathContext");
}

void TaskResolveRef::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic");
    DEBUG("TODO: visitExprRefPathStatic");
    DEBUG_LEAVE("visitExprRefPathStatic");
}

void TaskResolveRef::visitSymbolScope(ast::ISymbolScope *i) { 
//    m_ref = 
}

void TaskResolveRef::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {

}

void TaskResolveRef::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) { 

}

void TaskResolveRef::visitTemplateParamTypeValue(ast::ITemplateParamTypeValue *i) {
    DEBUG_ENTER("visitTemplateParamTypeValue");
    i->getValue()->accept(m_this);
    DEBUG_LEAVE("visitTemplateParamTypeValue");
}

void TaskResolveRef::visitTemplateParamExprValue(ast::ITemplateParamExprValue *i) {
    DEBUG_ENTER("visitTemplateParamExprValue");
    DEBUG_LEAVE("visitTemplateParamExprValue");
}

void TaskResolveRef::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier %s", i->getElems().at(0)->getId()->getId().c_str());
	// Find the first element

    ast::ISymbolRefPath *root = findRoot(i->getElems().at(0)->getId());

    if (!root) {
        const std::string &name = i->getElems().at(0)->getId()->getId();
        DEBUG("Note: failed to resolve root symbol %s", name.c_str());
        std::string suggestion = findCloseMatch(
            name, dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()));
        if (suggestion.empty()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getElems().at(0)->getId()->getLocation(),
                "unknown type '%s'",
                name.c_str());
        } else {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getElems().at(0)->getId()->getLocation(),
                "unknown type '%s'; did you mean '%s'?",
                name.c_str(),
                suggestion.c_str());
        }
        return;
    }

    if (i->getElems().at(0)->getParams()) {
        // Resolve parameter refs

        DEBUG_ENTER("resolve parameter references");
        for (std::vector<ast::ITemplateParamValueUP>::const_iterator
            it=i->getElems().at(0)->getParams()->getValues().begin();
            it!=i->getElems().at(0)->getParams()->getValues().end(); it++) {
            (*it)->accept(m_this);
        }
        DEBUG_LEAVE("resolve parameter references");

        ast::ISymbolRefPath *root_s = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                root, 
                i->getElems().at(0)->getParams());

        delete root;
        root = root_s;

        if (!root_s) {
            // Had an error that will be marked by an error marker
            return;
        }
    }

    ast::IScopeChild *root_t = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(root);

    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
        it=i->getElems().begin()+1;
        it!=i->getElems().end(); it++) {
        ast::IScopeChild *next = TaskResolveFieldRef(m_ctxt).resolve(
            (*it)->getId(),
            root_t,
            root);

        if (next) {
            DEBUG("Resolve %s", (*it)->getId()->getId().c_str());
            if ((*it)->getParams()) {
               root = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                        root, 
                        (*it)->getParams());
               root_t = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(root);
            } else {
                root_t = next;
            }

        } else {
            // Assume 
            DEBUG("Note: failed to resolve element %s", (*it)->getId()->getId().c_str());
            delete root;
            root = 0;
            break;
        }
    }

    m_ref = root;
    
    DEBUG_LEAVE("visitTypeIdentifier %p", m_ref);
}

ast::ISymbolRefPath *TaskResolveRef::findRoot(
        const ast::IExprId              *sym) {
    return TaskResolveRootRef(m_ctxt).resolve(sym);
}

ast::ISymbolRefPath *TaskResolveRef::specializeParameterizedRef(
        ast::ISymbolRefPath             *target,
        ast::ITemplateParamValueList    *pvals) {
    DEBUG_ENTER("specializeParameterizedRef");

    // Find the base type
    ast::IScopeChild *target_sc = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target);
    ast::ISymbolTypeScope *target_c = 
        TaskResolveSymbolPathRef(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolveT<ast::ISymbolTypeScope>(target);

    if (!target_c) {
        DEBUG("TODO: Flag error about templated type");
        return 0;
    }

    if (!target_c->getPlist()) {
        DEBUG("TODO: Flag type as not being templated");
        return 0;
    }

    // Form parameter list 
    ast::ITemplateParamDeclList *pdecl_list = TaskBuildParamValList(m_ctxt).build(
            target_c->getPlist(),
            pvals);
    TaskGetSpecializedTemplateType typespec_getter(m_ctxt);

    ast::ISymbolRefPath *target_t = typespec_getter.find(
        target, 
        pdecl_list);

    if (target_t) {
        // The new parameter list that we created is no longer needed
        DEBUG("Specialization already exists");
        delete pdecl_list;
    } else {
        DEBUG("Must create new specialization");
        target_t = typespec_getter.mk(target, pdecl_list);
    }
    

    DEBUG_LEAVE("specializeParameterizedRef %p", target_t);
    return target_t;
}

dmgr::IDebug *TaskResolveRef::m_dbg = 0;

}
