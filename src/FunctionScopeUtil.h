/**
 * FunctionScopeUtil.h
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
 * Facts about a SymbolFunctionScope that every place a function gains a
 * contribution needs to agree on. A function is assembled from several
 * declarations -- in one scope (TaskBuildSymbolTree), from an extension
 * (TaskApplyTypeExtensions) and from a type-form import (TaskResolveRefs) --
 * and the rules below used to be spelled out at each of them.
 */
#pragma once
#include <string>
#include "pssp/ast/IField.h"
#include "pssp/ast/IFieldCompRef.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ITargetTemplateFunction.h"

namespace pssp {

/**
 * The ways a function can be implemented. LRM 20.2 allows "only one
 * definition for any function", and 20.4/20.6 make an import and a target
 * template the other two kinds of definition.
 */
enum class FunctionImpl {
    None,
    Native,             // a PSS body
    TargetTemplate,     // `target L function ... = """...""";`
    Import              // `import ... function ...;`, either form
};

inline FunctionImpl functionImplementation(ast::ISymbolFunctionScope *f) {
    if (f->getBody()) {
        return FunctionImpl::Native;
    }
    // Target-template nodes are children of the scope, and an extension merge
    // moves them there too.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=f->getChildren().begin();
        it!=f->getChildren().end(); it++) {
        if (dynamic_cast<ast::ITargetTemplateFunction *>(it->get())) {
            return FunctionImpl::TargetTemplate;
        }
    }
    if (f->getImport_specs().size()) {
        return FunctionImpl::Import;
    }
    return FunctionImpl::None;
}

/**
 * The error for giving `f` an implementation of kind `incoming`, or "" when
 * `f` has none yet. The one statement of the at-most-one-implementation rule.
 */
inline std::string functionImplementationConflict(
        ast::ISymbolFunctionScope   *f,
        FunctionImpl                incoming) {
    FunctionImpl existing = functionImplementation(f);
    if (existing == FunctionImpl::None || incoming == FunctionImpl::None) {
        return "";
    }
    const std::string &name = f->getName();
    if (existing == FunctionImpl::Import && incoming == FunctionImpl::Import) {
        return "function '" + name + "' is already imported";
    } else if (existing == FunctionImpl::Import
            || incoming == FunctionImpl::Import) {
        return "function '" + name + "' cannot be both defined and imported";
    } else {
        return "function '" + name + "' is already defined";
    }
}

/**
 * Make `proto`'s parameters the ones names in the body resolve to.
 *
 * The plist is registered from the first declaration, and a definition may
 * name its parameters differently (20.2 asks only that the types, directions
 * and count agree, which PSS009 checks). The body is written against the
 * definition's names, so the definition's prototype has to own the plist.
 * Indices are positional, so ElemKind_ArgIdx references are unaffected.
 */
inline void resetFunctionParams(
        ast::ISymbolFunctionScope   *f,
        ast::IFunctionPrototype     *proto) {
    ast::ISymbolScope *plist = f->getPlist();
    if (!plist || !proto) {
        return;
    }
    plist->getSymtab().clear();
    plist->getChildren().clear();
    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=proto->getParameters().begin();
        it!=proto->getParameters().end(); it++) {
        if (!(*it)->getName()) {
            continue;
        }
        const std::string &pname = (*it)->getName()->getId();
        if (plist->getSymtab().find(pname) != plist->getSymtab().end()) {
            // A duplicate parameter: reportDuplicateParams answers for it.
            continue;
        }
        int32_t id = plist->getChildren().size();
        (*it)->setIndex(id);
        plist->getSymtab().insert({pname, id});
        plist->getChildren().push_back(ast::IScopeChildUP(it->get(), false));
    }
}

/**
 * True if any declaration of `f` says `static`: a prototype, a definition, an
 * import prototype or a target template (whose qualifier is on the template
 * node, not its prototype).
 *
 * This is the whole answer only for a component function. 20.2: "A global or
 * package function is always static", so a caller that is not looking at a
 * component's member has no question to ask.
 */
inline bool declaredStatic(ast::ISymbolFunctionScope *f) {
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=f->getPrototypes().begin();
        it!=f->getPrototypes().end(); it++) {
        if ((*it)->getIs_static()) {
            return true;
        }
    }
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=f->getChildren().begin();
        it!=f->getChildren().end(); it++) {
        ast::ITargetTemplateFunction *tf =
            dynamic_cast<ast::ITargetTemplateFunction *>(it->get());
        if (tf && tf->getIs_static()) {
            return true;
        }
    }
    return false;
}

/**
 * True if `c`, a member of a type, belongs to an instance of it rather than
 * to the type: a non-static function, a component instance, or a data field
 * that is neither static nor const. 18.3 lists what a type namespace holds --
 * "types, static constants, static functions, and enum items".
 *
 * A plain `const` field counts as a type member here. The LRM names only
 * static constants, but a const is the same value in every instance, and
 * rejecting it would be a new strictness nothing asked for.
 */
inline bool isInstanceMember(ast::IScopeChild *c) {
    if (ast::ISymbolFunctionScope *f =
            dynamic_cast<ast::ISymbolFunctionScope *>(c)) {
        return !declaredStatic(f);
    }
    if (ast::IField *f = dynamic_cast<ast::IField *>(c)) {
        return (f->getAttr() & (ast::FieldAttr::Static|ast::FieldAttr::Const))
            == ast::FieldAttr::NoFlags;
    }
    return dynamic_cast<ast::IFieldCompRef *>(c) != 0;
}

/**
 * True if `c`, a member of a component, belongs to the type: a static
 * function or a static constant. Not the complement of isInstanceMember --
 * types and enum items are neither, and are not "members" 9.1.4.1 f is
 * about.
 */
inline bool isStaticMember(ast::IScopeChild *c) {
    if (ast::ISymbolFunctionScope *f =
            dynamic_cast<ast::ISymbolFunctionScope *>(c)) {
        return declaredStatic(f);
    }
    if (ast::IField *f = dynamic_cast<ast::IField *>(c)) {
        return (f->getAttr() & ast::FieldAttr::Static) != ast::FieldAttr::NoFlags;
    }
    return false;
}

}
