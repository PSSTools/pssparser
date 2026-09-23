/*
 * TaskResolveRootRef.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/InternalError.h"
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/impl/TaskGetSymbolRefPathKind.h"
#include "TaskResolveRootRef.h"
#include "pssp/ast/ISymbolDeclaration.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "TaskResolveEnumRef.h"
#include "TaskResolveSuperTypeRef.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "pssp/impl/ActivityScopes.h"


namespace pssp {



TaskResolveRootRef::TaskResolveRootRef(
    ResolveContext      *ctxt,
    bool                search_imp) : TaskResolveBase(ctxt), m_search_imp(search_imp) {
    DEBUG_INIT("TaskResolveRootRef", ctxt->getDebugMgr());
}

TaskResolveRootRef::~TaskResolveRootRef() {

}

ast::ISymbolRefPath *TaskResolveRootRef::resolve(const ast::IExprId *id) {
    DEBUG_ENTER("resolve %s", id->getId().c_str());
    m_ref = 0;

    // A keyword the lexer returns as an ID. `\this` is an ordinary name.
    if (id->getId() == "this" && !id->getIs_escaped()) {
        m_ref = resolveThis();
        DEBUG_LEAVE("resolve this %p", m_ref);
        return m_ref;
    }

    // Push a clone of the active symbol table, since we
    // will be traversing it
    m_ctxt->pushCloneSymtab();
    m_id    = id;
    m_super_depth = 0;

    int32_t count = 0;
    while (!m_ref && m_ctxt->symtab()->hasScopes()) {
        // hasScopes() and getScope() do not answer the same question, and the
        // gap between them used to be a segfault (P7-X3). getScope() is
        // getSymScopeBack(), which walks the stack backwards for the first
        // entry that *is* a symbol scope and returns 0 when there is none --
        // so a non-empty stack of non-symbol scopes leaves the loop running
        // with nothing to run on. `foreach (i : a) { a[0] == 1; }` reached it:
        // resolving `a` walks out through the foreach's constraint scope, and
        // the walk reaches a point where the innermost entries carry no symbol
        // scope at all.
        //
        // Popping rather than breaking is what keeps the diagnostic right: the
        // enclosing action scope, where `a` actually lives, is further out. A
        // break here would resolve nothing and report PSS002 on a valid
        // reference -- trading a crash for a wrong answer.
        ast::ISymbolScope *scope = m_ctxt->symtab()->getScope();
        if (!scope) {
            m_ctxt->symtab()->popScope();
            continue;
        }

        DEBUG_ENTER("processing scope %s", scope->getName().c_str());
        if (ActivityScopes::asScope(scope)) {
            // Searched as the scope it is. Visiting it would go on into a
            // compound statement's bodies -- each a scope, each searched in
            // turn, and each able to clear a hit made in this one.
            visitSymbolScope(scope);
        } else {
            scope->accept(m_this);
        }
        DEBUG_LEAVE("processing scope %s", scope->getName().c_str());

        if (!m_ref) {
            m_ctxt->symtab()->popScope();
        }
    }

    // The lexical walk is exhausted. If this reference sits inside a member
    // contributed by a type extension, the walk went out through the
    // *extended* type's package -- LRM 17.2 says the extension belongs to the
    // package that encloses the `extend` statement, so that package and its
    // imports (17.2.3) get one more try. Deliberately last: the extended
    // type's own members must still win, which is what makes an extension
    // able to refer to what it is extending.
    if (!m_ref) {
        m_ref = searchExtensionCtxt(m_id);
    }

    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve %p (%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);

    return m_ref;
}

ast::ISymbolRefPath *TaskResolveRootRef::resolveThis() {
    DEBUG_ENTER("resolveThis");
    ast::ISymbolRefPath *ret = 0;

    // Inside `a with { ... }` the traversed action's scope is pushed on top of
    // the containing action's (visitActivityActionHandleTraversal). Names
    // search it first; `this` passes over it, which is the whole point of
    // `this` there -- reaching a containing-action field the sub-action's
    // field of the same name shadows.
    ast::ISymbolScope *skip = m_ctxt->inlineCtxt();

    m_ctxt->pushCloneSymtab();
    while (!ret && m_ctxt->symtab()->hasScopes()) {
        // See resolve() for why a null scope pops rather than breaks.
        ast::ISymbolScope *scope = m_ctxt->symtab()->getScope();
        if (scope && dynamic_cast<ast::ISymbolTypeScope *>(scope)) {
            if (scope == skip) {
                skip = 0;
            } else {
                ret = m_ctxt->symtab()->getScopeSymbolPath();
                ret->getPath().push_back({
                    ast::SymbolRefPathElemKind::ElemKind_This, 0});
                break;
            }
        }
        m_ctxt->symtab()->popScope();
    }
    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolveThis %p", ret);
    return ret;
}

void TaskResolveRootRef::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    DEBUG_ENTER("visitProceduralStmtRepeat");
    visitSymbolScope(i);
    DEBUG_LEAVE("visitProceduralStmtRepeat");
}

void TaskResolveRootRef::visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) {
    // Only inspect this scope's symtab (the iterator/index vars); do not let the
    // base visitor descend into the body and clobber a successful match.
    DEBUG_ENTER("visitProceduralStmtForeach");
    visitSymbolScope(i);
    DEBUG_LEAVE("visitProceduralStmtForeach");
}

void TaskResolveRootRef::visitTemplateString(ast::ITemplateString *i) {
    // Variables declared at the top level of a triple-quoted string, via
    // `{% int x; %}` (4.7.1.2). Same shape as the procedural loops above:
    // inspect only this scope's symtab, never the body.
    DEBUG_ENTER("visitTemplateString");
    visitSymbolScope(i);
    DEBUG_LEAVE("visitTemplateString");
}

void TaskResolveRootRef::visitTemplateBlock(ast::ITemplateBlock *i) {
    // A foreach iterator/index, a repeat index, or a variable declared inside
    // the block -- "added to the scope until the block closing directive"
    // (4.7.1.2). Covers TemplateIfClause too, which derives from this.
    DEBUG_ENTER("visitTemplateBlock");
    visitSymbolScope(i);
    DEBUG_LEAVE("visitTemplateBlock");
}

void TaskResolveRootRef::visitRootSymbolScope(ast::IRootSymbolScope *i) {
    DEBUG_ENTER("visitRootSymbolScope %s %d %p", i->getName().c_str(), i->getSymtab().size(), i);
    visitSymbolScope(i);
    DEBUG_LEAVE("visitRootSymbolScope %s %d %p", i->getName().c_str(), i->getSymtab().size(), i);
}

void TaskResolveRootRef::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope id=%s (%s) %d (%p)", 
        m_id->getId().c_str(), i->getName().c_str(),
        i->getSymtab().size(),
        i);
    std::unordered_map<std::string,int32_t>::const_iterator it = i->getSymtab().find(m_id->getId());

    DEBUG("imports: %p", i->getImports());
    if (it != i->getSymtab().end()) {
        DEBUG("Found symbol %s @ index %d", m_id->getId().c_str(), it->second);
        ast::IScopeChild *c = i->getChildren().at(it->second).get();

        if (dynamic_cast<ast::ISymbolTypeScope *>(c)) {
            DEBUG("Is a type scope");
            if (dynamic_cast<ast::ISymbolTypeScope *>(c)->getPlist()) {
                DEBUG("Is parameterized");
            }
        }
        // Path to the scope the symbol-table iterator is sitting on. That is
        // 'i' only while m_super_depth is zero; once visitSymbolTypeScope has
        // recursed up an inheritance chain, 'i' is a *base* of that scope and
        // the iterator has no idea.
        m_ref = m_ctxt->symtab()->getScopeSymbolPath();

        // One Super element per step taken up the chain, so that the child
        // index below is applied to the scope it was actually found in.
        // Without these the base's index indexed the derived type's children:
        // index 0 landed on some unrelated child and was reported as "'x' is
        // not a function", and every higher index fell off the end and
        // resolved to nothing at all -- which is why an inherited call with
        // the wrong argument count used to go unreported. See CL-N4.
        for (int32_t s=0; s<m_super_depth; s++) {
            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_Super, 0});
        }

        // Now, add in the child element that we just found
        m_ref->getPath().push_back({
            TaskGetSymbolRefPathKind(m_ctxt->getDebugMgr()).get(c),
            it->second});
    // If we're inside a typed context, and the type is Enum,
    // then search that enum
    } else if ((m_ref=TaskResolveEnumRef(m_ctxt).resolve(m_id))) {
        // Found in this scope
        DEBUG("Found symbol as an enumerator");
    } else if (m_search_imp && i->getImports() && (m_ref=searchImports(m_id, i->getImports()))) {
        // Found in imports
        DEBUG("Found symbol via imports");
    } else {
        DEBUG("Failed to find symbol");
    }

    DEBUG_LEAVE("visitSymbolScope m_ref=%p (sz=%d)", m_ref, (m_ref)?m_ref->getPath().size():-1);
}

//void TaskResolveRootRef::visitSymbolExecScope(ast::ISymbolExecScope *i) {
//    DEBUG_ENTER("visitSymbolExecScope");
//    visitSymbolScope(i);
//    DEBUG_LEAVE("visitSymbolExecScope");
//}

void TaskResolveRootRef::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    // Recurses up the super chain. TaskCheckTypeCycles' super_cyclic mark
    // ends a ring; this ends anything else that does not terminate.
    DepthGuard guard(m_ctxt->depth(), "TaskResolveRootRef (super-type search)");
    DEBUG_ENTER("visitSymbolTypeScope id=%s (%s)", 
        m_id->getId().c_str(), i->getName().c_str());
    visitSymbolScope(i); // Look in primary declaration scope

    DEBUG("TypeScope: m_ref=%p plist=%p", m_ref, i->getPlist());
    // A type's own template parameters only -- not a base type's, reached
    // through the super walk below. LRM 10.3: "A template parameter may not
    // be referenced from within subtypes that inherit from the template type
    // that originally defined the parameter." Looking there let a base's
    // parameter shadow an outer name: every packed struct inherits
    // packed_s<endianness_e e>, so a user type named `e` used inside one
    // bound to that parameter instead of the type.
    if (!m_ref && i->getPlist() && m_super_depth == 0) {
        std::unordered_map<std::string,int32_t>::const_iterator it;

        if (DEBUG_EN) {
        for (std::unordered_map<std::string,int32_t>::const_iterator
            it=i->getPlist()->getSymtab().begin();
            it!=i->getPlist()->getSymtab().end(); it++) {
            DEBUG("Sym: %s", it->first.c_str());
        }
        }

        if ((it=i->getPlist()->getSymtab().find(m_id->getId())) != i->getPlist()->getSymtab().end()) {
            // Target is a parameter value
            m_ref = m_ctxt->symtab()->getScopeSymbolPath();
            DEBUG("Found %s as a parameter (%d)",
                m_id->getId().c_str(), it->second);

            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ParamIdx, 
                it->second
            });

            DEBUG("Full path:");
            for (uint32_t i=0; i<m_ref->getPath().size(); i++) {
                DEBUG("  [%d] %d %d", i, m_ref->getPath().at(i).kind, m_ref->getPath().at(i).idx);
            }
        }
    }

    if (!m_ref) {
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
        if (ts && ts->getSuper_t() && ts->getSuper_t()->getTarget()) {
            DEBUG("Searching super-type chain for %s", m_id->getId().c_str());
            // Follows a parameter binding when the super type is one of the
            // generic's own parameters -- see TaskResolveSuperTypeRef.
            ast::IScopeChild *super_sc = TaskResolveSuperTypeRef(
                m_ctxt->getDebugMgr(), m_ctxt->root()
            ).resolve(ts);
            if (super_sc) {
                m_super_depth++;
                super_sc->accept(m_this);
                m_super_depth--;
            }
        }
    }

    DEBUG_LEAVE("visitSymbolTypeScope %p", m_ref);
}

void TaskResolveRootRef::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
    DEBUG_ENTER("visitSymbolFunctionScope %s (searching for %s)", i->getName().c_str(), m_id->getId().c_str());

    // A function scope built from a bare prototype has no plist -- see
    // TaskBuildSymbolTree::visitFunctionPrototype. That scope becomes reachable
    // once a definition of the same function follows, which attaches a body
    // whose statements resolve through here. visitSymbolTypeScope already
    // guards the equivalent lookup; this one did not, and segfaulted.
    std::unordered_map<std::string,int32_t>::const_iterator it;

    if (i->getPlist()) {
        it = i->getPlist()->getSymtab().find(m_id->getId());
    }

    if (i->getPlist() && it != i->getPlist()->getSymtab().end()) {
        ast::IScopeChild *c = i->getPlist()->getChildren().at(it->second).get();
        DEBUG("Found as a function parameter @ %d", it->second);
        m_ref = m_ctxt->symtab()->getScopeSymbolPath(); // Path to 'i'
        m_ref->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ArgIdx,
            it->second});
    } else {
        DEBUG("Delegate to SymbolScope");
        visitSymbolScope(i);
    }

    DEBUG_LEAVE("visitSymbolFunctionScope");
}

/**
 * `symbol s(A aa) { aa; }`: a symbol's parameters are in scope in its body
 * (11.4), addressed by position like a function's (ElemKind_ArgIdx). They are
 * a list on the declaration, not children, so nothing found them (S1).
 */
