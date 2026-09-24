/*
 * AstLinker.cpp
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
#ifdef _WIN32
#ifdef UNDEFINED
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif
#else
#include <sys/time.h>
#endif
#include "dmgr/impl/DebugMacros.h"
#include "pssp/impl/InternalError.h"
#include "pssp/impl/TaskCloneSymbolScope.h"
#include "AstLinker.h"
#include "MarkerLocationRecorder.h"
#include "ResolveContext.h"
#include "TaskApplyOverlay.h"
#include "TaskApplyTypeExtensions.h"
#include "TaskBuildSymbolTree.h"
#include "TaskResolveRefsOverlay.h"
#include "TaskResolveRefs.h"
#include "TaskResolveSuperTypes.h"
#include "TaskCheckPackedStructs.h"
#include "TaskCheckPackedUses.h"
#include "TaskCheckRefsResolved.h"
#include "TaskCheckTypeCycles.h"
#include "TaskResolveOverrideActions.h"


namespace pssp {




AstLinker::AstLinker(
    dmgr::IDebugMgr     *dmgr,
    IFactory            *factory) : m_dmgr(dmgr), m_factory(factory) {
    DEBUG_INIT("AstLinker", dmgr);
    m_ast_factory = m_factory->getAstFactory();
}

AstLinker::~AstLinker() {

}

static uint64_t time_ms() {
    uint64_t ret = 0;
#ifndef _WIN32
    struct timeval tv;
    gettimeofday(&tv, 0);
    ret = tv.tv_sec*1000;
    ret += tv.tv_usec/1000;
#else
#ifdef UNDEFINED
    static const uint64_t EPOCH = ((uint64_t) 116444736000000000ULL);

    SYSTEMTIME  system_time;
    FILETIME    file_time;
    uint64_t    time;

    GetSystemTime( &system_time );
    SystemTimeToFileTime( &system_time, &file_time );
    time =  ((uint64_t)file_time.dwLowDateTime )      ;
    time += ((uint64_t)file_time.dwHighDateTime) << 32;

    ret = ((time - EPOCH) / 10000000L);
    ret *= 1000;
    ret += system_time.wMilliseconds;
#endif
#endif
    return ret;
}

/**
 * Report an exception that escaped a link pass as a PSS000 marker. The
 * location is the thrower's when it had one; otherwise the marker is
 * location-less, which the Python side renders as a tool-level diagnostic.
 */
static void reportInternalError(
        IFactory            *factory,
        IMarkerListener     *marker_l,
        const char          *pass,
        const char          *what,
        const ast::Location *loc) {
    char tmp[1024];
    snprintf(tmp, sizeof(tmp),
        "internal error in %s: %s; please report this", pass, what);
    IMarkerUP marker(factory->mkMarker(
        tmp,
        MarkerSeverityE::Error,
        (loc)?*loc:ast::Location()));
    marker->setId(INTERNAL_ERROR_ID);
    marker_l->marker(marker.get());
}

ast::IRootSymbolScope *AstLinker::link(
        IMarkerListener                         *marker_l,
        const std::vector<ast::IGlobalScope *>  &scopes,
        bool                                    own_scopes) {
    // The catch-all (INV-1). Any exception that escapes a pass -- an
    // InternalError, a DEBUG_FATAL, an out-of-range .at() -- becomes one
    // PSS000 marker naming the pass, and the partially linked tree is
    // returned as it stands. Without it the exception crossed into Cython,
    // which had no `except +`, and the process aborted.
    const char *pass = "building the symbol tree";
    ast::IRootSymbolScope *symtree = 0;
    try {
        linkPasses(marker_l, scopes, own_scopes, symtree, pass);
    } catch (const InternalError &e) {
        reportInternalError(m_factory, marker_l, pass, e.what(),
            (e.hasLoc())?&e.loc():0);
    } catch (const std::exception &e) {
        reportInternalError(m_factory, marker_l, pass, e.what(), 0);
    } catch (...) {
        reportInternalError(m_factory, marker_l, pass, "unknown exception", 0);
    }
    return symtree;
}

