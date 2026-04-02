/*
 * ValInt.cpp
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
#include "ValInt.h"


namespace pssp {



ValInt::ValInt(
    bool            is_signed,
    int32_t         width,
    int64_t         init) : Val(ValKind::Int),
    m_is_signed(is_signed), m_width(width) {
    m_val.vs = init;
}

ValInt::~ValInt() {

}

int64_t ValInt::getValS() const {
    return m_val.vs;
}

uint64_t ValInt::getValU() const {
    return m_val.vs;
}

}
