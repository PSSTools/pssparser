/*
 * FunctionPurity.h
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
#include "pssp/ast/IScopeChild.h"

namespace pssp {

/**
 * Whether a function is pure: the predicate PSS114 checks a template
 * string's calls against (§4.7.1.1), shared with the lint library's
 * `is_pure` (lint-core-plan.md C6.6).
 */
enum class FunctionPurity {
    NoSignature,    ///< `target` offers no function signature
    Pure,           ///< a signature is declared `pure`, or a `pure component` declares it
    NotPure
};

/**
 * The purity of `target`, a linked function (an `ISymbolFunctionScope`, as a
 * call resolves to). A function is pure when *any* of its declarations --
 * prototypes, definition, imports -- says `pure`, or when it is declared
 * directly in a `pure component` (§20.3), which makes every function of the
 * component pure.
 */
FunctionPurity functionPurity(ast::IScopeChild *target);

}
