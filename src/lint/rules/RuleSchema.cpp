/*
 * RuleSchema.cpp
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
 * The JSON Schema of a rule file (lint-core-plan.md C4.4; pss-rules-format.md
 * §6.4), written from ruleFields(), the table the loader validates against,
 * so the two cannot drift apart. scripts/gen_rules_schema.py writes it to
 * docs/_static/pss-rules.schema.json.
 *
 * The schema checks shape only: keys, value types, enums, ID and name
 * grammar, and node kind names. It cannot check CEL, cross-field rules
 * (an option's default against its type is the exception) or what a
 * built-in rule file must also have; that is --check-rules' job.
 */
#include "Reflect.h"
#include "RuleLoader.h"
#include "../util/JsonWriter.h"

namespace pssp {
namespace lint {
namespace rules {

namespace {

namespace rf = pssp::ast::reflect;

// The grammars, as ECMA-262 patterns (format §3.1, §3.3, §5.1).
const char *CodePattern = "^[A-Z]{2,5}(-[A-Z]{2,5})?[0-9]{3}$";
const char *KebabPattern = "^[a-z][a-z0-9]*(-[a-z0-9]+)*$";
const char *VersionPattern = "^[0-9]{4}\\.[0-9]+$";
const char *IdentPattern = "^[A-Za-z_][A-Za-z0-9_]*$";
const char *HelperPattern =
    "^[A-Za-z_][A-Za-z0-9_]* *(\\( *([A-Za-z_][A-Za-z0-9_]*( *, *[A-Za-z_][A-Za-z0-9_]*)*)? *\\))?$";

void ref(JsonWriter &w, const char *def) {
    w.beginObject().kv("$ref", std::string("#/$defs/") + def).endObject();
}

// `x-*` keys are the author's own, and allowed wherever a mapping has
// fixed keys (format §2).
void xKeys(JsonWriter &w) {
    w.key("patternProperties").beginObject()
        .key("^x-").beginObject().endObject()
        .endObject();
    w.kv("additionalProperties", false);
}

void strings(JsonWriter &w, const std::vector<std::string> &l) {
    w.beginArray();
    for (const std::string &s : l) {
        w.value(s);
    }
    w.endArray();
}

// The schema of one rule field's value.
void fieldValue(JsonWriter &w, const FieldSpec &f) {
    if (f.type == FieldType::Reserved) {
        // `false` would do, but an object can carry the reason.
        w.beginObject().kv("description", std::string(f.doc) + "; not allowed in version 1")
            .key("not").beginObject().endObject().endObject();
        return;
    }
    w.beginObject().kv("description", f.doc);
    switch (f.type) {
    case FieldType::String:
    case FieldType::Template:
    case FieldType::Cel:
        w.kv("type", "string");
        break;
    case FieldType::Line:
        w.kv("type", "string").kv("pattern", "^[^\\n\\r]*$");
        w.key("not").beginObject().kv("pattern", "\\$\\{").endObject();
        break;
    case FieldType::Kebab:
        w.kv("type", "string").kv("pattern", KebabPattern);
        break;
    case FieldType::Enum:
        w.key("enum");
        strings(w, f.values);
        break;
    case FieldType::StringList:
        w.kv("type", "array").key("items").beginObject().kv("type", "string").endObject();
        break;
    case FieldType::Code:
        w.kv("$ref", "#/$defs/code");
        break;
    case FieldType::CodeList:
        w.kv("type", "array").key("items");
        ref(w, "code");
        break;
    case FieldType::Bool:
        w.kv("type", "boolean");
        break;
    case FieldType::Version:
        w.kv("type", "string").kv("pattern", VersionPattern);
        break;
    case FieldType::Options:
        w.kv("$ref", "#/$defs/options");
        break;
    case FieldType::Match:
        w.kv("$ref", "#/$defs/match");
        break;
    case FieldType::Defines:
        w.kv("$ref", "#/$defs/define");
        break;
    case FieldType::Lets:
        w.kv("$ref", "#/$defs/let");
        break;
    case FieldType::Examples:
        w.kv("$ref", "#/$defs/examples");
        break;
    case FieldType::Reserved:
        break;
    }
    w.endObject();
}

// A rule object, or `defaults:` (only the defaultable fields, none required).
void ruleObject(JsonWriter &w, bool defaults) {
    w.beginObject().kv("type", "object");
    if (!defaults) {
        // A field the loader requires but `defaults:` may supply (tier) is
        // not required here: the schema sees one rule at a time.
        w.key("required").beginArray();
        for (const FieldSpec &f : ruleFields()) {
            if (f.need == Need::Required && !f.defaultable) {
                w.value(f.name);
            }
        }
        w.endArray();
    }
    w.key("properties").beginObject();
    for (const FieldSpec &f : ruleFields()) {
        if (!defaults || f.defaultable) {
            w.key(f.name);
            fieldValue(w, f);
        }
    }
    w.endObject();
    xKeys(w);
    w.endObject();
}

// One node kind, or a non-empty list of them.
void kinds(JsonWriter &w) {
    w.beginObject().key("oneOf").beginArray();
    ref(w, "kind");
    w.beginObject().kv("type", "array").kv("minItems", 1).key("items");
    ref(w, "kind");
    w.endObject();
    w.endArray().endObject();
}

void ancestor(JsonWriter &w, const char *doc) {
    w.beginObject().kv("description", doc).kv("type", "object")
        .key("required").beginArray().value("kind").endArray();
    w.key("properties").beginObject();
    w.key("kind");
    kinds(w);
    w.key("stop");
    kinds(w);
    w.endObject();
    xKeys(w);
    w.endObject();
}

// An option's default must fit its type (format §3.5).
void optionTypeRule(JsonWriter &w, const char *type, const char *json) {
    w.beginObject();
    w.key("if").beginObject()
        .key("properties").beginObject()
            .key("type").beginObject().kv("const", type).endObject()
        .endObject()
        .key("required").beginArray().value("type").endArray()
        .endObject();
    w.key("then").beginObject()
        .key("properties").beginObject()
            .key("default").beginObject().kv("type", json).endObject()
        .endObject()
        .endObject();
    w.endObject();
}

}

std::string rulesSchemaJson() {
    JsonWriter w;
    w.beginObject();
    w.kv("$schema", "https://json-schema.org/draft/2020-12/schema");
    w.kv("title", "pss-rules file, version 1");
    w.kv("description", "A pssparser declarative lint rule file (pss-rules-format.md). "
        "Generated from the rule loader's field table by scripts/gen_rules_schema.py; "
        "do not edit. It checks the file's shape only: CEL, and what a built-in rule "
        "file must also have, are checked by `pssparser --check-rules`.");
    w.kv("type", "object");
    w.key("required").beginArray().value("pss-rules").endArray();
    w.key("properties").beginObject();
    w.key("pss-rules").beginObject().kv("type", "object")
        .key("required").beginArray().value("rules").endArray();
    w.key("properties").beginObject();
    w.key("version").beginObject()
        .kv("description", "Format major version; this schema is version 1")
        .kv("const", 1).endObject();
    w.key("defaults");
    ref(w, "defaults");
    w.key("define");
    ref(w, "define");
    w.key("rules").beginObject().kv("type", "array").key("items");
    ref(w, "rule");
    w.endObject();
    w.endObject();
    xKeys(w);
    w.endObject();      // pss-rules
    w.endObject();      // properties
    w.kv("additionalProperties", false);

    w.key("$defs").beginObject();
    w.key("rule");
    ruleObject(w, false);
    w.key("defaults");
    ruleObject(w, true);

    w.key("code").beginObject()
        .kv("description", "A marker ID: a namespace of 2-5 capitals, optionally qualified "
            "by a team (ACME-NET), then three digits")
        .kv("type", "string").kv("pattern", CodePattern).endObject();

    w.key("kind").beginObject()
        .kv("description", "An AST node kind; subclasses match too")
        .key("enum").beginArray();
    for (uint16_t k=1; k<=rf::NumClasses; k++) {
        w.value(rf::classes[k].name);
    }
    w.endArray().endObject();

    w.key("match").beginObject().kv("type", "object")
        .key("required").beginArray().value("kind").endArray();
    w.key("properties").beginObject();
    w.key("kind");
    kinds(w);
    w.key("inside");
    ancestor(w, "Some ancestor, nearest first, is of this kind (searched up to 'stop')");
    w.key("not_inside");
    ancestor(w, "No ancestor, up to 'stop', is of this kind");
    w.endObject();
    xKeys(w);
    w.endObject();

    w.key("options").beginObject().kv("type", "object")
        .key("propertyNames").beginObject().kv("pattern", IdentPattern).endObject()
        .key("additionalProperties");
    ref(w, "option");
    w.endObject();

    w.key("option").beginObject().kv("type", "object")
        .key("required").beginArray().value("default").endArray();
    w.key("properties").beginObject();
    w.key("type").beginObject().kv("description", "Default string").key("enum");
    strings(w, optionTypes());
    w.endObject();
    w.key("default").beginObject().kv("description", "Required: expressions need a value")
        .endObject();
    w.key("help").beginObject().kv("type", "string").endObject();
    w.key("choices").beginObject().kv("type", "array").endObject();
    w.endObject();
    xKeys(w);
    w.key("allOf").beginArray();
    // No `type` means string.
    w.beginObject();
    w.key("if").beginObject().key("not").beginObject()
        .key("required").beginArray().value("type").endArray().endObject().endObject();
    w.key("then").beginObject().key("properties").beginObject()
        .key("default").beginObject().kv("type", "string").endObject()
        .endObject().endObject();
    w.endObject();
    optionTypeRule(w, "string", "string");
    optionTypeRule(w, "int", "integer");
    optionTypeRule(w, "bool", "boolean");
    w.beginObject();
    w.key("if").beginObject()
        .key("properties").beginObject()
            .key("type").beginObject().kv("const", "string-list").endObject()
        .endObject()
        .key("required").beginArray().value("type").endArray()
        .endObject();
    w.key("then").beginObject()
        .key("properties").beginObject()
            .key("default").beginObject().kv("type", "array")
                .key("items").beginObject().kv("type", "string").endObject()
            .endObject()
        .endObject()
        .endObject();
    w.endObject();
    w.endArray();
    w.endObject();

    w.key("define").beginObject()
        .kv("description", "Helpers: 'name' or 'name(param, ...)' to one CEL expression")
        .kv("type", "object")
        .key("propertyNames").beginObject().kv("pattern", HelperPattern).endObject()
        .key("additionalProperties").beginObject().kv("type", "string").endObject()
        .endObject();

    w.key("let").beginObject()
        .kv("description", "Named CEL sub-expressions, in order")
        .kv("type", "object")
        .key("propertyNames").beginObject().kv("pattern", IdentPattern)
            .key("not").beginObject().key("enum").beginArray()
                .value("node").value("options").value("finding").endArray().endObject()
            .endObject()
        .key("additionalProperties").beginObject().kv("type", "string").endObject()
        .endObject();

    w.key("examples").beginObject().kv("type", "array").key("items");
    ref(w, "example");
    w.endObject();

    w.key("example").beginObject().kv("type", "object");
    w.key("properties").beginObject();
    w.key("name").beginObject().kv("type", "string").endObject();
    w.key("code").beginObject()
        .kv("description", "A complete model; '// expect: ID' marks a finding")
        .kv("type", "string").endObject();
    w.key("files").beginObject()
        .kv("description", "File name to text, in place of 'code'")
        .kv("type", "object").kv("minProperties", 1)
        .key("additionalProperties").beginObject().kv("type", "string").endObject()
        .endObject();
    w.endObject();
    xKeys(w);
    w.key("oneOf").beginArray();
    w.beginObject().key("required").beginArray().value("code").endArray().endObject();
    w.beginObject().key("required").beginArray().value("files").endArray().endObject();
    w.endArray();
    w.endObject();

    w.endObject();      // $defs
    w.endObject();
    return w.str();
}

}
}
}
