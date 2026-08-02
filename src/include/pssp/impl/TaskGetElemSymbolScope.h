/**
 * TaskGetElemSymbolScope.h
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
 * Created on:
 *     Author: 
 */
#pragma once
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {


class TaskGetElemSymbolScope : public virtual ast::VisitorBase {
public:
    TaskGetElemSymbolScope(
        dmgr::IDebugMgr         *dmgr,
        ast::ISymbolScope       *root,
        const std::string       &logid="pssp::TaskGetElemSymbolScope") : 
        m_dbg(0), m_path_resolver(dmgr, root) {
        DEBUG_INIT(logid.c_str(), dmgr);
    }

    virtual ~TaskGetElemSymbolScope() { }

    ast::ISymbolScope *resolve(ast::IScopeChild *c) {
        m_ret = 0;
        // Null is a normal answer from the callers' side -- resolvePath()
        // returns it for a path that runs off the end of a scope, which
        // happens whenever a type did not resolve. Every call site passed it
        // straight through to accept(); the first one to actually be handed a
        // null segfaulted the linker, on
        // `list<int> l; l.push_back(42)`.
        //
        // No test witnesses this any more, and that is worth stating rather
        // than leaving to be rediscovered: the call site that crashed was in
        // TaskResolveRefs::catOfDataType, and rewriting that function to read
        // the declaration directly (plan section 35.3) removed the call. The
        // guard is kept because the hazard is structural -- resolve() takes a
        // pointer that its callers routinely obtain from resolvePath() -- not
        // because anything currently exercises it.
        if (c) {
            c->accept(m_this);
        }
        return m_ret;
    }
    
    virtual void visitField(ast::IField *i) override {
        DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
        if (i->getType()) {
            i->getType()->accept(m_this);
        }
        DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
    }

    // A procedural local (`my_struct_s v;` inside an exec or function body)
    // reaches its members exactly as a declared field does. Without this,
    // `v.member` reported "root ref-path element v is not a composite scope"
    // -- the local resolved to its declaration, but the declaration was
    // never mapped to its type's scope.
    virtual void visitProceduralStmtDataDeclaration(
            ast::IProceduralStmtDataDeclaration *i) override {
        DEBUG_ENTER("visitProceduralStmtDataDeclaration %s",
            i->getName()->getId().c_str());
        if (i->getDatatype()) {
            i->getDatatype()->accept(m_this);
        }
        DEBUG_LEAVE("visitProceduralStmtDataDeclaration");
    }

    // Likewise for a function parameter, which is where this first showed up
    // (a `string` parameter could not reach its methods while a field of the
    // same type could).
    virtual void visitFunctionParamDecl(ast::IFunctionParamDecl *i) override {
        DEBUG_ENTER("visitFunctionParamDecl %s", i->getName()->getId().c_str());
        if (i->getType()) {
            i->getType()->accept(m_this);
        }
        DEBUG_LEAVE("visitFunctionParamDecl");
    }

    // forall iterator variable: map it to its type's scope so member access
    // through the iterator (`it.field`) resolves.
    virtual void visitConstraintStmtField(ast::IConstraintStmtField *i) override {
        DEBUG_ENTER("visitConstraintStmtField %s (type=%p)",
            i->getName()->getId().c_str(), i->getType());
        if (i->getType()) {
            i->getType()->accept(m_this);
        }
        DEBUG_LEAVE("visitConstraintStmtField");
    }

    // Labeled `do Type` traversals (e.g., `T1: do tx_data_a`).
    // Resolve target type scope so `T1.tx_byte` can follow the path.
    virtual void visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) override {
        DEBUG_ENTER("visitActivityActionTypeTraversal");
        if (i->getTarget()) {
            i->getTarget()->accept(m_this);
        }
        DEBUG_LEAVE("visitActivityActionTypeTraversal");
    }

    // Labeled handle traversal (e.g., `T1: cfg` where cfg is a declared handle).
    // Resolve the handle's action type scope so `T1.field` paths work.
    virtual void visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) override {
        DEBUG_ENTER("visitActivityActionHandleTraversal");
        // The target is an ExprRefPathContext -- defer; resolution happens
        // via the field lookup path in visitExprRefPathContext.
        DEBUG_LEAVE("visitActivityActionHandleTraversal");
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        DEBUG_ENTER("visitDataTypeUserDefined");
        if (i->getType_id()->getTarget()) {
            // Don't attempt to resolve unless the linkage is present
            ast::IScopeChild *c = m_path_resolver.resolve(i->getType_id()->getTarget());

            // This could be an indirect reference (eg via a parameter). Delegate
            // resolution to support further refinement
            if (c) {
                c->accept(m_this);
            }
        }
        DEBUG_LEAVE("visitDataTypeUserDefined");
    }

    virtual void visitTypeIdentifier(ast::ITypeIdentifier *i) override {
        DEBUG_ENTER("visitTypeIdentifier");
        ast::IScopeChild *c = m_path_resolver.resolve(i->getTarget());
        // This could be an indirect reference (eg via a parameter). Delegate
        // resolution to support further refinement
        if (c) {
            c->accept(m_this);
        }
        DEBUG_LEAVE("visitTypeIdentifier");
    }

    /**
     * The members reachable through a call are the members of what it
     * *returns*.
     *
     * Without this, the inherited `visitSymbolScope` matched -- a
     * SymbolFunctionScope is a SymbolScope -- and handed back the function's
     * own scope, so `f().x` looked `x` up among `f`'s parameters and locals.
     * That is not a near miss: `struct S { int x; } function S f(int p);`
     * accepted `f(1).p` and rejected `f(1).x`, exactly inverting the rule.
     *
     * Unconditional rather than asking whether the element carried a
     * parameter list, because a function name with nothing else after it is
     * not a value in PSS -- there is no other thing `f.something` could mean.
     *
     * A null return is the normal answer for a function returning `void` or a
     * scalar; every caller already treats a missing scope as "nothing to
     * search here".
     */
    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override {
        DEBUG_ENTER("visitSymbolFunctionScope \"%s\"", i->getName().c_str());
        // Any prototype that declares one will do. Overloads differing only
        // in return type are not a thing the LRM permits, and a prototype
        // pair that disagrees is already reported as such.
        for (std::vector<ast::IFunctionPrototype *>::const_iterator
            it=i->getPrototypes().begin(); it!=i->getPrototypes().end(); it++) {
            if ((*it)->getRtype()) {
                (*it)->getRtype()->accept(m_this);
                break;
            }
        }
        DEBUG_LEAVE("visitSymbolFunctionScope");
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        DEBUG_ENTER("visitSymbolScope \"%s\"", i->getName().c_str());
        m_ret = i;
        DEBUG_LEAVE("visitSymbolScope");
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        DEBUG_ENTER("visitSymbolTypeScope \"%s\"", i->getName().c_str());
        m_ret = i;
        DEBUG_LEAVE("visitSymbolTypeScope");
    }

    // On a *specialized* parameter list the dflt slot holds the bound
    // argument, which is what these want.  On an unspecialized one it holds
    // the declared default -- and there may not be one, so it can be null.
    // A parameter with nothing bound simply has no element scope; every
    // caller already handles a null return.

    virtual void visitTemplateGenericTypeParamDecl(ast::ITemplateGenericTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateGenericTypeParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        }
        DEBUG_LEAVE("visitTemplateGenericTypeParamDecl");
    }

    virtual void visitTemplateCategoryTypeParamDecl(ast::ITemplateCategoryTypeParamDecl *i) override {
        DEBUG_ENTER("visitTemplateCategoryTypeParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        }
        DEBUG_LEAVE("visitTemplateCategoryTypeParamDecl");
    }

    virtual void visitTemplateValueParamDecl(ast::ITemplateValueParamDecl *i) override {
        DEBUG_ENTER("visitTemplateValueParamDecl");
        if (i->getDflt()) {
            i->getDflt()->accept(m_this);
        }
        DEBUG_LEAVE("visitTemplateValueParamDecl");
    }

protected:
    dmgr::IDebug                *m_dbg;
    TaskResolveSymbolPathRef    m_path_resolver;
    ast::ISymbolScope           *m_ret;

};

}
