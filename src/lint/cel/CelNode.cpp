/*
 * CelNode.cpp
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
#include <unordered_map>
#include <vector>
#include "Reflect.h"
#include "CelNode.h"
#include "../run/Walker.h"

namespace pssp {
namespace lint {
namespace cel {

namespace rf = pssp::ast::reflect;

namespace {

// Field name -> index into rf::fields, per class, inherited fields included.
// Built once; C3.3 resolves names when a rule is checked, so this lookup is
// off the hot path from then on.
class FieldIndex {
public:
    FieldIndex() : m_byClass(rf::NumClasses + 1) {
        for (uint16_t k=1; k<=rf::NumClasses; k++) {
            for (uint16_t c=k; c; c=rf::classes[c].super) {
                const rf::ClassInfo &ci = rf::classes[c];
                for (uint16_t f=ci.firstField; f<ci.firstField+ci.numFields; f++) {
                    // A redeclared name resolves to the most-derived field.
                    m_byClass[k].emplace(rf::fields[f].name, f);
                }
            }
        }
        for (uint16_t k=1; k<=rf::NumClasses; k++) {
            m_types.emplace(rf::classes[k].name, Value::type(rf::classes[k].name));
            m_classes.emplace(rf::classes[k].name, k);
        }
        for (uint16_t s=0; s<rf::numStructs; s++) {
            m_types.emplace(rf::structs[s].name, Value::type(rf::structs[s].name));
            m_structs.emplace(rf::structs[s].name, s);
        }
        for (uint16_t e=0; e<rf::numEnums; e++) {
            m_types.emplace(rf::enums[e].name, Value::type(rf::enums[e].name));
            m_enums.emplace(rf::enums[e].name, e);
        }
    }

    const rf::FieldInfo *field(uint16_t kind, const std::string &name) const {
        if (kind == 0 || kind > rf::NumClasses) {
            return nullptr;
        }
        auto it = m_byClass[kind].find(name);
        return (it == m_byClass[kind].end()) ? nullptr : &rf::fields[it->second];
    }

    const Value *type(const std::string &name) const {
        auto it = m_types.find(name);
        return (it == m_types.end()) ? nullptr : &it->second;
    }

    const rf::EnumInfo *enumInfo(const std::string &name) const {
        auto it = m_enums.find(name);
        return (it == m_enums.end()) ? nullptr : &rf::enums[it->second];
    }

    bool cls(const std::string &name, uint16_t &out) const {
        auto it = m_classes.find(name);
        if (it == m_classes.end()) {
            return false;
        }
        out = it->second;
        return true;
    }

    bool st(const std::string &name, uint16_t &out) const {
        auto it = m_structs.find(name);
        if (it == m_structs.end()) {
            return false;
        }
        out = it->second;
        return true;
    }

    static const FieldIndex &get() {
        static const FieldIndex inst;
        return inst;
    }

private:
    std::vector<std::unordered_map<std::string, uint16_t>>  m_byClass;
    std::unordered_map<std::string, Value>                  m_types;
    std::unordered_map<std::string, uint16_t>               m_enums;
    std::unordered_map<std::string, uint16_t>               m_classes;
    std::unordered_map<std::string, uint16_t>               m_structs;
};

struct RecordTable {
    std::vector<RecordInfo>                     infos;
    std::unordered_map<std::string, uint16_t>   byName;
};

RecordTable &recordTable() {
    static RecordTable t;
    return t;
}

// The index of member `name` of a record, or -1.
int32_t recordMember(const RecordInfo &ri, const std::string &name) {
    for (size_t i=0; i<ri.members.size(); i++) {
        if (ri.members[i].name == name) {
            return static_cast<int32_t>(i);
        }
    }
    return -1;
}

// A record value's member `index`, if the value is a record holding it.
const Value *recordAt(const Value &obj, int32_t index) {
    const RecordInfo *ri = recordInfo(static_cast<uint16_t>(obj.i));
    if (!ri || !obj.list || index < 0 || static_cast<size_t>(index) >= obj.list->size()) {
        return nullptr;
    }
    return &(*obj.list)[index];
}

const rf::StructFieldInfo *structMember(uint16_t type, const std::string &name) {
    if (type >= rf::numStructs) {
        return nullptr;
    }
    const rf::StructInfo &si = rf::structs[type];
    for (uint16_t i=0; i<si.numFields; i++) {
        if (name == si.fields[i].name) {
            return &si.fields[i];
        }
    }
    return nullptr;
}

NodeRef toRef(const rf::Node &n) {
    NodeRef r;
    r.kind = n.kind;
    r.ptr = n.ptr;
    return r;
}

// One reflected value (a field, a list element, a struct member) as a CEL
// value. `field` names it, for the unset-node marker.
Value convert(const rf::Value &v, const char *field, uint64_t &elems) {
    using K = rf::Value::Kind;
    switch (v.kind) {
        case K::Absent: return Value::null();
        case K::Bool: return Value::boolean(v.b);
        case K::Int: case K::Enum: case K::Flags: return Value::integer(v.i);
        case K::Uint:
            if (v.u > static_cast<uint64_t>(INT64_MAX)) {
                return Value::error(std::string("field '") + field + "' is out of the int range");
            }
            return Value::integer(static_cast<int64_t>(v.u));
        case K::Float: return Value::dbl(v.d);
        case K::String: return Value::string(v.s ? *v.s : std::string());
        case K::Struct: return Value::mkStruct(v.st, v.type);
        case K::Node:
            return v.n ? Value::mkNode(toRef(v.n)) : Value::unset(field);
        case K::List: {
            uint32_t n = rf::listSize(v);
            ValueList out;
            out.reserve(n);
            for (uint32_t i=0; i<n; i++) {
                out.push_back(convert(rf::listAt(v, i), field, elems));
            }
            elems += n;
            return Value::mkList(std::move(out));
        }
    }
    return Value::null();
}

Value readList(const rf::FieldInfo &f, const rf::Node &n, uint64_t &elems) {
    uint32_t sz = f.size(n.ptr, n.kind);
    ValueList out;
    out.reserve(sz);
    for (uint32_t i=0; i<sz; i++) {
        rf::Value v = f.at(n.ptr, n.kind, i);
        if (v.kind == rf::Value::Kind::Node && (v.borrowed || run::Walker::implicit(v.n))) {
            // Listed here, owned elsewhere, or not in the source: as for
            // children() (Walker.h).
            continue;
        } else if (v.kind == rf::Value::Kind::Node && !v.n) {
            out.push_back(Value::null());
        } else {
            out.push_back(convert(v, f.name, elems));
        }
    }
    elems += sz;
    return Value::mkList(std::move(out));
}

bool present(const rf::Value &v) {
    using K = rf::Value::Kind;
    switch (v.kind) {
        case K::Absent: return false;
        case K::Bool: return v.b;
        case K::Int: case K::Enum: case K::Flags: return v.i != 0;
        case K::Uint: return v.u != 0;
        case K::Float: return v.d != 0.0;
        case K::String: return v.s && !v.s->empty();
        case K::Struct: return true;
        case K::Node: return static_cast<bool>(v.n);
        case K::List: return rf::listSize(v) != 0;
    }
    return false;
}

rf::Node fromRef(const NodeRef &r) {
    rf::Node n;
    n.kind = r.kind;
    n.ptr = r.ptr;
    return n;
}

}

namespace {

Value readNodeField(const rf::FieldInfo &f, const NodeRef &ref, uint64_t &elems) {
    rf::Node n = fromRef(ref);
    if (f.type == rf::FieldType::List) {
        return readList(f, n, elems);
    } else if (f.get) {
        return convert(f.get(n.ptr, n.kind), f.name, elems);
    }
    return Value::error(std::string("field '") + f.name + "' of '" + nodeClassName(ref.kind)
        + "' cannot be read in pss-rules");
}

bool nodeFieldSet(const rf::FieldInfo &f, const NodeRef &ref) {
    rf::Node n = fromRef(ref);
    if (f.type == rf::FieldType::List) {
        return f.size(n.ptr, n.kind) != 0;
    } else if (f.get) {
        return present(f.get(n.ptr, n.kind));
    }
    return false;
}

// What a reflected field or element type is in CEL. False when pss-rules has
// no type for it.
bool celType(rf::FieldType t, uint16_t target, Type &out) {
    using F = rf::FieldType;
    switch (t) {
        case F::Bool: out = Type(Type::Kind::Bool); return true;
        case F::I8: case F::U8: case F::I16: case F::U16: case F::I32: case F::U32:
        case F::I64: case F::U64:
            out = Type(Type::Kind::Int); return true;
        case F::Enum: case F::Flags:
            // An int, tagged with its enum (CelType.h), so the checker can
            // tell a flags word from a number (has_flag, C6.8).
            out = Type(Type::Kind::Int);
            out.param = (target < rf::numEnums) ? rf::enums[target].name : "";
            return true;
        case F::F32: case F::F64: out = Type(Type::Kind::Double); return true;
        case F::String: out = Type(Type::Kind::String); return true;
        case F::Struct: out = Type::structType(target); return true;
        case F::Node: out = Type::node(target); return true;
        case F::List: case F::Map: return false;
    }
    return false;
}

}

bool readField(const Value &obj, const std::string &name, Value &out, uint64_t &elems) {
    elems = 0;
    if (const RecordInfo *ri = (obj.kind == Value::Kind::Struct) ?
            recordInfo(static_cast<uint16_t>(obj.i)) : nullptr) {
        const Value *m = recordAt(obj, recordMember(*ri, name));
        if (!m) {
            return false;
        }
        out = *m;
        return true;
    }
    if (obj.kind == Value::Kind::Struct) {
        const rf::StructFieldInfo *m = structMember(static_cast<uint16_t>(obj.i), name);
        if (!m) {
            return false;
        }
        out = convert(m->get(obj.st), m->name, elems);
        return true;
    }
    if (obj.kind != Value::Kind::Node) {
        return false;
    }
    const rf::FieldInfo *f = FieldIndex::get().field(obj.node.kind, name);
    if (!f) {
        return false;
    }
    out = readNodeField(*f, obj.node, elems);
    return true;
}

bool hasField(const Value &obj, const std::string &name, bool &isSet) {
    if (const RecordInfo *ri = (obj.kind == Value::Kind::Struct) ?
            recordInfo(static_cast<uint16_t>(obj.i)) : nullptr) {
        const Value *m = recordAt(obj, recordMember(*ri, name));
        if (!m) {
            return false;
        }
        isSet = (m->kind != Value::Kind::Null);
        return true;
    }
    if (obj.kind == Value::Kind::Struct) {
        const rf::StructFieldInfo *m = structMember(static_cast<uint16_t>(obj.i), name);
        if (!m) {
            return false;
        }
        isSet = present(m->get(obj.st));
        return true;
    }
    if (obj.kind != Value::Kind::Node) {
        return false;
    }
    const rf::FieldInfo *f = FieldIndex::get().field(obj.node.kind, name);
    if (!f) {
        return false;
    }
    isSet = nodeFieldSet(*f, obj.node);
    return true;
}

namespace {

// Whether field `index` belongs to the value's class or struct. The checker
// resolves a field on the class it can prove, but CEL's `&&` evaluates its
// right side when the left is an error, so `type(x) == K && x.f` can read f
// of an x that is not a K: never trust the index without this.
bool fieldAtValid(const Value &obj, int32_t index) {
    if (obj.kind == Value::Kind::Struct && recordInfo(static_cast<uint16_t>(obj.i))) {
        return recordAt(obj, index) != nullptr;
    }
    if (obj.kind == Value::Kind::Struct) {
        return obj.i >= 0 && obj.i < rf::numStructs
            && index < rf::structs[obj.i].numFields;
    }
    return obj.kind == Value::Kind::Node && index < rf::numFields
        && isSubclass(obj.node.kind, rf::fields[index].owner);
}

}

bool readFieldAt(const Value &obj, int32_t index, Value &out, uint64_t &elems) {
    elems = 0;
    if (!fieldAtValid(obj, index)) {
        return false;
    }
    if (const Value *m = (obj.kind == Value::Kind::Struct) ? recordAt(obj, index) : nullptr) {
        out = *m;
    } else if (obj.kind == Value::Kind::Struct) {
        const rf::StructFieldInfo &m = rf::structs[obj.i].fields[index];
        out = convert(m.get(obj.st), m.name, elems);
    } else {
        out = readNodeField(rf::fields[index], obj.node, elems);
    }
    return true;
}

bool hasFieldAt(const Value &obj, int32_t index, bool &isSet) {
    if (!fieldAtValid(obj, index)) {
        return false;
    }
    if (const Value *m = (obj.kind == Value::Kind::Struct) ? recordAt(obj, index) : nullptr) {
        isSet = (m->kind != Value::Kind::Null);
    } else if (obj.kind == Value::Kind::Struct) {
        isSet = present(rf::structs[obj.i].fields[index].get(obj.st));
    } else {
        isSet = nodeFieldSet(rf::fields[index], obj.node);
    }
    return true;
}

bool nodeFieldType(uint16_t cls, const std::string &name, FieldRef &out) {
    const rf::FieldInfo *f = FieldIndex::get().field(cls, name);
    if (!f) {
        return false;
    }
    out.index = static_cast<int32_t>(f - rf::fields);
    out.error.clear();
    bool ok;
    if (f->type == rf::FieldType::List) {
        Type elem;
        ok = celType(f->elem, f->target, elem);
        out.type = Type::list(elem);
    } else {
        ok = celType(f->type, f->target, out.type) && f->get;
    }
    if (!ok) {
        out.error = std::string("field '") + name + "' of '" + nodeClassName(cls)
            + "' cannot be read in pss-rules";
    }
    return true;
}

std::vector<std::string> derivedFieldClasses(uint16_t cls, const std::string &name) {
    std::vector<std::string> out;
    for (uint16_t k=1; k<=rf::NumClasses; k++) {
        FieldRef f;
        if ((cls && !isSubclass(k, cls)) || !nodeFieldType(k, name, f)) {
            continue;
        }
        uint16_t super = rf::classes[k].super;
        if (super && super != cls && nodeFieldType(super, name, f)) {
            continue;       // inherited: its base is named instead
        }
        out.push_back(rf::classes[k].name);
    }
    return out;
}

bool structFieldType(uint16_t st, const std::string &name, FieldRef &out) {
    if (const RecordInfo *ri = recordInfo(st)) {
        int32_t i = recordMember(*ri, name);
        if (i < 0) {
            return false;
        }
        out.index = i;
        out.type = ri->members[i].type;
        out.error.clear();
        return true;
    }
    if (st >= rf::numStructs) {
        return false;
    }
    const rf::StructInfo &si = rf::structs[st];
    for (uint16_t i=0; i<si.numFields; i++) {
        if (name == si.fields[i].name) {
            out.index = i;
            out.error.clear();
            if (!celType(si.fields[i].type, si.fields[i].target, out.type)) {
                out.error = "member '" + name + "' of '" + si.name + "' cannot be read in pss-rules";
            }
            return true;
        }
    }
    return false;
}

bool lookupClass(const std::string &name, uint16_t &cls) {
    return FieldIndex::get().cls(name, cls);
}

bool lookupStruct(const std::string &name, uint16_t &st) {
    if (FieldIndex::get().st(name, st)) {
        return true;
    }
    const RecordTable &t = recordTable();
    auto it = t.byName.find(name);
    if (it == t.byName.end()) {
        return false;
    }
    st = it->second;
    return true;
}

bool isEnum(const std::string &name) {
    return FieldIndex::get().enumInfo(name) != nullptr;
}

bool isFlagsEnum(const std::string &name) {
    const rf::EnumInfo *ei = FieldIndex::get().enumInfo(name);
    return ei && ei->flags;
}

bool splitTypePath(const std::string &path, std::vector<std::string> &segs, bool &global,
        std::string &why) {
    segs.clear();
    global = (path.compare(0, 2, "::") == 0);
    size_t i = global ? 2 : 0;
    while (true) {
        size_t b = i;
        while (i < path.size() && (std::isalnum(static_cast<unsigned char>(path[i]))
                || path[i] == '_')) {
            i++;
        }
        bool ident = (i > b && !std::isdigit(static_cast<unsigned char>(path[b])));
        if (ident) {
            segs.push_back(path.substr(b, i - b));
            if (i == path.size()) {
                return true;
            }
        }
        if (!ident || path.compare(i, 2, "::") != 0) {
            why = (i < path.size() && path[i] == '<') ?
                "write the generic's name without template arguments; it matches every "
                "specialization" :
                "write it as 'pkg::name', or '::name' for the global package";
            return false;
        }
        i += 2;
    }
}

bool isSubclass(uint16_t k, uint16_t base) {
    for (; k && k <= rf::NumClasses; k=rf::classes[k].super) {
        if (k == base) {
            return true;
        }
    }
    return false;
}

uint16_t commonBase(uint16_t a, uint16_t b) {
    if (!a || !b) {
        return 0;
    }
    for (uint16_t c=a; c; c=rf::classes[c].super) {
        if (isSubclass(b, c)) {
            return c;
        }
    }
    return 0;
}

const char *nodeClassName(uint16_t kind) {
    return (kind && kind <= rf::NumClasses) ? rf::classes[kind].name : "node";
}

const char *structName(uint16_t type) {
    if (const RecordInfo *ri = recordInfo(type)) {
        return ri->name.c_str();
    }
    return (type < rf::numStructs) ? rf::structs[type].name : "struct";
}

bool lookupType(const std::string &name, Value &out) {
    const Value *t = FieldIndex::get().type(name);
    if (t) {
        out = *t;
        return true;
    }
    if (recordTable().byName.count(name)) {
        out = Value::type(name);
        return true;
    }
    return false;
}

bool enumConstant(const std::string &type, const std::string &member, int64_t &out) {
    const rf::EnumInfo *ei = FieldIndex::get().enumInfo(type);
    if (!ei) {
        return false;
    }
    for (uint16_t i=0; i<ei->numValues; i++) {
        if (member == ei->values[i]) {
            // Flags enums are bit masks (FieldAttr::Rand == 1 << 2); plain
            // enums count from 0, as the generated C++ enums do.
            out = ei->flags ? (int64_t(1) << i) : int64_t(i);
            return true;
        }
    }
    return false;
}

bool structEquals(const Value &a, const Value &b) {
    if (a.i != b.i) {
        return false;
    }
    if (a.st == b.st) {
        return true;
    }
    uint16_t t = static_cast<uint16_t>(a.i);
    if (t >= rf::numStructs) {
        return false;
    }
    const rf::StructInfo &si = rf::structs[t];
    for (uint16_t i=0; i<si.numFields; i++) {
        rf::Value x = si.fields[i].get(a.st), y = si.fields[i].get(b.st);
        if (x.kind != y.kind) {
            return false;
        }
        if (x.kind == rf::Value::Kind::Uint ? (x.u != y.u)
                : x.kind == rf::Value::Kind::Float ? (x.d != y.d)
                : x.kind == rf::Value::Kind::Bool ? (x.b != y.b)
                : (x.i != y.i)) {
            return false;
        }
    }
    return true;
}

uint16_t defineRecord(const std::string &name, const std::string &doc,
        std::vector<RecordMember> members) {
    RecordTable &t = recordTable();
    auto it = t.byName.find(name);
    if (it != t.byName.end()) {
        return it->second;      // a second registry (tests) defines it again
    }
    RecordInfo ri;
    ri.id = static_cast<uint16_t>(rf::numStructs + t.infos.size());
    ri.name = name;
    ri.doc = doc;
    ri.members = std::move(members);
    t.byName.emplace(name, ri.id);
    t.infos.push_back(std::move(ri));
    return t.infos.back().id;
}

const RecordInfo *recordInfo(uint16_t type) {
    const RecordTable &t = recordTable();
    if (type < rf::numStructs || type - rf::numStructs >= t.infos.size()) {
        return nullptr;
    }
    return &t.infos[type - rf::numStructs];
}

const std::vector<RecordInfo> &records() {
    return recordTable().infos;
}


}
}
}
