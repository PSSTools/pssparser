/*
 * ParseProfileInfo.h
 *
 * Implementation of profiling data export interfaces
 */

#pragma once
#include "pssp/IParseProfileInfo.h"
#include "atn/ParseInfo.h"
#include "atn/DecisionInfo.h"

namespace pssp {


class DecisionProfileInfo : public IDecisionProfileInfo {
public:
    DecisionProfileInfo(const antlr4::atn::DecisionInfo &info);
    virtual ~DecisionProfileInfo() { }

    virtual size_t getDecision() const override { return m_decision; }
    virtual long long getInvocations() const override { return m_invocations; }
    virtual long long getTimeInPrediction() const override { return m_time_in_prediction; }
    virtual long long getSLLLookaheadOps() const override { return m_sll_lookahead; }
    virtual long long getLLLookaheadOps() const override { return m_ll_lookahead; }
    virtual long long getSLLATNTransitions() const override { return m_sll_atn_transitions; }
    virtual long long getLLATNTransitions() const override { return m_ll_atn_transitions; }
    virtual long long getLLFallback() const override { return m_ll_fallback; }
    virtual size_t getAmbiguityCount() const override { return m_ambiguity_count; }
    virtual size_t getContextSensitivityCount() const override { return m_context_sensitivity_count; }
    virtual size_t getErrorCount() const override { return m_error_count; }
    virtual size_t getMaxLookahead() const override { return m_max_lookahead; }

private:
    size_t m_decision;
    long long m_invocations;
    long long m_time_in_prediction;
    long long m_sll_lookahead;
    long long m_ll_lookahead;
    long long m_sll_atn_transitions;
    long long m_ll_atn_transitions;
    long long m_ll_fallback;
    size_t m_ambiguity_count;
    size_t m_context_sensitivity_count;
    size_t m_error_count;
    size_t m_max_lookahead;
};

class ParseProfileInfo : public IParseProfileInfo {
public:
    ParseProfileInfo(const std::vector<antlr4::atn::DecisionInfo> &decisions);
    virtual ~ParseProfileInfo();

    virtual std::vector<IDecisionProfileInfo*> getDecisionInfo() override;
    virtual std::vector<size_t> getLLDecisions() override;
    virtual long long getTotalTimeInPrediction() override;
    virtual long long getTotalSLLLookaheadOps() override;
    virtual long long getTotalLLLookaheadOps() override;
    virtual long long getTotalSLLATNLookaheadOps() override;
    virtual long long getTotalLLATNLookaheadOps() override;
    virtual long long getTotalATNLookaheadOps() override;
    virtual size_t getDFASize() override;

private:
    // All data is extracted in constructor from the provided vector
    std::vector<IDecisionProfileInfo*> m_decisions;
    std::vector<size_t> m_ll_decisions;
    long long m_total_time;
    long long m_total_sll_lookahead;
    long long m_total_ll_lookahead;
    long long m_total_sll_atn_lookahead;
    long long m_total_ll_atn_lookahead;
    long long m_total_atn_lookahead;
    size_t m_dfa_size;
};

}
