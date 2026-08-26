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
#include "pssp/impl/TaskIndexTemplateScope.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/ITemplateElem.h"
#include "pssp/ast/ITemplateString.h"

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

bool AstSymbolTableIterator::isTemplateScope(ast::IScopeChild *c) {
    return dynamic_cast<ast::ITemplateString *>(c) != 0 ||
        dynamic_cast<ast::ITemplateElem *>(c) != 0;
}

bool AstSymbolTableIterator::isPlistOf(
        ast::IScopeChild        *outer,
        ast::IScopeChild        *c) {
    // A `<plist>` is pushed so that a type's parameters are in scope, but it
    // gets no path element of its own: the element that follows it is an
    // ElemKind_ParamIdx or ElemKind_ArgIdx, and resolving one of those steps
    // into the plist itself. Emitting the plist as well would step in twice.
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(outer);

    if (ts && ts->getPlist() == c) {
        return true;
    }

    ast::ISymbolFunctionScope *fs = dynamic_cast<ast::ISymbolFunctionScope *>(outer);

    return fs && fs->getPlist() == c;
}

ast::ISymbolRefPath *AstSymbolTableIterator::getScopeSymbolPath(int32_t off) const {
    DEBUG_ENTER("getScopeSymbolPath (off=%d)", off);
    ast::ISymbolRefPath *ret = m_factory->mkSymbolRefPath();
    int32_t n = (int32_t)m_path.size()-off;

    for (int32_t i=0; i<n; i++) {
        if (isTemplateScope(m_scope_s.at(i))) {
            // 4.7.1. A template scope has no child index -- it is not a child
            // of anything in the symbol tree -- so it needs an element of its
            // own. Collapse the whole run of them to one: nested blocks are
            // numbered relative to the same enclosing scope as the string that
            // holds them, and the innermost is the one the symbol was found in.
            int32_t last = i;
            while (last+1 < n && isTemplateScope(m_scope_s.at(last+1))) {
                last++;
            }

            // The nearest enclosing scope that *is* addressable. Everything the
            // path has emitted so far navigates to it, so this is the same
            // scope resolution will be standing in when it reads the element.
            ast::IScopeChild *encl = 0;
            for (int32_t j=i-1; j>=0 && !encl; j--) {
                encl = TaskGetSymbolScope().get(m_scope_s.at(j));
            }

            int32_t idx = (encl)
                ?TaskIndexTemplateScope().index(encl, m_scope_s.at(last))
                :-1;

            ret->getPath().push_back(
                {ast::SymbolRefPathElemKind::ElemKind_TemplateScope, idx});
            DEBUG("Add template-scope %d (idx=%d..%d)", idx, i, last);

            i = last;
        } else if (m_path.at(i).idx >= 0) {
            ret->getPath().push_back(m_path.at(i));
            DEBUG("Add child-idx %d (idx=%d)", m_path.at(i).idx, i);
        } else if (i > 0 && isPlistOf(m_scope_s.at(i-1), m_scope_s.at(i))) {
            DEBUG("NOTE: skip plist at index %d", i);
        } else if (i > 0) {
            // Some other scope with no index. Emitting it is what keeps the
            // path honest: dropping it used to leave a shorter path that still
            // resolved -- against the *enclosing* scope, so a reference came
            // back as whichever unrelated declaration sat at that index. A
            // negative element resolves to nothing instead.
            ret->getPath().push_back(m_path.at(i));
            DEBUG("NOTE: unaddressable scope at index %d", i);
        } else {
            // The root, which is where every path starts. It is the one scope
            // that needs no element at all.
            DEBUG("NOTE: skip root");
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

        // A path can outlive the scope it was built against -- most visibly
        // an import path resolved before the tree it indexes is final. at()
        // then throws, and because nothing here catches it the whole process
        // aborts on what is only a failed lookup. Every caller already
        // handles a null return.
        if (elem.idx < 0 || elem.idx >= (int32_t)scope->getChildren().size()) {
            DEBUG("Index %d out of range for scope %s (%d children)",
                elem.idx, scope->getName().c_str(),
                (int32_t)scope->getChildren().size());
            return 0;
        }

        ast::IScopeChild *next = scope->getChildren().at(elem.idx).get();

        if (i+1 < path->getPath().size()) {
            if (!(scope=dynamic_cast<ast::ISymbolScope *>(next))) {
                DEBUG("Path element %d of %d does not name a symbol scope",
                    i, (int32_t)path->getPath().size());
                return 0;
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
