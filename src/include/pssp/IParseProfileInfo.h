/*
 * IParseProfileInfo.h
 *
 * Interfaces for exporting ANTLR profiling data to Python.
 * Provides a simplified view of ANTLR's ParseInfo structure.
 */

#pragma once
#include <string>
#include <vector>
#include <memory>

namespace pssp {


/**
 * Per-decision profiling information
 */
class IDecisionProfileInfo {
public:
    virtual ~IDecisionProfileInfo() { }

    // Decision number (index into ATN decision table)
    virtual size_t getDecision() const = 0;

    // Number of times this decision was invoked
    virtual long long getInvocations() const = 0;

    // Time spent in prediction for this decision (nanoseconds)
    virtual long long getTimeInPrediction() const = 0;

    // Number of SLL lookahead operations
    virtual long long getSLLLookaheadOps() const = 0;

    // Number of LL lookahead operations
    virtual long long getLLLookaheadOps() const = 0;

    // Number of SLL ATN transitions
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

    // Maximum lookahead depth used
    virtual size_t getMaxLookahead() const = 0;
};

using IDecisionProfileInfoUP = std::unique_ptr<IDecisionProfileInfo>;

/**
 * Aggregate profiling information for an entire parse
 */
class IParseProfileInfo {
public:
    virtual ~IParseProfileInfo() { }

    // Get all decision-level profiling information
    // Caller takes ownership of returned pointers
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

    // Total number of DFA states across all decisions
    virtual size_t getDFASize() = 0;
};

using IParseProfileInfoUP = std::unique_ptr<IParseProfileInfo>;

}
