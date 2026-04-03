/*
 * AstSymbolTableIterator.cpp
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
#include "AstSymbolTableIterator.h"
#include "TaskGetItemIndex.h"
#include "TaskGetSymbolScope.h"

namespace pssp {




AstSymbolTableIterator::AstSymbolTableIterator(
    dmgr::IDebugMgr         *dmgr,
    ast::IFactory           *factory,
    ast::ISymbolScope       *root) : m_factory(factory) {
    DEBUG_INIT("AstSymbolTableIterator", dmgr);
    int32_t idx = TaskGetItemIndex().get(root);
    DEBUG("AstSymbolTableIterator: idx=%d", idx);
    m_scope_s.push_back(root);
    m_path.push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, idx});
}

AstSymbolTableIterator::AstSymbolTableIterator(
    const AstSymbolTableIterator &other) : 
    m_factory(other.m_factory),
    m_path(other.m_path.begin(), other.m_path.end()),
    m_scope_s(other.m_scope_s.begin(), other.m_scope_s.end()) {

    if (m_scope_s.size() == 0) {
        fprintf(stdout, "Error: initial scope-stack size is 0\n");
    }

}

AstSymbolTableIterator::~AstSymbolTableIterator() {

}

int32_t AstSymbolTableIterator::findLocalSymbol(const std::string &name) {
    DEBUG_ENTER("findLocalSymbol %s", name.c_str());
    ast::ISymbolScope *ss = getSymScopeBack();
    std::unordered_map<std::string,int32_t>::const_iterator it =
        ss->getSymtab().find(name);

    if (it != ss->getSymtab().end()) {
        DEBUG_LEAVE("findLocalSymbol %s - success", name.c_str());
        return it->second;
    } else {
        DEBUG_LEAVE("findLocalSymbol %s - fail", name.c_str());
        return -1;
    }
}

ast::ISymbolRefPath *AstSymbolTableIterator::findLocalSymbolPath(const std::string &name) {
    int32_t idx = findLocalSymbol(name);

    if (idx != -1) {
        ast::ISymbolRefPath *ret = m_factory->mkSymbolRefPath();
        ret->getPath().insert(
            ret->getPath().begin(),
            m_path.begin(), 
            m_path.end());
        ret->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, idx});
        return ret;
    } else {
        return 0;
    }
}

ast::ISymbolRefPath *AstSymbolTableIterator::getScopeSymbolPath(int32_t off) const {
    DEBUG_ENTER("getScopeSymbolPath (off=%d)", off);
    ast::ISymbolRefPath *ret = m_factory->mkSymbolRefPath();

    for (int32_t i=0; i<(m_path.size()-off); i++) {
        if (m_path.at(i).idx >= 0) {
            ret->getPath().push_back(m_path.at(i));
            DEBUG("Add child-idx %d (idx=%d)", m_path.at(i).idx, i);
        } else {
            DEBUG("NOTE: skip index %d with child-idx %d", i, m_path.at(i).idx);
        }
    }

    DEBUG_LEAVE("getScopeSymbolPath");
    return ret;
}

ast::ISymbolScope *AstSymbolTableIterator::getRootScope() const {
    return getSymScopeFront();
}

ast::ISymbolScope *AstSymbolTableIterator::getScope(int32_t off) {
    return getSymScopeBack(off);
}

ast::IScopeChild *AstSymbolTableIterator::getScopeChild(int32_t idx) {
    return getSymScopeBack()->getChildren().at(idx).get();
}

ast::IScopeChild *AstSymbolTableIterator::resolveAbsPath(const ast::ISymbolRefPath *path) {
    ast::IScopeChild *ret = 0;

    ast::ISymbolScope *scope = getSymScopeFront();
    for (uint32_t i=0; i<path->getPath().size(); i++) {
        DEBUG("Scope: %s @ %d", scope->getName().c_str(), path->getPath().at(i));
        const ast::SymbolRefPathElem &elem = path->getPath().at(i);
        ast::IScopeChild *next = scope->getChildren().at(elem.idx).get();

        if (i+1 < path->getPath().size()) {
            if (!(scope=dynamic_cast<ast::ISymbolScope *>(next))) {
                fprintf(stdout, "i=%d size=%d and target isn't a symbol scope (next=%p)\n",
                    i, path->getPath().size(), next);
                break;
            }
        } else {
            ret = next;
        }
    }

    return ret;
}

int32_t AstSymbolTableIterator::pushNamedScope(const std::string &name) {
    DEBUG_ENTER("pushNamedScope %s", name.c_str());
    ast::ISymbolScope *ss = getSymScopeBack();
    std::unordered_map<std::string,int32_t>::const_iterator it =
        ss->getSymtab().find(name);

    if (it != ss->getSymtab().end()) {
        ast::ISymbolScope *scope = dynamic_cast<ast::ISymbolScope *>(
            ss->getChildren().at(it->second).get());
        if (scope) {
            m_scope_s.push_back(scope);
            m_path.push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second});
            DEBUG_LEAVE("pushNamedScope %s - success sz=%d", 
                name.c_str(), m_scope_s.size());
            return it->second;
        } else {
            DEBUG_LEAVE("pushNamedScope %s - fail", name.c_str());
            return -1;
        }
    } else {
        DEBUG_LEAVE("pushNamedScope %s - fail", name.c_str());
        return -1;
    }
}

void AstSymbolTableIterator::pushScope(
        ast::IScopeChild            *s,
        ast::SymbolRefPathElemKind  kind) {
    DEBUG_ENTER("pushScope %s %d %p",
        (dynamic_cast<ast::ISymbolScope *>(s))?dynamic_cast<ast::ISymbolScope *>(s)->getName().c_str():"<unknown>",
        (dynamic_cast<ast::ISymbolScope *>(s))?dynamic_cast<ast::ISymbolScope *>(s)->getSymtab().size():-1,
        s);
    int32_t idx = (dynamic_cast<ast::ISymbolScope *>(s))?dynamic_cast<ast::ISymbolScope *>(s)->getId():-1;
    int32_t idx1 = TaskGetItemIndex().get(s);
    if (!dynamic_cast<ast::ISymbolScope *>(s)) {
        DEBUG("Not a symbol scope");
    }
    if (idx != idx1) {
        DEBUG("negative (idx=%d idx1=%d)", idx, idx1);
    } else if (idx1 == -1) {
        DEBUG("Scope results in negative idx");
    }
    m_scope_s.push_back(s);
    m_path.push_back({kind, idx1});
    DEBUG_LEAVE("pushScope");
}

void AstSymbolTableIterator::popScope() {
    DEBUG_ENTER("popScope %d", m_scope_s.size());
    if (m_scope_s.size() > 0) {
        m_scope_s.pop_back();
        m_path.pop_back();
        /*
        if (m_scope_s.size() == 0) {
            FATAL("emptied scope stack");
        }
         */
    } else {
        DEBUG_FATAL("attempt to pop an empty stack");
    }
    DEBUG_LEAVE("popScope - sz=%d", m_scope_s.size());
}

