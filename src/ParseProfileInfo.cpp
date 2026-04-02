/*
 * ParseProfileInfo.cpp
 *
 * Implementation of profiling data export
 */

#include "ParseProfileInfo.h"

namespace pssp {


using namespace antlr4::atn;

DecisionProfileInfo::DecisionProfileInfo(const DecisionInfo &info) {
    m_decision = info.decision;
    m_invocations = info.invocations;
    m_time_in_prediction = info.timeInPrediction;
    m_sll_lookahead = info.SLL_TotalLook;
    m_ll_lookahead = info.LL_TotalLook;
    m_sll_atn_transitions = info.SLL_ATNTransitions;
    m_ll_atn_transitions = info.LL_ATNTransitions;
    m_ll_fallback = info.LL_Fallback;
    m_ambiguity_count = info.ambiguities.size();
    m_context_sensitivity_count = info.contextSensitivities.size();
    m_error_count = info.errors.size();
    m_max_lookahead = info.SLL_MaxLook;
    if (info.LL_MaxLook > m_max_lookahead) {
        m_max_lookahead = info.LL_MaxLook;
    }
}

ParseProfileInfo::ParseProfileInfo(const std::vector<DecisionInfo> &decisions) {
    // Extract all data from the provided decision vector
    // We need to compute the aggregates ourselves
    m_total_time = 0;
    m_total_sll_lookahead = 0;
    m_total_ll_lookahead = 0;
    m_total_sll_atn_lookahead = 0;
    m_total_ll_atn_lookahead = 0;
    m_dfa_size = 0;
    
    for (const auto &decision : decisions) {
        m_decisions.push_back(new DecisionProfileInfo(decision));
        
        // Compute aggregates
        m_total_time += decision.timeInPrediction;
        m_total_sll_lookahead += decision.SLL_TotalLook;
        m_total_ll_lookahead += decision.LL_TotalLook;
        m_total_sll_atn_lookahead += decision.SLL_ATNTransitions;
        m_total_ll_atn_lookahead += decision.LL_ATNTransitions;
        
        // Track LL decisions (decisions that fell back from SLL)
        if (decision.LL_Fallback > 0) {
            m_ll_decisions.push_back(decision.decision);
        }
        
        // DFA size (count unique DFA states across all decisions)
        if (decision.SLL_MaxLook > 0 || decision.LL_MaxLook > 0) {
            m_dfa_size++;
        }
    }
    
    m_total_atn_lookahead = m_total_sll_atn_lookahead + m_total_ll_atn_lookahead;
}

ParseProfileInfo::~ParseProfileInfo() {
    // Clean up decision info
    for (auto *dec : m_decisions) {
        delete dec;
    }
}

std::vector<IDecisionProfileInfo*> ParseProfileInfo::getDecisionInfo() {
    return m_decisions;
}

std::vector<size_t> ParseProfileInfo::getLLDecisions() {
    return m_ll_decisions;
}

long long ParseProfileInfo::getTotalTimeInPrediction() {
    return m_total_time;
}

long long ParseProfileInfo::getTotalSLLLookaheadOps() {
    return m_total_sll_lookahead;
}

long long ParseProfileInfo::getTotalLLLookaheadOps() {
    return m_total_ll_lookahead;
}

long long ParseProfileInfo::getTotalSLLATNLookaheadOps() {
    return m_total_sll_atn_lookahead;
}

long long ParseProfileInfo::getTotalLLATNLookaheadOps() {
    return m_total_ll_atn_lookahead;
}

long long ParseProfileInfo::getTotalATNLookaheadOps() {
    return m_total_atn_lookahead;
}

size_t ParseProfileInfo::getDFASize() {
    return m_dfa_size;
}

}
