/**
 * ValInt.h
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
 *
 * Created on:
 *     Author: 
 */
#pragma once
#include "pssp/IValInt.h"
#include "Val.h"

namespace pssp {




class ValInt : 
    public virtual IValInt,
    public virtual Val {
public:
    ValInt(
        bool        is_signed,
        int32_t     width,
        int64_t     init
    );

    virtual ~ValInt();

    virtual bool isSigned() const override {
        return m_is_signed;
    }

    virtual int32_t getWidth() const override {
        return m_width;
    }

    virtual void accept(IValVisitor *v) override {
        v->visitValInt(this);
    }

    virtual int64_t getValS() const override;

    virtual uint64_t getValU() const override;

private:
    bool            m_is_signed;
    int32_t         m_width;
    union {
        uint64_t        vs;
        uint64_t        *vp;
    }               m_val;

};

}
