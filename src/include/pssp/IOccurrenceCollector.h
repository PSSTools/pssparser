/**
 * IOccurrenceCollector.h
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
#include <memory>
#include <vector>
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/IScopeChild.h"

namespace pssp {

/**
 * How an identifier occurrence was bound. A closed set: a client that meets a
 * value it does not know should fail rather than guess (pss-scrambler
 * FR-001-Q1). Python mirrors it as pssparser.refs.Resolution.
 */
enum class OccurrenceResolution {
    User,           ///< Bound to a declaration in a user file (fileid >= 1)
    Library,        ///< Bound to a standard-library declaration (fileid 0)
    Builtin,        ///< A built-in: no source declaration (`comp`, `this`, collection methods)
    Unresolved,     ///< Not bound
    Dependent       ///< Not bound, inside a generic template body; depends on a parameter
};

/**
 * One identifier as written in a user file.
 */
struct Occurrence {
    ast::IExprId            *id;        ///< The identifier (location and text)
    ast::IScopeChild        *decl;      ///< Canonical declaration, or null
    ast::IExprId            *decl_name; ///< The declaration's own name, or null
    ast::IScopeChild        *base_decl; ///< Declaration this one overrides or shadows, or null
    bool                    is_decl;    ///< This occurrence is the declaration's name
    OccurrenceResolution    resolution;
};

class IOccurrenceCollector;
using IOccurrenceCollectorUP=std::unique_ptr<IOccurrenceCollector>;

/**
 * Collects every identifier occurrence in the user units of a linked tree,
 * with the declaration each one names. Units with fileid < 1 (the standard
 * library, built-ins) are searched for declarations but not reported.
 * Occurrences are unique by location and sorted by (fileid, line, col).
 */
class IOccurrenceCollector {
public:
    virtual ~IOccurrenceCollector() { }

    virtual void collect(
        ast::IRootSymbolScope       *root,
        std::vector<Occurrence>     &out) = 0;

};

} /* namespace pssp */
