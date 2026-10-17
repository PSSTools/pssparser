/*
 * LintTestHooks.h
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
#pragma once
#include "pssp/lint/ILintTestHooks.h"

namespace pssp { class IFactory; }

namespace pssp {
namespace lint {

class LintTestHooks : public virtual ILintTestHooks {
public:
    LintTestHooks(IFactory *factory=nullptr);
    virtual ~LintTestHooks();

    virtual std::string yamlLoad(const std::string &name, const std::string &text) override;
    virtual std::string yamlSourceMaps(const std::string &name, const std::string &text) override;
    virtual std::string yamlCelParse(
        const std::string &name, const std::string &text, const std::string &key) override;
    virtual std::string celParse(const std::string &text) override;
    virtual std::string celEval(
        const std::string &text, const std::string &bindings, uint64_t max_steps) override;
    virtual std::string celFunctions() override;
    virtual std::string celCheck(const std::string &name, const std::string &text) override;
    virtual std::string celCheckNode(const std::string &name, const std::string &text,
        ast::IScopeChild *root, ast::IRootSymbolScope *model) override;
    virtual std::string celEvalNode(const std::string &text, ast::IScopeChild *root,
        const std::string &bindings, uint64_t max_steps,
        ast::IRootSymbolScope *model) override;
    virtual std::string ruleLoad(const std::string &name, const std::string &text,
        bool builtin) override;
    virtual std::string rulesSchema() override;
    virtual std::string regexSearch(const std::string &pattern, const std::string &text) override;
    virtual std::string reflectSchema() override;
    virtual std::string reflectCensus(ast::IScopeChild *root) override;

    virtual std::string lintWalk(const std::string &name, const std::string &text,
        const std::vector<ast::IScopeChild *> &roots) override;

    virtual std::string lintRun(const std::string &name, const std::string &text,
        const std::vector<ast::IScopeChild *> &roots, bool allEnabled,
        const std::vector<std::string> &enabled, uint64_t maxSteps,
        uint32_t gateErrors, ast::IRootSymbolScope *model) override;

    virtual std::string declPaths(ast::IScopeChild *root) override;

    virtual std::string exprTypes(
        ast::IRootSymbolScope *model, ast::IScopeChild *root) override;

private:
    IFactory        *m_factory;
};

}
}
