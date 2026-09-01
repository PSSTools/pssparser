/*
 * IParseProfileInfo.h
 *
 * Interfaces for exporting ANTLR profiling data to Python.
 * Provides a simplified view of ANTLR's ParseInfo structure.
 */

#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <memory>

namespace pssp {


/**
 * One profiler event, resolved to a source location.
 *
 * ANTLR records these as `DecisionEventInfo`, which carries *token indices*
 * into the `TokenStream` the parse ran against, plus a raw pointer to that
 * stream.  Neither survives the parse: the stream is replaced on the next
 * `build()`, and the `ATNConfigSet` the event also points at dies with the
 * simulator.  Everything here is therefore resolved to line/column and copied
 * out while the parser is still standing -- see `AstBuilderInt::build`.
 *
 * Events are what make a hot decision *diagnosable*.  "Decision 302 is
 * ambiguous" is a scoreboard entry; "decision 302 is ambiguous at
 * std_pkg.pss:88:12, on this text" is a work order.
 */
class IDecisionEventInfo {
public:
    enum class KindE {
        /// Two or more alternatives matched.  A grammar defect, not merely a
        /// cost: ANTLR resolves it by silently taking the lowest alternative.
        Ambiguity,
        /// SLL and LL prediction disagreed; the decision needs the call stack.
        ContextSensitivity,
        /// Prediction reached a syntax error.
        Error,
        /// A semantic predicate was evaluated.
        PredicateEval,
        /// The invocation that set `getSLLMaxLookahead()`.
        SLLMaxLook,
        /// The invocation that set `getLLMaxLookahead()`.
        LLMaxLook
    };

    virtual ~IDecisionEventInfo() { }

    virtual KindE getKind() const = 0;

    /// Kind as a stable lowercase string, for reports and JSON.
    virtual const std::string &getKindName() const = 0;

    /// 1-based line of the first token of the span, 0 when unresolvable.
    virtual uint32_t getStartLine() const = 0;

    /// 0-based column of the first token of the span.
    virtual uint32_t getStartColumn() const = 0;

    /// 1-based line of the last token of the span, 0 when unresolvable.
    virtual uint32_t getStopLine() const = 0;

    /// 0-based column of the last token of the span.
    virtual uint32_t getStopColumn() const = 0;

    /// Token count spanned by the event.
    virtual uint32_t getTokenCount() const = 0;

    /// The source text of the span, truncated -- see `kMaxEventTextLen`.
    virtual const std::string &getText() const = 0;
};

/**
 * Per-decision profiling information
 */
class IDecisionProfileInfo {
public:
    virtual ~IDecisionProfileInfo() { }

    // Decision number (index into ATN decision table)
    virtual size_t getDecision() const = 0;

    // Index of the grammar rule this decision belongs to
    virtual size_t getRuleIndex() const = 0;

    // Name of the grammar rule this decision belongs to.  This is what makes
    // a profile actionable: the decision number alone names nothing a grammar
    // author can edit.
    virtual const std::string &getRuleName() const = 0;

    // Number of times this decision was invoked
    virtual long long getInvocations() const = 0;

    // Time spent in prediction for this decision (nanoseconds)
    virtual long long getTimeInPrediction() const = 0;

    // Number of SLL lookahead operations.  Counted on every invocation,
    // whether or not the DFA already had the answer, which makes it the one
    // metric here that is independent of cache warmth -- and therefore the
    // one to rank on.
    virtual long long getSLLLookaheadOps() const = 0;

    // Number of LL lookahead operations
    virtual long long getLLLookaheadOps() const = 0;

    // Number of SLL ATN transitions.  Counted only on a DFA *miss*, so this
    // measures the one-time cost of learning the decision, not its steady
    // state.  Never sum it with the lookahead counters.
    virtual long long getSLLATNTransitions() const = 0;

    // Number of LL ATN transitions
    virtual long long getLLATNTransitions() const = 0;

    // Number of times SLL prediction failed and fell back to LL
    virtual long long getLLFallback() const = 0;

    // Number of ambiguities detected
    virtual size_t getAmbiguityCount() const = 0;

    // Number of context sensitivities detected
    virtual size_t getContextSensitivityCount() const = 0;

    // Number of errors during prediction
    virtual size_t getErrorCount() const = 0;

    // Number of semantic-predicate evaluations
    virtual size_t getPredicateEvalCount() const = 0;

    // Minimum and maximum lookahead, kept apart.  A decision with min 1 and
    // max 40 has a cheap common case; one with min 38 and max 40 is uniformly
    // expensive.  Collapsing them loses exactly that distinction.
    virtual size_t getSLLMinLookahead() const = 0;
    virtual size_t getSLLMaxLookahead() const = 0;
    virtual size_t getLLMinLookahead() const = 0;
    virtual size_t getLLMaxLookahead() const = 0;

    // max(SLL_MaxLook, LL_MaxLook).  Retained for callers written against the
    // original interface; prefer the four accessors above.
    virtual size_t getMaxLookahead() const = 0;

    // Resolved profiler events for this decision.  Capped -- see
    // `kMaxEventsPerDecision`; the counts above are never capped.
    virtual size_t getNumEvents() const = 0;
    virtual IDecisionEventInfo *getEvent(size_t idx) const = 0;
};

using IDecisionProfileInfoUP = std::unique_ptr<IDecisionProfileInfo>;

/**
 * Aggregate profiling information for an entire parse
 */
class IParseProfileInfo {
public:
    virtual ~IParseProfileInfo() { }

    // Get all decision-level profiling information.  The returned pointers are
    // owned by this object and die with it.
    virtual std::vector<IDecisionProfileInfo*> getDecisionInfo() = 0;

    // Get decisions that required LL fallback
    virtual std::vector<size_t> getLLDecisions() = 0;

    // Total time spent in prediction across all decisions (nanoseconds)
    virtual long long getTotalTimeInPrediction() = 0;

    // Total SLL lookahead operations
    virtual long long getTotalSLLLookaheadOps() = 0;

    // Total LL lookahead operations
    virtual long long getTotalLLLookaheadOps() = 0;

    // Total SLL ATN lookahead operations
    virtual long long getTotalSLLATNLookaheadOps() = 0;

    // Total LL ATN lookahead operations
    virtual long long getTotalLLATNLookaheadOps() = 0;

    // Total ATN lookahead operations (SLL + LL)
    virtual long long getTotalATNLookaheadOps() = 0;

    // Total number of DFA states across every decision's DFA, as it stood at
    // the end of the parse.  Process-global and cumulative: the DFA is shared
    // by every parser instance, so this grows across files and does not reset.
    virtual size_t getDFASize() = 0;

    // Number of tokens in the parsed unit, for normalizing the counters above.
    virtual size_t getTokenCount() = 0;
};

using IParseProfileInfoUP = std::unique_ptr<IParseProfileInfo>;

}
