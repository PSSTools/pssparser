/*
 * TaskSpecializeParameterizedRef.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "TaskSpecializeParameterizedRef.h"
#include "TaskGetSpecializedTemplateType.h"
#include "TaskBuildParamValList.h"


namespace pssp {



TaskSpecializeParameterizedRef::TaskSpecializeParameterizedRef(ResolveContext *ctxt) :
    m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskSpecializeParameterizedRef", ctxt->getDebugMgr());
}

TaskSpecializeParameterizedRef::~TaskSpecializeParameterizedRef() {

}

ast::ISymbolRefPath *TaskSpecializeParameterizedRef::specialize(
        ast::ISymbolRefPath                 *target,
        ast::ITemplateParamValueList        *pvals) {
    DEBUG_ENTER("specialize");
    // Find the base type
    ast::IScopeChild *target_sc = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), 
        m_ctxt->root()).resolve(target);
    ast::ISymbolTypeScope *target_c = 
        TaskResolveSymbolPathRef(
            m_ctxt->getDebugMgr(), 
            m_ctxt->root()).resolveT<ast::ISymbolTypeScope>(target);

    if (!target_c) {
        DEBUG("TODO: Flag error about templated type");
        return 0;
    }

    if (!target_c->getPlist()) {
        DEBUG_ERROR("Type %s is not templated", target_c->getName().c_str());
        m_ctxt->addErrorMarker(
            ast::Location{-1, -1, -1},
            "Type %s is not templated",
            target_c->getName().c_str());
        return 0;
    }

    DEBUG("target: %s", target_c->getName().c_str());

    // Form parameter list 
    ast::ITemplateParamDeclList *pdecl_list = TaskBuildParamValList(m_ctxt).build(
            target_c->getPlist(),
            pvals);
    TaskGetSpecializedTemplateType typespec_getter(m_ctxt);

    if (!pdecl_list) {
        // Encountered an error while building out the param list
        return 0;
    }

    ast::ISymbolRefPath *target_t = typespec_getter.find(
        target, 
        pdecl_list);

    if (target_t) {
        // The new parameter list that we created is no longer needed
        DEBUG("Specialization already exists");
        delete pdecl_list;
    } else {
        DEBUG("Must create new specialization");
        target_t = typespec_getter.mk(
            target, 
            pdecl_list);
    }
    

    DEBUG_LEAVE("specialize %p", target_t);
    return target_t;
}

dmgr::IDebug *TaskSpecializeParameterizedRef::m_dbg = 0;

}
