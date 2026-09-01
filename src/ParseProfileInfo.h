/*
 * ParseProfileInfo.h
 *
 * Implementation of profiling data export interfaces
 */

#pragma once
#include "pssp/IParseProfileInfo.h"
#include "atn/ParseInfo.h"
#include "atn/DecisionInfo.h"
#include "Parser.h"

namespace pssp {

/// Events kept per decision.  `predicateEvals` and `errors` grow with input
/// size -- an invalid file generates errors freely -- and the events are only
/// ever read by a human triaging a hotspot, who needs a handful of examples
/// rather than every one.  The *counts* are exact regardless; only the stored
/// examples are capped.
static const size_t kMaxEventsPerDecision = 8;

/// Characters of source text kept per event.  Enough to recognize the
/// construct; a max-lookahead event can span forty tokens of a long
/// expression, and the whole point is that it is long.
static const size_t kMaxEventTextLen = 120;

/**
 * A profiler event resolved away from the parser that produced it.
 *
 * Plain values only.  Nothing here points back at the `TokenStream`, the
 * `ATNConfigSet`, or anything else the parse owned.
 */
struct DecisionEventSnapshot {
    IDecisionEventInfo::KindE   kind;
    std::string                 kind_name;
    uint32_t                    start_line = 0;
    uint32_t                    start_column = 0;
    uint32_t                    stop_line = 0;
    uint32_t                    stop_column = 0;
    uint32_t                    token_count = 0;
    std::string                 text;
};

/**
 * One decision's profile, resolved and self-contained.
 */
struct DecisionSnapshot {
    size_t                              decision = 0;
    size_t                              rule_index = 0;
    std::string                         rule_name;
    long long                           invocations = 0;
    long long                           time_in_prediction = 0;
    long long                           sll_lookahead = 0;
    long long                           ll_lookahead = 0;
    long long                           sll_atn_transitions = 0;
    long long                           ll_atn_transitions = 0;
    long long                           ll_fallback = 0;
    size_t                              ambiguity_count = 0;
    size_t                              context_sensitivity_count = 0;
    size_t                              error_count = 0;
    size_t                              predicate_eval_count = 0;
    size_t                              sll_min_lookahead = 0;
    size_t                              sll_max_lookahead = 0;
    size_t                              ll_min_lookahead = 0;
    size_t                              ll_max_lookahead = 0;
    std::vector<DecisionEventSnapshot>  events;
};

/**
 * A whole parse's profile, resolved and self-contained.
 *
 * `AstBuilderInt::build` produces one of these *while the parser is alive*
 * and hands it on.  Deferring the work would be a use-after-free: ANTLR's
 * event records hold raw pointers into the token stream and the simulator,
 * and the next `build()` replaces both.
 */
struct ProfileSnapshot {
    std::vector<DecisionSnapshot>   decisions;
    size_t                          dfa_size = 0;
    size_t                          token_count = 0;
};

/**
 * Take a snapshot of `parser`'s profiling state.
 *
 * Must be called before `parser` goes out of scope.  Returns an empty
 * snapshot if the parser was not profiling.
 */
ProfileSnapshot mkProfileSnapshot(antlr4::Parser &parser);


class DecisionEventInfo : public IDecisionEventInfo {
public:
    DecisionEventInfo(const DecisionEventSnapshot &ev) : m_ev(ev) { }
    virtual ~DecisionEventInfo() { }

    virtual KindE getKind() const override { return m_ev.kind; }
    virtual const std::string &getKindName() const override { return m_ev.kind_name; }
    virtual uint32_t getStartLine() const override { return m_ev.start_line; }
    virtual uint32_t getStartColumn() const override { return m_ev.start_column; }
    virtual uint32_t getStopLine() const override { return m_ev.stop_line; }
    virtual uint32_t getStopColumn() const override { return m_ev.stop_column; }
    virtual uint32_t getTokenCount() const override { return m_ev.token_count; }
    virtual const std::string &getText() const override { return m_ev.text; }

private:
    DecisionEventSnapshot   m_ev;
};

class DecisionProfileInfo : public IDecisionProfileInfo {
public:
    DecisionProfileInfo(const DecisionSnapshot &info);
    virtual ~DecisionProfileInfo();

    virtual size_t getDecision() const override { return m_info.decision; }
    virtual size_t getRuleIndex() const override { return m_info.rule_index; }
    virtual const std::string &getRuleName() const override { return m_info.rule_name; }
    virtual long long getInvocations() const override { return m_info.invocations; }
    virtual long long getTimeInPrediction() const override { return m_info.time_in_prediction; }
    virtual long long getSLLLookaheadOps() const override { return m_info.sll_lookahead; }
    virtual long long getLLLookaheadOps() const override { return m_info.ll_lookahead; }
    virtual long long getSLLATNTransitions() const override { return m_info.sll_atn_transitions; }
    virtual long long getLLATNTransitions() const override { return m_info.ll_atn_transitions; }
    virtual long long getLLFallback() const override { return m_info.ll_fallback; }
    virtual size_t getAmbiguityCount() const override { return m_info.ambiguity_count; }
    virtual size_t getContextSensitivityCount() const override { return m_info.context_sensitivity_count; }
    virtual size_t getErrorCount() const override { return m_info.error_count; }
    virtual size_t getPredicateEvalCount() const override { return m_info.predicate_eval_count; }
    virtual size_t getSLLMinLookahead() const override { return m_info.sll_min_lookahead; }
    virtual size_t getSLLMaxLookahead() const override { return m_info.sll_max_lookahead; }
    virtual size_t getLLMinLookahead() const override { return m_info.ll_min_lookahead; }
    virtual size_t getLLMaxLookahead() const override { return m_info.ll_max_lookahead; }
    virtual size_t getMaxLookahead() const override;

    virtual size_t getNumEvents() const override { return m_events.size(); }
    virtual IDecisionEventInfo *getEvent(size_t idx) const override;

private:
    DecisionSnapshot                m_info;
    std::vector<IDecisionEventInfo*>  m_events;
};

class ParseProfileInfo : public IParseProfileInfo {
public:
    ParseProfileInfo(const ProfileSnapshot &snapshot);
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
    virtual size_t getTokenCount() override;

private:
    // All data is extracted in the constructor from the provided snapshot
    std::vector<IDecisionProfileInfo*> m_decisions;
    std::vector<size_t> m_ll_decisions;
    long long m_total_time;
    long long m_total_sll_lookahead;
    long long m_total_ll_lookahead;
    long long m_total_sll_atn_lookahead;
    long long m_total_ll_atn_lookahead;
    long long m_total_atn_lookahead;
    size_t m_dfa_size;
    size_t m_token_count;
};

}
