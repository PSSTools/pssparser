/*
 * TaskLoadStandardLibrary.cpp
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
#include <sstream>
#include "dmgr/impl/DebugMacros.h"
#include "AssocDataTypeScopeSizeof.h"
#include "TaskLoadStandardLibrary.h"
#include "pss_stdlib.h"


namespace pssp {



TaskLoadStandardLibrary::TaskLoadStandardLibrary(dmgr::IDebugMgr *dmgr) {
    DEBUG_INIT("pssp::TaskLoadStandardLibrray", dmgr);

}

TaskLoadStandardLibrary::~TaskLoadStandardLibrary() {

}

void TaskLoadStandardLibrary::load(
    IAstBuilder         *ast_builder,
    ast::IGlobalScope   *global) {
    DEBUG_ENTER("load");

    for (uint32_t i=0; pss_stdlib[i]; i++) {
        std::stringstream s(pss_stdlib[i]);

        ast_builder->build(global, &s);
    }

    // Perform post-load fixup
    global->accept(m_this);

    DEBUG_LEAVE("load");
}

void TaskLoadStandardLibrary::visitComponent(ast::IComponent *i) {
    DEBUG_ENTER("visitComponent %s", i->getName()->getId().c_str());
    VisitorBase::visitComponent(i);
    DEBUG_LEAVE("visitComponent %s", i->getName()->getId().c_str());
}

void TaskLoadStandardLibrary::visitStruct(ast::IStruct *i) {
    DEBUG_ENTER("visitStruct %s", i->getName()->getId().c_str());
    const std::string &name = i->getName()->getId();

    if (name == "sizeof_s") {
        DEBUG("Setting associated-data for SizeofS");
        i->setAssocData(new AssocDataTypeScopeSizeof());
    }

    DEBUG_LEAVE("visitStruct %s", i->getName()->getId().c_str());
}

dmgr::IDebug *TaskLoadStandardLibrary::m_dbg = 0;

}