void TaskResolveRootRef::visitSymbolDeclaration(ast::ISymbolDeclaration *i) {
    DEBUG_ENTER("visitSymbolDeclaration %s (searching for %s)", i->getName().c_str(), m_id->getId().c_str());
    for (uint32_t idx=0; idx<i->getParams().size(); idx++) {
        ast::IFunctionParamDecl *p = i->getParams().at(idx).get();
        if (p->getName() && p->getName()->getId() == m_id->getId()) {
            DEBUG("Found as a symbol parameter @ %d", idx);
            m_ref = m_ctxt->symtab()->getScopeSymbolPath(); // Path to 'i'
            m_ref->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ArgIdx, (int32_t)idx});
            DEBUG_LEAVE("visitSymbolDeclaration");
            return;
        }
    }
    visitSymbolScope(i);
    DEBUG_LEAVE("visitSymbolDeclaration");
}

ast::ISymbolRefPath *TaskResolveRootRef::absPath(ast::ISymbolScope *s) {
    // An absolute path -- rooted, as searchImport's paths are -- built by
    // walking the symbol tree upward and recording each scope's index in its
    // parent. There is no ready-made "path to this scope": getScopeSymbolPath()
    // answers for the iterator's current position, which is exactly the thing
    // that is wrong here.
    std::vector<int32_t> idx;
    ast::ISymbolScope *cur = s;

    while (cur && cur != m_ctxt->root()) {
        if (cur->getId() < 0) {
            // Unnamed position. Nothing downstream can index through it, and
            // a partial path would resolve to the wrong node rather than to
            // none -- the failure mode ElemKind_ChildIdx's negative-index
            // guard exists to avoid.
            DEBUG("absPath: scope %s has no index", cur->getName().c_str());
            return 0;
        }
        idx.push_back(cur->getId());
        cur = dynamic_cast<ast::ISymbolScope *>(cur->getUpper());
    }

    if (cur != m_ctxt->root()) {
        DEBUG("absPath: walk did not reach the root");
        return 0;
    }

    ast::ISymbolRefPath *ret =
        m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
    for (std::vector<int32_t>::const_reverse_iterator
        it=idx.rbegin(); it!=idx.rend(); it++) {
        ret->getPath().push_back({
            ast::SymbolRefPathElemKind::ElemKind_ChildIdx, *it});
    }
    return ret;
}

