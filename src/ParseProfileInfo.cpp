/*
 * ParseProfileInfo.cpp
 *
 * Implementation of profiling data export
 */

#include "ParseProfileInfo.h"
#include "Token.h"
#include "atn/ProfilingATNSimulator.h"
#include "atn/ParserATNSimulator.h"
#include "atn/DecisionState.h"
// The event types below are only forward-declared by DecisionInfo.h.  Without
// the full definitions the compiler cannot see that each derives from
// DecisionEventInfo, and `mkEvent` will not bind to any of them.
#include "atn/AmbiguityInfo.h"
#include "atn/ContextSensitivityInfo.h"
#include "atn/ErrorInfo.h"
#include "atn/LookaheadEventInfo.h"
#include "atn/PredicateEvalInfo.h"
#include "dfa/DFA.h"
#include "misc/Interval.h"

namespace pssp {

using antlr4::atn::DecisionInfo;

namespace {

/**
 * Resolve one ANTLR profiler event to line/column and source text.
 *
 * Everything the event points at -- the token stream, the configuration set --
 * belongs to the parse.  Nothing survives here but values.
 */
DecisionEventSnapshot mkEvent(
        IDecisionEventInfo::KindE                   kind,
        const std::string                           &kind_name,
        const antlr4::atn::DecisionEventInfo        &ev) {
    DecisionEventSnapshot ret;
    ret.kind = kind;
    ret.kind_name = kind_name;

    antlr4::TokenStream *input = const_cast<antlr4::TokenStream *>(ev.input);
    if (!input) {
        return ret;
    }

    // `INVALID_INDEX` is SIZE_MAX, and a prediction that ends at EOF can leave
    // stopIndex past the buffered tokens.  Clamp rather than trust: this runs
    // over a corpus that deliberately contains invalid input, where prediction
    // ends in places valid input never reaches.
    size_t n_tokens = input->size();
    if (n_tokens == 0 || ev.startIndex >= n_tokens) {
        return ret;
    }
    size_t start = ev.startIndex;
    size_t stop = (ev.stopIndex >= n_tokens) ? (n_tokens - 1) : ev.stopIndex;
    if (stop < start) {
        stop = start;
    }

    antlr4::Token *start_tok = input->get(start);
    antlr4::Token *stop_tok = input->get(stop);
    ret.start_line = static_cast<uint32_t>(start_tok->getLine());
    ret.start_column = static_cast<uint32_t>(start_tok->getCharPositionInLine());
    ret.stop_line = static_cast<uint32_t>(stop_tok->getLine());
    ret.stop_column = static_cast<uint32_t>(stop_tok->getCharPositionInLine());
    ret.token_count = static_cast<uint32_t>(stop - start + 1);

    ret.text = input->getText(antlr4::misc::Interval(start, stop));
    if (ret.text.size() > kMaxEventTextLen) {
        ret.text = ret.text.substr(0, kMaxEventTextLen) + "...";
    }

    return ret;
}

/**
 * Copy up to `kMaxEventsPerDecision` events of one kind into `dst`.
 *
 * Takes the *first* of each kind rather than a sample: the first occurrence is
 * the one a grammar author can most easily reason about, and later ones in a
 * corpus sweep are usually the same construct in another file.
 */
template <class T> void addEvents(
        std::vector<DecisionEventSnapshot>  &dst,
        IDecisionEventInfo::KindE           kind,
        const std::string                   &kind_name,
        const std::vector<T>                &src) {
    for (const T &ev : src) {
        if (dst.size() >= kMaxEventsPerDecision) {
            break;
        }
        dst.push_back(mkEvent(kind, kind_name, ev));
    }
}

}

ProfileSnapshot mkProfileSnapshot(antlr4::Parser &parser) {
    ProfileSnapshot ret;

    antlr4::atn::ParserATNSimulator *sim =
        parser.getInterpreter<antlr4::atn::ParserATNSimulator>();
    antlr4::atn::ProfilingATNSimulator *prof =
        dynamic_cast<antlr4::atn::ProfilingATNSimulator *>(sim);

    if (!prof) {
        // Not profiling.  `Parser::getParseInfo` would hand `ParseInfo` a null
        // simulator and the first accessor would dereference it.
        return ret;
    }

    // The DFA is shared process-wide by every parser instance (the generated
    // parser holds it in static data), so this is a cumulative figure across
    // every file parsed in this process -- not the cost of this one.
    for (const antlr4::dfa::DFA &dfa : sim->decisionToDFA) {
        ret.dfa_size += dfa.states.size();
    }

    if (parser.getTokenStream()) {
        ret.token_count = parser.getTokenStream()->size();
    }

    const std::vector<std::string> &rule_names = parser.getRuleNames();
    const antlr4::atn::ATN &atn = parser.getATN();

    std::vector<DecisionInfo> decisions = parser.getParseInfo().getDecisionInfo();
    ret.decisions.reserve(decisions.size());

    for (const DecisionInfo &info : decisions) {
        DecisionSnapshot d;
        d.decision = info.decision;

        // The mapping that makes a profile actionable.  A decision is an index
        // into the ATN's decision table; the state it names carries the rule it
        // was generated from.
        d.rule_index = 0;
        if (info.decision < atn.decisionToState.size()) {
            antlr4::atn::DecisionState *state = atn.decisionToState[info.decision];
            if (state) {
                d.rule_index = state->ruleIndex;
            }
        }
        d.rule_name = (d.rule_index < rule_names.size())
            ? rule_names[d.rule_index] : std::string("<unknown>");

        d.invocations = info.invocations;
        d.time_in_prediction = info.timeInPrediction;
        d.sll_lookahead = info.SLL_TotalLook;
        d.ll_lookahead = info.LL_TotalLook;
        d.sll_atn_transitions = info.SLL_ATNTransitions;
        d.ll_atn_transitions = info.LL_ATNTransitions;
        d.ll_fallback = info.LL_Fallback;
        d.ambiguity_count = info.ambiguities.size();
        d.context_sensitivity_count = info.contextSensitivities.size();
        d.error_count = info.errors.size();
        d.predicate_eval_count = info.predicateEvals.size();
        d.sll_min_lookahead = static_cast<size_t>(info.SLL_MinLook);
        d.sll_max_lookahead = static_cast<size_t>(info.SLL_MaxLook);
        d.ll_min_lookahead = static_cast<size_t>(info.LL_MinLook);
        d.ll_max_lookahead = static_cast<size_t>(info.LL_MaxLook);

        // Ambiguities first: they are grammar defects rather than mere costs,
        // and the per-decision cap must not spend its budget on the predicate
        // evaluations of a file that happens to have many.
        addEvents(d.events, IDecisionEventInfo::KindE::Ambiguity,
            "ambiguity", info.ambiguities);
        addEvents(d.events, IDecisionEventInfo::KindE::ContextSensitivity,
            "context-sensitivity", info.contextSensitivities);

        if (info.SLL_MaxLookEvent && d.events.size() < kMaxEventsPerDecision) {
            d.events.push_back(mkEvent(IDecisionEventInfo::KindE::SLLMaxLook,
                "sll-max-look", *info.SLL_MaxLookEvent));
        }
        if (info.LL_MaxLookEvent && d.events.size() < kMaxEventsPerDecision) {
            d.events.push_back(mkEvent(IDecisionEventInfo::KindE::LLMaxLook,
                "ll-max-look", *info.LL_MaxLookEvent));
        }

        addEvents(d.events, IDecisionEventInfo::KindE::Error,
            "error", info.errors);
        addEvents(d.events, IDecisionEventInfo::KindE::PredicateEval,
            "predicate-eval", info.predicateEvals);

        ret.decisions.push_back(std::move(d));
    }

    return ret;
}

DecisionProfileInfo::DecisionProfileInfo(const DecisionSnapshot &info) : m_info(info) {
    m_events.reserve(m_info.events.size());
    for (const DecisionEventSnapshot &ev : m_info.events) {
        m_events.push_back(new DecisionEventInfo(ev));
    }
}

DecisionProfileInfo::~DecisionProfileInfo() {
    for (IDecisionEventInfo *ev : m_events) {
        delete ev;
    }
}

size_t DecisionProfileInfo::getMaxLookahead() const {
    return (m_info.ll_max_lookahead > m_info.sll_max_lookahead)
        ? m_info.ll_max_lookahead : m_info.sll_max_lookahead;
}

IDecisionEventInfo *DecisionProfileInfo::getEvent(size_t idx) const {
    return (idx < m_events.size()) ? m_events[idx] : nullptr;
}

ParseProfileInfo::ParseProfileInfo(const ProfileSnapshot &snapshot) {
    m_total_time = 0;
    m_total_sll_lookahead = 0;
    m_total_ll_lookahead = 0;
    m_total_sll_atn_lookahead = 0;
    m_total_ll_atn_lookahead = 0;
    m_dfa_size = snapshot.dfa_size;
    m_token_count = snapshot.token_count;

    for (const DecisionSnapshot &decision : snapshot.decisions) {
        m_decisions.push_back(new DecisionProfileInfo(decision));

        // Compute aggregates
        m_total_time += decision.time_in_prediction;
        m_total_sll_lookahead += decision.sll_lookahead;
        m_total_ll_lookahead += decision.ll_lookahead;
        m_total_sll_atn_lookahead += decision.sll_atn_transitions;
        m_total_ll_atn_lookahead += decision.ll_atn_transitions;

        // Track LL decisions (decisions that fell back from SLL)
        if (decision.ll_fallback > 0) {
            m_ll_decisions.push_back(decision.decision);
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

size_t ParseProfileInfo::getTokenCount() {
    return m_token_count;
}

}
