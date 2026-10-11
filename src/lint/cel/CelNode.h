/*
 * CelNode.h
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
 * AST nodes as CEL values (lint-core-plan.md C3.1), through the generated
 * reflection tables (C1.3) and nothing else.
 *
 * - A node's fields are its class's schema fields, inherited ones included.
 * - An unset node field reads as null, marked with the field's name, so that
 *   navigating through it is the D-C6 error "field 'lhs' of unset 'rhs'".
 * - list<...> fields are CEL lists, without the elements that do not own
 *   their node (the linker lists an `extend`'s members in a template's body
 *   that way; they belong to the `extend`) and the builder's implicit nodes
 *   (run::Walker::implicit); enum and flags fields are ints (CEL
 *   enums are ints); Location and the other schema structs are struct values
 *   with their members as fields.
 * - has() is proto3 presence: a node field is present when set, a list when
 *   non-empty, a scalar when not its zero value; a struct always.
 * - Class, struct and enum names are type values; an enum type's members are
 *   its constants: ExprBinOp.BinOp_Eq.
 */
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "CelType.h"
#include "CelValue.h"

namespace pssp {
namespace lint {
namespace cel {

/**
 * Reads field `name` of a node or struct value into `out`. Returns false if
 * the value's class has no such field. `elems` is set to the number of list
 * elements read, which the evaluator charges as steps.
 */
bool readField(const Value &obj, const std::string &name, Value &out, uint64_t &elems);

/** has(obj.name). Returns false if the class has no such field. */
bool hasField(const Value &obj, const std::string &name, bool &present);

const char *nodeClassName(uint16_t kind);
const char *structName(uint16_t type);

/** A class, struct or enum name as a type value. */
bool lookupType(const std::string &name, Value &out);

//* For the checker (C3.3): the schema as types.

bool lookupClass(const std::string &name, uint16_t &cls);
bool lookupStruct(const std::string &name, uint16_t &st);
bool isEnum(const std::string &name);

/** Whether class `k` is `base` or derives from it. */
bool isSubclass(uint16_t k, uint16_t base);

/** The nearest class both derive from, or 0 (any node) if none. */
uint16_t commonBase(uint16_t a, uint16_t b);

/**
 * A field of a node class or a struct, as the checker sees it. `index`
 * identifies it to readFieldAt(); `error` is set, and the field cannot be
 * used, when pss-rules has no type for it (the symbol tables' maps).
 */
struct FieldRef {
    Type            type;
    int32_t         index = -1;
    std::string     error;
};
bool nodeFieldType(uint16_t cls, const std::string &name, FieldRef &out);

/**
 * The classes deriving from `cls` (0: any class) that have field `name`
 * although `cls` lacks it, topmost first-declared only (a class that
 * inherits it from one of these is not listed): the checker's hint for a
 * field that needs a `type(x) == K` test first.
 */
std::vector<std::string> derivedFieldClasses(uint16_t cls, const std::string &name);
bool structFieldType(uint16_t st, const std::string &name, FieldRef &out);

/**
 * readField() and hasField() for a field the checker resolved: `index` is
 * FieldRef::index. False, with nothing read, if the value is not of the
 * class or struct the field belongs to; the caller then reads by name.
 */
bool readFieldAt(const Value &obj, int32_t index, Value &out, uint64_t &elems);
bool hasFieldAt(const Value &obj, int32_t index, bool &isSet);

/** `type.member` where `type` names an enum. */
bool enumConstant(const std::string &type, const std::string &member, int64_t &out);

/** Member-wise equality of two struct values of the same struct type. */
bool structEquals(const Value &a, const Value &b);

}
}
}
