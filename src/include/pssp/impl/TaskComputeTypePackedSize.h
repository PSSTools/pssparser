/**
 * TaskComputeTypePackedSize.h
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
#include "pssp/impl/TaskClassifyPackable.h"

namespace pssp {

/**
 * Packed size of a type, in bits.
 *
 * Kept for API compatibility; the answer comes from TaskClassifyPackable,
 * which is the one place packed sizes are computed. A type that is not
 * packable, or whose size is not known, reports 0 bits and incomplete().
 */
class TaskComputeTypePackedSize {
public:

    TaskComputeTypePackedSize(
        IFactory                *factory,
        ast::ISymbolScope       *root) : 
            m_classifier(factory, root), m_incomplete(false) { }

    virtual ~TaskComputeTypePackedSize() { }

    int32_t bits(ast::IDataType *t) {
        PackableInfo info = m_classifier.classify(t);
        m_incomplete = (info.kind != PackableInfo::Ok);
        return m_incomplete?0:info.bits;
    }

    /**
     * True when bits() has no exact answer: the type is not packable, or a
     * member's type or width is not known yet.
     */
    bool incomplete() const { return m_incomplete; }

private:
    TaskClassifyPackable        m_classifier;
    bool                        m_incomplete;

};

} /* namespace pssp */
