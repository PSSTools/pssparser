/**
 * FmtCst.h
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
#include <iostream>
#include <memory>
#include <vector>

#include "pssp/IFmtCst.h"
#include "FmtTokenStream.h"

namespace pssp {

/**
 * A materialized CST node.
 *
 * The ANTLR tree is owned by the parser and dies with it.  Copying the shape
 * we need into our own nodes lets the parser go away as soon as parsing is
 * done, which keeps the lifetime story simple: an :cpp:class:`IFmtCst` owns
 * everything reachable from it and nothing else.
 */
class FmtCstNode : public virtual IFmtCstNode {
public:
    FmtCstNode(
        bool                    is_rule,
        bool                    is_error,
        int32_t                 rule_index,
        const std::string       &rule_name,
        int32_t                 token_index);

    virtual ~FmtCstNode();

    virtual bool isRule() const override { return m_is_rule; }

    virtual bool isError() const override { return m_is_error; }

    virtual int32_t getRuleIndex() const override { return m_rule_index; }

    virtual const std::string &getRuleName() const override {
        return m_rule_name;
    }

    virtual int32_t getTokenIndex() const override { return m_token_index; }

    virtual uint32_t getNumChildren() const override {
        return static_cast<uint32_t>(m_children.size());
    }

    virtual IFmtCstNode *getChild(uint32_t idx) const override {
        return m_children.at(idx).get();
    }

    virtual int32_t getStartToken() const override { return m_start_token; }

    virtual int32_t getStopToken() const override { return m_stop_token; }

    void addChild(FmtCstNode *c) {
        m_children.push_back(std::unique_ptr<FmtCstNode>(c));
    }

    void setSpan(int32_t start, int32_t stop) {
        m_start_token = start;
        m_stop_token = stop;
    }

private:
    bool                                        m_is_rule;
    bool                                        m_is_error;
    int32_t                                     m_rule_index;
    std::string                                 m_rule_name;
    int32_t                                     m_token_index;
    int32_t                                     m_start_token;
    int32_t                                     m_stop_token;
    std::vector<std::unique_ptr<FmtCstNode>>    m_children;

};

class FmtCst : public virtual IFmtCst {
public:
    FmtCst(std::istream *in);

    virtual ~FmtCst();

    virtual IFmtTokenStream *getTokens() override { return m_tokens.get(); }

    virtual IFmtCstNode *getRoot() override { return m_root.get(); }

    virtual uint32_t getNumSyntaxErrors() const override {
        return m_num_syntax_errors;
    }

private:
    std::unique_ptr<FmtTokenStream>     m_tokens;
    std::unique_ptr<FmtCstNode>         m_root;
    uint32_t                            m_num_syntax_errors;

};

}
