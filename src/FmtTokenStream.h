/**
 * FmtTokenStream.h
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
#include <iterator>
#include <map>
#include <vector>

#include "pssp/IFmtTokenStream.h"

namespace pssp {

/**
 * Lexes an input stream eagerly and completely, then holds the result.
 *
 * Eager because the guarantee is about the whole file: the gap-filling that
 * makes concatenation lossless needs to see where the *next* successfully
 * lexed token starts, so there is nothing to be gained by being lazy.
 */
class FmtTokenStream : public virtual IFmtTokenStream {
public:
    FmtTokenStream(std::istream *in);

    virtual ~FmtTokenStream();

    virtual uint32_t size() const override {
        return static_cast<uint32_t>(m_tokens.size());
    }

    virtual const FmtToken &at(uint32_t idx) const override {
        return m_tokens.at(idx);
    }

    virtual const std::string &getTypeName(int32_t type) const override;

    virtual uint32_t getNumErrors() const override {
        return m_num_errors;
    }

    virtual bool isValidUtf8() const override {
        return m_valid_utf8;
    }

private:
    /** Copies the grammar's symbolic token names out of the lexer vocabulary. */
    void loadTypeNames();

    /** Lexes *body*, whose offsets are shifted by *base* code points. */
    void lex(const std::string &body, int32_t base);

    /**
     * Appends *tok*, assigning its index and advancing the line/column cursor
     * over its text.  The caller supplies ``line``/``col``, because a real
     * token takes them from ANTLR and only a synthetic one needs the cursor.
     */
    void push(FmtToken &tok);

    /** Advances m_line/m_col over *text*, counting code points. */
    void advance(const std::string &text);

private:
    std::vector<FmtToken>               m_tokens;
    std::map<int32_t,std::string>       m_type_names;
    std::string                         m_no_such_type;
    uint32_t                            m_num_errors;
    bool                                m_valid_utf8;
    int32_t                             m_line;
    int32_t                             m_col;
    /** Extra column to add to line-1 tokens when a BOM precedes them. */
    int32_t                             m_col_bias;

};

}
