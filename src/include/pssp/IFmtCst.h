/**
 * IFmtCst.h
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
#include <cstdint>
#include <memory>
#include <string>

#include "pssp/IFmtTokenStream.h"

namespace pssp {

class IFmtCstNode;

/**
 * A node in the concrete syntax tree: either a grammar rule or a token.
 *
 * "Concrete" is the operative word.  This tree is what the parser matched,
 * with nothing folded away -- the parentheses the author wrote are nodes here,
 * every branch of a ``compile if`` is present, and the order and extent of
 * everything is exactly the source's.  The abstract syntax tree is a different
 * thing built for a different purpose, and it is not a substitute: it drops
 * all three of those, each of which a source-preserving tool needs.
 */
class IFmtCstNode {
public:

    virtual ~IFmtCstNode() { }

    /** True for a grammar rule, false for a token. */
    virtual bool isRule() const = 0;

    /**
     * True for a token the parser did not expect.
     *
     * The tree is still complete when this is set -- error recovery inserts
     * or skips tokens rather than giving up -- but a consumer that rewrites
     * layout should decline to, because the structure around an error node is
     * a guess.
     */
    virtual bool isError() const = 0;

    /** Grammar rule index, or -1 for a token. */
    virtual int32_t getRuleIndex() const = 0;

    /**
     * Grammar rule name -- ``"component_declaration"``, ``"expression"`` --
     * or an empty string for a token.
     *
     * Names rather than indices are what a rule in a formatter should switch
     * on: the indices are generated and renumber whenever the grammar grows.
     */
    virtual const std::string &getRuleName() const = 0;

    /**
     * For a token, its index in the accompanying
     * :cpp:class:`IFmtTokenStream`.  -1 for a rule.
     *
     * This is the join between structure and text, and it is an index into
     * *that* stream -- trivia, error and BOM tokens included -- not into
     * ANTLR's, which counts differently.
     */
    virtual int32_t getTokenIndex() const = 0;

    virtual uint32_t getNumChildren() const = 0;

    /** The child at *idx*.  Owned by this node. */
    virtual IFmtCstNode *getChild(uint32_t idx) const = 0;

    /**
     * First token index this node spans, or -1 if it spans none.
     *
     * A rule can match nothing -- an optional clause that was absent still
     * appears as a node -- so the empty case is normal, not a failure.
     */
    virtual int32_t getStartToken() const = 0;

    /** Last token index this node spans, inclusive, or -1 if it spans none. */
    virtual int32_t getStopToken() const = 0;

};

class IFmtCst;
using IFmtCstUP=std::unique_ptr<IFmtCst>;

/**
 * A parsed source unit: the token stream and the tree over it.
 *
 * Produced by :cpp:func:`IFactory::mkCstParser`, which parses **without
 * building an AST**.  That is not an optimization, it is a requirement: AST
 * construction evaluates ``compile if`` and keeps only the winning branch, and
 * a tool that reproduces source has to see both.
 *
 * The token stream and the tree agree by construction -- every token index a
 * node reports is valid in :cpp:func:`getTokens`.
 */
class IFmtCst {
public:

    virtual ~IFmtCst() { }

    /** The complete token stream, trivia included.  Owned by this object. */
    virtual IFmtTokenStream *getTokens() = 0;

    /**
     * The root of the tree, always the ``compilation_unit`` rule.  Owned by
     * this object.  Null only if the input was not valid UTF-8, in which case
     * :cpp:func:`IFmtTokenStream::isValidUtf8` on the token stream is false.
     */
    virtual IFmtCstNode *getRoot() = 0;

    /**
     * Number of syntax errors the parser reported.
     *
     * Zero does not mean the source is *correct* -- name resolution and type
     * checking happen elsewhere and are not run here -- only that it matched
     * the grammar.
     */
    virtual uint32_t getNumSyntaxErrors() const = 0;

};

}
