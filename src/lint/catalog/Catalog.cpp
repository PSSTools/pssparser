/*
 * Catalog.cpp
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
#include "Catalog.h"
#include "../regex/Regex.h"

namespace pssp {
namespace lint {
namespace catalog {

namespace {

using NK = yaml::Node::Kind;

void strings(const yaml::Node *n, const std::string &what, std::vector<std::string> &out,
        std::vector<std::string> &problems) {
    if (!n || n->kind == NK::Null) {
        return;
    }
    if (n->kind != NK::Seq) {
        problems.push_back(what + ": not a list of strings");
        return;
    }
    for (const yaml::NodeUP &i : n->items) {
        if (i->kind == NK::String) {
            out.push_back(i->s);
        } else {
            problems.push_back(what + ": not a list of strings");
        }
    }
}

std::string string(const yaml::Node *n) {
    return (n && n->kind == NK::String) ? n->s : std::string();
}

}

bool readMarker(const yaml::Node &m, pipeline::MarkerMeta &mm,
        std::vector<std::string> &problems) {
    const yaml::Node *id = m.get("id");
    if (!id || id->kind != NK::String) {
        problems.push_back("markers: an entry without an \"id\"");
        return false;
    }
    mm.id = id->s;
    for (auto f : std::vector<std::pair<const char *, std::string *>>{
            {"name", &mm.name}, {"tier", &mm.tier}, {"family", &mm.family},
            {"since", &mm.since}, {"status", &mm.status}, {"severity", &mm.severity}}) {
        const yaml::Node *v = m.get(f.first);
        if (v && v->kind == NK::String) {
            *f.second = v->s;
        } else if (v && v->kind != NK::Null) {
            problems.push_back("markers: " + mm.id + "." + f.first + ": not a string");
        }
    }
    strings(m.get("aliases"), "markers: " + mm.id + ".aliases", mm.aliases, problems);
    strings(m.get("replaced_by"), "markers: " + mm.id + ".replaced_by", mm.replacedBy,
        problems);
    for (auto f : std::vector<std::pair<const char *, bool *>>{
            {"default_enabled", &mm.defaultEnabled}, {"minimal", &mm.minimal}}) {
        const yaml::Node *v = m.get(f.first);
        if (v && v->kind == NK::Bool) {
            *f.second = v->b;
        } else if (v && v->kind != NK::Null) {
            problems.push_back("markers: " + mm.id + "." + f.first + ": not a boolean");
        }
    }
    return true;
}

Catalog::Catalog() {
    yaml::NodeUP doc;
    try {
        doc = yaml::parse("<catalog.json>", catalogText());
    } catch (const yaml::YamlError &e) {
        problems.push_back(e.what());
        return;
    }

    if (const yaml::Node *t = doc->get("taxonomy")) {
        if (const yaml::Node *tiers = t->get("tiers"); tiers && tiers->kind == NK::Seq) {
            for (const yaml::NodeUP &p : tiers->items) {
                if (p->kind == NK::Seq && p->items.size() == 2) {
                    taxonomy.tiers.emplace_back(string(p->items[0].get()),
                        string(p->items[1].get()));
                    if (taxonomy.tiers.back().first != "tool") {
                        taxonomy.lintTiers.push_back(taxonomy.tiers.back().first);
                    }
                }
            }
        }
        strings(t->get("families"), "taxonomy.families", taxonomy.families, problems);
        strings(t->get("profiles"), "taxonomy.profiles", taxonomy.profiles, problems);
        taxonomy.defaultProfile = string(t->get("default_profile"));
        if (const yaml::Node *pt = t->get("profile_tiers"); pt && pt->kind == NK::Map) {
            for (const yaml::Node::Member &m : pt->members) {
                strings(m.value.get(), "taxonomy.profile_tiers." + m.key,
                    taxonomy.profileTiers[m.key], problems);
            }
        }
        taxonomy.docUrl = string(t->get("doc_url"));
    } else {
        problems.push_back("no \"taxonomy\"");
    }

    if (const yaml::Node *ms = doc->get("markers"); ms && ms->kind == NK::Seq) {
        for (const yaml::NodeUP &m : ms->items) {
            Entry e;
            if (!readMarker(*m, e.meta, problems)) {
                continue;
            }
            e.summary = string(m->get("summary"));
            e.detail = string(m->get("detail"));
            strings(m->get("lrm"), "markers: " + e.meta.id + ".lrm", e.lrm, problems);
            markers.push_back(std::move(e));
        }
    } else {
        problems.push_back("no \"markers\"");
    }

    if (const yaml::Node *ps = doc->get("patterns"); ps && ps->kind == NK::Seq) {
        for (const yaml::NodeUP &p : ps->items) {
            if (p->kind != NK::Seq || p->items.size() != 2) {
                problems.push_back("patterns: an entry that is not [regex, id]");
                continue;
            }
            std::string rx = string(p->items[0].get()), id = string(p->items[1].get());
            try {
                patterns.emplace_back(
                    std::unique_ptr<regex::Regex>(regex::Regex::compile(rx)), id);
            } catch (const regex::RegexError &e) {
                problems.push_back("patterns: " + id + ": " + e.what());
            }
        }
    } else {
        problems.push_back("no \"patterns\"");
    }
}

Catalog::~Catalog() { }

const Catalog &get() {
    static const Catalog cat;
    return cat;
}

const Taxonomy &taxonomy() {
    return get().taxonomy;
}

std::string codeFor(const std::string &msg) {
    for (const auto &p : get().patterns) {
        if (p.first->search(msg)) {
            return p.second;
        }
    }
    return "";
}

std::string docUrl(const std::string &id) {
    std::string url = taxonomy().docUrl;
    std::string lower(id);
    for (char &c : lower) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    size_t at = url.find("{id}");
    if (at != std::string::npos) {
        url.replace(at, 4, lower);
    }
    return url;
}

}
}
}
