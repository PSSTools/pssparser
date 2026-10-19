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

    // The standard library itself uses constructs the builder does not yet
    // represent (`default` constraints in addr_reg_pkg, for one).  Those are
    // real gaps, but they are not the user's source and the user cannot act
    // on them, so PSSP101 is suppressed for the duration of the load.
    bool report_unrepresented = ast_builder->getReportUnrepresented();
    ast_builder->setReportUnrepresented(false);

    // One build of the files back to back, so that each file has its own band
    // of lines in fileid 0 (see CoreLibrarySource). Built one at a time, every
    // file started at line 1 and the locations of different files collided.
    std::string text;
    for (const CoreLibrarySource *f=pss_stdlib_files; f->name; f++) {
        text += f->text;
    }
    std::stringstream s(text);
    ast_builder->build(global, &s);

    ast_builder->setReportUnrepresented(report_unrepresented);

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

const CoreLibrarySource *TaskLoadStandardLibrary::sources() {
    return pss_stdlib_files;
}

dmgr::IDebug *TaskLoadStandardLibrary::m_dbg = 0;

}