ast::ISymbolRefPath *TaskResolveRootRef::searchExtensionCtxt(
        const ast::IExprId *id) {
    ast::ISymbolScope *decl_s = m_ctxt->extensionCtxt();

    if (!decl_s) {
        return 0;
    }

    DEBUG_ENTER("searchExtensionCtxt %s in %s",
        id->getId().c_str(), decl_s->getName().c_str());

    ast::ISymbolRefPath *ret = 0;
    std::unordered_map<std::string,int32_t>::const_iterator it =
        decl_s->getSymtab().find(id->getId());

    if (it != decl_s->getSymtab().end()) {
        if ((ret=absPath(decl_s))) {
            ret->getPath().push_back({
                TaskGetSymbolRefPathKind(m_ctxt->getDebugMgr()).get(
                    decl_s->getChildren().at(it->second).get()),
                it->second});
        }
    } else if (m_search_imp && decl_s->getImports()) {
        // 17.2.3: the imports in effect for an extension body are the ones at
        // the extension's own declaration site.
        //
        // searchImport resolves the import's own absolute path through
        // m_ctxt->symtab(), and by the time this runs the caller's loop has
        // popped every scope off the clone it pushed -- resolveAbsPath on an
        // empty stack segfaults. Give it a fresh iterator at the root, which
        // is all an absolute path needs.
        m_ctxt->pushSymtab(
            m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()));
        ret = searchImports(id, decl_s->getImports());
        m_ctxt->popSymtab();
    }

    DEBUG_LEAVE("searchExtensionCtxt %s %p", id->getId().c_str(), ret);
    return ret;
}

