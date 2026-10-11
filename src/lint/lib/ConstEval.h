/*
 * ConstEval.h
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
 * Constant folding for the lint library (lint-core-plan.md C6.4): the
 * linker's TaskEvalExpr, with what may be followed through a reference
 * narrowed to what is constant in every instance of the model:
 * - a `const` field's initializer;
 * - a bound template value parameter: one in a specialization, whose
 *   `dflt` slot holds the argument. In the generic template a parameter's
 *   default is not its value, so a use there does not fold.
 * Any other target (a non-const field, an enum item, a type) does not fold,
 * and nor does a bit slice of a constant.
 */
#pragma once
#include <functional>
#include "pssp/impl/TaskEvalExpr.h"

namespace pssp {
namespace lint {
namespace lib {

class ConstEval : public TaskEvalExpr {
public:
    /** `bound` says whether a template value parameter is a specialization's. */
    ConstEval(IFactory *factory, ast::ISymbolScope *root,
        std::function<bool(ast::ITemplateValueParamDecl *)> bound);

    virtual ~ConstEval();

    virtual void visitExprRefPath(ast::IExprRefPath *i) override;
    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override;
    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override;
    virtual void visitField(ast::IField *i) override;
    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override;

    // Anything the base class's visitor would walk into on the way.
    virtual void visitEnumItem(ast::IEnumItem *i) override { }

private:
    void follow(const ast::ISymbolRefPath *target);

private:
    IFactory                                                *m_factory;
    ast::ISymbolScope                                       *m_root;
    std::function<bool(ast::ITemplateValueParamDecl *)>     m_bound;
};

}
}
}
