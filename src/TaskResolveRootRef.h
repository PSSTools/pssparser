/**
 * TaskResolveRootRef.h
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
#include "NameLookup.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The unqualified-name entry points, over NameLookup. Kept so that callers
 * need not change; the procedure itself, and what each of these means, is
 * documented there.
 */
class TaskResolveRootRef {
public:
    using SuperStatus = NameLookup::SuperStatus;
    using SuperResult = NameLookup::SuperResult;

    TaskResolveRootRef(ResolveContext *ctxt) : m_lookup(ctxt) { }

    virtual ~TaskResolveRootRef() { }

    ast::ISymbolRefPath *resolve(const ast::IExprId *id) {
        return m_lookup.lookupFirst(id);
    }

    ast::ISymbolRefPath *resolveSuper(
        const ast::IExprId          *id,
        SuperResult                 &res) {
        return m_lookup.lookupSuper(id, res);
    }

    ast::ISymbolTypeScope *contextType() {
        return m_lookup.contextType();
    }

    static bool isOrderSensitive(const ast::ISymbolScope *s) {
        return NameLookup::isOrderSensitive(s);
    }

    static const ast::Location &declLocation(const ast::IScopeChild *c) {
        return NameLookup::declLocation(c);
    }

    static bool declaredAfter(
        const ast::IScopeChild      *decl,
        const ast::Location         &use) {
        return NameLookup::declaredAfter(decl, use);
    }

private:
    NameLookup                      m_lookup;
};

}