/**
 * 18.1.3: an explicit import takes precedence over a wildcard import, and a
 * name that more than one import of the same kind provides is not imported
 * at all. So the explicit imports are searched first and the wildcards only
 * when they yield nothing; within a tier, two routes to the *same*
 * declaration are one match (F18: this compared counts, so `p::*` together
 * with an explicit `p::s` was "ambiguous"). A real ambiguity is reported and
 * resolves to nothing, rather than to the first import, which cascaded.
 * Aliases are 6.4.
 */
ast::ISymbolRefPath *TaskResolveRootRef::searchImports(
    const ast::IExprId          *id,
    ast::ISymbolImportSpec      *imp) {
    DEBUG_ENTER("searchImports - %d statements", imp->getImports().size());
    ast::ISymbolRefPath *ret = 0;

    for (int tier=0; tier<2 && !ret; tier++) {
        bool want_wildcard = (tier == 1);
        ast::IScopeChild *found = 0;
        bool ambiguous = false;
        for (std::vector<ast::IPackageImportStmt *>::const_iterator
                imp_it=imp->getImports().begin();
                imp_it!=imp->getImports().end(); imp_it++) {
            if ((*imp_it)->getWildcard() != want_wildcard) {
                continue;
            }
            ast::ISymbolRefPath *ret_t = searchImport(id, *imp_it);
            if (!ret_t) {
                continue;
            }
            ast::IScopeChild *node = m_ctxt->resolveSymbolPathRef(ret_t);
            if (!ret) {
                ret = ret_t;
                found = node;
            } else if (node != found) {
                ambiguous = true;
                delete ret_t;
            } else {
                delete ret_t;
            }
        }
        if (ambiguous) {
            m_ctxt->addErrorMarker(
                id->getLocation(),
                "ambiguous reference to '%s': more than one %s import provides "
                "it, so none does (18.1.3); qualify the name",
                id->getId().c_str(),
                want_wildcard ? "wildcard" : "explicit");
            delete ret;
            ret = 0;
            break;
        }
    }

    DEBUG_LEAVE("searchImports %p", ret);
    return ret;
}

