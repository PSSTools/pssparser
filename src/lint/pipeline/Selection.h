/*
 * Selection.h
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
 * Rule selection, profiles and per-path overrides (lint-core-plan.md C7.1;
 * lint-framework L3, F2.5). A port of python/pssparser/checkers/selectors.py,
 * which stays as the test oracle; the messages are the same, word for word.
 *
 * Everywhere an ID is accepted, these selectors are too:
 *
 *   ID         LINT104              one rule
 *   name       unknown-annotation   one rule
 *   prefix     LINT1                an ID band
 *   namespace  ACME                 every code in the namespace and, for an
 *                                   organisation, its teams (ACME-NET001)
 *   family     family:constraint    every rule in the family
 *   tier       correctness          every rule in the tier
 *   profile    recommended          every rule the profile enables
 *
 * When several selectors match one rule, the most specific wins (ID or
 * name, then prefix, namespace, family, tier, profile); a tie between
 * select and ignore goes to ignore.
 */
#pragma once
#include <cstdint>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include "../yaml/YamlDoc.h"

namespace pssp {
namespace lint {
class JsonWriter;
namespace rules { class Rule; }
namespace pipeline {

/** What selection needs to know of a marker: a loaded rule's metadata, or a host's. */
struct MarkerMeta {
    std::string                 id;
    std::string                 name;
    std::string                 tier;           // "" for an LRM or tool marker
    std::string                 family;
    std::string                 since;          // "YYYY.N", or ""
    std::string                 status = "active";
    std::string                 severity;       // "" takes the tier's
    std::vector<std::string>    aliases;
    std::vector<std::string>    replacedBy;
    bool                        defaultEnabled = true;
    bool                        minimal = false;    // in the `minimal` profile
    const rules::Rule           *rule = nullptr;    // a loaded rule; null for a host's

    bool isLint() const { return !tier.empty() && tier != "tool"; }
    bool emittable() const { return status == "active" || status == "deprecated"; }
    /** An error the model cannot be built past: never widened to by a group selector. */
    bool isCoreError() const;
};

/** The default severity of each tier (taxonomy.TIER_SEVERITY); "" for an unknown tier. */
const char *tierSeverity(const std::string &tier);

/** "LINT104" -> ("LINT", true); false when `code` is not a well-formed code. */
bool splitCode(const std::string &code, std::string &ns, int &num);

/** The levenshtein-closest of `candidates` within 2 edits (cli/suggestion.py). */
std::string suggest(const std::string &name, const std::vector<std::string> &candidates);

struct Selector {
    enum class Kind { Id, Name, Prefix, Namespace, Family, Tier, Profile };
    std::string     text;
    Kind            kind = Kind::Id;
    std::string     value;

    int specificity() const;
    /** Names one rule, an ID band or a namespace: a request to see it (E3(a)). */
    bool isExplicit() const { return specificity() >= 50; }
};

/**
 * Every marker the selectors may name: the host's, then the loaded rules
 * the host's do not replace. Holds no state of a run.
 */
class Catalogue {
public:
    /** `host` first; a loaded rule with a host entry's ID, or in `refused`, is left out. */
    Catalogue(const std::vector<MarkerMeta> &host, const std::set<std::string> &refused,
        const std::vector<const rules::Rule *> &loaded);

    /** Parses `text`; false with `err` set (the selectors.py message) when unknown. */
    bool parse(const std::string &text, Selector &sel, std::string &err) const;

    bool matches(const Selector &sel, const MarkerMeta &m) const;

    /** The IDs `profile` enables, after the rules-version pin. */
    const std::set<std::string> &profileMembers(const std::string &profile) const;

    /** Rules the pin keeps out of `profile`, sorted. */
    std::vector<std::string> heldBack(const std::string &profile) const;

    /** Every emittable marker, in catalogue order. */
    const std::vector<MarkerMeta> &markers() const { return m_markers; }

    /** The emittable lint rules, in catalogue order. */
    const std::vector<const MarkerMeta *> &lint() const { return m_lint; }

    const MarkerMeta *byId(const std::string &id) const;
    const MarkerMeta *byName(const std::string &name) const;

    /** `{old: current}`: aliases, and retired codes' replacements. */
    const std::map<std::string, std::string> &aliases() const { return m_aliases; }

    /**
     * Each marker `sels` match, to (the selector's text, its specificity),
     * the most specific selector per ID: `[severity]` keys, `-W` groups and
     * waivers (RuleSet.expand). A selector broader than an ID or name never
     * reaches a core error unless `includeCoreErrors`.
     */
    std::map<std::string, std::pair<std::string, int>> expand(
        const std::vector<Selector> &sels, bool includeCoreErrors=false) const;

    /** "" or "YYYY.N": rules newer than this stay out of the profiles. */
    void setRulesVersion(const std::string &pin);

    /** Every spelling a selector may take, sorted, for did-you-mean. */
    std::vector<std::string> candidates() const;

