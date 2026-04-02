/*
 * TaskResolveBase.cpp
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
#include <stdarg.h>
#include "TaskResolveBase.h"


namespace pssp {



TaskResolveBase::TaskResolveBase(ResolveContext *ctxt) : m_ctxt(ctxt) {

}

TaskResolveBase::~TaskResolveBase() {

}

    /*
void TaskResolveBase::visitSymbolScope(ast::ISymbolScope *i) {
    m_ctxt->symtab()->pushScope(i);
    for (std::vector<ast::IScopeChild *>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    m_ctxt->symtab()->popScope();
}
     */

void TaskResolveBase::addMarker(
        MarkerSeverityE         severity,
        const ast::Location     &loc,
        const char              *fmt, ...) {
    va_list ap;
    
    va_start(ap, fmt);
    m_ctxt->addMarker(severity, loc, fmt, ap);
    va_end(ap);
}

}
