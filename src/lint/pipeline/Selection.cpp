/*
 * Selection.cpp
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
#include <algorithm>
#include <cctype>
#include "Selection.h"
#include "Glob.h"
#include "../rules/Rule.h"
#include "../util/JsonWriter.h"
#include "../util/Paths.h"
#include "../catalog/Catalog.h"

namespace pssp {
namespace lint {
namespace pipeline {

namespace {

// taxonomy.py, from the embedded catalogue (C7.3): tiers (documentation
// order) with their default severity, families, profiles, and the tiers each
// profile enables.
const std::vector<std::pair<std::string, std::string>> &tierTable() {
    return catalog::taxonomy().tiers;
}

const std::vector<std::string> &families() {
    return catalog::taxonomy().families;
}

const std::vector<std::string> &profiles() {
    return catalog::taxonomy().profiles;
}

std::vector<std::string> profileTiers(const std::string &profile) {
    const auto &pt = catalog::taxonomy().profileTiers;
    auto it = pt.find(profile);
    return (it == pt.end()) ? std::vector<std::string>() : it->second;
}

bool contains(const std::vector<std::string> &v, const std::string &s) {
    return std::find(v.begin(), v.end(), s) != v.end();
}

bool isTier(const std::string &s) {
    for (const auto &t : tierTable()) {
        if (t.first == s) {
            return true;
        }
    }
    return false;
}

// `[A-Z]{n,m}` from `at`: the length taken, 0 when fewer than n.
size_t upperRun(const std::string &s, size_t at, size_t n, size_t m) {
    size_t i = at;
    while (i < s.size() && i - at < m && s[i] >= 'A' && s[i] <= 'Z') {
        i++;
    }
    return (i - at >= n) ? i - at : 0;
}

// NAMESPACE_PATTERN from the start of `s`: its length, 0 for none. A
// longer run of capitals is not a namespace (the pattern is anchored by
// what follows it: '-', a digit or the end).
size_t namespaceLen(const std::string &s) {
    size_t a = upperRun(s, 0, 2, 5);
    if (!a || (a < s.size() && s[a] >= 'A' && s[a] <= 'Z')) {
        return 0;
    }
    if (a < s.size() && s[a] == '-') {
        size_t b = upperRun(s, a + 1, 2, 5);
        if (b && !(a + 1 + b < s.size() && s[a+1+b] >= 'A' && s[a+1+b] <= 'Z')) {
            return a + 1 + b;
        }
    }
    return a;
}

// _PREFIX_RE: a namespace and 0-2 digits, the whole of `s`.
bool prefixParts(const std::string &s, std::string &ns, std::string &digits) {
    size_t n = namespaceLen(s);
    if (!n) {
        return false;
    }
    size_t i = n;
    while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i]))) {
        i++;
    }
    if (i != s.size() || i - n > 2) {
        return false;
    }
    ns = s.substr(0, n);
    digits = s.substr(n);
    return true;
}

std::string namespaceOf(const std::string &code) {
    std::string ns;
    int num;
    return splitCode(code, ns, num) ? ns : "";
}

bool namespaceSelects(const std::string &sel, const std::string &ns) {
    return ns == sel || (sel.find('-') == std::string::npos && ns.size() > sel.size()
        && ns.compare(0, sel.size() + 1, sel + "-") == 0);
}

bool parseRulesVersion(const std::string &s, std::pair<int, int> &out) {
    size_t dot = s.find('.');
    if (dot != 4 || s.size() < 6) {
        return false;
    }
    for (size_t i=0; i<s.size(); i++) {
        if (i != dot && !std::isdigit(static_cast<unsigned char>(s[i]))) {
            return false;
        }
    }
    out = {std::stoi(s.substr(0, 4)), std::stoi(s.substr(5))};
    return true;
}

std::string lower(const std::string &s) {
    std::string out = s;
    for (char &c : out) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return out;
}

size_t levenshtein(const std::string &a, const std::string &b) {
    std::vector<size_t> dp(b.size() + 1);
    for (size_t j=0; j<=b.size(); j++) {
        dp[j] = j;
    }
    for (size_t i=1; i<=a.size(); i++) {
        size_t prev = dp[0];
        dp[0] = i;
        for (size_t j=1; j<=b.size(); j++) {
            size_t cost = (a[i-1] == b[j-1]) ? 0 : 1;
            size_t tmp = dp[j];
            dp[j] = std::min({dp[j] + 1, dp[j-1] + 1, prev + cost});
            prev = tmp;
        }
    }
    return dp[b.size()];
}

std::string trim(const std::string &s) {
    size_t b = s.find_first_not_of(" \t\n\r\f\v");
    if (b == std::string::npos) {
        return "";
    }
    size_t e = s.find_last_not_of(" \t\n\r\f\v");
    return s.substr(b, e - b + 1);
}

// An input value as JSON, unchanged.
void nodeJson(JsonWriter &w, const yaml::Node *n) {
    using NK = yaml::Node::Kind;
    if (!n || n->kind == NK::Null) {
        w.valueNull();
    } else if (n->kind == NK::Bool) {
        w.value(n->b);
    } else if (n->kind == NK::Int) {
        w.value(n->i);
    } else if (n->kind == NK::Float) {
        w.value(n->d);
    } else if (n->kind == NK::String) {
        w.value(n->s);
    } else if (n->kind == NK::Seq) {
        w.beginArray();
        for (const yaml::NodeUP &i : n->items) {
            nodeJson(w, i.get());
        }
        w.endArray();
    } else {
        w.beginObject();
        for (const yaml::Node::Member &m : n->members) {
            w.key(m.key);
            nodeJson(w, m.value.get());
        }
        w.endObject();
    }
}

void stringArray(JsonWriter &w, const std::string &key, const std::vector<std::string> &v) {
    w.key(key).beginArray();
    for (const std::string &s : v) {
        w.value(s);
    }
    w.endArray();
}

void stringArray(JsonWriter &w, const std::string &key, const std::set<std::string> &v) {
    stringArray(w, key, std::vector<std::string>(v.begin(), v.end()));
}

}

const char *tierSeverity(const std::string &tier) {
    for (const auto &t : tierTable()) {
        if (t.first == tier) {
            return t.second.c_str();
        }
    }
    return "";
}

bool splitCode(const std::string &code, std::string &ns, int &num) {
    size_t n = namespaceLen(code);
    if (!n || code.size() != n + 3) {
        return false;
    }
    for (size_t i=n; i<code.size(); i++) {
        if (!std::isdigit(static_cast<unsigned char>(code[i]))) {
            return false;
        }
    }
    ns = code.substr(0, n);
    num = std::stoi(code.substr(n));
    return true;
}

std::string suggest(const std::string &name, const std::vector<std::string> &candidates) {
    const size_t maxDist = 2;
    std::string best;
    size_t bestDist = maxDist + 1;
    bool bestCase = false;
    for (const std::string &cand : candidates) {
        size_t d = levenshtein(name, cand);
        if (d == 0 || d >= bestDist) {
            if (d == bestDist && d <= maxDist) {
                bool caseMatch = lower(name) == lower(cand);
                if (caseMatch && !bestCase) {
                    best = cand;
                    bestCase = true;
                }
            }
            continue;
        }
        best = cand;
        bestDist = d;
        bestCase = lower(name) == lower(cand);
    }
    return best;
}

bool MarkerMeta::isCoreError() const {
    std::string sev = severity.empty() ? tierSeverity(tier) : severity;
    std::string ns = namespaceOf(id);
    return sev == "error" && (tier.empty() || tier == "tool") && (ns == "PSS" || ns == "PSSP");
}

int Selector::specificity() const {
    int base = 0;
    switch (kind) {
        case Kind::Id: case Kind::Name: return 100;
        case Kind::Prefix: case Kind::Namespace: base = 50; break;
        case Kind::Family: return 30;
        case Kind::Tier: return 20;
        case Kind::Profile: return 10;
    }
    // A team is narrower than its organisation, each digit of band
    // narrower again: ACME < ACME-NET < ACME-NET1.
    std::string ns, digits;
    if (prefixParts(value, ns, digits)) {
        base += (ns.find('-') != std::string::npos ? 1 : 0) + 2 * static_cast<int>(digits.size());
    }
    return base;
}

Catalogue::Catalogue(const std::vector<MarkerMeta> &host, const std::set<std::string> &refused,
        const std::vector<const rules::Rule *> &loaded) {
    std::vector<MarkerMeta> all = host;
    std::set<std::string> hostIds;
    for (const MarkerMeta &m : host) {
        hostIds.insert(m.id);
    }
    for (const rules::Rule *r : loaded) {
        if (hostIds.count(r->m_id) || refused.count(r->m_id)) {
            continue;
        }
        MarkerMeta m;
        m.id = r->m_id;
        m.name = r->m_name;
        m.tier = r->m_tier;
        m.family = r->m_family;
        m.since = r->m_since;
        m.status = r->m_status;
        m.severity = r->m_severity;
        m.aliases = r->m_aliases;
        m.replacedBy = r->m_replacedBy;
        m.defaultEnabled = r->m_defaultEnabled;
        m.rule = r;
        all.push_back(m);
    }
    // manager.alias_map(): every definition's aliases, then retired codes.
    for (const MarkerMeta &m : all) {
        for (const std::string &a : m.aliases) {
            m_aliases[a] = m.id;
        }
    }
    for (const MarkerMeta &m : all) {
        if (m.status == "retired" && !m.replacedBy.empty()) {
            m_aliases.emplace(m.id, m.replacedBy[0]);
        }
    }
    for (const MarkerMeta &m : all) {
        if (m.emittable()) {
            m_markers.push_back(m);
        }
    }
    for (size_t i=0; i<m_markers.size(); i++) {
        const MarkerMeta &m = m_markers[i];
        m_byId[m.id] = i;
        if (!m.name.empty()) {
            m_byName[m.name] = i;
        }
    }
    for (const MarkerMeta &m : m_markers) {
        if (m.isLint()) {
            m_lint.push_back(&m);
        }
    }
}

const MarkerMeta *Catalogue::byId(const std::string &id) const {
    auto it = m_byId.find(id);
    return (it == m_byId.end()) ? nullptr : &m_markers[it->second];
}

const MarkerMeta *Catalogue::byName(const std::string &name) const {
    auto it = m_byName.find(name);
    return (it == m_byName.end()) ? nullptr : &m_markers[it->second];
}

void Catalogue::setRulesVersion(const std::string &pin) {
    m_pinned = !pin.empty() && parseRulesVersion(pin, m_pin);
    m_profiles.clear();
}

std::vector<std::string> Catalogue::candidates() const {
    std::set<std::string> c;
    for (const MarkerMeta &m : m_markers) {
        c.insert(m.id);
        if (!m.name.empty()) {
            c.insert(m.name);
        }
        std::string ns = namespaceOf(m.id);
        if (!ns.empty()) {
            c.insert(ns);
        }
    }
    for (const auto &t : tierTable()) {
        c.insert(t.first);
    }
    for (const std::string &f : families()) {
        c.insert("family:" + f);
    }
    for (const std::string &p : profiles()) {
        c.insert(p);
    }
    return std::vector<std::string>(c.begin(), c.end());
}

std::string Catalogue::unknown(const std::string &text, const std::string &what) const {
    std::string hint = suggest(text, candidates());
    std::string kind = what.empty() ? "marker or selector" : what + " selector";
    std::string detail = hint.empty()
        ? "run --list-markers to see the declared IDs and names"
        : "did you mean '" + hint + "'?";
    return "unknown " + kind + " '" + text + "'; " + detail;
}

bool Catalogue::parse(const std::string &raw, Selector &sel, std::string &err) const {
    std::string text = trim(raw);
    auto al = m_aliases.find(text);
    std::string canonical = (al == m_aliases.end()) ? text : al->second;
    sel.text = text;
    if (m_byId.count(canonical)) {
        sel.kind = Selector::Kind::Id;
        sel.value = canonical;
        return true;
    }
    if (m_byName.count(canonical)) {
        sel.kind = Selector::Kind::Name;
        sel.value = canonical;
        return true;
    }
    if (contains(profiles(), text)) {
        sel.kind = Selector::Kind::Profile;
        sel.value = text;
        return true;
    }
    if (isTier(text)) {
        sel.kind = Selector::Kind::Tier;
        sel.value = text;
        return true;
    }
    if (text.compare(0, 7, "family:") == 0) {
        std::string fam = text.substr(7);
        if (contains(families(), fam)) {
            sel.kind = Selector::Kind::Family;
            sel.value = fam;
            return true;
        }
        err = unknown(text, "family");
        return false;
    }
    std::string ns, digits;
    if (prefixParts(text, ns, digits)) {
        sel.kind = digits.empty() ? Selector::Kind::Namespace : Selector::Kind::Prefix;
        sel.value = text;
        for (const MarkerMeta &m : m_markers) {
            if (matches(sel, m)) {
                return true;
            }
        }
    }
    err = unknown(text, "");
    return false;
}

bool Catalogue::matches(const Selector &sel, const MarkerMeta &m) const {
    switch (sel.kind) {
        case Selector::Kind::Id: return m.id == sel.value;
        case Selector::Kind::Name: return m.name == sel.value;
        case Selector::Kind::Prefix: return m.id.compare(0, sel.value.size(), sel.value) == 0;
        case Selector::Kind::Namespace: return namespaceSelects(sel.value, namespaceOf(m.id));
        case Selector::Kind::Family: return m.family == sel.value;
        case Selector::Kind::Tier: return m.tier == sel.value;
        case Selector::Kind::Profile: return profileMembers(sel.value).count(m.id) != 0;
    }
    return false;
}

bool Catalogue::pinnedOut(const MarkerMeta &m) const {
    std::pair<int, int> since;
    return m_pinned && !m.since.empty() && parseRulesVersion(m.since, since) && since > m_pin;
}

const std::set<std::string> &Catalogue::profileMembers(const std::string &profile) const {
    auto it = m_profiles.find(profile);
    if (it != m_profiles.end()) {
        return it->second;
    }
    // Every profile but `none` includes `minimal`, whatever its tiers say.
    std::set<std::string> members;
    if (profile != "none") {
        for (const MarkerMeta &m : m_markers) {
            if (m.minimal) {
                members.insert(m.id);
            }
        }
        std::vector<std::string> tiers = profileTiers(profile);
        for (const MarkerMeta *m : m_lint) {
            if (contains(tiers, m->tier) && m->defaultEnabled && !pinnedOut(*m)) {
                members.insert(m->id);
            }
        }
    }
    return m_profiles.emplace(profile, std::move(members)).first->second;
}

std::vector<std::string> Catalogue::heldBack(const std::string &profile) const {
    std::vector<std::string> out;
    if (!m_pinned || profile == "none") {
        return out;
    }
    std::vector<std::string> tiers = profileTiers(profile);
    for (const MarkerMeta *m : m_lint) {
        if (contains(tiers, m->tier) && m->defaultEnabled && pinnedOut(*m)) {
            out.push_back(m->id);
        }
    }
    std::sort(out.begin(), out.end());
    return out;
}

int Catalogue::best(const std::vector<Selector> &sels, const MarkerMeta &m,
        const Selector **winner) const {
    int best = -1;
    for (const Selector &s : sels) {
        if (matches(s, m) && s.specificity() > best) {
            best = s.specificity();
            if (winner) {
                *winner = &s;
            }
        }
    }
    return best;
}

Selection::Selection(Catalogue &cat, const yaml::Node &input) : m_cat(cat) {
    using NK = yaml::Node::Kind;
    if (input.kind != NK::Map && input.kind != NK::Null) {
        error("request", "", "the selection is not a JSON object");
    }
    static const std::vector<std::string> topKeys = {
        "lint", "command_line", "severity", "warnings", "base_dir", "paths"};
    for (const yaml::Node::Member &m : input.members) {
        if (!contains(topKeys, m.key)) {
            error("request", m.key, "unknown key '" + m.key + "'");
        }
    }
    if (const yaml::Node *bd = input.get("base_dir")) {
        if (bd->kind == NK::String) {
            m_baseDir = bd->s;
            m_hasBaseDir = true;
        } else if (bd->kind != NK::Null) {
            error("request", "base_dir", "base_dir: not a string");
        }
    }
    const yaml::Node *lint = input.get("lint");
    std::string pin;
    if (lint && lint->kind == NK::Map) {
        if (const yaml::Node *rv = lint->get("rules-version")) {
            if (rv->kind == NK::String) {
                pin = rv->s;
            } else if (rv->kind != NK::Null) {
                error("request", "lint.rules-version", "lint.rules-version: not a string");
            }
        }
    }
    m_cat.setRulesVersion(pin);

    // The order selectors.py and config.py check in, so the host's first
    // error is the one it reported before C7.1.
    expandSeverity(input.get("severity"));
    const yaml::Node *warnings = input.get("warnings");
    if (warnings && warnings->kind == NK::Map) {
        const yaml::Node *e = warnings->get("error");
        if (e && e->kind == NK::Seq) {
            expandCodes(e, "warnings.error", m_werror, &m_werrorSpelling);
        }
        expandCodes(warnings->get("no-error"), "warnings.no-error", m_noError, nullptr);
    } else if (warnings && warnings->kind != NK::Null) {
        error("request", "warnings", "warnings: not an object");
    }

    if (lint && lint->kind != NK::Map && lint->kind != NK::Null) {
        error("request", "lint", "lint: not an object");
        lint = nullptr;
    }
    readLayer(lint, "lint", m_base, false);
    const yaml::Node *cli = input.get("command_line");
    if (cli && cli->kind == NK::Map) {
        readLayer(cli, "command_line", m_cli, false);
    } else if (cli && cli->kind != NK::Null) {
        error("request", "command_line", "command_line: not an object");
    }
    readOptions(m_base.rule, "lint.rule");
    if (lint) {
        if (const yaml::Node *ovs = lint->get("overrides")) {
            if (ovs->kind != NK::Seq) {
                error("request", "lint.overrides", "lint.overrides: not a list");
            } else {
                for (size_t i=0; i<ovs->items.size(); i++) {
                    std::string key = "lint.overrides[" + std::to_string(i) + "]";
                    m_overrides.emplace_back();
                    readLayer(ovs->items[i].get(), key, m_overrides.back(), true);
                    readOptions(m_overrides.back().rule, key + ".rule");
                }
            }
        }
    }

    // Group 0: the files no override matches.
    m_groups.emplace_back();
    build(m_groups[0]);
    m_groupIndex[{}] = 0;
}

void Selection::error(const std::string &key, const std::string &text,
        const std::string &message) {
    m_errors.push_back({key, text, message});
}

void Selection::readStrings(const yaml::Node *n, const std::string &key,
        std::vector<std::string> &out) {
    using NK = yaml::Node::Kind;
    if (!n || n->kind == NK::Null) {
        return;
    }
    if (n->kind != NK::Seq) {
        error("request", key, key + ": not a list of strings");
        return;
    }
    for (const yaml::NodeUP &i : n->items) {
        if (i->kind != NK::String) {
            error("request", key, key + ": not a list of strings");
            return;
        }
        out.push_back(i->s);
    }
}

void Selection::readSelectors(const yaml::Node *n, const std::string &key,
        std::vector<Selector> &out) {
    std::vector<std::string> texts;
    readStrings(n, key, texts);
    // The command line's flags are named as the user typed them.
    std::string shown = (key == "command_line.select") ? "--select"
        : (key == "command_line.ignore") ? "--ignore" : key;
    for (const std::string &t : texts) {
        Selector s;
        std::string err;
        if (m_cat.parse(t, s, err)) {
            out.push_back(s);
        } else {
            error(shown, t, "'" + shown + "' names an " + err);
        }
    }
}

void Selection::readLayer(const yaml::Node *n, const std::string &key, Layer &l,
        bool isOverride) {
    using NK = yaml::Node::Kind;
    l.key = key;
    if (!n || n->kind == NK::Null) {
        if (isOverride) {
            error("request", key, key + ": not an object");
        }
        return;
    }
    if (n->kind != NK::Map) {
        error("request", key, key + ": not an object");
        return;
    }
    static const std::vector<std::string> lintKeys = {
        "profile", "select", "ignore", "rules-version", "rule", "overrides", "baseline",
        "rules"};
    static const std::vector<std::string> overrideKeys = {
        "files", "profile", "select", "ignore", "rule"};
    static const std::vector<std::string> cliKeys = {"select", "ignore"};
    const std::vector<std::string> &known = isOverride ? overrideKeys
        : (key == "command_line") ? cliKeys : lintKeys;
    for (const yaml::Node::Member &m : n->members) {
        if (!contains(known, m.key)) {
            error("request", key + "." + m.key, key + ": unknown key '" + m.key + "'");
        }
    }
    if (const yaml::Node *p = n->get("profile")) {
        if (p->kind == NK::String && contains(profiles(), p->s)) {
            l.hasProfile = true;
            l.profile = p->s;
        } else if (p->kind != NK::Null) {
            error("request", key + ".profile", key + ".profile: not a profile name");
        }
    }
    readSelectors(n->get("select"), key + ".select", l.select);
    readSelectors(n->get("ignore"), key + ".ignore", l.ignore);
    if (const yaml::Node *r = n->get("rule")) {
        if (r->kind == NK::Map) {
            l.rule = r;
        } else if (r->kind != NK::Null) {
            error("request", key + ".rule", key + ".rule: not an object");
        }
    }
    if (isOverride) {
        readStrings(n->get("files"), key + ".files", l.files);
        if (l.files.empty()) {
            error("request", key + ".files", key + ": 'files' must list at least one pattern");
        }
    }
}

void Selection::readOptions(const yaml::Node *rule, const std::string &key) {
    using NK = yaml::Node::Kind;
    if (!rule) {
        return;
    }
    for (const yaml::Node::Member &m : rule->members) {
        const MarkerMeta *md = m_cat.byName(m.key);
        if (!md) {
            md = m_cat.byId(m.key);
        }
        if (!md || !md->isLint()) {
            std::vector<std::string> names;
            for (const MarkerMeta *l : m_cat.lint()) {
                if (!l->name.empty()) {
                    names.push_back(l->name);
                }
            }
            std::sort(names.begin(), names.end());
            names.erase(std::unique(names.begin(), names.end()), names.end());
            std::string hint = suggest(m.key, names);
            std::string detail = hint.empty() ? "run --list-markers to see the rule names"
                : "did you mean '" + hint + "'?";
            std::string shown = (key == "lint.rule") ? "[lint.rule." + m.key + "]"
                : key + "." + m.key;
            error(key + "." + m.key, m.key,
                "'" + shown + "' configures an unknown lint rule; " + detail);
        } else if (m.value->kind != NK::Map) {
            error("request", key + "." + m.key, key + "." + m.key + ": not an object");
        }
    }
}

std::map<std::string, std::pair<std::string, int>> Catalogue::expand(
        const std::vector<Selector> &sels, bool includeCoreErrors) const {
    // A broad selector (anything but an ID or name) never reaches a core
    // error: core errors cannot be configured.
    std::map<std::string, std::pair<std::string, int>> result;
    for (const Selector &sel : sels) {
        bool exact = sel.kind == Selector::Kind::Id || sel.kind == Selector::Kind::Name;
        for (const MarkerMeta &m : m_markers) {
            if (!matches(sel, m) || (!exact && !includeCoreErrors && m.isCoreError())) {
                continue;
            }
            auto it = result.find(m.id);
            if (it == result.end() || sel.specificity() > it->second.second) {
                result[m.id] = {sel.text, sel.specificity()};
            }
        }
    }
    return result;
}

void Selection::expandSeverity(const yaml::Node *n) {
    using NK = yaml::Node::Kind;
    if (!n || n->kind == NK::Null) {
        return;
    }
    if (n->kind != NK::Map) {
        error("request", "severity", "severity: not an object");
        return;
    }
    std::vector<Selector> sels;
    std::map<std::string, std::string> sevOf;
    for (const yaml::Node::Member &m : n->members) {
        Selector s;
        std::string err;
        if (m.value->kind != NK::String) {
            error("request", "severity." + m.key, "severity." + m.key + ": not a string");
        } else if (m_cat.parse(m.key, s, err)) {
            // The key as written: a selector reads it trimmed.
            s.text = m.key;
            sels.push_back(s);
            sevOf[m.key] = m.value->s;
        } else {
            error("severity." + m.key, m.key, "'[severity]' names an " + err);
        }
    }
    for (const auto &e : m_cat.expand(sels)) {
        m_severity[e.first] = {sevOf[e.second.first], e.second.first};
    }
}

void Selection::expandCodes(const yaml::Node *n, const std::string &key,
        std::vector<std::string> &ids, std::map<std::string, std::string> *spelling) {
    std::vector<std::string> texts;
    readStrings(n, key, texts);
    for (const std::string &t : texts) {
        if (t == "info") {
            if (spelling) {
                m_werrorInfo = true;
            }
            continue;
        }
        Selector s;
        std::string err;
        if (!m_cat.parse(t, s, err)) {
            error(key, t, "'" + key + "' names an " + err);
            continue;
        }
        s.text = t;
        // In catalogue order, as the oracle's dict.
        std::map<std::string, std::pair<std::string, int>> got = m_cat.expand({s});
        for (const MarkerMeta &m : m_cat.markers()) {
            if (got.count(m.id) && !contains(ids, m.id)) {
                ids.push_back(m.id);
                if (spelling) {
                    spelling->emplace(m.id, t);
                }
            }
        }
    }
}

void Selection::overlay(const Layer &l, std::set<std::string> &on,
        std::set<std::string> &expl) const {
    if (l.select.empty() && l.ignore.empty()) {
        return;
    }
    // A rule a selector of this layer matches is decided by this layer
    // alone; the others keep their state.
    for (const MarkerMeta *m : m_cat.lint()) {
        const Selector *w = nullptr;
        int bOn = m_cat.best(l.select, *m, &w);
        int bOff = m_cat.best(l.ignore, *m);
        if (bOn < 0 && bOff < 0) {
            continue;
        }
        if (bOn > bOff) {
            on.insert(m->id);
            if (w->isExplicit()) {
                expl.insert(m->id);
            } else {
                expl.erase(m->id);
            }
        } else {
            on.erase(m->id);
            expl.erase(m->id);
        }
    }
}

void Selection::build(SelectionGroup &g) {
    g.profile = m_base.hasProfile ? m_base.profile : catalog::taxonomy().defaultProfile;
    for (uint32_t i : g.overrides) {
        if (m_overrides[i].hasProfile) {
            g.profile = m_overrides[i].profile;
        }
    }
    // The profile is the base, at profile specificity; then the project's
    // select and ignore.
    std::vector<Selector> on;
    Selector p;
    p.text = g.profile;
    p.kind = Selector::Kind::Profile;
    p.value = g.profile;
    on.push_back(p);
    on.insert(on.end(), m_base.select.begin(), m_base.select.end());
    for (const MarkerMeta *m : m_cat.lint()) {
        const Selector *w = nullptr;
        int bOn = m_cat.best(on, *m, &w);
        int bOff = m_cat.best(m_base.ignore, *m);
        if (bOn >= 0 && bOn > bOff) {
            g.enabled.insert(m->id);
            if (w->isExplicit()) {
                g.explicitIds.insert(m->id);
            }
        }
    }
    for (uint32_t i : g.overrides) {
        overlay(m_overrides[i], g.enabled, g.explicitIds);
    }
    overlay(m_cli, g.enabled, g.explicitIds);
    g.heldBack = m_cat.heldBack(g.profile);

    std::vector<const yaml::Node *> tables = {m_base.rule};
    for (uint32_t i : g.overrides) {
        tables.push_back(m_overrides[i].rule);
    }
    for (const yaml::Node *t : tables) {
        if (!t) {
            continue;
        }
        for (const yaml::Node::Member &m : t->members) {
            const MarkerMeta *md = m_cat.byName(m.key);
            if (!md) {
                md = m_cat.byId(m.key);
            }
            if (!md || !md->isLint() || m.value->kind != yaml::Node::Kind::Map) {
                continue;
            }
            for (const yaml::Node::Member &o : m.value->members) {
                g.options[md->id][o.key] = o.value.get();
            }
        }
    }
}

std::string Selection::relPath(const std::string &path) const {
    return util::normalPath(path, m_baseDir);
}

uint32_t Selection::groupOf(const std::string &path) {
    std::string rel = relPath(path);
    std::vector<uint32_t> hit;
    for (uint32_t i=0; i<m_overrides.size(); i++) {
        for (const std::string &g : m_overrides[i].files) {
            if (globMatchesPath(g, rel)) {
                hit.push_back(i);
                break;
            }
        }
    }
    auto it = m_groupIndex.find(hit);
    if (it != m_groupIndex.end()) {
        return it->second;
    }
    uint32_t idx = static_cast<uint32_t>(m_groups.size());
    m_groups.emplace_back();
    m_groups.back().overrides = hit;
    build(m_groups.back());
    m_groupIndex[hit] = idx;
    return idx;
}

void Selection::toJson(JsonWriter &w, const std::vector<std::string> &paths) {
    std::vector<uint32_t> pg;
    for (const std::string &p : paths) {
        pg.push_back(groupOf(p));
    }
    w.beginObject();
    w.kv("ok", true);
    w.key("errors").beginArray();
    for (const SelectionError &e : m_errors) {
        w.beginObject().kv("key", e.key).kv("text", e.text).kv("message", e.message)
            .endObject();
    }
    w.endArray();
    std::set<std::string> lintIds;
    for (const MarkerMeta *m : m_cat.lint()) {
        lintIds.insert(m->id);
    }
    stringArray(w, "lint_ids", lintIds);
    w.key("groups").beginArray();
    for (const SelectionGroup &g : m_groups) {
        w.beginObject();
        w.key("overrides").beginArray();
        for (uint32_t i : g.overrides) {
            w.value(i);
        }
        w.endArray();
        w.kv("profile", g.profile);
        stringArray(w, "enabled", g.enabled);
        stringArray(w, "explicit", g.explicitIds);
        stringArray(w, "held_back", g.heldBack);
        w.key("options").beginObject();
        for (const auto &r : g.options) {
            w.key(r.first).beginObject();
            for (const auto &o : r.second) {
                w.key(o.first);
                nodeJson(w, o.second);
            }
            w.endObject();
        }
        w.endObject();
        w.endObject();
    }
    w.endArray();
    w.key("paths").beginArray();
    for (size_t i=0; i<paths.size(); i++) {
        w.beginObject().kv("path", paths[i]).kv("rel", relPath(paths[i])).kv("group", pg[i])
            .endObject();
    }
    w.endArray();
    w.key("severity").beginObject();
    for (const auto &s : m_severity) {
        w.key(s.first).beginObject().kv("severity", s.second.first).kv("key", s.second.second)
            .endObject();
    }
    w.endObject();
    w.key("warnings").beginObject();
    stringArray(w, "error", m_werror);
    w.kv("error_info", m_werrorInfo);
    w.key("spelling").beginObject();
    for (const auto &s : m_werrorSpelling) {
        w.kv(s.first, s.second);
    }
    w.endObject();
    stringArray(w, "no_error", m_noError);
    w.endObject();
    w.endObject();
}

}
}
}
