/*
 * CoreLibraryLookup.cpp
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
#include <cstdint>
#include <unordered_map>
#include "CoreLibraryLookup.h"

namespace pssp {

std::string findCoreLibraryPackage(
    ast::ISymbolScope       *root,
    const std::string       &name) {
    // PSS 3.1 clause 21: the core library is exactly these four packages.
    // Listed in the order the clause introduces them, so that a name declared
    // in more than one (none are, today) reports the most likely intent.
    static const char *core_pkgs[] = {
        "std_pkg", "executor_pkg", "addr_reg_pkg", "sync_pkg", 0
    };

    if (!root) {
        return "";
    }

    for (uint32_t i=0; core_pkgs[i]; i++) {
        std::unordered_map<std::string,int32_t>::const_iterator p_it =
            root->getSymtab().find(core_pkgs[i]);

        if (p_it == root->getSymtab().end() ||
            p_it->second < 0 ||
            p_it->second >= (int32_t)root->getChildren().size()) {
            continue;
        }

        // The package's own symbol scope. A user package of the same name
        // merges into this one, which is fine: the suggestion is still to
        // import that package.
        ast::ISymbolScope *pkg_s = dynamic_cast<ast::ISymbolScope *>(
            root->getChildren().at(p_it->second).get());

        if (pkg_s && pkg_s->getSymtab().find(name) != pkg_s->getSymtab().end()) {
            return core_pkgs[i];
        }
    }

    return "";
}

}