    /** The best (most specific) of `sels` that matches `m`; -1 when none does. */
    int best(const std::vector<Selector> &sels, const MarkerMeta &m,
        const Selector **winner=nullptr) const;

private:
    bool pinnedOut(const MarkerMeta &m) const;
    std::string unknown(const std::string &text, const std::string &what) const;

private:
    std::vector<MarkerMeta>                             m_markers;
    std::vector<const MarkerMeta *>                     m_lint;
    std::unordered_map<std::string, size_t>             m_byId;
    std::unordered_map<std::string, size_t>             m_byName;
    std::map<std::string, std::string>                  m_aliases;
    bool                                                m_pinned = false;
    std::pair<int, int>                                 m_pin;
    mutable std::map<std::string, std::set<std::string>> m_profiles;
};

/** One problem with a selection: a selector, rule or key the catalogue does not know. */
struct SelectionError {
    std::string     key;        // "lint.select", "lint.overrides[0].ignore", "--select", ...
    std::string     text;       // the selector as written
    std::string     message;    // "unknown marker or selector 'X'; did you mean 'Y'?"
};

/** The effective rule set of the files a set of overrides matches. */
struct SelectionGroup {
    std::vector<uint32_t>                   overrides;      // indexes, in order
    std::string                             profile;
    std::set<std::string>                   enabled;
    std::set<std::string>                   explicitIds;    // enabled by name (E3(a))
    std::vector<std::string>                heldBack;
    // `[lint.rule.<name>]`, merged: rule ID -> option -> value (a node of the input).
    std::map<std::string, std::map<std::string, const yaml::Node *>> options;
};

/**
 * A resolved selection (C7.1): the input JSON, as the configuration's
 * TOML parsed,
 *   {"lint": {"profile", "select", "ignore", "rules-version",
 *             "rule": {name: {opt: value}},
 *             "overrides": [{"files": [glob...], "profile", "select",
 *                            "ignore", "rule"}]},
 *    "command_line": {"select", "ignore"},
 *    "severity": {selector: severity},
 *    "warnings": {"error": [selector...], "no-error": [selector...]},
 *    "base_dir": "..."}
 * Every key is optional. Shapes are the host's to validate; a value of the
 * wrong shape here is an error with key "request".
 */
class Selection {
public:
    Selection(Catalogue &cat, const yaml::Node &input);

    const std::vector<SelectionError> &errors() const { return m_errors; }

    /** The group of `path` (as the host names it; made relative to base_dir). */
    uint32_t groupOf(const std::string &path);

    /** The directory the globs are relative to, when the input gave none. */
    void defaultBaseDir(const std::string &dir) {
        if (!m_hasBaseDir) {
            m_baseDir = dir;
        }
    }

    /** `path` normalized and relative to base_dir, as the globs see it. */
    std::string relPath(const std::string &path) const;

    const SelectionGroup &group(uint32_t g) const { return m_groups[g]; }
    uint32_t numGroups() const { return static_cast<uint32_t>(m_groups.size()); }

    /** `[severity]` expanded to IDs: ID -> (severity, the key that set it). */
    const std::map<std::string, std::pair<std::string, std::string>> &severity() const {
        return m_severity;
    }

    /**
     * The whole resolution as JSON, with the group and relative path of
     * each of `paths`: see ILintEngine::resolveSelection().
     */
    void toJson(JsonWriter &w, const std::vector<std::string> &paths);

private:
    struct Layer {
        std::string                 key;        // "lint", "lint.overrides[N]", "command_line"
        std::vector<Selector>       select;
        std::vector<Selector>       ignore;
        bool                        hasProfile = false;
        std::string                 profile;
        const yaml::Node            *rule = nullptr;
        std::vector<std::string>    files;      // overrides only
    };

    void readLayer(const yaml::Node *n, const std::string &key, Layer &l, bool isOverride);
    void readSelectors(const yaml::Node *n, const std::string &key, std::vector<Selector> &out);
    void readStrings(const yaml::Node *n, const std::string &key, std::vector<std::string> &out);
    void readOptions(const yaml::Node *rule, const std::string &key);
    void expandSeverity(const yaml::Node *n);
    void expandCodes(const yaml::Node *n, const std::string &key,
        std::vector<std::string> &ids, std::map<std::string, std::string> *spelling);
    void build(SelectionGroup &g);
    void overlay(const Layer &l, std::set<std::string> &on, std::set<std::string> &expl) const;
    void error(const std::string &key, const std::string &text, const std::string &message);

private:
    Catalogue                                       &m_cat;
    std::vector<SelectionError>                     m_errors;
    Layer                                           m_base;
    std::vector<Layer>                              m_overrides;
    Layer                                           m_cli;
    std::string                                     m_baseDir;
    bool                                            m_hasBaseDir = false;
    std::vector<SelectionGroup>                     m_groups;
    std::map<std::vector<uint32_t>, uint32_t>       m_groupIndex;
    std::map<std::string, std::pair<std::string, std::string>>  m_severity;
    std::vector<std::string>                        m_werror;
    std::map<std::string, std::string>              m_werrorSpelling;
    bool                                            m_werrorInfo = false;
    std::vector<std::string>                        m_noError;
};

}
}
}