ast::ISymbolRefPath *TaskResolveRootRef::searchImport(
        const ast::IExprId          *id,
        ast::IPackageImportStmt     *imp) {
	DEBUG_ENTER("searchImport sym=%s", id->getId().c_str());
    ast::ISymbolRefPath *ret = 0;

	// ast::ISymbolRefPath *ret = 0;
	if (!imp->getPath()->getTarget()) {
		DEBUG("Skipping, due to unset import target");
		return 0;
	}

	// A single-symbol import names the symbol; it does not open it as a scope.
	// `import p::t;` has to match `t` and hand back the path the import itself
	// resolved to. Falling through to the wildcard search below instead looked
	// for `t` inside `t`, never found it, and left every `import p::t;` in the
	// workspace doing nothing at all.
	if (!imp->getWildcard()) {
		const std::vector<ast::ITypeIdentifierElemUP> &elems =
			imp->getPath()->getElems();
		if (elems.empty() ||
			elems.back()->getId()->getId() != id->getId()) {
			DEBUG_LEAVE("searchImport %s - single-symbol import of something else",
				id->getId().c_str());
			return 0;
		}
		ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
		ret->getPath().insert(
			ret->getPath().begin(),
			imp->getPath()->getTarget()->getPath().begin(),
			imp->getPath()->getTarget()->getPath().end());
		DEBUG_LEAVE("searchImport %s - single-symbol import", id->getId().c_str());
		return ret;
	}
	for (uint32_t i=0; i<imp->getPath()->getTarget()->getPath().size(); i++) {
		DEBUG("Imp Path[%d] %d", i, imp->getPath()->getTarget()->getPath().at(i));
	}
	ast::IScopeChild *target_c = m_ctxt->symtab()->resolveAbsPath(imp->getPath()->getTarget());
	ast::ISymbolScope *target_s = dynamic_cast<ast::ISymbolScope *>(target_c);
	DEBUG("target_c: %p ; target_s: %p", target_c, target_s);

	if (target_s) {
		DEBUG("Have a symbol scope (%s)", target_s->getName().c_str());
		std::unordered_map<std::string, int32_t>::const_iterator it;
		it = target_s->getSymtab().find(id->getId());

		if (it != target_s->getSymtab().end()) {
			DEBUG("Found the symbol (%s)", id->getId().c_str());
			ret = m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
			ret->getPath().insert(
				ret->getPath().begin(),
				imp->getPath()->getTarget()->getPath().begin(),
				imp->getPath()->getTarget()->getPath().end());
			ret->getPath().push_back({
                ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second
            });
		} else {
            ret = TaskResolveEnumRef(m_ctxt, target_s).resolve(id);
        }
	}

	DEBUG_LEAVE("searchImport %s %p", id->getId().c_str(), ret);
	return ret;
}

dmgr::IDebug *TaskResolveRootRef::m_dbg = 0;

}
