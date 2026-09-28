/**
 * DebugInitCached.h
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
#include "dmgr/IDebugMgr.h"

/**
 * DEBUG_INIT for a class whose m_dbg is a member, not a static: the
 * header-only tasks, which are built per reference or per path step. Plain
 * DEBUG_INIT looks the scope up by name every time one is built, since the
 * member always starts null -- 7% of a link. This looks it up once per
 * class and copies it.
 */
#define DEBUG_INIT_CACHED(scope, mgr) { \
    static dmgr::IDebug *s_dbg = 0; \
    if (!s_dbg && (mgr)) { \
        s_dbg = (mgr)->findDebug(scope); \
    } \
    m_dbg = s_dbg; \
}
