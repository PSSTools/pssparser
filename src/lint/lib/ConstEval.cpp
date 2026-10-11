/*
 * ConstEval.cpp
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
 * Constant folding for the lint library (lint-core-plan.md C6.4); see
 * ConstEval.h.
 */
#include "ConstEval.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/ITemplateValueParamDecl.h"

namespace pssp {
namespace lint {
namespace lib {

ConstEval::ConstEval(IFactory *factory, ast::ISymbolScope *root,
        std::function<bool(ast::ITemplateValueParamDecl *)> bound) :
        TaskEvalExpr(factory, root), m_factory(factory), m_root(root),
        m_bound(std::move(bound)) { }

ConstEval::~ConstEval() { }

void ConstEval::follow(const ast::ISymbolRefPath *target) {
    if (!target) {
        return;
    }
    ast::IScopeChild *t = TaskResolveSymbolPathRef(m_factory->getDebugMgr(), m_root)
        .resolve(target);
    if (NodeKind::cast<ast::IField>(t) || NodeKind::cast<ast::ITemplateValueParamDecl>(t)) {
        t->accept(m_this);
    }
}

void ConstEval::visitExprRefPath(ast::IExprRefPath *i) {
    follow(i->getTarget());
}

void ConstEval::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    if (!i->getSlice()) {
        follow(i->getTarget());
    }
}

void ConstEval::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    follow(i->getTarget());
}

void ConstEval::visitField(ast::IField *i) {
    if ((i->getAttr() & ast::FieldAttr::Const) != ast::FieldAttr::NoFlags) {
        TaskEvalExpr::visitField(i);
    }
}

void ConstEval::visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) {
    if (m_bound(i)) {
        TaskEvalExpr::visitTemplateValueParamDecl(i);
    }
}

}
}
}
