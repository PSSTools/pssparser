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
#include "pssp/impl/TaskCloneSymbolScope.h"
#include "AstLinker.h"
#include "ResolveContext.h"
#include "TaskApplyOverlay.h"
#include "TaskApplyTypeExtensions.h"
#include "TaskBuildSymbolTree.h"
#include "TaskResolveRefsOverlay.h"
#include "TaskResolveRefs.h"


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

ast::IRootSymbolScope *AstLinker::link(
        IMarkerListener                         *marker_l,
        const std::vector<ast::IGlobalScope *>  &scopes,
        bool                                    own_scopes) {
    uint64_t build_symtree_s = time_ms();
    ast::IRootSymbolScope *symtree = TaskBuildSymbolTree(
        m_dmgr,
        m_ast_factory,
        marker_l).build(scopes, own_scopes);
    uint64_t build_symtree_e = time_ms();
    DEBUG("Build symtree: %lldms", (build_symtree_e-build_symtree_s));

    // Now, apply type extension
    uint64_t apply_ext_s = time_ms();
    TaskApplyTypeExtensions(m_dmgr, m_factory, marker_l).apply(symtree);
    uint64_t apply_ext_e = time_ms();
    DEBUG("Apply extensions: %lldms", (apply_ext_e-apply_ext_s));

    // Finally, resolve remaining names

    uint64_t resolve_s = time_ms();
    ResolveContext ctxt(m_factory, marker_l, symtree);
    TaskResolveRefs(&ctxt).resolve(symtree);
    uint64_t resolve_e = time_ms();
    DEBUG("Resolve: %lldms", (resolve_e-resolve_s));

    return symtree;
}

ast::IRootSymbolScope *AstLinker::linkOverlay(
        IMarkerListener                         *marker_l,
        ast::IRootSymbolScope                   *base_symtab,
        ast::IGlobalScope                       *overlay,
        bool                                    own_scopes) {
    DEBUG_ENTER("linkOverlay");
    // First, clone the base symbol table
    ast::IRootSymbolScope *root = TaskCloneSymbolScope(
        m_dmgr, m_ast_factory).clone(base_symtab);

    ResolveContext ctxt(m_factory, marker_l, root);

    TaskApplyOverlay(m_dmgr, m_ast_factory).apply(
        root,
        overlay);

    TaskResolveRefsOverlay(&ctxt).resolve(overlay);
    /*
     */

    // Match overlay with original files base fileId

    // Apply the overlay files to the newly-cloned root,
    // replacing symbol-table references to files whose
    // content will be overlaid

    // Now, resolve symbols just in the overlay files

    DEBUG_LEAVE("linkOverlay");
    return root;
}

dmgr::IDebug *AstLinker::m_dbg = 0;

}
