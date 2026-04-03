/*
 * ResolveContext.cpp
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
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "AstSymbolTableIterator.h"
#include "ResolveContext.h"


namespace pssp {



ResolveContext::ResolveContext(
    IFactory                *factory,
    IMarkerListener         *marker_l,
    ast::IRootSymbolScope   *root) : 
    m_factory(factory), m_marker_l(marker_l), m_root(root),
    m_specialization_depth(0) {
    m_symtab_it_s.push_back(ISymbolTableIteratorUP(new AstSymbolTableIterator(
        factory->getDebugMgr(),
        factory->getAstFactory(),
        root)));
    m_inbound_refs.resize(root->getUnits().size(), std::unordered_set<int32_t>());
    m_outbound_refs.resize(root->getUnits().size(), std::unordered_set<int32_t>());
}

ResolveContext::~ResolveContext() {

}

ast::IScopeChild *ResolveContext::resolveSymbolPathRef(ast::ISymbolRefPath *path) {
    return TaskResolveSymbolPathRef(m_factory->getDebugMgr(), m_root).resolve(path);
}

void ResolveContext::addRef(int32_t from, int32_t to) {
    std::unordered_map<int32_t,int32_t>::const_iterator it;
    int32_t from_idx = -1;
    int32_t to_idx = -1;
    
    if ((it=m_root->getId2idx().find(from)) != m_root->getId2idx().end()) {
        from_idx = it->second;
    }
    if ((it=m_root->getId2idx().find(to)) != m_root->getId2idx().end()) {
        to_idx = it->second;
    }

    if (from_idx != -1 && to_idx != -1) {
        m_inbound_refs.at(to_idx).insert(from);
        m_outbound_refs.at(from_idx).insert(to);
    }
}

void ResolveContext::addMarker(
        MarkerSeverityE     severity,
        const ast::Location &loc,
        const char          *fmt,
        va_list             ap) {
    char tmp[1024];
    vsnprintf(tmp, sizeof(tmp), fmt, ap);
    IMarkerUP marker(m_factory->mkMarker(
        tmp,
        severity,
        loc));
    m_marker_l->marker(marker.get());
}

void ResolveContext::addMarker(
        MarkerSeverityE     severity,
        const ast::Location &loc,
        const char          *fmt,
        ...) {
    va_list ap;
    va_start(ap, fmt);
    addMarker(severity, loc, fmt, ap);
    va_end(ap);
}

void ResolveContext::addErrorMarker(
        const ast::Location &loc,
        const char          *fmt,
        ...) {
    va_list ap;
    va_start(ap, fmt);
    addMarker(
        MarkerSeverityE::Error,
        loc,
        fmt,
        ap);
    va_end(ap);
}

}
