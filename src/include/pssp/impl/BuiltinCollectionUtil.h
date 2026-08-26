/**
 * BuiltinCollectionUtil.h
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
 */
#pragma once
#include <string>
#include "pssp/ast/ISymbolScope.h"
#include "pssp/ast/ITypeScope.h"

namespace pssp {

/**
 * Recognizing the built-in collections -- without guessing from a name.
 *
 * These were identified by string tests on the *scope* name, in three places
 * and three different ways: an exact match on the written type name, a prefix
 * match (``n.rfind("array", 0) == 0``), and a prefix match on a
 * specialization's name (``"array<"``).
 *
 * A prefix match is wrong for an ordinary reason: user type names begin with
 * those letters all the time. ``setup_s``, ``map_cfg_s`` and ``array_of_s``
 * were all treated as collections, so ``setup_s.size()`` was accepted on a
 * plain struct with no ``size`` member anywhere.
 *
 * The name alone cannot decide it in any case, because a user may declare
 * their own ``array`` in their own package. What separates the built-ins is
 * where they are declared: ``BuiltinsFactory`` builds them into a global scope
 * with ``fileid == -1``, and every declaration that came from a source file
 * has a real file id. So the test is the declared name *and* the absence of a
 * file -- which is also why it must be applied to the **declaration**
 * (``array``) rather than to a specialization's scope name (``array<>``).
 */
enum class CollectionKind {
    None,
    Array,
    List,
    Set,
    Map
};

static inline CollectionKind builtinCollectionKind(ast::ITypeScope *ts) {
    if (!ts || !ts->getName()) {
        return CollectionKind::None;
    }
    // A declaration with a file behind it is the user's, whatever it is called.
    if (ts->getLocation().fileid != -1) {
        return CollectionKind::None;
    }
    const std::string &name = ts->getName()->getId();
    if (name == "array") {
        return CollectionKind::Array;
    } else if (name == "list") {
        return CollectionKind::List;
    } else if (name == "set") {
        return CollectionKind::Set;
    } else if (name == "map") {
        return CollectionKind::Map;
    }
    return CollectionKind::None;
}

static inline CollectionKind builtinCollectionKind(ast::ISymbolScope *s) {
    return (s)?builtinCollectionKind(
        dynamic_cast<ast::ITypeScope *>(s->getTarget())):CollectionKind::None;
}

/**
 * The template parameter a subscript yields, or -1 if the collection cannot
 * be subscripted.
 *
 * ``map<K,V>`` yields its **value** -- the second parameter. ``set<T>`` is not
 * subscriptable at all.
 */
static inline int32_t collectionElemParam(CollectionKind k) {
    switch (k) {
        case CollectionKind::Array:
        case CollectionKind::List:
            return 0;
        case CollectionKind::Map:
            return 1;
        default:
            return -1;
    }
}

}
