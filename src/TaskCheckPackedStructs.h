/**
 * TaskCheckPackedStructs.h
 *
 * Copyright 2026 Matthew Ballance and Contributors
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
 */
#pragma once
#include <set>
#include <string>
#include <tuple>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/impl/TaskClassifyPackable.h"
#include "ResolveContext.h"

namespace pssp {

/**
 * The member rules of 21.13.1, checked once every reference is bound.
 *
 * - A packed struct's fields must be packable: numeric, bool, an enum with a
 *   base type, a packed struct, or an array of those (PSS012).
 * - A type extension of a packed struct must not add a field (PSS013).
 *
 * What is packable, and what a type's width is, comes from
 * TaskClassifyPackable -- the same answer sizeof_s gives. See
 * docs/design/packed-struct-checks-plan.md.
 *
 * Generic bodies are not checked: a member typed by a template parameter has
 * no type until the generic is specialized. Each specialization is checked
 * instead, and a finding is reported once per source position however many
 * specializations reach it.
 */
class TaskCheckPackedStructs {
public:
    TaskCheckPackedStructs(ResolveContext *ctxt);

    virtual ~TaskCheckPackedStructs();

    void check(ast::IRootSymbolScope *root);

private:
    void walk(ast::ISymbolScope *s);

    void checkTypeScope(ast::ISymbolTypeScope *s);

    void checkMembers(ast::ISymbolTypeScope *s);

    void checkExtensionFields(ast::ISymbolTypeScope *s);

    void report(
        const ast::Location     &loc,
        const std::string       &msg,
        ast::IScopeChild        *related,
        const std::string       &related_label);

    static std::string typeName(ast::ISymbolTypeScope *s);

private:
    static dmgr::IDebug                                 *m_dbg;
    ResolveContext                                      *m_ctxt;
    TaskClassifyPackable                                m_classifier;
    std::set<std::tuple<int32_t,int32_t,int32_t,std::string>> m_reported;
};

}
