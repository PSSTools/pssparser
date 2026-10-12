/*
 * Finish.cpp
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
#include <map>
#include "Finish.h"
#include "../catalog/Catalog.h"

namespace pssp {
namespace lint {
namespace pipeline {

namespace {

// The internal-error code: never re-severitied (DiagnosticCollection).
const char *INTERNAL_ERROR = "PSSP000";

std::set<std::string> lintIds(const Catalogue &cat) {
    std::set<std::string> ids;
    for (const MarkerMeta *m : cat.lint()) {
        ids.insert(m->id);
    }
    return ids;
}

// diagnostics.py's WarningPolicy.promotion_flag: "" when not promoted.
std::string promotion(const Selection::Warnings &pol, const FinishDiag &d) {
    if (d.severity != "warning" && d.severity != "info") {
        return "";
    }
    if (!d.code.empty() && pol.noError.count(d.code)) {
        return "";
    }
    if (!d.code.empty() && pol.error.count(d.code)) {
        auto it = pol.spelling.find(d.code);
        return "-Werror=" + (it == pol.spelling.end() ? d.code : it->second);
    }
    if (d.severity == "info") {
        return pol.errorInfo ? "-Werror=info" : "";
    }
    return pol.errorAll ? "-Werror" : "";
}

}

FinishResult finish(const Catalogue &cat, Selection &sel, const Selection::Warnings &pol,
        std::vector<FinishDiag> diags, FinishRequest &req) {
    FinishResult res;
    const auto &severity = sel.severity();
    std::set<std::string> refused;

    // select: lint codes only (lint-framework L3).
    if (req.select) {
        std::set<std::string> lint = lintIds(cat);
        std::map<std::string, uint32_t> groups;
        std::vector<FinishDiag> kept;
        for (FinishDiag &d : diags) {
            if (lint.count(d.code)) {
                auto g = groups.find(d.file);
                if (g == groups.end()) {
                    g = groups.emplace(d.file, sel.groupOf(d.file)).first;
                }
                if (!sel.group(g->second).enabled.count(d.code)) {
                    continue;
                }
                if (req.haveOwned && !req.owned.count(d.file)) {
                    res.outside++;
                    continue;
                }
            }
            kept.push_back(std::move(d));
        }
        diags.swap(kept);
    }

    // severity: by ID, after every diagnostic has its code.
    auto severityOf = [&](const std::string &code, std::string &out) {
        if (code.empty() || code == INTERNAL_ERROR) {
            return false;
        }
        auto it = severity.find(code);
        if (it == severity.end()) {
            return false;
        }
        const MarkerMeta *m = cat.byId(code);
        if (m && m->isCoreError() && it->second.first != "error") {
            if (refused.insert(code).second) {
                res.problems.push_back("severity: '" + code + "' is a core error; its"
                    " severity stays 'error'");
            }
            return false;
        }
        out = it->second.first;
        return true;
    };
    if (req.severity) {
        std::vector<FinishDiag> kept;
        for (FinishDiag &d : diags) {
            std::string sev;
            if (severityOf(d.code, sev)) {
                if (sev == "off") {
                    continue;
                }
                d.severity = sev;
            }
            kept.push_back(std::move(d));
        }
        diags.swap(kept);
    }

    // waive: after the severity map, so a waiver covers a rule the config
    // promoted; before the policy, so -Werror never promotes a waived one.
    if (req.waive && !req.waivers.empty()) {
        std::vector<WaiverDiag> wd;
        for (const FinishDiag &d : diags) {
            WaiverDiag x;
            x.code = d.code;
            x.file = d.file;
            x.line = d.line;
            x.col = d.col;
            wd.push_back(x);
        }
        WaiverResult wr = applyWaivers(cat, wd, req.waivers, req.ran);
        std::vector<FinishDiag> kept;
        for (uint32_t i : wr.kept) {
            kept.push_back(std::move(diags[i]));
        }
        for (const auto &p : wr.waived) {
            FinishDiag &d = diags[p.first];
            d.waiver = p.second;
            res.waived.push_back(std::move(d));
        }
        for (const WaiverMarker &m : wr.markers) {
            FinishDiag d;
            d.code = m.code;
            d.severity = m.severity;
            d.message = m.message;
            d.file = m.file;
            d.line = m.line;
            d.col = m.col;
            std::string sev;
            if (req.severity && severityOf(d.code, sev)) {
                if (sev == "off") {
                    continue;
                }
                d.severity = sev;
            }
            kept.push_back(std::move(d));
        }
        diags.swap(kept);
    }

    // policy: suppression before promotion, so --no-warnings -Werror
    // leaves nothing to promote.
    if (req.policy) {
        std::vector<FinishDiag> kept;
        for (FinishDiag &d : diags) {
            if (pol.none && d.severity == "warning") {
                continue;
            }
            std::string flag = promotion(pol, d);
            if (!flag.empty()) {
                d.originalSeverity = d.severity;
                d.severity = "error";
                d.werror = flag;
            }
            kept.push_back(std::move(d));
        }
        diags.swap(kept);
    }

    res.diagnostics = std::move(diags);
    return res;
}

std::set<std::string> codesThatRan(const Catalogue &cat, Selection &sel,
        const std::vector<std::string> &paths) {
    std::set<std::string> ran;
    for (const catalog::Entry &e : catalog::get().markers) {
        if (e.meta.status == "active") {
            ran.insert(e.meta.id);
        }
    }
    for (const MarkerMeta &m : cat.markers()) {
        if (m.rule) {
            ran.insert(m.id);
        }
    }
    std::set<std::string> enabled;
    if (paths.empty()) {
        enabled = sel.group(0).enabled;
    }
    for (const std::string &p : paths) {
        const std::set<std::string> &on = sel.group(sel.groupOf(p)).enabled;
        enabled.insert(on.begin(), on.end());
    }
    for (const MarkerMeta *m : cat.lint()) {
        if (!enabled.count(m->id)) {
            ran.erase(m->id);
        }
    }
    for (const auto &s : sel.severity()) {
        if (s.second.first == "off") {
            ran.erase(s.first);
        }
    }
    return ran;
}

}
}
}