bool AstSymbolTableIterator::hasScopes() {
    return m_scope_s.size() > 0;
}

ISymbolTableIterator *AstSymbolTableIterator::clone() const {
    return new AstSymbolTableIterator(*this);
}

ast::ISymbolScope *AstSymbolTableIterator::getSymScopeBack() {
    DEBUG_ENTER("getSymScopeBack");
    // Walk through the scope backwards and return the 
    // first symbol scope
    ast::ISymbolScope *ss = 0;

    for (int32_t i=m_scope_s.size()-1; i>=0; i--) {
        if ((ss=TaskGetSymbolScope().get(m_scope_s.at(i)))) {
            break;
        } else {
            DEBUG("Remove scope @ %d", i);
            m_scope_s.erase(m_scope_s.begin()+i);
            m_path.erase(m_path.begin()+i);
        }
    }

    DEBUG_LEAVE("getSymScopeBack %p", ss);
    return ss;
}

// ast::ISymbolScope *AstSymbolTableIterator::getSymScopeBack() const {
//     // Walk through the scope backwards and return the 
//     // first symbol scope
//     ast::ISymbolScope *ss = 0;

//     for (int32_t i=m_scope_s.size()-1; i>=0; i--) {
//         if ((ss=TaskGetSymbolScope().get(m_scope_s.at(i)))) {
//             break;
//         }
//     }

//     return ss;
// }

ast::ISymbolScope *AstSymbolTableIterator::getSymScopeBack(int32_t off) {
    // Walk through the scope backwards and return the 
    // first symbol scope
    ast::ISymbolScope *ss = 0;
    DEBUG_ENTER("getSymScopeBack %d", off);

    for (int32_t i=m_scope_s.size()-1; i>=0; i--) {
        if ((ss=TaskGetSymbolScope().get(m_scope_s.at(i)))) {
            if (!off) {
                break;
            } else {
                off--;
                ss = 0;
            }
        } else {
            DEBUG("Remove scope @ %d", i);
            m_scope_s.erase(m_scope_s.begin()+i);
            m_path.erase(m_path.begin()+i);
        }
    }

    DEBUG_LEAVE("getSymScopeBack %p", ss);
    return ss;
}


ast::ISymbolScope *AstSymbolTableIterator::getSymScopeFront() const {
    // Walk through the scope backwards and return the 
    // first symbol scope
    ast::ISymbolScope *ss = 0;

    for (std::vector<ast::IScopeChild *>::const_iterator
        it=m_scope_s.begin();
        it!=m_scope_s.end(); it++) {
        if ((ss=TaskGetSymbolScope().get(*it))) {
            break;
        }
    }

    return ss;
}

dmgr::IDebug *AstSymbolTableIterator::m_dbg = 0;

}