void AstLinker::linkPasses(
        IMarkerListener                         *marker_l,
        const std::vector<ast::IGlobalScope *>  &scopes,
        bool                                    own_scopes,
        ast::IRootSymbolScope                   *&symtree,
        const char                              *&pass) {
    // Every pass reports through this, so the completeness gate at the end
    // knows what has already been said, whichever pass said it.
    MarkerLocationRecorder recorder(marker_l);
    marker_l = &recorder;

    uint64_t build_symtree_s = time_ms();
    pass = "building the symbol tree";
    symtree = TaskBuildSymbolTree(
        m_dmgr,
        m_ast_factory,
        marker_l).build(scopes, own_scopes);
    uint64_t build_symtree_e = time_ms();
    DEBUG("Build symtree: %lldms", (build_symtree_e-build_symtree_s));

    // Now, apply type extension
    uint64_t apply_ext_s = time_ms();
    pass = "applying type extensions";
    TaskApplyTypeExtensions apply_ext(m_dmgr, m_factory, marker_l);
    apply_ext.apply(symtree);
    uint64_t apply_ext_e = time_ms();
    DEBUG("Apply extensions: %lldms", (apply_ext_e-apply_ext_s));

    // Finally, resolve remaining names

    uint64_t resolve_s = time_ms();
    ResolveContext ctxt(m_factory, marker_l, symtree);

    // Which package each extension-contributed member came from. The pass
    // above moved those members into the extended type; this is what lets
    // TaskResolveRefs put their declaring package back in scope while it
    // walks them (LRM 17.2, known-issues CL-N1).
    ctxt.setExtensionDeclScopes(apply_ext.extensionDeclScopes());

    // Super types first, so that resolving a reference to an inherited
    // member does not depend on the base type having been declared in an
    // earlier file than the use. See TaskResolveSuperTypes.
    pass = "resolving super types";
    TaskResolveSuperTypes(&ctxt).resolve(symtree);

    // Then override actions, whose super type is their own name and so has
    // to be looked up in the declaring component's base chain rather than by
    // the ordinary rules. Separate from the pass above because walking more
    // than one level up needs every component's super type already resolved.
    pass = "resolving override actions";
    TaskResolveOverrideActions(&ctxt).resolve(symtree);

    // Between the two on purpose. Super-type references are bound above, so
    // the inheritance graph is readable; TaskResolveRefs below is the pass
    // that walks it. This pass reports the ring, so the user is told which
    // types form it, and marks every type on it (TypeScope.super_cyclic) so
    // that every super-chain walker stops there instead of going round it.
    // See TaskCheckTypeCycles.h.
    pass = "checking for inheritance cycles";
    TaskCheckTypeCycles(&ctxt).check(symtree);

    pass = "resolving references";
    TaskResolveRefs(&ctxt).resolve(symtree);

    // `compile if` conditions, which the builder evaluated and set aside.
    // Bound for tools (find-references, rename); never reported.
    pass = "binding compile-time conditions";
    TaskResolveRefs(&ctxt).resolveCompileConds(symtree);

    // Work deferred from specialization until every reference is bound --
    // sizing sizeof_s<T> when T's members were not yet resolved.
    pass = "running post-resolve actions";
    ctxt.runPostResolveActions();
    uint64_t resolve_e = time_ms();
    DEBUG("Resolve: %lldms", (resolve_e-resolve_s));

    // 21.13.1's member rules. After resolution, because they need every
    // member type bound; before the completeness gate, which has nothing to
    // say about packing.
    pass = "checking packed structs";
    TaskCheckPackedStructs(&ctxt).check(symtree);
    TaskCheckPackedUses(&ctxt).check(symtree);

    // The completeness gate. Resolution is finished, so a type reference that
    // is still unbound is unbound for good -- report it rather than hand a
    // consumer a field with no type. Deliberately last and deliberately
    // structural: it does not know which code path failed to bind a reference,
    // which is what makes it hold for paths that do not exist yet. See
    // TaskCheckRefsResolved.h.
    pass = "checking that references are resolved";
    TaskCheckRefsResolved(&ctxt).check(symtree, 1 /* the bundled stdlib */);
}

ast::IRootSymbolScope *AstLinker::linkOverlay(
        IMarkerListener                         *marker_l,
        ast::IRootSymbolScope                   *base_symtab,
        ast::IGlobalScope                       *overlay,
        bool                                    own_scopes) {
    DEBUG_ENTER("linkOverlay");
    const char *pass = "cloning the base symbol table";
    ast::IRootSymbolScope *root = 0;
    try {
        // First, clone the base symbol table
        root = TaskCloneSymbolScope(
            m_dmgr, m_ast_factory).clone(base_symtab);

        ResolveContext ctxt(m_factory, marker_l, root);

        pass = "applying the overlay";
        TaskApplyOverlay(&ctxt).apply(
            root,
            overlay);

        pass = "resolving overlay references";
        TaskResolveRefsOverlay(&ctxt).resolve(overlay);
        ctxt.runPostResolveActions();
    } catch (const InternalError &e) {
        reportInternalError(m_factory, marker_l, pass, e.what(),
            (e.hasLoc())?&e.loc():0);
    } catch (const std::exception &e) {
        reportInternalError(m_factory, marker_l, pass, e.what(), 0);
    } catch (...) {
        reportInternalError(m_factory, marker_l, pass, "unknown exception", 0);
    }

    DEBUG_LEAVE("linkOverlay");
    return root;
}

dmgr::IDebug *AstLinker::m_dbg = 0;

}
