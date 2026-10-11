/*
 * IRuleSet.h
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
 *
 * The rules loaded from one rule file (pss-rules-format.md): the ones that
 * loaded without errors, in file order.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include "pssp/lint/IRule.h"

namespace pssp {
namespace lint {

class IRuleSet;
using IRuleSetUP=std::unique_ptr<IRuleSet>;
class IRuleSet {
public:
    virtual ~IRuleSet() { }

    /** The source name the rules were loaded from. */
    virtual const std::string &name() const = 0;

    virtual uint32_t numRules() const = 0;

    virtual const IRule *getRule(uint32_t idx) const = 0;

    /** True for a built-in rule file (`LINT` namespace; stricter fields). */
    virtual bool builtin() const = 0;
};

}
}
