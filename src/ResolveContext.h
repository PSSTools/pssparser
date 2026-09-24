/**
 * ResolveContext.h
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
#include <stdint.h>
#include <functional>
#include <map>
#include <string>
#include <set>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IRootSymbolScope.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ISymbolRefPath.h"
#include "pssp/IFactory.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTableIterator.h"

namespace pssp {




class ResolveContext {
public:
    ResolveContext(
        IFactory                *factory,
        IMarkerListener         *marker_l,
        ast::IRootSymbolScope   *root);

    virtual ~ResolveContext();

    ast::ISymbolScope *root() const { return m_root; }

    void pushInlineCtxt(ast::ISymbolScope *s) {
        m_inline_ctxt_s.push_back(s);
    }

    ast::ISymbolScope *inlineCtxt() const { 
        return (m_inline_ctxt_s.size())?m_inline_ctxt_s.back():0;
    }

    void popInlineCtxt() {
        m_inline_ctxt_s.pop_back();
    }

    /**
     * The scope an `extend` body's names resolve in, in addition to the
     * extended type's.
     *
     * LRM 17.2: "every type extension ... is associated with the nearest
     * package that lexically encloses its definition", and 17.2.3 makes that
     * package's imports apply to the extension body. But
     * TaskApplyTypeExtensions re-homes an extension's members into the
     * *extended* type's symbol scope, and TaskResolveRefs walks them from
     * there -- so the lexical chain a name is looked up along runs out through
     * the extended type's package, never the extension's.
     *
     * TaskResolveRefs pushes the declaring scope here while visiting a
     * re-homed member, and NameLookup searches that scope's package chain
     * where the extended type's levels end. After them, not instead of them:
     * an extension body must see the extended type's own members, which is
     * the whole point of writing one.
     *
     * A stack, because an extension may contribute a nested type whose own
     * body is visited within it.
     */
    void pushExtensionCtxt(ast::ISymbolScope *s) {
        m_ext_ctxt_s.push_back(s);
    }

    ast::ISymbolScope *extensionCtxt() const {
        return (m_ext_ctxt_s.size())?m_ext_ctxt_s.back():0;
    }

    void popExtensionCtxt() {
        m_ext_ctxt_s.pop_back();
    }

    /**
     * Maps a member re-homed by TaskApplyTypeExtensions to the scope that
     * lexically declared it. Populated by that pass; read by TaskResolveRefs
     * to know when to push an extension context.
     */
    void setExtensionDeclScopes(
        const std::map<ast::IScopeChild *, ast::ISymbolScope *> &m) {
        m_ext_decl_scope = m;
    }

    ast::ISymbolScope *extensionDeclScope(ast::IScopeChild *c) const {
        std::map<ast::IScopeChild *, ast::ISymbolScope *>::const_iterator it =
            m_ext_decl_scope.find(c);
        return (it != m_ext_decl_scope.end())?it->second:0;
    }

    IFactory *getFactory() const { return m_factory; }

    dmgr::IDebugMgr *getDebugMgr() const { return m_factory->getDebugMgr(); }

    int32_t specializationDepth() const { return m_specialization_depth; }

    void incSpecializationDepth() { m_specialization_depth++; }

    void decSpecializationDepth() { m_specialization_depth--; }

    void pushSymtab(ISymbolTableIterator *t) {
        m_symtab_it_s.push_back(ISymbolTableIteratorUP(t));
    }

    void pushCloneSymtab() {
        pushSymtab(cloneSymtab());
    }

    const ISymbolTableIterator *symtab() const {
        return (m_symtab_it_s.size())?m_symtab_it_s.back().get():0;
    }

    ISymbolTableIterator *symtab() {
        return (m_symtab_it_s.size())?m_symtab_it_s.back().get():0;
    }

    ISymbolTableIterator *cloneSymtab() const {
        return (m_symtab_it_s.size())?m_symtab_it_s.back()->clone():0;
    }

    void popSymtab() {
        m_symtab_it_s.pop_back();
    }

    ast::IScopeChild *resolveSymbolPathRef(ast::ISymbolRefPath *path);

    void addRef(int32_t from, int32_t to);

    void addMarker(
        MarkerSeverityE     severity,
        const ast::Location &loc,
        const char          *fmt,
        va_list             ap);

    void addMarker(
        MarkerSeverityE     severity,
        const ast::Location &loc,
        const char          *fmt,
        ...);

    void addErrorMarker(
        const ast::Location &loc,
        const char          *fmt,
        ...);

    /**
     * Report a defect in pssparser rather than in the model: a PSS000
     * marker, "internal error: ...". For a state the code believed could
     * not happen, at a site that can carry on (the reference stays unbound).
     * A site that cannot carry on throws InternalError instead, and the
     * linker's catch-all reports it the same way.
     */
    void internalError(
        const ast::Location &loc,
        const char          *fmt,
        ...);

    /**
     * The shared recursion counter for DepthGuard. One per link: every
     * recursive resolution entry point guards against the same budget, so
     * runaway mutual recursion between two walkers is caught as surely as
     * self-recursion within one.
     */
    int32_t &depth() { return m_depth; }

    /**
     * A marker with related locations -- (location, label) pairs pointing at
     * the declarations the message is about.
     */
    void addMarker(
        MarkerSeverityE     severity,
        const ast::Location &loc,
        const std::string   &msg,
        const std::vector<std::pair<ast::Location, std::string>> &related);

    /**
     * Set by NameLookup after each unqualified lookup: the later
     * declaration of `id` the lookup passed over (18.2a/b), when the lookup
     * found nothing else; otherwise null. Lets the site that reports the miss
     * say "used before its declaration" instead of "unknown identifier".
     */
    void setFwdDeclHint(const ast::IExprId *id, ast::IScopeChild *decl) {
        m_fwd_id = id;
        m_fwd_decl = decl;
    }

    ast::IScopeChild *fwdDeclHint(const ast::IExprId *id) const {
        return (id == m_fwd_id)?m_fwd_decl:0;
    }

    /**
     * Also set by NameLookup after each unqualified lookup: the static
     * function the lookup passed out of on its way to an instance member of
     * the component (20.2), or null. The lookup keeps its answer, so the use
     * is bound and the report is one error, not a cascade.
     */
    void setStaticCtxtHint(const ast::IExprId *id, ast::IScopeChild *fn) {
        m_static_id = id;
        m_static_fn = fn;
    }

    ast::IScopeChild *staticCtxtHint(const ast::IExprId *id) const {
        return (id == m_static_id)?m_static_fn:0;
    }

    /**
     * True if an error has already been reported at this source position.
     * Lets a later pass stay quiet about a failure an earlier one described
     * better -- see TaskCheckRefsResolved.
     */
    bool wasReported(const ast::Location &loc) const;

    /**
     * True if a marker of any severity -- a warning included -- has been
     * reported at this position, by any of the linker's passes.
     */
    bool wasNoted(const ast::Location &loc) const;

    /** True if any error has been reported to the listener, by any pass. */
    bool hasErrors() const {
        return m_marker_l && m_marker_l->hasSeverity(MarkerSeverityE::Error);
    }

    /**
     * While quiet, markers are dropped: used to bind names that must not be
     * diagnosed (a `compile if` condition, which the builder already
     * evaluated). Nests.
     */
    void pushQuiet() { m_quiet++; }
    void popQuiet() { m_quiet--; }

    /**
     * Queue work that needs every reference resolved -- the linker runs it
     * once TaskResolveRefs is done. For a computation made during
     * specialization, which can run before the types it depends on are
     * bound (sizeof_s of a struct declared after the use).
     */
    void addPostResolveAction(const std::function<void()> &a) {
        m_post_resolve.push_back(a);
    }

    /**
     * Run and clear the queued actions. An action may queue another; it
     * runs in the same call.
     */
    void runPostResolveActions() {
        for (uint32_t i=0; i<m_post_resolve.size(); i++) {
            std::function<void()> a = m_post_resolve.at(i);
            a();
        }
        m_post_resolve.clear();
    }

    /**
     * The enums declared directly in `s`. NameLookup asks at every level it
     * searches, and finding them means a dynamic_cast per child -- costly on
     * this hierarchy, and most children are not enums. Kept per scope, and
     * rebuilt when the scope has gained children since.
     */
    const std::vector<ast::ISymbolEnumScope *> &enumsOf(ast::ISymbolScope *s) {
        EnumCache &e = m_enum_cache[s];
        if (!e.valid || e.n_children != s->getChildren().size()) {
            e.enums.clear();
            for (std::vector<ast::IScopeChildUP>::const_iterator
                    it=s->getChildren().begin();
                    it!=s->getChildren().end(); it++) {
                if (ast::ISymbolEnumScope *es =
                        dynamic_cast<ast::ISymbolEnumScope *>(it->get())) {
                    e.enums.push_back(es);
                }
            }
            e.n_children = s->getChildren().size();
            e.valid = true;
        }
        return e.enums;
    }

