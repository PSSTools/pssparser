/*
 * IRule.h
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
 * One loaded rule (pss-rules-format.md §3). Only rules that loaded without
 * errors exist: a bad rule is reported and left out (format §6.3).
 */
#pragma once
#include <string>

namespace pssp {
namespace lint {

class IRule {
public:
    virtual ~IRule() { }

    virtual const std::string &id() const = 0;

    virtual const std::string &name() const = 0;

    virtual const std::string &tier() const = 0;

    /** Empty when the rule names none (allowed for site rules). */
    virtual const std::string &family() const = 0;

    /** Computed at load from the functions the rule calls: "L0"-"L4". */
    virtual const char *level() const = 0;

    /** Computed at load: "file" or "model". */
    virtual const char *scope() const = 0;
};

}
}
