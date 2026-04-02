/**
 * TaskResolveBase.h
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
#pragma once
#include "dmgr/IDebugMgr.h"
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "ResolveContext.h"

namespace pssp {




class TaskResolveBase : public virtual ast::VisitorBase {
public:
    TaskResolveBase(ResolveContext *ctxt);

    virtual ~TaskResolveBase();

//    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    void addMarker(
        MarkerSeverityE         severity,
        const ast::Location     &loc,
        const char              *fmt, 
        ...);

protected:
    ResolveContext          *m_ctxt;

};

}
