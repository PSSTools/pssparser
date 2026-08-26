/**
 * TaskGetSubscriptSymbolScope.h
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "TaskResolveSymbolPathRef.h"
#include "pssp/impl/TaskGetElemSymbolScope.h"
#include "pssp/impl/BuiltinCollectionUtil.h"

namespace pssp {


/**
 * The scope a subscripted reference denotes: `arr[0]` on an `array<my_s,4>`
 * is an `my_s`, so member lookup continues there rather than on the array.
 *
 * Two things this has to get right, and neither was:
 *
 * - **How many levels to unwrap.** One subscript peels one collection. The
 *   walk used to recurse for as long as the element type was itself a
 *   collection, regardless of how many subscripts were written, so
 *   `arr[0].zork` on an `array<array<my_s,2>,4>` resolved -- reaching a member
 *   of the *inner* element from a reference that only names the outer one.
 *   `n_subscript` is now honoured.
 * - **Which collections.** Only `array<>` was recognized, so `l[0].zork` on a
 *   `list<my_s>` failed to find `zork` at all. `list<>` yields its element
 *   type and `map<>` its *value* type -- the second parameter, not the first.
 *   `set<>` is not subscriptable and yields nothing.
 *
 * The collection is identified from the *declaration*, not from the scope
 * name: `i->getName()` is `array<>` for every specialization of every generic
 * called `array`, including a user's own. See BuiltinCollectionUtil.
 */
class TaskGetSubscriptSymbolScope : public virtual TaskGetElemSymbolScope {
public:

    TaskGetSubscriptSymbolScope(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root,
        uint32_t                n_subscript=1,
        const std::string       &logid="pssp::TaskGetSubscriptSymbolScope") : 
        TaskGetElemSymbolScope(dmgr, root, logid), m_n_subscript(n_subscript) {
    }

    virtual ~TaskGetSubscriptSymbolScope() { }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope \"%s\" (%d subscript(s) left)",
            i->getName().c_str(), m_n_subscript);

        ast::ITypeScope *type = dynamic_cast<ast::ITypeScope *>(i->getTarget());

        // Which collection this is -- decided from the declaration, not from
        // the scope's name. A specialization is named `array<>` whatever it
        // came from, and a user type may be named `array` in their own
        // package; see BuiltinCollectionUtil.
        int32_t param_idx = (m_n_subscript > 0)
            ?collectionElemParam(builtinCollectionKind(type)):-1;

        if (param_idx >= 0 && type && type->getParams() &&
            param_idx < (int32_t)type->getParams()->getParams().size()) {
            m_n_subscript--;
            type->getParams()->getParams().at(param_idx)->accept(m_this);
        } else {
            // Either every subscript has been accounted for, or this is not a
            // collection. Stopping here is what makes a reference with too few
            // subscripts fail to find its member, rather than silently
            // reaching through a dimension that was never written.
            m_ret = i;
        }
        DEBUG_LEAVE("visitSymbolTypeScope");
    }


protected:
    uint32_t                m_n_subscript;

};

}
