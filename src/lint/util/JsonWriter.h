/*
 * JsonWriter.h
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
 * Minimal streaming JSON writer. The lint engine's results cross both binding
 * layers (Cython and Embind) as JSON text, so the same string is produced
 * natively and in WASM and the parity tests can compare them byte for byte.
 */
#pragma once
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace pssp {
namespace lint {

class JsonWriter {
public:
    JsonWriter() { m_first.push_back(true); }

    const std::string &str() const { return m_out; }

    JsonWriter &beginObject() { sep(); m_out += '{'; m_first.push_back(true); return *this; }
    JsonWriter &endObject() { m_out += '}'; m_first.pop_back(); return *this; }
    JsonWriter &beginArray() { sep(); m_out += '['; m_first.push_back(true); return *this; }
    JsonWriter &endArray() { m_out += ']'; m_first.pop_back(); return *this; }

    JsonWriter &key(const std::string &k) {
        sep();
        quote(k);
        m_out += ':';
        m_after_key = true;
        return *this;
    }

    JsonWriter &value(const std::string &v) { sep(); quote(v); return *this; }
    JsonWriter &value(const char *v) { return value(std::string(v)); }
    JsonWriter &value(bool v) { sep(); m_out += v ? "true" : "false"; return *this; }
    JsonWriter &value(int64_t v) { sep(); m_out += std::to_string(v); return *this; }
    JsonWriter &value(uint64_t v) { sep(); m_out += std::to_string(v); return *this; }
    JsonWriter &value(int v) { return value(static_cast<int64_t>(v)); }
    JsonWriter &value(uint32_t v) { return value(static_cast<uint64_t>(v)); }
    JsonWriter &valueNull() { sep(); m_out += "null"; return *this; }

    // JSON has no NaN or infinity; those are written as strings, which the
    // reader side knows to expect for a double.
    JsonWriter &value(double v) {
        sep();
        if (std::isnan(v)) {
            m_out += "\"NaN\"";
        } else if (std::isinf(v)) {
            m_out += (v > 0) ? "\"Infinity\"" : "\"-Infinity\"";
        } else {
            char buf[32];
            snprintf(buf, sizeof(buf), "%.17g", v);
            m_out += buf;
            // Keep it a double on the way back: "2" would read as an int.
            if (!strpbrk(buf, ".eE")) {
                m_out += ".0";
            }
        }
        return *this;
    }

    template <class T> JsonWriter &kv(const std::string &k, T v) {
        key(k);
        return value(v);
    }

private:
    void sep() {
        if (m_after_key) {
            m_after_key = false;
            return;
        }
        if (!m_first.back()) {
            m_out += ',';
        }
        m_first.back() = false;
    }

    void quote(const std::string &s) {
        m_out += '"';
        for (unsigned char c : s) {
            switch (c) {
                case '"': m_out += "\\\""; break;
                case '\\': m_out += "\\\\"; break;
                case '\n': m_out += "\\n"; break;
                case '\r': m_out += "\\r"; break;
                case '\t': m_out += "\\t"; break;
                case '\b': m_out += "\\b"; break;
                case '\f': m_out += "\\f"; break;
                default:
                    if (c < 0x20) {
                        char buf[8];
                        snprintf(buf, sizeof(buf), "\\u%04x", c);
                        m_out += buf;
                    } else {
                        m_out += static_cast<char>(c);
                    }
            }
        }
        m_out += '"';
    }

    std::string         m_out;
    std::vector<bool>   m_first;
    bool                m_after_key = false;
};

}
}
