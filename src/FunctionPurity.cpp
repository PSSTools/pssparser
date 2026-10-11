/*
 * FunctionPurity.cpp
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
#include <vector>
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/ISymbolChild.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/impl/NodeKind.h"
#include "FunctionPurity.h"
#include "TaskCheckCallArgs.h"

namespace pssp {

namespace {

// Whether `target` is declared directly in a `pure component`, which declares
// all of its functions pure (§20.3 / known-issues P5-X3).
bool inPureComponent(ast::IScopeChild *target) {
    ast::ISymbolChild *sc = NodeKind::cast<ast::ISymbolChild>(target);

    if (!sc) {
        return false;
    }

    // One level, not the whole chain. `pure component` says every function *of
    // the component* is pure; it says nothing about a function of an action
    // declared inside it, which is a type of its own.
    ast::ISymbolTypeScope *ts = NodeKind::cast<ast::ISymbolTypeScope>(sc->getUpper());

    if (!ts) {
        return false;
    }

    ast::IComponent *comp = NodeKind::cast<ast::IComponent>(ts->getTarget());

    // Deliberately the *enclosing* type rather than the one the call was
    // written against. A function inherited from a pure component is pure
    // because of where it is declared, so a plain `component D : PC` does not
    // make D's own functions pure -- and a function added by
    // `extend component PC` is pure, because applying the extension re-homes it
    // into PC (see known-issues P2-A5b).
    return comp && comp->getIs_pure();
}

}

FunctionPurity functionPurity(ast::IScopeChild *target) {
    std::vector<ast::IFunctionPrototype *> protos;
    // Every declaration, not one per signature: a definition may leave out
    // the `pure` its prototype says (§20.2.6 b).
    TaskCheckCallArgs::collectPrototypes(target, protos, false);

    if (protos.empty()) {
        return FunctionPurity::NoSignature;
    }

    for (ast::IFunctionPrototype *p : protos) {
        if (p->getIs_pure()) {
            return FunctionPurity::Pure;
        }
    }

    return inPureComponent(target) ? FunctionPurity::Pure : FunctionPurity::NotPure;
}

}
