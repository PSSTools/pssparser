/*
 * CelType.cpp
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
#include <cctype>
#include <stdexcept>
#include "CelNode.h"
#include "CelType.h"

namespace pssp {
namespace lint {
namespace cel {

namespace {

class TypeParser {
public:
    explicit TypeParser(const std::string &text) : m_text(text), m_pos(0) { }

    Type parseAll() {
        Type t = parseType();
        skipSpace();
        if (m_pos != m_text.size()) {
            fail("trailing text");
        }
        return t;
    }

private:
    Type parseType() {
        std::string name = ident();
        Type t;
        if (name == "bool") {
            t.kind = Type::Kind::Bool;
        } else if (name == "int") {
            t.kind = Type::Kind::Int;
        } else if (name == "double") {
            t.kind = Type::Kind::Double;
        } else if (name == "string") {
            t.kind = Type::Kind::String;
        } else if (name == "null_type") {
            t.kind = Type::Kind::Null;
        } else if (name == "type") {
            t.kind = Type::Kind::TypeType;
        } else if (name == "node") {
            t.kind = Type::Kind::Node;
        } else if (name == "list" || name == "optional") {
            t.kind = (name == "list") ? Type::Kind::List : Type::Kind::Optional;
            expect('(');
            t.args.push_back(parseType());
            expect(')');
        } else if (name == "map") {
            t.kind = Type::Kind::Map;
            expect('(');
            t.args.push_back(parseType());
            expect(',');
            t.args.push_back(parseType());
            expect(')');
        } else if (name.size() == 1 && std::isupper(static_cast<unsigned char>(name[0]))) {
            t.kind = Type::Kind::Param;
            t.param = name;
        } else if (lookupClass(name, t.cls)) {
            t.kind = Type::Kind::Node;
        } else if (lookupStruct(name, t.cls)) {
            t.kind = Type::Kind::Struct;
        } else {
            fail("unknown type '" + name + "'");
        }
        return t;
    }

    std::string ident() {
        skipSpace();
        size_t b = m_pos;
        while (m_pos < m_text.size()
                && (std::isalnum(static_cast<unsigned char>(m_text[m_pos])) || m_text[m_pos] == '_')) {
            m_pos++;
        }
        if (b == m_pos) {
            fail("expected a type");
        }
        return m_text.substr(b, m_pos - b);
    }

    void expect(char c) {
        skipSpace();
        if (m_pos >= m_text.size() || m_text[m_pos] != c) {
            fail(std::string("expected '") + c + "'");
        }
        m_pos++;
    }

    void skipSpace() {
        while (m_pos < m_text.size() && m_text[m_pos] == ' ') {
            m_pos++;
        }
    }

    [[noreturn]] void fail(const std::string &msg) {
        throw std::invalid_argument("type '" + m_text + "': " + msg);
    }

    const std::string   &m_text;
    size_t              m_pos;
};

}

Type Type::parse(const std::string &text) {
    return TypeParser(text).parseAll();
}

std::string Type::str() const {
    switch (kind) {
        case Kind::Null: return "null_type";
        case Kind::Bool: return "bool";
        case Kind::Int: return "int";
        case Kind::Double: return "double";
        case Kind::String: return "string";
        case Kind::TypeType: return "type";
        case Kind::Node: return cls ? nodeClassName(cls) : "node";
        case Kind::Struct: return structName(cls);
        case Kind::Param: return (param.empty() || param[0] == '%') ? "?" : param;
        case Kind::Error: return "error";
        case Kind::List: return "list(" + args[0].str() + ")";
        case Kind::Optional: return "optional(" + args[0].str() + ")";
        case Kind::Map: return "map(" + args[0].str() + ", " + args[1].str() + ")";
    }
    return "?";
}

bool Type::admits(const Value &v) const {
    using K = Value::Kind;
    switch (kind) {
        case Kind::Param: return !v.isError();
        case Kind::Null: return v.kind == K::Null;
        case Kind::Bool: return v.kind == K::Bool;
        case Kind::Int: return v.kind == K::Int;
        case Kind::Double: return v.kind == K::Double;
        case Kind::String: return v.kind == K::String;
        case Kind::TypeType: return v.kind == K::Type;
        case Kind::Node: return v.kind == K::Node && (!cls || isSubclass(v.node.kind, cls));
        case Kind::Struct: return v.kind == K::Struct && v.i == cls;
        case Kind::Error: return false;
        case Kind::List: return v.kind == K::List;
        case Kind::Map: return v.kind == K::Map;
        case Kind::Optional: return v.kind == K::Optional;
    }
    return false;
}

}
}
}
