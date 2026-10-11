/*
 * CelValue.h
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
 * CEL run-time values (lint-core-plan.md C3.1): null, bool, int, double,
 * string, list, map, optional, node, struct, type and error.
 *
 * Nodes and structs are opaque handles here. What a node's fields are, and
 * how to read them, is the reflection table's business (CelNode.h); this
 * header knows nothing about PSS.
 */
#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace pssp {
namespace lint {
namespace cel {

struct Value;
using ValueList = std::vector<Value>;
using ValueMap = std::vector<std::pair<Value, Value>>;   // insertion order

/** An AST node: its reflection class id and the node itself. */
struct NodeRef {
    uint16_t    kind = 0;
    void        *ptr = nullptr;
};

struct Value {
    enum class Kind {
        Null, Bool, Int, Double, String, List, Map, Optional, Node, Struct, Type, Error
    };

    Kind                                kind = Kind::Null;
    bool                                b = false;
    int64_t                             i = 0;      // Int; Struct: the struct index
    double                              d = 0.0;
    // String: the value. Error: the message. Type: the type's name.
    // Null: the name of the unset node field it was read from, if any (D-C6).
    std::string                         s;
    std::shared_ptr<const ValueList>    list;
    std::shared_ptr<const ValueMap>     map;
    std::shared_ptr<const Value>        opt;        // Optional: null for none
    NodeRef                             node;       // Node
    const void                          *st = nullptr;  // Struct: owned by its node

    static Value null() { return Value(); }
    static Value unset(std::string field) { Value r; r.s = std::move(field); return r; }
    static Value boolean(bool v) { Value r; r.kind = Kind::Bool; r.b = v; return r; }
    static Value integer(int64_t v) { Value r; r.kind = Kind::Int; r.i = v; return r; }
    static Value dbl(double v) { Value r; r.kind = Kind::Double; r.d = v; return r; }
    static Value string(std::string v) {
        Value r; r.kind = Kind::String; r.s = std::move(v); return r;
    }
    static Value error(std::string msg) {
        Value r; r.kind = Kind::Error; r.s = std::move(msg); return r;
    }
    static Value mkList(ValueList v) {
        Value r; r.kind = Kind::List;
        r.list = std::make_shared<const ValueList>(std::move(v));
        return r;
    }
    static Value mkMap(ValueMap v) {
        Value r; r.kind = Kind::Map;
        r.map = std::make_shared<const ValueMap>(std::move(v));
        return r;
    }
    static Value none() { Value r; r.kind = Kind::Optional; return r; }
    static Value some(Value v) {
        Value r; r.kind = Kind::Optional;
        r.opt = std::make_shared<const Value>(std::move(v));
        return r;
    }
    static Value mkNode(NodeRef n) { Value r; r.kind = Kind::Node; r.node = n; return r; }
    static Value mkStruct(const void *st, uint16_t type) {
        Value r; r.kind = Kind::Struct; r.st = st; r.i = type; return r;
    }
    static Value type(std::string name) {
        Value r; r.kind = Kind::Type; r.s = std::move(name); return r;
    }

    bool isError() const { return kind == Kind::Error; }
    bool isBool() const { return kind == Kind::Bool; }
    bool isNumeric() const { return kind == Kind::Int || kind == Kind::Double; }
};

/** The CEL name of a value kind: "int", "optional_type", "node", ... */
const char *kindName(Value::Kind k);

/**
 * The CEL type name of a value, as type() returns it and as messages show it:
 * a node's or struct's own class name rather than "node".
 */
std::string typeName(const Value &v);

}
}
}
