/*
 * CelOps.h
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
 *
 * Value operations shared by the evaluator (CelEval.cpp) and the standard
 * library (CelStdLib.cpp). Internal to the CEL engine.
 */
#pragma once
#include <cstdint>
#include <string>
#include "CelValue.h"

namespace pssp {
namespace lint {
namespace cel {

/**
 * Three-way numeric comparison across int and double; 2 means unordered
 * (NaN). The int is converted to double, lossily, as the CEL spec does.
 */
int cmpNumeric(const Value &a, const Value &b);

/** The value stored under `key` (CEL equality), or null. */
const Value *mapFind(const ValueMap &m, const Value &key);

/** Map keys the profile allows: int, bool, string. */
bool isValidMapKey(const Value &v);

}
}
}
