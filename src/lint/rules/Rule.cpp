/*
 * Rule.cpp
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
#include "Rule.h"
#include "../util/JsonWriter.h"

namespace pssp {
namespace lint {
namespace rules {

namespace {

void strings(JsonWriter &w, const std::string &key, const std::vector<std::string> &l) {
    w.key(key).beginArray();
    for (const std::string &s : l) {
        w.value(s);
    }
    w.endArray();
}

// An option value: a string, int, bool or list of strings.
void optionValue(JsonWriter &w, const cel::Value &v) {
    switch (v.kind) {
        case cel::Value::Kind::String: w.value(v.s); break;
        case cel::Value::Kind::Int: w.value(v.i); break;
        case cel::Value::Kind::Bool: w.value(v.b); break;
        case cel::Value::Kind::List:
            w.beginArray();
            for (const cel::Value &e : *v.list) {
                optionValue(w, e);
            }
            w.endArray();
            break;
        default: w.valueNull();
    }
}

void kinds(JsonWriter &w, const std::string &key, const KindSet &k) {
    strings(w, key, k.names);
}

void ancestor(JsonWriter &w, const std::string &key, const AncestorTest &a) {
    w.key(key);
    if (!a.present) {
        w.valueNull();
        return;
    }
    w.beginObject();
    kinds(w, "kind", a.kind);
    kinds(w, "stop", a.stop);
    w.endObject();
}

}

void Rule::toJson(JsonWriter &w) const {
    w.beginObject();
    w.kv("id", m_id).kv("name", m_name).kv("tier", m_tier).kv("family", m_family);
    w.kv("summary", m_summary).kv("message", m_message).kv("doc", m_doc);
    strings(w, "lrm", m_lrm);
    w.kv("since", m_since).kv("status", m_status);
    strings(w, "aliases", m_aliases);
    strings(w, "replaced_by", m_replacedBy);
    w.kv("severity", m_severity).kv("default_enabled", m_defaultEnabled);
    w.kv("level", cel::levelName(m_level)).kv("scope", cel::scopeName(m_scope));
    w.key("calls").beginArray();
    for (const cel::Overload *o : m_calls) {
        w.value(o->id);
    }
    w.endArray();

    w.key("match").beginObject();
    kinds(w, "kind", m_match);
    ancestor(w, "inside", m_inside);
    ancestor(w, "not_inside", m_notInside);
    w.endObject();
    w.kv("node_type", m_nodeType.str()).kv("finding_type", m_findingType.str());

    w.key("options").beginArray();
    for (const RuleOption &o : m_options) {
        w.beginObject().kv("name", o.name).kv("type", o.type);
        w.key("default");
        optionValue(w, o.def);
        w.key("choices").beginArray();
        for (const cel::Value &c : o.choices) {
            optionValue(w, c);
        }
        w.endArray();
        w.kv("help", o.help).endObject();
    }
    w.endArray();

    w.key("let").beginArray();
    for (const LetBinding &l : m_lets) {
        w.beginObject().kv("name", l.name).kv("type", l.type.str()).endObject();
    }
    w.endArray();
    w.kv("where", m_where != nullptr).kv("report", m_report != nullptr);
    w.key("message_parts").beginArray();
    for (const MessagePart &p : m_messageParts) {
        w.beginObject();
        if (p.expr) {
            w.kv("expr", p.text).kv("type", p.type.str());
        } else {
            w.kv("text", p.text);
        }
        w.endObject();
    }
    w.endArray();

    w.key("examples").beginArray();
    for (const Example &x : m_examples) {
        w.beginObject().kv("name", x.name);
        w.key("files").beginArray();
        for (const ExampleFile &f : x.files) {
            w.beginObject().kv("name", f.name).kv("text", f.text);
            w.key("expect").beginArray();
            for (const Expectation &e : f.expect) {
                w.beginObject().kv("id", e.id).kv("line", e.line).kv("col", e.col).endObject();
            }
            w.endArray();
            w.endObject();
        }
        w.endArray();
        w.endObject();
    }
    w.endArray();

    w.kv("file", m_file).kv("line", m_mark.line).kv("col", m_mark.col);
    w.endObject();
}

void diagnosticsToJson(JsonWriter &w, const std::vector<RuleDiagnostic> &diags) {
    w.beginArray();
    for (const RuleDiagnostic &d : diags) {
        w.beginObject().kv("code", d.code);
        w.kv("severity", d.severity == RuleDiagnostic::Severity::Error ? "error"
            : d.severity == RuleDiagnostic::Severity::Warning ? "warning" : "info");
        w.kv("message", d.message).kv("file", d.file).kv("line", d.line).kv("col", d.col);
        w.kv("rule", d.rule);
        if (d.hasRelated) {
            w.key("related").beginObject().kv("file", d.relatedFile).kv("line", d.relatedLine);
            w.kv("col", d.relatedCol).endObject();
        }
        w.endObject();
    }
    w.endArray();
}

}
}
}