private:
    struct EnumCache {
        bool                                    valid = false;
        size_t                                  n_children = 0;
        std::vector<ast::ISymbolEnumScope *>    enums;
    };

private:
    ast::IRootSymbolScope                           *m_root;
    std::unordered_map<ast::ISymbolScope *, EnumCache> m_enum_cache;
    std::vector<ast::ISymbolScope *>                m_inline_ctxt_s;
    std::vector<ast::ISymbolScope *>                m_ext_ctxt_s;
    std::map<ast::IScopeChild *, ast::ISymbolScope *> m_ext_decl_scope;
    IFactory                                        *m_factory;
    IMarkerListener                                 *m_marker_l;
    int32_t                                         m_specialization_depth;
    int32_t                                         m_depth;
    std::vector<ISymbolTableIteratorUP>             m_symtab_it_s;
    std::vector<std::unordered_set<int32_t>>        m_inbound_refs;
    std::vector<std::unordered_set<int32_t>>        m_outbound_refs;
    // (fileid, lineno, linepos) of every position that already carries an
    // error marker; see wasReported().
    std::set<std::tuple<int32_t,int32_t,int32_t>>   m_reported;
    std::vector<std::function<void()>>              m_post_resolve;
    int32_t                                         m_quiet = 0;
    const ast::IExprId                              *m_fwd_id = 0;
    ast::IScopeChild                                *m_fwd_decl = 0;
    const ast::IExprId                              *m_static_id = 0;
    ast::IScopeChild                                *m_static_fn = 0;

};

}
